# -*- coding: utf-8 -*-
"""山竹小姐の学士帽 — Flask 预定平台"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

def _beijing_tz():
    try:
        import tzdata  # noqa: F401 — Windows 上 ZoneInfo 依赖此包

        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Shanghai")
    except Exception:
        return timezone(timedelta(hours=8))

from functools import wraps

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "store.json"

from image_cache import (
    attach_image_variants,
    ensure_optimized,
    is_raster_path,
    warm_catalog_images,
)

# 全站时间以北京时间（东八区 / Asia/Shanghai）为准
BEIJING_TZ = _beijing_tz()
BEIJING_TZ_LABEL = "北京时间"

RENT_PER_DAY = 20
DEPOSIT_PER_UNIT = 30

SHOP_NAME = "花枝鼠の学士帽"
SHOP_ADDRESS = "每天10:00配送至宿舍楼下，可自取"
SHOP_NOTICE = "租借为实物档期制：支付后锁定排期。"

# 进站导览图（放于 static/img/fengye.png）
FENGYE_IMAGE = "img/fengye.png"

# 商家账单：在「我的」页弹窗登录；部署请改 ADMIN_USERNAME / ADMIN_PASSWORD
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "shopowner")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "cap-shop-admin-2026")


def normalize_admin_slug(raw: str | None) -> str:
    s = (raw or "admin").strip().strip("/")
    s = re.sub(r"[^a-zA-Z0-9_-]", "", s)
    return s or "admin"


ADMIN_SLUG = normalize_admin_slug(os.environ.get("ADMIN_PATH", "admin"))

STATUS_LABELS = {
    "pending_payment": "待付款",
    "paid": "已付款",
    "cancelled": "已取消",
}

ADMIN_STATUS_OPTIONS = [
    ("pending_payment", "待付款"),
    ("paid", "已付款"),
    ("cancelled", "已取消"),
]

CATEGORIES = [
    {"id": "zan", "name": "簪花款"},
    {"id": "miaoyin", "name": "苗银款"},
    {"id": "chouxiang", "name": "抽象款"},
    {"id": "zhonggong", "name": "重工款"},
]

DEFAULT_PRODUCTS = [
    {
        "id": "r01",
        "name": "春野粉簪",
        "type": "rental",
        "category_id": "zan",
        "image": "img/caps/ch1_1.jpg",
        "image_2": "img/caps/ch1_2.jpg",
        "desc": "侧簪层次丰富，粉调温柔出片",
        "tags": ["热销", "店长推荐"],
        "monthly_sales": 186,
        "total": 25,
    },
    {
        "id": "r02",
        "name": "铃兰垂丝",
        "type": "rental",
        "category_id": "zan",
        "image": "img/caps/ch2_1.jpg",
        "image_2": "img/caps/ch2_2.jpg",
        "desc": "垂坠铃兰造型，清新学院感",
        "tags": ["必租"],
        "monthly_sales": 142,
        "total": 20,
    },
    {
        "id": "r03",
        "name": "山茶绣球",
        "type": "rental",
        "category_id": "zan",
        "image": "img/caps/ch3_1.jpg",
        "image_2": "img/caps/ch3_2.jpg",
        "desc": "围边山茶 + 绣球体量感",
        "tags": ["上新"],
        "monthly_sales": 96,
        "total": 18,
    },
    {
        "id": "r04",
        "name": "银铃叮当",
        "type": "rental",
        "category_id": "miaoyin",
        "image": "img/caps/ch4_1.jpg",
        "image_2": "img/caps/ch4_2.jpg",
        "desc": "苗银流苏细节，行走有轻响",
        "tags": ["民族风"],
        "monthly_sales": 131,
        "total": 22,
    },
    {
        "id": "r05",
        "name": "孔雀碧羽",
        "type": "rental",
        "category_id": "miaoyin",
        "image": "img/caps/ch5_1.jpg",
        "image_2": "img/caps/ch5_2.jpg",
        "desc": "碧色羽饰 + 银饰层次",
        "tags": ["出片"],
        "monthly_sales": 118,
        "total": 18,
    },
    {
        "id": "r06",
        "name": "红瑙璎珞",
        "type": "rental",
        "category_id": "miaoyin",
        "image": "img/caps/ch6_1.jpg",
        "image_2": "img/caps/ch6_2.jpg",
        "desc": "玛瑙红珠璎珞，气场更足",
        "tags": ["重工银饰"],
        "monthly_sales": 104,
        "total": 16,
    },
    {
        "id": "r07",
        "name": "水墨雾面",
        "type": "rental",
        "category_id": "chouxiang",
        "image": "img/caps/ch7_1.jpg",
        "image_2": "img/caps/ch7_2.jpg",
        "desc": "黑白渐变雾面，像画里走出来",
        "tags": ["艺术感"],
        "monthly_sales": 88,
        "total": 20,
    },
    {
        "id": "r08",
        "name": "霓虹线条",
        "type": "rental",
        "category_id": "chouxiang",
        "image": "img/caps/r08.svg",
        "desc": "夜色霓虹线条，酷感毕业照",
        "tags": ["小众"],
        "monthly_sales": 76,
        "total": 14,
    },
    {
        "id": "r09",
        "name": "珍珠蕾丝冠冕",
        "type": "rental",
        "category_id": "zhonggong",
        "image": "img/caps/r09.svg",
        "desc": "蕾丝 + 珍珠排列，仪式感拉满",
        "tags": ["婚礼感"],
        "monthly_sales": 67,
        "total": 12,
    },
    {
        "id": "r10",
        "name": "水晶流苏城堡",
        "type": "rental",
        "category_id": "zhonggong",
        "image": "img/caps/r10.svg",
        "desc": "水晶折射 + 流苏层次，灯光下很闪",
        "tags": ["限量"],
        "monthly_sales": 54,
        "total": 10,
    },
]


def ensure_dirs() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)


def beijing_now() -> datetime:
    return datetime.now(BEIJING_TZ)


def beijing_today() -> date:
    return beijing_now().date()


def beijing_now_iso() -> str:
    return beijing_now().replace(microsecond=0).isoformat(timespec="seconds")


def parse_created_at(value: str | None) -> datetime | None:
    """解析订单时间；无偏移的历史数据按已是北京时间处理。"""
    if not value:
        return None
    raw = str(value).strip()
    try:
        normalized = raw.replace("Z", "+00:00")
        if "T" not in normalized and " " in normalized:
            normalized = normalized.replace(" ", "T", 1)
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=BEIJING_TZ)
        return dt.astimezone(BEIJING_TZ)
    except ValueError:
        return None


def format_beijing_time(value: str | None) -> str:
    """将 ISO 时间格式化为北京时间显示。"""
    dt = parse_created_at(value)
    if dt is None:
        return str(value or "").strip()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def beijing_time_payload() -> dict:
    now = beijing_now()
    return {
        "timezone": "Asia/Shanghai",
        "label": BEIJING_TZ_LABEL,
        "now": beijing_now_iso(),
        "today": beijing_today().isoformat(),
        "utc_offset": now.strftime("%z"),
    }


def static_image_exists(rel_path: str) -> bool:
    return (BASE_DIR / "static" / rel_path).is_file()


def static_image_href(rel_path: str) -> str:
    return f"/static/{rel_path.lstrip('/')}"


def static_fallback_href(product_id: str) -> str:
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".svg"):
        rel = f"img/caps/{product_id}{ext}"
        if static_image_exists(rel):
            return static_image_href(rel)
    return static_image_href(f"img/caps/{product_id}.svg")


def enrich_product_images(prod: dict) -> dict:
    row = dict(prod)
    if row.get("image_medium"):
        return row
    pid = str(row["id"])
    img1 = row.get("image") or f"img/caps/{pid}.svg"
    img2 = row.get("image_2") or img1
    if is_raster_path(img1) and static_image_exists(img1):
        attach_image_variants(row, img1, "image")
    else:
        href = static_image_href(img1) if static_image_exists(img1) else static_fallback_href(pid)
        row["image"] = row["image_medium"] = row["image_full"] = href
    if img2 != img1 and is_raster_path(img2) and static_image_exists(img2):
        attach_image_variants(row, img2, "image_2")
    elif img2 != img1 and static_image_exists(img2):
        href2 = static_image_href(img2)
        row["image_2"] = row["image_2_medium"] = row["image_2_full"] = href2
    else:
        row["image_2"] = row.get("image_2", row["image"])
        row["image_2_medium"] = row.get("image_2_medium", row["image_medium"])
        row["image_2_full"] = row.get("image_2_full", row["image_full"])
    return row


def merge_catalog_from_totals(totals: dict[str, object]) -> list[dict]:
    out: list[dict] = []
    for d in DEFAULT_PRODUCTS:
        row = enrich_product_images(dict(d))
        tid = str(d["id"])
        if tid in totals and totals[tid] is not None:
            try:
                row["total"] = int(totals[tid])  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
        out.append(row)
    return out


def get_rental_product(store: dict, pid: str) -> dict | None:
    prod = next((p for p in store["products"] if p["id"] == pid), None)
    if not prod or prod.get("type") != "rental":
        return None
    return enrich_product_images(prod)


def product_gallery_items(prod: dict) -> list[dict]:
    items: list[dict] = []
    for suffix in ("", "_2"):
        medium = prod.get(f"image{suffix}_medium") or prod.get(f"image{suffix}")
        full = prod.get(f"image{suffix}_full") or medium
        if medium and not any(x["medium"] == medium for x in items):
            items.append({"medium": str(medium), "full": str(full)})
    if not items:
        fb = static_fallback_href(str(prod["id"]))
        items.append({"medium": fb, "full": fb})
    return items


def welcome_image_href() -> str | None:
    if not static_image_exists(FENGYE_IMAGE):
        return None
    return ensure_optimized(FENGYE_IMAGE, "welcome") or static_image_href(FENGYE_IMAGE)


def load_store() -> dict:
    ensure_dirs()
    if not DATA_PATH.exists():
        store = {"bookings": [], "products": merge_catalog_from_totals({})}
        save_store(store)
        return store
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    bookings = raw.get("bookings", [])
    totals: dict[str, object] = {}
    for p in raw.get("products", []) or []:
        pid = p.get("id")
        if pid is not None:
            totals[str(pid)] = p.get("total")
    return {"bookings": bookings, "products": merge_catalog_from_totals(totals)}


def save_store(store: dict) -> None:
    ensure_dirs()
    tmp = DATA_PATH.with_suffix(".tmp")
    payload = {"bookings": store.get("bookings", []), "products": store.get("products", [])}
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(DATA_PATH)


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def max_overlap_usage(
    product_id: str, start: date, end: date, bookings: list, ignore_id: str | None = None
) -> int:
    peak = 0
    for d in daterange(start, end):
        used = 0
        for b in bookings:
            if b.get("id") == ignore_id:
                continue
            if b.get("product_id") != product_id:
                continue
            if b.get("status") == "cancelled":
                continue
            if b.get("kind") != "rental":
                continue
            bs = parse_date(b.get("start_date"))
            be = parse_date(b.get("end_date"))
            if not bs or not be:
                continue
            if bs <= d <= be:
                used += int(b.get("quantity") or 1)
        peak = max(peak, used)
    return peak


def max_cart_overlap(
    cart: list, product_id: str, start: date, end: date, ignore_cart_id: str | None = None
) -> int:
    peak = 0
    for d in daterange(start, end):
        used = 0
        for item in cart:
            if item.get("cart_id") == ignore_cart_id:
                continue
            if item.get("product_id") != product_id:
                continue
            bs = parse_date(item.get("start_date"))
            be = parse_date(item.get("end_date"))
            if not bs or not be:
                continue
            if bs <= d <= be:
                used += int(item.get("quantity") or 1)
        peak = max(peak, used)
    return peak


def rental_available(
    product: dict,
    bookings: list,
    start: date,
    end: date,
    qty: int,
    cart: list | None = None,
    ignore_cart_id: str | None = None,
) -> bool:
    total = int(product.get("total") or 0)
    if total <= 0:
        return False
    peak = max_overlap_usage(product["id"], start, end, bookings)
    if cart:
        peak += max_cart_overlap(cart, product["id"], start, end, ignore_cart_id)
    return peak + qty <= total


def get_cart() -> list:
    cart = session.get("cart")
    return cart if isinstance(cart, list) else []


def save_cart(cart: list) -> None:
    session["cart"] = cart
    session.modified = True


def cart_count() -> int:
    return len(get_cart())


def cart_totals(cart: list) -> dict:
    rent = sum(int(i.get("rent_yuan") or 0) for i in cart)
    deposit = sum(int(i.get("deposit_yuan") or 0) for i in cart)
    return {"rent": rent, "deposit": deposit, "total": rent + deposit, "items": len(cart)}


def parse_rental_form() -> dict:
    try:
        qty = int(request.form.get("quantity") or "1")
    except ValueError:
        qty = 0
    return {
        "product_id": request.form.get("product_id", "").strip(),
        "start": parse_date(request.form.get("start_date")),
        "end": parse_date(request.form.get("end_date")),
        "qty": qty,
        "customer_name": request.form.get("customer_name", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "address": request.form.get("address", "").strip(),
        "location_note": request.form.get("location_note", "").strip(),
        "action": request.form.get("action", "checkout").strip(),
    }


def validate_rental_fields(
    start: date | None, end: date | None, qty: int
) -> str | None:
    if not start or not end or end < start:
        return "请选择有效的起止日期。"
    if start < beijing_today():
        return f"租借开始不能早于今天（{BEIJING_TZ_LABEL}）。"
    if qty < 1 or qty > 10:
        return "数量应在 1～10 顶之间。"
    return None


def build_cart_line(prod: dict, start: date, end: date, qty: int) -> dict:
    cost = compute_rental_cost(start, end, qty)
    return {
        "cart_id": uuid.uuid4().hex[:10],
        "product_id": prod["id"],
        "product_name": prod["name"],
        "product_image": prod.get("image", ""),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "quantity": qty,
        "days": cost["days"],
        "rent_yuan": cost["rent"],
        "deposit_yuan": cost["deposit"],
        "total_yuan": cost["total"],
    }


def build_booking(
    prod: dict,
    start: date,
    end: date,
    qty: int,
    customer_name: str,
    phone: str,
    address: str,
    location_note: str,
) -> dict:
    cost = compute_rental_cost(start, end, qty)
    return {
        "id": uuid.uuid4().hex[:12],
        "kind": "rental",
        "product_id": prod["id"],
        "product_name": prod["name"],
        "customer_name": customer_name,
        "phone": phone,
        "address": address,
        "location_note": location_note,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "quantity": qty,
        "rent_yuan": cost["rent"],
        "deposit_yuan": cost["deposit"],
        "total_yuan": cost["total"],
        "days": cost["days"],
        "status": "pending_payment",
        "created_at": beijing_now_iso(),
    }


def compute_rental_cost(start: date, end: date, qty: int) -> dict:
    days = (end - start).days + 1
    if days < 1:
        days = 1
    rent = days * RENT_PER_DAY * qty
    deposit = DEPOSIT_PER_UNIT * qty
    return {"days": days, "rent": rent, "deposit": deposit, "total": rent + deposit}


def inventory_snapshot(store: dict) -> list[dict]:
    products = store["products"]
    bookings = store["bookings"]
    out: list[dict] = []
    today = beijing_today()
    horizon_end = today + timedelta(days=120)
    for p in products:
        if p.get("type") != "rental":
            continue
        total = int(p.get("total") or 0)
        peak_booked = 0
        for d in daterange(today, horizon_end):
            used = 0
            for b in bookings:
                if b.get("product_id") != p["id"]:
                    continue
                if b.get("status") == "cancelled":
                    continue
                if b.get("kind") != "rental":
                    continue
                bs = parse_date(b.get("start_date"))
                be = parse_date(b.get("end_date"))
                if not bs or not be:
                    continue
                if bs <= d <= be:
                    used += int(b.get("quantity") or 1)
            peak_booked = max(peak_booked, used)
        remaining = max(0, total - peak_booked)
        out.append(
            {
                "id": p["id"],
                "name": p["name"],
                "type": "rental",
                "image": p.get("image"),
                "category_id": p.get("category_id"),
                "desc": p.get("desc", ""),
                "total": total,
                "peak_booked": peak_booked,
                "remaining_hint": remaining,
            }
        )
    return out


def group_products_by_category(products: list[dict]) -> list[tuple[dict, list[dict]]]:
    cat_map = {c["id"]: c for c in CATEGORIES}
    buckets: dict[str, list[dict]] = {c["id"]: [] for c in CATEGORIES}
    for p in products:
        if p.get("type") != "rental":
            continue
        cid = p.get("category_id")
        if cid in buckets:
            buckets[cid].append(p)
    ordered: list[tuple[dict, list[dict]]] = []
    for c in CATEGORIES:
        ordered.append((cat_map[c["id"]], buckets.get(c["id"], [])))
    return ordered


def nav_active_key() -> str:
    ep = request.endpoint or ""
    if ep == "index":
        return "home" if request.args.get("tab") == "home" else "menu"
    if ep in ("product_detail", "book_rental_page"):
        return "menu"
    if ep in ("cart_page", "cart_checkout_done", "orders_page", "order_detail"):
        return "cart"
    if ep == "mine_page":
        return "mine"
    return "menu"


def admin_logged_in() -> bool:
    return bool(session.get("admin_logged_in"))


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not admin_logged_in():
            flash("请先登录账单管理。", "error")
            return redirect(url_for("mine_page", panel="admin"))
        return view(*args, **kwargs)

    return wrapped


def verify_admin_credentials(username: str, password: str) -> bool:
    return username.strip() == ADMIN_USERNAME.strip() and password == ADMIN_PASSWORD


def sort_bookings_newest_first(bookings: list) -> list:
    return sorted(bookings, key=lambda b: b.get("created_at") or "", reverse=True)


def admin_bills_context(store: dict) -> tuple[list, dict]:
    bookings = sort_bookings_newest_first(store.get("bookings", []))
    amount_pending = 0
    amount_paid = 0
    pending = 0
    paid = 0
    for b in bookings:
        status = b.get("status")
        total = int(b.get("total_yuan") or 0)
        if status == "pending_payment":
            pending += 1
            amount_pending += total
        elif status == "paid":
            paid += 1
            amount_paid += total
    stats = {
        "total": len(bookings),
        "pending": pending,
        "paid": paid,
        "amount_pending": amount_pending,
        "amount_paid": amount_paid,
    }
    return bookings, stats


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-bachelor-cap-secret")

    import threading

    def _warm_images() -> None:
        warm_catalog_images(DEFAULT_PRODUCTS, [FENGYE_IMAGE])

    threading.Thread(target=_warm_images, daemon=True).start()

    @app.after_request
    def static_cache_headers(response):
        if request.path.startswith("/static/img/_cache/"):
            response.cache_control.max_age = 31536000
            response.cache_control.public = True
        return response

    @app.template_filter("fmt_bj")
    def fmt_bj_filter(value: str | None) -> str:
        return format_beijing_time(value)

    @app.context_processor
    def inject_shop():
        return {
            "RENT_PER_DAY": RENT_PER_DAY,
            "DEPOSIT_PER_UNIT": DEPOSIT_PER_UNIT,
            "SHOP_NAME": SHOP_NAME,
            "SHOP_ADDRESS": SHOP_ADDRESS,
            "SHOP_NOTICE": SHOP_NOTICE,
            "CATEGORIES": CATEGORIES,
            "nav_active": nav_active_key,
            "STATUS_LABELS": STATUS_LABELS,
            "beijing_today_iso": beijing_today().isoformat(),
            "beijing_tz_label": BEIJING_TZ_LABEL,
            "cart_count": cart_count,
        }

    @app.route("/")
    def welcome():
        img = welcome_image_href()
        if not img:
            return redirect(url_for("index", tab="menu"))
        return render_template("welcome.html", welcome_image=img)

    @app.route("/shop")
    def index():
        store = load_store()
        inv = inventory_snapshot(store)
        inv_map = {x["id"]: x for x in inv}
        rentals = [p for p in store["products"] if p.get("type") == "rental"]
        signature = rentals[:4]
        grouped = group_products_by_category(store["products"])
        return render_template(
            "index.html",
            products=store["products"],
            rentals=rentals,
            inv_map=inv_map,
            signature=signature,
            grouped=grouped,
        )

    @app.route("/cart")
    def cart_page():
        cart = get_cart()
        totals = cart_totals(cart)
        return render_template("cart.html", cart=cart, totals=totals)

    @app.route("/cart/remove/<cart_id>", methods=["POST"])
    def cart_remove(cart_id: str):
        cart = [i for i in get_cart() if i.get("cart_id") != cart_id]
        save_cart(cart)
        flash("已从购物车移除。", "ok")
        return redirect(url_for("cart_page"))

    @app.route("/cart/checkout", methods=["POST"])
    def cart_checkout():
        cart = get_cart()
        if not cart:
            flash("购物车是空的。", "error")
            return redirect(url_for("cart_page"))

        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        addr = request.form.get("address", "").strip()
        loc_note = request.form.get("location_note", "").strip()
        if not name or not phone or not addr:
            flash("请填写姓名、手机与送货地址。", "error")
            return redirect(url_for("cart_page"))

        store = load_store()
        created_ids: list[str] = []
        pending_bookings = list(store["bookings"])

        for item in cart:
            pid = item.get("product_id", "")
            prod = next((p for p in store["products"] if p["id"] == pid), None)
            if not prod or prod.get("type") != "rental":
                flash(f"「{item.get('product_name', pid)}」已失效，请移除后重试。", "error")
                return redirect(url_for("cart_page"))
            start = parse_date(item.get("start_date"))
            end = parse_date(item.get("end_date"))
            qty = int(item.get("quantity") or 1)
            err = validate_rental_fields(start, end, qty)
            if err:
                flash(f"{item.get('product_name')}：{err}", "error")
                return redirect(url_for("cart_page"))
            if not rental_available(prod, pending_bookings, start, end, qty):
                flash(f"「{prod['name']}」所选时段库存不足，请调整购物车。", "error")
                return redirect(url_for("cart_page"))
            booking = build_booking(prod, start, end, qty, name, phone, addr, loc_note)
            pending_bookings.append(booking)
            created_ids.append(booking["id"])

        store["bookings"] = pending_bookings
        save_store(store)
        save_cart([])
        flash(f"已生成 {len(created_ids)} 笔订单，请分别扫码支付。", "ok")
        return redirect(url_for("cart_checkout_done", ids=",".join(created_ids)))

    @app.route("/cart/done")
    def cart_checkout_done():
        raw = request.args.get("ids", "")
        ids = [x.strip() for x in raw.split(",") if x.strip()]
        store = load_store()
        orders = [
            b for b in store["bookings"] if b.get("id") in ids and b.get("status") != "cancelled"
        ]
        orders = sort_bookings_newest_first(orders)
        grand = sum(int(o.get("total_yuan") or 0) for o in orders)
        return render_template("cart_done.html", orders=orders, grand_total=grand)

    @app.route("/orders")
    def orders_page():
        return render_template("orders.html")

    @app.route("/mine")
    def mine_page():
        store = load_store()
        open_panel = request.args.get("panel") == "admin"
        ctx: dict = {
            "admin_logged_in": admin_logged_in(),
            "open_admin_panel": open_panel,
            "bookings": [],
            "stats": {"total": 0, "pending": 0, "paid": 0, "amount_pending": 0, "amount_paid": 0},
            "status_options": ADMIN_STATUS_OPTIONS,
        }
        if ctx["admin_logged_in"]:
            bookings, stats = admin_bills_context(store)
            ctx["bookings"] = bookings
            ctx["stats"] = stats
        return render_template("mine.html", **ctx)

    @app.route("/mine/admin/login", methods=["POST"])
    def mine_admin_login():
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if verify_admin_credentials(username, password):
            session["admin_logged_in"] = True
            session.permanent = True
            flash("已登录，可查看账单。", "ok")
        else:
            flash("账号或密码错误。", "error")
        return redirect(url_for("mine_page", panel="admin"))

    @app.route("/mine/admin/logout", methods=["POST"])
    def mine_admin_logout():
        session.pop("admin_logged_in", None)
        flash("已退出账单管理。", "ok")
        return redirect(url_for("mine_page"))

    @app.route("/mine/admin/order/<bid>/status", methods=["POST"])
    @admin_required
    def mine_admin_update_status(bid: str):
        new_status = request.form.get("status", "").strip()
        allowed = {s for s, _ in ADMIN_STATUS_OPTIONS}
        if new_status not in allowed:
            flash("无效的状态。", "error")
            return redirect(url_for("mine_page", panel="admin"))
        store = load_store()
        booking = next((b for b in store["bookings"] if b.get("id") == bid), None)
        if not booking:
            flash("订单不存在。", "error")
            return redirect(url_for("mine_page", panel="admin"))
        booking["status"] = new_status
        save_store(store)
        flash(f"订单已更新为「{STATUS_LABELS.get(new_status, new_status)}」。", "ok")
        return redirect(url_for("mine_page", panel="admin"))

    @app.route("/api/time")
    def api_time():
        return jsonify(beijing_time_payload())

    @app.route("/api/inventory")
    def api_inventory():
        store = load_store()
        payload = beijing_time_payload()
        payload["updated_at"] = payload["now"]
        payload["items"] = inventory_snapshot(store)
        return jsonify(payload)

    @app.route("/product/<pid>")
    def product_detail(pid: str):
        store = load_store()
        prod = get_rental_product(store, pid)
        if not prod:
            flash("未找到该款式。", "error")
            return redirect(url_for("index"))
        inv = {x["id"]: x for x in inventory_snapshot(store)}
        return render_template(
            "product_detail.html",
            product=prod,
            inv=inv.get(pid, {}),
            gallery_items=product_gallery_items(prod),
        )

    @app.route("/product/<pid>/detail/2")
    def product_detail_2(pid: str):
        return redirect(url_for("product_detail", pid=pid))

    @app.route("/product/<pid>/book")
    def book_rental_page(pid: str):
        store = load_store()
        prod = get_rental_product(store, pid)
        if not prod:
            flash("未找到该款式。", "error")
            return redirect(url_for("index"))
        inv = {x["id"]: x for x in inventory_snapshot(store)}
        return render_template(
            "book_rental.html",
            product=prod,
            inv=inv.get(pid, {}),
        )

    @app.route("/book/rental", methods=["POST"])
    def book_rental():
        store = load_store()
        form = parse_rental_form()
        pid = form["product_id"]
        prod = get_rental_product(store, pid)
        if not prod:
            flash("款式无效。", "error")
            return redirect(url_for("index"))

        start, end, qty = form["start"], form["end"], form["qty"]
        err = validate_rental_fields(start, end, qty)
        if err:
            flash(err, "error")
            return redirect(url_for("book_rental_page", pid=pid))

        cart = get_cart()
        if not rental_available(prod, store["bookings"], start, end, qty, cart=cart):
            flash("所选时段库存不足，请调整日期或数量。", "error")
            return redirect(url_for("book_rental_page", pid=pid))

        if form["action"] == "cart":
            cart.append(build_cart_line(prod, start, end, qty))
            save_cart(cart)
            flash("已加入购物车。", "ok")
            return redirect(url_for("cart_page"))

        name, phone, addr, loc_note = (
            form["customer_name"],
            form["phone"],
            form["address"],
            form["location_note"],
        )
        if not name or not phone or not addr:
            flash("请填写姓名、手机与送货地址。", "error")
            return redirect(url_for("book_rental_page", pid=pid))

        booking = build_booking(prod, start, end, qty, name, phone, addr, loc_note)
        store["bookings"].append(booking)
        save_store(store)
        flash("预定已创建，请扫码支付。", "ok")
        return redirect(url_for("order_detail", bid=booking["id"]))

    @app.route("/order/<bid>")
    def order_detail(bid: str):
        store = load_store()
        booking = next((b for b in store["bookings"] if b.get("id") == bid), None)
        if not booking:
            flash("订单不存在。", "error")
            return redirect(url_for("index"))
        qr_candidates = [
            BASE_DIR / "static" / "img" / "payment_qr.png",
            BASE_DIR / "static" / "img" / "payment_qr.jpg",
            BASE_DIR / "static" / "img" / "payment_qr.jpeg",
            BASE_DIR / "static" / "img" / "payment_qr.webp",
        ]
        qr_url = None
        for p in qr_candidates:
            if p.is_file():
                qr_url = url_for("static", filename=f"img/{p.name}")
                break
        if qr_url is None:
            qr_url = url_for("static", filename="img/payment_placeholder.svg")
        return render_template("order.html", order=booking, qr_url=qr_url)

    @app.route(f"/{ADMIN_SLUG}/login", methods=["GET", "POST"])
    @app.route(f"/{ADMIN_SLUG}")
    def admin_legacy_redirect():
        return redirect(url_for("mine_page", panel="admin"))

    return app


app = create_app()

if __name__ == "__main__":
    ensure_dirs()
    app.run(host="127.0.0.1", port=5000, debug=True)
