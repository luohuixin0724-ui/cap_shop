# -*- coding: utf-8 -*-
"""E2E：保存订单确认弹窗流程（TC-011）。"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_save_order_via_modal(
    page: Page,
    base_url: str,
    rental_dates: tuple[str, str],
    rental_product_id: str,
):
    start, end = rental_dates

    page.goto(f"{base_url}/product/{rental_product_id}/book")
    page.locator("#start_date").fill(start)
    page.locator("#end_date").fill(end)
    page.locator("#phone").fill("13900139000")
    page.locator("#address").fill("上海大学宝山校区2号楼")

    page.locator("#btn-open-save-modal").click()
    expect(page.locator("#save-order-modal.is-open")).to_be_visible()
    expect(page.locator("#confirm-product-name")).not_to_be_empty()

    page.locator("#btn-confirm-save-order").click()
    page.wait_for_url(re.compile(r".*/order/.*"))

    expect(page.locator("h1.page-h1")).to_have_text("订单已保存")
    expect(page.locator(".mono")).to_contain_text(re.compile(r"[a-f0-9]{12}"))
