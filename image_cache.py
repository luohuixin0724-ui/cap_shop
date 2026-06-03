# -*- coding: utf-8 -*-
"""商品图缩略图/中图缓存，加快列表与详情加载。"""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

IMAGE_SIZE_PRESETS = {
    "thumb": 240,
    "medium": 800,
    "welcome": 1080,
}

RASTER_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def is_raster_path(rel: str) -> bool:
    return Path(rel).suffix.lower() in RASTER_EXTS


def _open_image(src: Path):
    from PIL import Image

    img = Image.open(src)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _resize_to_width(img, max_width: int):
    from PIL import Image

    w, h = img.size
    if w <= max_width:
        return img
    nh = max(1, int(h * max_width / w))
    return img.resize((max_width, nh), Image.Resampling.LANCZOS)


def ensure_optimized(rel_path: str, size: str = "medium") -> str | None:
    """生成或读取缓存图，返回 /static/... URL。"""
    rel = rel_path.lstrip("/").replace("\\", "/")
    src = STATIC_DIR / rel
    if not src.is_file():
        return None
    if src.suffix.lower() not in RASTER_EXTS:
        return f"/static/{rel}"

    max_w = IMAGE_SIZE_PRESETS.get(size, IMAGE_SIZE_PRESETS["medium"])
    cache_rel = str(Path(f"img/_cache/{size}") / Path(rel).with_suffix(".jpg")).replace("\\", "/")
    cache_path = STATIC_DIR / cache_rel
    try:
        if cache_path.is_file() and cache_path.stat().st_mtime >= src.stat().st_mtime:
            return f"/static/{cache_rel.replace(chr(92), '/')}"
    except OSError:
        pass

    try:
        img = _open_image(src)
        img = _resize_to_width(img, max_w)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(cache_path, "JPEG", quality=82, optimize=True)
        return f"/static/{cache_rel.replace(chr(92), '/')}"
    except Exception:
        return f"/static/{rel}"


def attach_image_variants(row: dict, rel: str | None, base_key: str = "image") -> None:
    if not rel:
        return
    thumb = ensure_optimized(rel, "thumb") or f"/static/{rel}"
    medium = ensure_optimized(rel, "medium") or thumb
    full = f"/static/{rel.lstrip('/')}"
    row[base_key] = thumb
    row[f"{base_key}_medium"] = medium
    row[f"{base_key}_full"] = full


def warm_catalog_images(product_defs: list[dict], extra_paths: list[str] | None = None) -> None:
    seen: set[str] = set()
    for p in product_defs:
        for key in ("image", "image_2"):
            rel = p.get(key)
            if not rel or rel in seen:
                continue
            seen.add(rel)
            ensure_optimized(rel, "thumb")
            ensure_optimized(rel, "medium")
    for rel in extra_paths or []:
        if rel and rel not in seen:
            ensure_optimized(rel, "welcome")
