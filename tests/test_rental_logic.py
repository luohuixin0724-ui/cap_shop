# -*- coding: utf-8 -*-
"""租赁计价、库存与校验相关单元测试。"""

from __future__ import annotations

from datetime import date

import pytest

import app
from tests.conftest import cart_line, rental_booking, rental_product


class TestParseDate:
    def test_valid_iso_date(self):
        assert app.parse_date("2026-06-10") == date(2026, 6, 10)

    def test_strips_whitespace(self):
        assert app.parse_date("  2026-06-10  ") == date(2026, 6, 10)

    @pytest.mark.parametrize(
        "raw",
        ["", None, "2026/06/10", "not-a-date", "2026-13-01"],
    )
    def test_invalid_returns_none(self, raw):
        assert app.parse_date(raw) is None


class TestComputeRentalCost:
    def test_single_day_one_unit(self):
        start = end = date(2026, 6, 10)
        cost = app.compute_rental_cost(start, end, 1)
        assert cost == {"days": 1, "rent": 15, "deposit": 30, "total": 45}

    def test_multi_day_multi_quantity(self):
        start = date(2026, 6, 10)
        end = date(2026, 6, 12)
        cost = app.compute_rental_cost(start, end, 2)
        assert cost["days"] == 3
        assert cost["rent"] == 3 * app.RENT_PER_DAY * 2
        assert cost["deposit"] == app.DEPOSIT_PER_UNIT * 2
        assert cost["total"] == cost["rent"] + cost["deposit"]

    def test_end_before_start_clamps_days_to_one(self):
        cost = app.compute_rental_cost(date(2026, 6, 12), date(2026, 6, 10), 1)
        assert cost["days"] == 1


class TestValidateRentalFields:
    def test_valid_range(self, fixed_today):
        err = app.validate_rental_fields(date(2026, 6, 10), date(2026, 6, 12), 2)
        assert err is None

    def test_missing_dates(self, fixed_today):
        assert app.validate_rental_fields(None, date(2026, 6, 10), 1) is not None
        assert app.validate_rental_fields(date(2026, 6, 10), None, 1) is not None

    def test_end_before_start(self, fixed_today):
        err = app.validate_rental_fields(date(2026, 6, 12), date(2026, 6, 10), 1)
        assert err == "请选择有效的起止日期。"

    def test_start_before_today(self, fixed_today):
        err = app.validate_rental_fields(date(2026, 6, 6), date(2026, 6, 10), 1)
        assert "不能早于今天" in err

    def test_quantity_bounds(self, fixed_today):
        assert app.validate_rental_fields(date(2026, 6, 10), date(2026, 6, 10), 0) is not None
        assert app.validate_rental_fields(date(2026, 6, 10), date(2026, 6, 10), 11) is not None
        assert app.validate_rental_fields(date(2026, 6, 10), date(2026, 6, 10), 10) is None


class TestMaxOverlapUsage:
    def test_empty_bookings(self):
        peak = app.max_overlap_usage(
            "r01", date(2026, 6, 10), date(2026, 6, 12), []
        )
        assert peak == 0

    def test_counts_peak_across_days(self):
        bookings = [
            rental_booking("r01", date(2026, 6, 10), date(2026, 6, 11), quantity=1),
            rental_booking(
                "r01",
                date(2026, 6, 11),
                date(2026, 6, 12),
                booking_id="bk002",
                quantity=1,
            ),
        ]
        peak = app.max_overlap_usage(
            "r01", date(2026, 6, 10), date(2026, 6, 12), bookings
        )
        assert peak == 2

    def test_ignores_cancelled_and_other_products(self):
        bookings = [
            rental_booking("r01", date(2026, 6, 10), date(2026, 6, 10), status="cancelled"),
            rental_booking("r02", date(2026, 6, 10), date(2026, 6, 10), booking_id="bk002"),
            {"id": "bk003", "kind": "sale", "product_id": "r01", "start_date": "2026-06-10", "end_date": "2026-06-10"},
        ]
        peak = app.max_overlap_usage(
            "r01", date(2026, 6, 10), date(2026, 6, 10), bookings
        )
        assert peak == 0

    def test_ignore_id_excludes_booking(self):
        booking = rental_booking("r01", date(2026, 6, 10), date(2026, 6, 10))
        peak = app.max_overlap_usage(
            "r01",
            date(2026, 6, 10),
            date(2026, 6, 10),
            [booking],
            ignore_id="bk001",
        )
        assert peak == 0


class TestMaxCartOverlap:
    def test_sums_overlapping_cart_lines(self):
        cart = [
            cart_line("r01", date(2026, 6, 10), date(2026, 6, 10), cart_id="c1"),
            cart_line("r01", date(2026, 6, 10), date(2026, 6, 10), cart_id="c2"),
        ]
        peak = app.max_cart_overlap(cart, "r01", date(2026, 6, 10), date(2026, 6, 10))
        assert peak == 2

    def test_ignore_cart_id(self):
        cart = [cart_line("r01", date(2026, 6, 10), date(2026, 6, 10), cart_id="c1")]
        peak = app.max_cart_overlap(
            cart, "r01", date(2026, 6, 10), date(2026, 6, 10), ignore_cart_id="c1"
        )
        assert peak == 0


class TestRentalAvailable:
    def test_available_when_under_total(self):
        prod = rental_product(total=2)
        bookings = [rental_booking("r01", date(2026, 6, 10), date(2026, 6, 10))]
        assert app.rental_available(
            prod, bookings, date(2026, 6, 10), date(2026, 6, 10), 1
        )

    def test_unavailable_when_peak_exceeds_total(self):
        prod = rental_product(total=1)
        bookings = [rental_booking("r01", date(2026, 6, 10), date(2026, 6, 10))]
        assert not app.rental_available(
            prod, bookings, date(2026, 6, 10), date(2026, 6, 10), 1
        )

    def test_includes_cart_overlap(self):
        prod = rental_product(total=2)
        cart = [cart_line("r01", date(2026, 6, 10), date(2026, 6, 10))]
        assert app.rental_available(
            prod, [], date(2026, 6, 10), date(2026, 6, 10), 2, cart=cart
        ) is False

    def test_zero_total_always_unavailable(self):
        prod = rental_product(total=0)
        assert not app.rental_available(
            prod, [], date(2026, 6, 10), date(2026, 6, 10), 1
        )


class TestCartTotals:
    def test_sums_rent_deposit_and_count(self):
        cart = [
            {"rent_yuan": 30, "deposit_yuan": 60},
            {"rent_yuan": 15, "deposit_yuan": 30},
        ]
        totals = app.cart_totals(cart)
        assert totals == {"rent": 45, "deposit": 90, "total": 135, "items": 2}

    def test_empty_cart(self):
        assert app.cart_totals([]) == {"rent": 0, "deposit": 0, "total": 0, "items": 0}


class TestBuildCartLine:
    def test_contains_pricing_and_ids(self):
        prod = rental_product()
        line = app.build_cart_line(prod, date(2026, 6, 10), date(2026, 6, 11), 2)
        assert line["product_id"] == "r01"
        assert line["quantity"] == 2
        assert line["days"] == 2
        assert line["rent_yuan"] == 2 * app.RENT_PER_DAY * 2
        assert line["cart_id"]
        assert line["start_date"] == "2026-06-10"


class TestBuildBooking:
    def test_pending_payment_defaults(self):
        prod = rental_product()
        booking = app.build_booking(
            prod,
            date(2026, 6, 10),
            date(2026, 6, 11),
            1,
            "张三",
            "13800138000",
            "宿舍",
            "南门",
        )
        assert booking["kind"] == "rental"
        assert booking["status"] == "pending_payment"
        assert booking["customer_name"] == "张三"
        assert booking["phone"] == "13800138000"
        assert booking["total_yuan"] == booking["rent_yuan"] + booking["deposit_yuan"]
        assert booking["created_at"]


class TestRentalBookingCount:
    def test_counts_active_rentals_only(self):
        bookings = [
            rental_booking("r01", date(2026, 6, 10), date(2026, 6, 10)),
            rental_booking(
                "r01",
                date(2026, 6, 11),
                date(2026, 6, 11),
                booking_id="bk002",
                status="cancelled",
            ),
            rental_booking("r02", date(2026, 6, 10), date(2026, 6, 10), booking_id="bk003"),
        ]
        assert app.rental_booking_count("r01", bookings) == 1


class TestPeakBookedUnits:
    def test_peak_within_range(self):
        bookings = [
            rental_booking("r01", date(2026, 6, 10), date(2026, 6, 11), quantity=1),
            rental_booking(
                "r01",
                date(2026, 6, 11),
                date(2026, 6, 12),
                booking_id="bk002",
                quantity=1,
            ),
        ]
        peak = app.peak_booked_units(
            "r01", bookings, date(2026, 6, 10), date(2026, 6, 12)
        )
        assert peak == 2


class TestInventorySnapshot:
    def test_remaining_hint_reflects_peak_usage(self, fixed_today):
        store = {
            "products": [rental_product(total=3)],
            "bookings": [
                rental_booking("r01", date(2026, 6, 10), date(2026, 6, 10), quantity=2),
            ],
        }
        snap = app.inventory_snapshot(store)
        assert len(snap) == 1
        assert snap[0]["total"] == 3
        assert snap[0]["booked_count"] == 1
        assert snap[0]["remaining_hint"] == 1


class TestGroupProductsByCategory:
    def test_only_rentals_grouped_in_category_order(self):
        products = [
            rental_product("r01"),
            {**rental_product("r99", total=1), "category_id": "miaoyin"},
            {"id": "x1", "type": "sale", "category_id": "zan"},
        ]
        grouped = app.group_products_by_category(products)
        assert len(grouped) == len(app.CATEGORIES)
        zan_bucket = next(items for cat, items in grouped if cat["id"] == "zan")
        assert len(zan_bucket) == 1
        assert zan_bucket[0]["id"] == "r01"


class TestVerifyAdminCredentials:
    def test_valid_credentials(self, monkeypatch):
        monkeypatch.setattr(app, "ADMIN_USERNAME", "owner")
        monkeypatch.setattr(app, "ADMIN_PASSWORD", "secret")
        assert app.verify_admin_credentials("owner", "secret")

    def test_invalid_password(self, monkeypatch):
        monkeypatch.setattr(app, "ADMIN_USERNAME", "owner")
        monkeypatch.setattr(app, "ADMIN_PASSWORD", "secret")
        assert not app.verify_admin_credentials("owner", "wrong")


class TestNormalizeAdminSlug:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("admin", "admin"),
            ("  /shop-admin/ ", "shop-admin"),
            ("bad slug!", "badslug"),
            ("", "admin"),
            (None, "admin"),
        ],
    )
    def test_slug_sanitized(self, raw, expected):
        assert app.normalize_admin_slug(raw) == expected
