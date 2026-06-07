# -*- coding: utf-8 -*-
"""JSON API 接口测试（Flask test client）。"""

from __future__ import annotations

from datetime import date

import pytest

import app
from tests.conftest import rental_booking, rental_product, write_store

TIME_KEYS = {"timezone", "label", "now", "today", "utc_offset"}
INVENTORY_ITEM_KEYS = {
    "id",
    "name",
    "type",
    "total",
    "booked_count",
    "remaining_hint",
}
QUOTE_OK_KEYS = {
    "ok",
    "days",
    "rent_yuan",
    "deposit_yuan",
    "total_yuan",
    "rent_per_day",
    "deposit_per_unit",
}


def assert_json_response(resp, status: int = 200):
    assert resp.status_code == status
    assert resp.content_type.startswith("application/json")
    data = resp.get_json()
    assert data is not None
    return data


class TestApiTime:
    def test_returns_beijing_payload(self, client, fixed_today):
        data = assert_json_response(client.get("/api/time"))
        assert data["today"] == "2026-06-07"
        assert data["label"] == app.BEIJING_TZ_LABEL
        assert data["timezone"] == "Asia/Shanghai"
        assert TIME_KEYS.issubset(data.keys())
        assert data["now"].startswith("2026-06-07")

    def test_only_get_allowed(self, client):
        assert client.post("/api/time").status_code == 405


class TestApiRentalQuote:
    def test_success(self, client, fixed_today):
        data = assert_json_response(
            client.get(
                "/api/rental-quote",
                query_string={
                    "start_date": "2026-06-10",
                    "end_date": "2026-06-12",
                    "quantity": "2",
                },
            )
        )
        assert data["ok"] is True
        assert QUOTE_OK_KEYS.issubset(data.keys())
        assert data["days"] == 3
        assert data["rent_yuan"] == 3 * app.RENT_PER_DAY * 2
        assert data["deposit_yuan"] == app.DEPOSIT_PER_UNIT * 2
        assert data["total_yuan"] == data["rent_yuan"] + data["deposit_yuan"]
        assert data["rent_per_day"] == app.RENT_PER_DAY
        assert data["deposit_per_unit"] == app.DEPOSIT_PER_UNIT

    def test_default_quantity_is_one(self, client, fixed_today):
        data = assert_json_response(
            client.get(
                "/api/rental-quote",
                query_string={"start_date": "2026-06-10", "end_date": "2026-06-10"},
            )
        )
        assert data["ok"] is True
        assert data["rent_yuan"] == app.RENT_PER_DAY
        assert data["deposit_yuan"] == app.DEPOSIT_PER_UNIT

    @pytest.mark.parametrize(
        ("query", "error_fragment"),
        [
            ({"start_date": "2026-06-12", "end_date": "2026-06-10"}, "有效的起止日期"),
            ({"start_date": "", "end_date": "2026-06-10"}, "有效的起止日期"),
            ({"start_date": "2026-06-01", "end_date": "2026-06-10"}, "不能早于今天"),
            ({"start_date": "2026-06-10", "end_date": "2026-06-10", "quantity": "0"}, "1～10"),
            ({"start_date": "2026-06-10", "end_date": "2026-06-10", "quantity": "11"}, "1～10"),
            ({"start_date": "2026-06-10", "end_date": "2026-06-10", "quantity": "abc"}, "1～10"),
        ],
    )
    def test_validation_errors_return_400(self, client, fixed_today, query, error_fragment):
        data = assert_json_response(client.get("/api/rental-quote", query_string=query), 400)
        assert data["ok"] is False
        assert "error" in data
        assert error_fragment in data["error"]

    def test_boundary_quantity_ten(self, client, fixed_today):
        data = assert_json_response(
            client.get(
                "/api/rental-quote",
                query_string={
                    "start_date": "2026-06-10",
                    "end_date": "2026-06-10",
                    "quantity": "10",
                },
            )
        )
        assert data["ok"] is True
        assert data["rent_yuan"] == app.RENT_PER_DAY * 10

    def test_only_get_allowed(self, client, fixed_today):
        assert client.post("/api/rental-quote").status_code == 405


class TestApiInventory:
    def test_returns_rental_items(self, client, isolated_store, fixed_today):
        write_store(
            isolated_store,
            products=[rental_product(total=2)],
            bookings=[
                rental_booking("r01", date(2026, 6, 10), date(2026, 6, 10), quantity=1),
            ],
        )
        data = assert_json_response(client.get("/api/inventory"))
        assert data["today"] == "2026-06-07"
        assert data["updated_at"] == data["now"]
        assert TIME_KEYS.issubset(data.keys())
        assert "items" in data
        assert len(data["items"]) >= 1
        item = next(x for x in data["items"] if x["id"] == "r01")
        assert INVENTORY_ITEM_KEYS.issubset(item.keys())
        assert item["type"] == "rental"
        assert item["total"] == 2
        assert item["booked_count"] == 1
        assert item["remaining_hint"] == 1

    def test_cancelled_booking_does_not_reduce_remaining(self, client, isolated_store, fixed_today):
        write_store(
            isolated_store,
            products=[rental_product(total=1)],
            bookings=[
                rental_booking(
                    "r01",
                    date(2026, 6, 10),
                    date(2026, 6, 10),
                    status="cancelled",
                ),
            ],
        )
        data = assert_json_response(client.get("/api/inventory"))
        item = next(x for x in data["items"] if x["id"] == "r01")
        assert item["booked_count"] == 0
        assert item["remaining_hint"] == 1

    def test_non_rental_products_excluded(self, client, isolated_store, fixed_today):
        write_store(
            isolated_store,
            products=[
                rental_product(total=1),
                {"id": "sale1", "name": "售卖", "type": "sale", "total": 5},
            ],
        )
        data = assert_json_response(client.get("/api/inventory"))
        ids = {x["id"] for x in data["items"]}
        assert "sale1" not in ids
        assert "r01" in ids

    def test_only_get_allowed(self, client):
        assert client.post("/api/inventory").status_code == 405
