# -*- coding: utf-8 -*-
"""pytest 共享 fixture。"""

from __future__ import annotations

import json
from datetime import date

import pytest


@pytest.fixture
def fixed_today(monkeypatch) -> date:
    """固定「今天」为 2026-06-07，便于日期校验用例可重复。"""
    today = date(2026, 6, 7)
    monkeypatch.setattr("app.beijing_today", lambda: today)
    return today


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """将订单数据写入临时目录，避免污染 data/store.json。"""
    store_path = tmp_path / "store.json"
    monkeypatch.setattr("app.DATA_PATH", store_path)
    return store_path


@pytest.fixture
def flask_app(isolated_store):
    from app import create_app

    application = create_app()
    application.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        WTF_CSRF_ENABLED=False,
    )
    return application


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


def rental_product(product_id: str = "r01", total: int = 2) -> dict:
    return {
        "id": product_id,
        "name": "测试款式",
        "type": "rental",
        "category_id": "zan",
        "total": total,
    }


def rental_booking(
    product_id: str,
    start: date,
    end: date,
    *,
    booking_id: str = "bk001",
    quantity: int = 1,
    status: str = "pending_payment",
) -> dict:
    return {
        "id": booking_id,
        "kind": "rental",
        "product_id": product_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "quantity": quantity,
        "status": status,
    }


def cart_line(
    product_id: str,
    start: date,
    end: date,
    *,
    cart_id: str = "c001",
    quantity: int = 1,
) -> dict:
    return {
        "cart_id": cart_id,
        "product_id": product_id,
        "product_name": "测试款式",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "quantity": quantity,
        "rent_yuan": 15,
        "deposit_yuan": 30,
        "total_yuan": 45,
    }


def write_store(path, products=None, bookings=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "products": products or [rental_product()],
        "bookings": bookings or [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
