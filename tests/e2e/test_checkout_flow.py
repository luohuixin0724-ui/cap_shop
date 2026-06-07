# -*- coding: utf-8 -*-
"""E2E：加入购物车 → 结算 → 下单成功（TC-010、TC-021）。"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_cart_checkout_flow(
    page: Page,
    base_url: str,
    rental_dates: tuple[str, str],
    rental_product_id: str,
):
    start, end = rental_dates

    page.goto(f"{base_url}/product/{rental_product_id}/book")
    expect(page.locator("h1.detail-name")).to_be_visible()

    page.locator("#start_date").fill(start)
    page.locator("#end_date").fill(end)
    page.locator('button[value="cart"]').click()

    page.wait_for_url(re.compile(r".*/cart$"))
    expect(page.locator("h3.cart-item-name")).to_be_visible()

    page.locator("#phone").fill("13800138000")
    page.locator("#address").fill("上海大学宝山校区1号楼")
    page.locator('form[action*="checkout"] button[type="submit"]').click()

    page.wait_for_url(re.compile(r".*/cart/done"))
    expect(page.locator("h1.page-h1")).to_contain_text("已生成")
    expect(page.locator(".cart-done-card")).to_have_count(1)


def test_empty_cart_shows_placeholder(page: Page, base_url: str):
    page.goto(f"{base_url}/cart")
    expect(page.locator("h1.page-h1")).to_have_text("购物车是空的")
