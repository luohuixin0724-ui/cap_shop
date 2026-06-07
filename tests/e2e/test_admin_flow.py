# -*- coding: utf-8 -*-
"""E2E：管理端登录与改订单状态（TC-031、TC-032）。"""

from __future__ import annotations

from datetime import date

import pytest
from playwright.sync_api import Page, expect

import app as app_module
from tests.conftest import write_store

pytestmark = pytest.mark.e2e


def _seed_pending_order(store_path) -> str:
    store = app_module.load_store()
    prod = next(p for p in store["products"] if p.get("type") == "rental")
    booking = app_module.build_booking(
        prod,
        date(2026, 6, 10),
        date(2026, 6, 11),
        1,
        "",
        "13800138000",
        "上海大学测试地址",
        "南门",
    )
    write_store(store_path, bookings=[booking])
    return booking["id"]


def test_admin_login_and_update_status(
    page: Page,
    base_url: str,
    store_path,
    admin_credentials: tuple[str, str],
):
    order_id = _seed_pending_order(store_path)
    username, password = admin_credentials

    page.goto(f"{base_url}/mine?panel=admin")
    expect(page.locator("#admin-modal.is-open")).to_be_visible()

    page.locator("#admin-username").fill(username)
    page.locator("#admin-password").fill(password)
    page.locator("form.admin-form button[type='submit']").click()

    expect(page.locator(".admin-order-list")).to_be_visible()
    expect(page.locator(f"#status-{order_id}")).to_be_visible()

    page.locator(f"#status-{order_id}").select_option("paid")
    page.locator(f"form[action*='{order_id}'] button[type='submit']").click()

    expect(page.locator(".flash.ok")).to_contain_text("已更新")
    expect(page.locator(".admin-order-card .status-pill")).to_have_text("已付款")


def test_admin_wrong_password(page: Page, base_url: str):
    page.goto(f"{base_url}/mine?panel=admin")
    page.locator("#admin-username").fill("wrong")
    page.locator("#admin-password").fill("wrong")
    page.locator("form.admin-form button[type='submit']").click()
    expect(page.locator(".flash.error")).to_contain_text("账号或密码错误")
