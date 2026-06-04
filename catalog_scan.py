# -*- coding: utf-8 -*-
"""扫描 static/img 下的 ch{n}_{1|2} 商品图，自动生成商品列表与分类。"""

from __future__ import annotations

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_IMG = BASE_DIR / "static" / "img"
META_PATH = BASE_DIR / "data" / "catalog_meta.json"

CH_FILE_RE = re.compile(r"^ch(\d+)_([12])\.(jpe?g|png|webp)$", re.I)
RASTER_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# 扫描目录（靠前优先；img/img 为你放实拍图的目录）
SCAN_DIRS = [
    STATIC_IMG / "img",
    STATIC_IMG / "caps",
]

# 无 meta 时按商品序号默认分类（与原先 ch1～ch7 一致）
DEFAULT_CATEGORY_BY_CH: dict[int, str] = {
    1: "zan",
    2: "zan",
    3: "zan",
    4: "zan",
    5: "zhonggong",
    6: "miaoyin",
    7: "miaoyin",
}

# 内置展示文案（可被 catalog_meta.json 覆盖）
BUILTIN_META: dict[str, dict] = {
    "ch1": {
        "name": "春晓繁花",
        "category_id": "zan",
        "desc": "春日繁花簪花，层次饱满温柔出片",
        "tags": ["热销", "店长推荐"],
        "monthly_sales": 186,
        "total": 1,
    },
    "ch2": {
        "name": "蓝凰展翼",
        "category_id": "zan",
        "desc": "蓝调凰羽展翼造型，清冷又上镜",
        "tags": ["必租"],
        "monthly_sales": 142,
        "total": 1,
    },
    "ch3": {
        "name": "银鹤凌霄",
        "category_id": "zan",
        "desc": "银鹤凌空点缀，仙气学院感",
        "tags": ["上新"],
        "monthly_sales": 96,
        "total": 1,
    },
    "ch4": {
        "name": "流碧修竹",
        "category_id": "zan",
        "desc": "碧色竹韵流苏，清爽雅致",
        "tags": ["清新"],
        "monthly_sales": 131,
        "total": 1,
    },
    "ch5": {
        "name": "冷月皎翼",
        "category_id": "zhonggong",
        "desc": "冷月银饰与皎翼层次，重工仪式感",
        "tags": ["重工"],
        "monthly_sales": 118,
        "total": 1,
    },
    "ch6": {
        "name": "银丝松蝶",
        "category_id": "miaoyin",
        "desc": "苗银丝线与松蝶细节，民族风十足",
        "tags": ["民族风"],
        "monthly_sales": 104,
        "total": 1,
    },
    "ch7": {
        "name": "暮紫流苏",
        "category_id": "miaoyin",
        "desc": "暮紫色调流苏银饰，行走有韵味",
        "tags": ["出片"],
        "monthly_sales": 88,
        "total": 1,
    },
}


def load_catalog_meta() -> dict[str, dict]:
    if not META_PATH.is_file():
        return dict(BUILTIN_META)
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        merged = dict(BUILTIN_META)
        for key, val in (raw.get("products") or {}).items():
            if isinstance(val, dict):
                merged[str(key)] = {**merged.get(str(key), {}), **val}
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(BUILTIN_META)


def _rel_from_static(path: Path) -> str:
    rel = path.relative_to(BASE_DIR / "static")
    return rel.as_posix()


def _category_from_parent(parent_name: str, valid_ids: set[str]) -> str | None:
    if parent_name in valid_ids:
        return parent_name
    return None


def discover_ch_image_groups(valid_category_ids: set[str]) -> dict[int, dict[int, dict]]:
    """ch 编号 -> 图位 1|2 -> {rel, category_id?}"""
    groups: dict[int, dict[int, dict]] = {}
    for scan_dir in SCAN_DIRS:
        if not scan_dir.is_dir():
            continue
        for path in scan_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in RASTER_EXTS:
                continue
            if "_cache" in path.parts or path.name == "fengye.png":
                continue
            m = CH_FILE_RE.match(path.name)
            if not m:
                continue
            ch_num = int(m.group(1))
            slot = int(m.group(2))
            parent_cat = _category_from_parent(path.parent.name, valid_category_ids)
            rel = _rel_from_static(path)
            bucket = groups.setdefault(ch_num, {})
            if slot not in bucket or scan_dir == SCAN_DIRS[0]:
                bucket[slot] = {"rel": rel, "category_id": parent_cat}
    return groups


def _default_category(ch_num: int, index: int, category_ids: list[str]) -> str:
    if ch_num in DEFAULT_CATEGORY_BY_CH:
        return DEFAULT_CATEGORY_BY_CH[ch_num]
    if category_ids:
        return category_ids[index % len(category_ids)]
    return "zan"


def build_catalog_from_images(
    categories: list[dict],
    totals: dict[str, object] | None = None,
) -> list[dict]:
    totals = totals or {}
    cat_ids = {c["id"] for c in categories}
    cat_names = {c["id"]: c["name"] for c in categories}
    cat_id_list = [c["id"] for c in categories]
    meta_map = load_catalog_meta()
    groups = discover_ch_image_groups(cat_ids)

    if not groups:
        return []

    products: list[dict] = []
    for index, ch_num in enumerate(sorted(groups.keys())):
        slots = groups[ch_num]
        photo_key = f"ch{ch_num}"
        meta = meta_map.get(photo_key, {})
        rel1 = slots.get(1, {}).get("rel")
        rel2 = slots.get(2, {}).get("rel") or rel1
        if not rel1:
            continue
        folder_cat = slots.get(1, {}).get("category_id") or slots.get(2, {}).get("category_id")
        category_id = (
            meta.get("category_id")
            or folder_cat
            or _default_category(ch_num, index, cat_id_list)
        )
        if category_id not in cat_ids:
            category_id = cat_id_list[0] if cat_id_list else "zan"

        pid = f"r{index + 1:02d}"
        name = meta.get("name") or f"{cat_names.get(category_id, '款式')}·{ch_num}"
        prod = {
            "id": pid,
            "photo_key": photo_key,
            "name": name,
            "type": "rental",
            "category_id": category_id,
            "image": rel1,
            "image_2": rel2,
            "desc": meta.get("desc") or f"{name}，欢迎预约租借。",
            "tags": list(meta.get("tags") or []),
            "monthly_sales": int(meta.get("monthly_sales") or 0),
            "total": int(meta.get("total") or 1),
        }
        if pid in totals and totals[pid] is not None:
            try:
                prod["total"] = int(totals[pid])  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
        elif photo_key in totals and totals[photo_key] is not None:
            try:
                prod["total"] = int(totals[photo_key])  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
        products.append(prod)
    return products


def save_catalog_meta_template(products: list[dict]) -> None:
    """根据当前扫描结果更新 catalog_meta.json（仅补充缺失项）。"""
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {"products": {}}
    if META_PATH.is_file():
        try:
            with open(META_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {"products": {}}
    bucket = existing.setdefault("products", {})
    for p in products:
        key = p.get("photo_key") or p["id"]
        if key not in bucket:
            bucket[key] = {
                "name": p["name"],
                "category_id": p["category_id"],
                "desc": p.get("desc", ""),
                "tags": p.get("tags", []),
                "total": p.get("total", 1),
            }
    existing["_help"] = (
        "在此填写商品名称与分类。图片文件名须为 ch1_1.jpg、ch1_2.jpg（放在 static/img/img/）。"
        "category_id 可选：zan, miaoyin, chouxiang, zhonggong。也可建子文件夹如 static/img/img/zan/ch1_1.jpg"
    )
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
