from __future__ import annotations

import json
import re
import time
from html import unescape
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
SOURCE_ROOT = BACKEND_DIR / "assets" / "source-images"
SOURCE_ROOT.mkdir(parents=True, exist_ok=True)

COMMONS_HEADERS = {"User-Agent": "game-demo-bot/1.0"}
SEARCH_TERMS: dict[str, str] = {
    "cat": "cat photograph",
    "dog": "golden retriever photograph",
    "horse": "horse photograph",
    "eagle": "eagle bird photograph",
    "motorcycle": "motorcycle bike photograph",
    "bicycle": "bicycle bike photograph",
    "train": "train locomotive photograph",
    "airplane": "airliner photograph",
    "castle": "castle photograph",
    "lighthouse": "lighthouse photograph",
}


def main() -> None:
    attributions: dict[str, list[dict[str, str | None]]] = {}

    for asset_key, query in SEARCH_TERMS.items():
        print(f"下载素材：{asset_key}")
        pages = _search_commons(query)
        target_dir = SOURCE_ROOT / asset_key
        target_dir.mkdir(parents=True, exist_ok=True)
        for existing in target_dir.iterdir():
            if existing.is_file():
                existing.unlink()

        samples: list[dict[str, str | None]] = []
        for index, page in enumerate(pages[:3], start=1):
            imageinfo = page["imageinfo"][0]
            thumb_url = imageinfo.get("thumburl") or imageinfo["url"]
            suffix = Path(thumb_url).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
                suffix = ".jpg"
            destination = target_dir / f"sample-{index:02d}{suffix}"
            destination.write_bytes(_fetch_bytes(thumb_url))

            metadata = imageinfo.get("extmetadata", {})
            samples.append(
                {
                    "sample_id": f"sample-{index:02d}",
                    "title": page["title"].removeprefix("File:"),
                    "source_page": "https://commons.wikimedia.org/wiki/"
                    + page["title"].replace(" ", "_"),
                    "download_url": thumb_url,
                    "author": _strip_html(metadata.get("Artist", {}).get("value")),
                    "license": _strip_html(metadata.get("LicenseShortName", {}).get("value")),
                    "license_url": _strip_html(metadata.get("LicenseUrl", {}).get("value")),
                }
            )
            time.sleep(1.5)

        attributions[asset_key] = samples
        time.sleep(2)

    (SOURCE_ROOT / "ATTRIBUTIONS.json").write_text(
        json.dumps(attributions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已下载首批真实图片素材：{SOURCE_ROOT}")


def _search_commons(query: str) -> list[dict[str, object]]:
    url = (
        "https://commons.wikimedia.org/w/api.php?action=query&generator=search"
        f"&gsrnamespace=6&gsrsearch={quote(query)}&gsrlimit=3"
        "&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=640&format=json"
    )
    data = _fetch_json(url)
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda page: page["index"])
    if len(pages) < 3:
        raise RuntimeError(f"Commons 搜索结果不足 3 条：{query}")
    return pages


def _fetch_json(url: str) -> dict[str, object]:
    request = Request(url, headers=COMMONS_HEADERS)
    for attempt in range(6):
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code != 429 or attempt == 5:
                raise
            time.sleep(2 + attempt * 2)
    raise RuntimeError("unreachable")


def _fetch_bytes(url: str) -> bytes:
    request = Request(url, headers=COMMONS_HEADERS)
    for attempt in range(6):
        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except HTTPError as error:
            if error.code != 429 or attempt == 5:
                raise
            time.sleep(3 + attempt * 3)
    raise RuntimeError("unreachable")


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"<[^>]+>", "", value)
    cleaned = re.sub(r"\s+", " ", unescape(cleaned)).strip()
    return cleaned or None


if __name__ == "__main__":
    main()
