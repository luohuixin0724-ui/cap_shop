# -*- coding: utf-8 -*-
"""山竹小姐の学士帽 — Flask 预定平台"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "store.json"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif"}

RENT_PER_DAY = 20
DEPOSIT_PER_UNIT = 30
CUSTOM_PRICE = 80
CUSTOM_LEAD_DAYS = 7

SHOP_NAME = "花枝鼠の学士帽"
SHOP_ADDRESS = "工作室直发 · 全城送货上门（时段以短信确认为准）"
SHOP_NOTICE = "租借为实物档期制：以下库存为「未来档期峰值占用」估算，支付后锁定排期。"

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
        "image": "img/caps/r01.jpg",
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
        "image": "img/caps/r02.svg",
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
        "image": "img/caps/r03.svg",
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
        "image": "img/caps/r04.svg",
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
        "image": "img/caps/r05.svg",
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
        "image": "img/caps/r06.svg",
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
        "image": "img/caps/r07.svg",
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
    {
        "id": "custom",
        "name": "私人定制款",
        "type": "custom",
        "category_id": "custom",
        "image": "img/caps/custom.svg",
        "desc": f"提前 {CUSTOM_LEAD_DAYS} 天发图，确认后制作并发货",
        "tags": ["来图定制"],
        "monthly_sales": 0,
        "total": 0,
        "note": "提前一周发图，工作人员确认后制作",
    },
]


def ensure_dirs() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def merge_catalog_from_totals(totals: dict[str, object]) -> list[dict]:
    out: list[dict] = []
    for d in DEFAULT_PRODUCTS:
        row = dict(d)
        tid = str(d["id"])
        if tid in totals and totals[tid] is not None:
            try:
                row["total"] = int(totals[tid])  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
        out.append(row)
    return out


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


def rental_available(product: dict, bookings: list, start: date, end: date, qty: int) -> bool:
    total = int(product.get("total") or 0)
    if total <= 0:
        return False
    peak = max_overlap_usage(product["id"], start, end, bookings)
    return peak + qty <= total


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
    today = date.today()
    horizon_end = today + timedelta(days=120)
    for p in products:
        if p.get("type") == "custom":
            pending = sum(
                1
                for b in bookings
                if b.get("product_id") == p["id"]
                and b.get("kind") == "custom"
                and b.get("status") != "cancelled"
            )
            out.append(
                {
                    "id": p["id"],
                    "name": p["name"],
                    "type": "custom",
                    "image": p.get("image"),
                    "category_id": p.get("category_id"),
                    "total": None,
                    "booked_custom_orders": pending,
                }
            )
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
    if ep in ("product_detail",):
        return "menu"
    if ep in ("orders_page", "order_detail"):
        return "orders"
    if ep == "mine_page":
        return "mine"
    return "menu"


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-bachelor-cap-secret")

    @app.context_processor
    def inject_shop():
        return {
            "RENT_PER_DAY": RENT_PER_DAY,
            "DEPOSIT_PER_UNIT": DEPOSIT_PER_UNIT,
            "CUSTOM_PRICE": CUSTOM_PRICE,
            "CUSTOM_LEAD_DAYS": CUSTOM_LEAD_DAYS,
            "SHOP_NAME": SHOP_NAME,
            "SHOP_ADDRESS": SHOP_ADDRESS,
            "SHOP_NOTICE": SHOP_NOTICE,
            "CATEGORIES": CATEGORIES,
            "nav_active": nav_active_key,
        }

    @app.route("/")
    def index():
        store = load_store()
        inv = inventory_snapshot(store)
        inv_map = {x["id"]: x for x in inv}
        rentals = [p for p in store["products"] if p.get("type") == "rental"]
        custom = next((p for p in store["products"] if p.get("type") == "custom"), None)
        signature = rentals[:4]
        grouped = group_products_by_category(store["products"])
        return render_template(
            "index.html",
            products=store["products"],
            rentals=rentals,
            inv_map=inv_map,
            signature=signature,
            grouped=grouped,
            custom_product=custom,
        )

    @app.route("/orders")
    def orders_page():
        return render_template("orders.html")

    @app.route("/mine")
    def mine_page():
        return render_template("mine.html")

    @app.route("/api/inventory")
    def api_inventory():
        store = load_store()
        return jsonify(
            {
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "items": inventory_snapshot(store),
            }
        )

    @app.route("/product/<pid>")
    def product_detail(pid: str):
        store = load_store()
        prod = next((p for p in store["products"] if p["id"] == pid), None)
        if not prod:
            flash("未找到该款式。", "error")
            return redirect(url_for("index"))
        today_iso = date.today().isoformat()
        custom_min_iso = (date.today() + timedelta(days=CUSTOM_LEAD_DAYS)).isoformat()
        if prod.get("type") == "custom":
            return render_template(
                "book_custom.html", product=prod, today_iso=today_iso, custom_min_iso=custom_min_iso
            )
        inv = {x["id"]: x for x in inventory_snapshot(store)}
        return render_template(
            "book_rental.html",
            product=prod,
            inv=inv.get(pid, {}),
            today_iso=today_iso,
        )

    @app.route("/book/rental", methods=["POST"])
    def book_rental():
        store = load_store()
        pid = request.form.get("product_id", "").strip()
        prod = next((p for p in store["products"] if p["id"] == pid), None)
        if not prod or prod.get("type") != "rental":
            flash("款式无效。", "error")
            return redirect(url_for("index"))

        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        addr = request.form.get("address", "").strip()
        loc_note = request.form.get("location_note", "").strip()
        start = parse_date(request.form.get("start_date"))
        end = parse_date(request.form.get("end_date"))
        try:
            qty = int(request.form.get("quantity") or "1")
        except ValueError:
            qty = 0

        if not name or not phone or not addr:
            flash("请填写姓名、手机与送货地址。", "error")
            return redirect(url_for("product_detail", pid=pid))
        if not start or not end or end < start:
            flash("请选择有效的起止日期。", "error")
            return redirect(url_for("product_detail", pid=pid))
        if qty < 1 or qty > 10:
            flash("数量应在 1～10 顶之间。", "error")
            return redirect(url_for("product_detail", pid=pid))

        if not rental_available(prod, store["bookings"], start, end, qty):
            flash("所选时段库存不足，请调整日期或数量。", "error")
            return redirect(url_for("product_detail", pid=pid))

        cost = compute_rental_cost(start, end, qty)
        bid = uuid.uuid4().hex[:12]
        booking = {
            "id": bid,
            "kind": "rental",
            "product_id": pid,
            "product_name": prod["name"],
            "customer_name": name,
            "phone": phone,
            "address": addr,
            "location_note": loc_note,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "quantity": qty,
            "rent_yuan": cost["rent"],
            "deposit_yuan": cost["deposit"],
            "total_yuan": cost["total"],
            "days": cost["days"],
            "status": "pending_payment",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        store["bookings"].append(booking)
        save_store(store)
        flash("预定已创建，请扫码支付。", "ok")
        return redirect(url_for("order_detail", bid=bid))

    @app.route("/book/custom", methods=["POST"])
    def book_custom():
        store = load_store()
        prod = next((p for p in store["products"] if p.get("type") == "custom"), None)
        if not prod:
            flash("系统未配置定制款。", "error")
            return redirect(url_for("index"))

        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        addr = request.form.get("address", "").strip()
        need = parse_date(request.form.get("need_date"))
        notes = request.form.get("notes", "").strip()
        f = request.files.get("design_image")

        if not name or not phone or not addr:
            flash("请填写姓名、手机与收货信息。", "error")
            return redirect(url_for("product_detail", pid=prod["id"]))
        if not need:
            flash("请选择需要送达的日期。", "error")
            return redirect(url_for("product_detail", pid=prod["id"]))
        min_day = date.today() + timedelta(days=CUSTOM_LEAD_DAYS)
        if need < min_day:
            flash(f"定制款需提前至少 {CUSTOM_LEAD_DAYS} 天提交设计图。", "error")
            return redirect(url_for("product_detail", pid=prod["id"]))

        if not f or not f.filename:
            flash("请上传设计参考图。", "error")
            return redirect(url_for("product_detail", pid=prod["id"]))

        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in ALLOWED_EXT:
            flash("图片仅支持 png / jpg / jpeg / webp / gif。", "error")
            return redirect(url_for("product_detail", pid=prod["id"]))

        bid = uuid.uuid4().hex[:12]
        fname = f"{bid}_{secure_filename(f.filename)}"
        path = UPLOAD_DIR / fname
        f.save(path)

        booking = {
            "id": bid,
            "kind": "custom",
            "product_id": prod["id"],
            "product_name": prod["name"],
            "customer_name": name,
            "phone": phone,
            "address": addr,
            "need_date": need.isoformat(),
            "notes": notes,
            "image_file": fname,
            "total_yuan": CUSTOM_PRICE,
            "status": "pending_payment",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        store["bookings"].append(booking)
        save_store(store)
        flash("定制订单已创建，请扫码支付。", "ok")
        return redirect(url_for("order_detail", bid=bid))

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

    return app


app = create_app()

if __name__ == "__main__":
    ensure_dirs()
    app.run(host="127.0.0.1", port=5000, debug=True)
