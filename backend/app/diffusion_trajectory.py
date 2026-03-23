from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from PIL import Image

from .frame_renderer import DEFAULT_MODEL_ID, DEFAULT_TOTAL_FRAMES, TrajectoryVariant
from .game_data import TargetDefinition


DEFAULT_NEGATIVE_PROMPT = (
    "low quality, blurry, distorted, abstract, illustration, painting, extra limbs, mutated"
)
WRONG_FAMILY_SUBJECTS: dict[str, str] = {
    "living": "vehicle or machine",
    "machine": "animal",
    "structure": "animal",
}


@dataclass(frozen=True)
class GenerationConfig:
    model_id: str = DEFAULT_MODEL_ID
    num_steps: int = DEFAULT_TOTAL_FRAMES
    device: str = "auto"


class DiffusionBackend(Protocol):
    def generate_frames(
        self,
        *,
        image: Image.Image,
        prompt: str,
        negative_prompt: str,
        inversion_guidance_scale: float,
        guidance_scale: float,
        total_frames: int,
        seed: int,
        frozen_region: str | None,
        reference_lead_steps: int,
        corruption_noise_scale: float,
        corruption_noise_points: tuple[float, ...],
    ) -> list[Image.Image]:
        ...


class DiffusionDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class VariantGenerationPlan:
    prompt: str
    negative_prompt: str
    inversion_guidance_scale: float
    guidance_scale: float
    frozen_region: str | None
    reference_lead_steps: int
    corruption_noise_scale: float
    corruption_noise_points: tuple[float, ...]


class DiffusionTrajectoryGenerator:
    def __init__(
        self,
        config: GenerationConfig | None = None,
        backend: DiffusionBackend | None = None,
    ) -> None:
        self.config = config or GenerationConfig()
        self.backend = backend or DiffusersDDIMBackend(self.config)

    def generate_variant_frames(
        self,
        *,
        image: Image.Image,
        target: TargetDefinition,
        sample_id: str,
        variant: TrajectoryVariant,
    ) -> list[Image.Image]:
        plan = resolve_variant_plan(target=target, variant=variant)
        frames = self.backend.generate_frames(
            image=image,
            prompt=plan.prompt,
            negative_prompt=plan.negative_prompt,
            inversion_guidance_scale=plan.inversion_guidance_scale,
            guidance_scale=plan.guidance_scale,
            total_frames=self.config.num_steps,
            seed=stable_seed(target.asset_key, sample_id, variant.key),
            frozen_region=plan.frozen_region,
            reference_lead_steps=plan.reference_lead_steps,
            corruption_noise_scale=plan.corruption_noise_scale,
            corruption_noise_points=plan.corruption_noise_points,
        )
        if frames:
            frames[-1] = image.copy()
        return frames


def resolve_variant_plan(
    *,
    target: TargetDefinition,
    variant: TrajectoryVariant,
) -> VariantGenerationPlan:
    subject = target.prompt_token
    if variant.wrong_family:
        subject = WRONG_FAMILY_SUBJECTS[target.family]

    prompt_segments = [f"a high quality photo of {subject}"]
    if variant.prompt_suffix:
        prompt_segments.append(variant.prompt_suffix)

    return VariantGenerationPlan(
        prompt=", ".join(prompt_segments),
        negative_prompt=variant.negative_prompt or DEFAULT_NEGATIVE_PROMPT,
        inversion_guidance_scale=variant.inversion_guidance_scale,
        guidance_scale=variant.guidance_scale,
        frozen_region=variant.frozen_region,
        reference_lead_steps=variant.reference_lead_steps,
        corruption_noise_scale=variant.corruption_noise_scale,
        corruption_noise_points=variant.corruption_noise_points,
    )


def corruption_step_indices(total_frames: int, points: tuple[float, ...]) -> set[int]:
    last_index = max(0, total_frames - 1)
    return {
        max(0, min(last_index, int(last_index * point)))
        for point in points
    }


def stable_seed(*parts: object) -> int:
    import hashlib

    payload = "::".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def region_mask(region: str, size: tuple[int, int]) -> np.ndarray:
    width, height = size
    mask = np.zeros((height, width), dtype=np.float32)
    if region == "upper-left":
        mask[: int(height * 0.56), : int(width * 0.56)] = 1.0
    elif region == "lower-right":
        mask[int(height * 0.44) :, int(width * 0.44) :] = 1.0
    else:
        mask[int(height * 0.22) : int(height * 0.78), int(width * 0.22) : int(width * 0.78)] = 1.0
    return mask


class DiffusersDDIMBackend:
    def __init__(self, config: GenerationConfig) -> None:
        self.config = config
        try:
            import torch
            from diffusers import DDIMInverseScheduler, DDIMScheduler, StableDiffusionPipeline
        except ImportError as error:
            raise DiffusionDependencyError(
                "缺少真实扩散生成依赖，请安装 diffusers / transformers / accelerate / safetensors。"
            ) from error

        self.torch = torch
        self.DDIMScheduler = DDIMScheduler
        self.DDIMInverseScheduler = DDIMInverseScheduler
        self.device = self._resolve_device(config.device, torch)
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32

        self.pipeline = StableDiffusionPipeline.from_pretrained(
            config.model_id,
            torch_dtype=self.dtype,
            safety_checker=None,
            requires_safety_checker=False,
        )
        self.pipeline.scheduler = DDIMScheduler.from_config(self.pipeline.scheduler.config)
        self.pipeline.to(self.device)
        self.pipeline.set_progress_bar_config(disable=True)

    def generate_frames(
        self,
        *,
        image: Image.Image,
        prompt: str,
        negative_prompt: str,
        inversion_guidance_scale: float,
        guidance_scale: float,
        total_frames: int,
        seed: int,
        frozen_region: str | None,
        reference_lead_steps: int,
        corruption_noise_scale: float,
        corruption_noise_points: tuple[float, ...],
    ) -> list[Image.Image]:
        prompt_embeds, negative_prompt_embeds = self._encode_prompt(prompt, negative_prompt)
        clean_latents = self._encode_image(image)
        inverse_latents = self._invert(
            latents=clean_latents,
            prompt_embeds=prompt_embeds,
            negative_prompt_embeds=negative_prompt_embeds,
            guidance_scale=inversion_guidance_scale,
            total_frames=total_frames,
        )
        reverse_latents = self._reverse_denoise(
            noisy_latents=inverse_latents[-1],
            prompt_embeds=prompt_embeds,
            negative_prompt_embeds=negative_prompt_embeds,
            guidance_scale=guidance_scale,
            total_frames=total_frames,
            seed=seed,
            corruption_noise_scale=corruption_noise_scale,
            corruption_noise_points=corruption_noise_points,
        )

        if frozen_region is not None and reference_lead_steps > 0:
            reverse_latents = self._apply_frozen_region(
                reverse_latents=reverse_latents,
                frozen_region=frozen_region,
                reference_lead_steps=reference_lead_steps,
            )

        return [self._decode_latents(latents) for latents in reverse_latents]

    def _encode_prompt(self, prompt: str, negative_prompt: str):
        tokenizer = self.pipeline.tokenizer
        text_encoder = self.pipeline.text_encoder
        prompt_inputs = tokenizer(
            [prompt],
            padding="max_length",
            max_length=tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt",
        )
        negative_inputs = tokenizer(
            [negative_prompt],
            padding="max_length",
            max_length=tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt",
        )

        prompt_embeds = text_encoder(prompt_inputs.input_ids.to(self.device))[0]
        negative_prompt_embeds = text_encoder(negative_inputs.input_ids.to(self.device))[0]
        return prompt_embeds, negative_prompt_embeds

    def _encode_image(self, image: Image.Image):
        image_array = np.asarray(image, dtype=np.float32) / 255.0
        image_tensor = self.torch.from_numpy(image_array).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.to(device=self.device, dtype=self.dtype)
        image_tensor = image_tensor * 2.0 - 1.0
        with self.torch.inference_mode():
            latents = self.pipeline.vae.encode(image_tensor).latent_dist.mode()
        return latents * self.pipeline.vae.config.scaling_factor

    def _invert(
        self,
        *,
        latents,
        prompt_embeds,
        negative_prompt_embeds,
        guidance_scale: float,
        total_frames: int,
    ):
        scheduler = self.DDIMInverseScheduler.from_config(self.pipeline.scheduler.config)
        scheduler.set_timesteps(total_frames, device=self.device)
        current = latents
        history = [current.clone()]

        with self.torch.inference_mode():
            for timestep in scheduler.timesteps:
                noise_pred = self._guided_noise_prediction(
                    latents=current,
                    timestep=timestep,
                    prompt_embeds=prompt_embeds,
                    negative_prompt_embeds=negative_prompt_embeds,
                    guidance_scale=guidance_scale,
                )
                current = scheduler.step(noise_pred, timestep, current).prev_sample
                history.append(current.clone())
        return history

    def _reverse_denoise(
        self,
        *,
        noisy_latents,
        prompt_embeds,
        negative_prompt_embeds,
        guidance_scale: float,
        total_frames: int,
        seed: int,
        corruption_noise_scale: float,
        corruption_noise_points: tuple[float, ...],
    ):
        scheduler = self.DDIMScheduler.from_config(self.pipeline.scheduler.config)
        scheduler.set_timesteps(total_frames, device=self.device)
        noise_steps = corruption_step_indices(total_frames, corruption_noise_points)
        generator = self.torch.Generator(device=self.device)
        generator.manual_seed(seed)

        current = noisy_latents.clone()
        history = []
        with self.torch.inference_mode():
            for index, timestep in enumerate(scheduler.timesteps):
                noise_pred = self._guided_noise_prediction(
                    latents=current,
                    timestep=timestep,
                    prompt_embeds=prompt_embeds,
                    negative_prompt_embeds=negative_prompt_embeds,
                    guidance_scale=guidance_scale,
                )
                current = scheduler.step(noise_pred, timestep, current).prev_sample
                if corruption_noise_scale > 0 and index in noise_steps:
                    current = current + (
                        self.torch.randn_like(current, generator=generator) * corruption_noise_scale
                    )
                history.append(current.clone())
        return history

    def _apply_frozen_region(
        self,
        *,
        reverse_latents,
        frozen_region: str,
        reference_lead_steps: int,
    ):
        height = reverse_latents[0].shape[-2]
        width = reverse_latents[0].shape[-1]
        mask = region_mask(frozen_region, (width, height))
        mask_tensor = self.torch.from_numpy(mask).to(device=self.device, dtype=self.dtype)
        mask_tensor = mask_tensor.unsqueeze(0).unsqueeze(0)

        blended = []
        for index, latents in enumerate(reverse_latents):
            reference_index = min(len(reverse_latents) - 1, index + reference_lead_steps)
            reference_latents = reverse_latents[reference_index]
            blended.append((latents * (1.0 - mask_tensor)) + (reference_latents * mask_tensor))
        return blended

    def _guided_noise_prediction(
        self,
        *,
        latents,
        timestep,
        prompt_embeds,
        negative_prompt_embeds,
        guidance_scale: float,
    ):
        latent_model_input = self.torch.cat([latents, latents], dim=0)
        encoder_hidden_states = self.torch.cat([negative_prompt_embeds, prompt_embeds], dim=0)
        noise_pred = self.pipeline.unet(
            latent_model_input,
            timestep,
            encoder_hidden_states=encoder_hidden_states,
        ).sample
        noise_pred_uncond, noise_pred_text = noise_pred.chunk(2)
        return noise_pred_uncond + guidance_scale * (noise_pred_text - noise_pred_uncond)

    def _decode_latents(self, latents) -> Image.Image:
        with self.torch.inference_mode():
            decoded = self.pipeline.vae.decode(
                latents / self.pipeline.vae.config.scaling_factor
            ).sample
        decoded = (decoded / 2 + 0.5).clamp(0, 1)
        image_array = decoded[0].permute(1, 2, 0).detach().cpu().numpy()
        image_array = (image_array * 255).round().astype("uint8")
        return Image.fromarray(image_array)

    def _resolve_device(self, requested: str, torch_module):
        if requested == "auto":
            return torch_module.device("cuda" if torch_module.cuda.is_available() else "cpu")
        return torch_module.device(requested)
