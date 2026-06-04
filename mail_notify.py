# -*- coding: utf-8 -*-
"""订单创建后通过 QQ 邮箱 SMTP 通知店主。"""

from __future__ import annotations

import logging
import os
import smtplib
import threading
from email.header import Header
from email.mime.text import MIMEText
from typing import Iterable

logger = logging.getLogger(__name__)

QQ_SMTP_HOST = "smtp.qq.com"
QQ_SMTP_PORT = 465
DEFAULT_MAIL_TO = "1036014704@qq.com"
DEFAULT_MAIL_FROM = "1036014704@qq.com"


def _mail_user() -> str:
    return os.environ.get("QQ_MAIL_USER", DEFAULT_MAIL_FROM).strip()


def _mail_password() -> str:
    return (
        os.environ.get("QQ_MAIL_AUTH_CODE", "").strip()
        or os.environ.get("SMTP_PASSWORD", "").strip()
    )


def _mail_to() -> str:
    return os.environ.get("QQ_MAIL_TO", DEFAULT_MAIL_TO).strip()


def mail_configured() -> bool:
    return bool(_mail_user() and _mail_password() and _mail_to())


def format_order_block(booking: dict, shop_name: str) -> str:
    lines = [
        f"【{shop_name}】新订单",
        f"订单号：{booking.get('id', '')}",
        f"下单时间：{booking.get('created_at', '')}",
        f"状态：{booking.get('status', '')}",
        f"商品：{booking.get('product_name', '')}",
        f"租期：{booking.get('start_date', '')} ～ {booking.get('end_date', '')}（{booking.get('days', '')} 天）",
        f"数量：{booking.get('quantity', 1)} 顶",
        f"租金：{booking.get('rent_yuan', 0)} 元 · 押金：{booking.get('deposit_yuan', 0)} 元",
        f"应付合计：{booking.get('total_yuan', 0)} 元",
        f"手机：{booking.get('phone', '')}",
        f"地址：{booking.get('address', '')}",
    ]
    note = booking.get("location_note", "").strip()
    if note:
        lines.append(f"送达说明：{note}")
    return "\n".join(lines)


def build_email_body(bookings: Iterable[dict], shop_name: str) -> tuple[str, str]:
    items = list(bookings)
    if len(items) == 1:
        b = items[0]
        subject = f"【{shop_name}】新订单 {b.get('id', '')} · {b.get('product_name', '')}"
        body = format_order_block(b, shop_name)
    else:
        subject = f"【{shop_name}】新订单 {len(items)} 笔"
        parts = [f"共 {len(items)} 笔订单：\n"]
        for i, b in enumerate(items, 1):
            parts.append(f"--- 第 {i} 笔 ---")
            parts.append(format_order_block(b, shop_name))
            parts.append("")
        body = "\n".join(parts)
    return subject, body


def send_order_email(bookings: list[dict], shop_name: str) -> bool:
    if not bookings:
        return False
    if not mail_configured():
        logger.warning("QQ 邮箱未配置 QQ_MAIL_AUTH_CODE，跳过订单邮件通知。")
        return False

    user = _mail_user()
    password = _mail_password()
    to_addr = _mail_to()
    subject, body = build_email_body(bookings, shop_name)

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = user
    msg["To"] = to_addr
    msg["Subject"] = Header(subject, "utf-8")

    try:
        with smtplib.SMTP_SSL(QQ_SMTP_HOST, QQ_SMTP_PORT, timeout=15) as smtp:
            smtp.login(user, password)
            smtp.sendmail(user, [to_addr], msg.as_string())
        logger.info("订单邮件已发送至 %s", to_addr)
        return True
    except Exception as exc:
        logger.exception("发送订单邮件失败: %s", exc)
        return False


def notify_orders_async(bookings: list[dict], shop_name: str) -> None:
    """后台发送，不阻塞下单页面。"""

    def _run() -> None:
        send_order_email(bookings, shop_name)

    threading.Thread(target=_run, daemon=True).start()
