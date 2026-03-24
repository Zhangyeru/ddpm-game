from __future__ import annotations

import unittest

from PIL import Image

from backend.app.diffusion_trajectory import (
    DEFAULT_NEGATIVE_PROMPT,
    DiffusionTrajectoryGenerator,
    GenerationConfig,
    corruption_step_indices,
    resolve_variant_plan,
    region_mask,
)
from backend.app.frame_renderer import TRAJECTORY_VARIANTS
from backend.app.game_data import TARGETS


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_frames(self, **kwargs) -> list[Image.Image]:
        self.calls.append(kwargs)
        total_frames = kwargs["total_frames"]
        return [Image.new("RGB", (8, 8), (0, 0, 0)) for _ in range(total_frames)]


class DiffusionTrajectoryTest(unittest.TestCase):
    def test_resolve_variant_plan_uses_english_prompt_tokens(self) -> None:
        target = TARGETS[0]
        plan = resolve_variant_plan(target=target, variant=TRAJECTORY_VARIANTS["focus_living"])

        self.assertIn("cat", plan.prompt)
        self.assertIn("real-world documentary photograph", plan.prompt)
        self.assertIn("natural lighting", plan.prompt)
        self.assertIn("organic details", plan.prompt)
        self.assertEqual(plan.negative_prompt, DEFAULT_NEGATIVE_PROMPT)
        self.assertGreater(plan.guidance_scale, 1.0)
        self.assertLess(plan.inversion_guidance_scale, plan.guidance_scale)

    def test_misguided_variant_switches_to_wrong_family_prompt(self) -> None:
        target = TARGETS[0]
        plan = resolve_variant_plan(target=target, variant=TRAJECTORY_VARIANTS["misguided"])

        self.assertIn("vehicle or machine", plan.prompt)
        self.assertIn("real-world documentary photograph", plan.prompt)
        self.assertNotIn("cat", plan.prompt)

    def test_generator_passes_100_frame_config_to_backend(self) -> None:
        backend = FakeBackend()
        generator = DiffusionTrajectoryGenerator(
            GenerationConfig(num_steps=100, device="cpu"),
            backend=backend,
        )

        frames = generator.generate_variant_frames(
            image=Image.new("RGB", (16, 16), "white"),
            target=TARGETS[0],
            sample_id="sample-01",
            variant=TRAJECTORY_VARIANTS["base"],
        )

        self.assertEqual(len(frames), 100)
        self.assertEqual(backend.calls[0]["total_frames"], 100)
        self.assertEqual(backend.calls[0]["inversion_guidance_scale"], 0.0)

    def test_base_variant_keeps_source_image_as_last_frame(self) -> None:
        source = Image.new("RGB", (16, 16), "white")

        class EchoBackend:
            def generate_frames(self, **kwargs) -> list[Image.Image]:
                return [Image.new("RGB", (16, 16), "black") for _ in range(kwargs["total_frames"])]

        generator = DiffusionTrajectoryGenerator(
            GenerationConfig(num_steps=4, device="cpu"),
            backend=EchoBackend(),
        )

        frames = generator.generate_variant_frames(
            image=source,
            target=TARGETS[0],
            sample_id="sample-01",
            variant=TRAJECTORY_VARIANTS["base"],
        )

        self.assertEqual(frames[-1].tobytes(), source.tobytes())

    def test_corruption_and_region_helpers_match_100_step_plan(self) -> None:
        self.assertEqual(corruption_step_indices(100, (0.2, 0.4, 0.6, 0.8)), {19, 39, 59, 79})
        mask = region_mask("center", (10, 10))
        self.assertEqual(mask.shape, (10, 10))
        self.assertGreater(mask.sum(), 0)


if __name__ == "__main__":
    unittest.main()
