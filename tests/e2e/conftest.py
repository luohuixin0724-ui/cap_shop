# -*- coding: utf-8 -*-
"""E2E 测试：启动 Flask 本地服务 + 隔离数据。"""

from __future__ import annotations

import threading
from datetime import date

import pytest
from werkzeug.serving import make_server

import app as app_module
from tests.conftest import write_store


@pytest.fixture(scope="session")
def e2e_env(tmp_path_factory):
    """模块级测试服务器，使用临时 store 与固定日期。"""
    store_path = tmp_path_factory.mktemp("e2e") / "store.json"
    fixed_today = date(2026, 6, 7)

    original_data_path = app_module.DATA_PATH
    original_beijing_today = app_module.beijing_today
    original_admin_user = app_module.ADMIN_USERNAME
    original_admin_pass = app_module.ADMIN_PASSWORD
    original_notify = app_module.notify_orders_async

    app_module.DATA_PATH = store_path
    app_module.beijing_today = lambda: fixed_today
    app_module.ADMIN_USERNAME = "testadmin"
    app_module.ADMIN_PASSWORD = "testpass"
    app_module.notify_orders_async = lambda *_a, **_k: None

    write_store(store_path)

    application = app_module.create_app()
    application.config.update(TESTING=True, SECRET_KEY="e2e-secret")

    server = make_server("127.0.0.1", 0, application)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    env = {
        "base_url": f"http://127.0.0.1:{port}",
        "store_path": store_path,
        "today": fixed_today,
        "admin_user": "testadmin",
        "admin_pass": "testpass",
    }
    yield env

    server.shutdown()
    app_module.DATA_PATH = original_data_path
    app_module.beijing_today = original_beijing_today
    app_module.ADMIN_USERNAME = original_admin_user
    app_module.ADMIN_PASSWORD = original_admin_pass
    app_module.notify_orders_async = original_notify


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 390, "height": 844},
        "locale": "zh-CN",
    }


@pytest.fixture(scope="session")
def base_url(e2e_env):
    return e2e_env["base_url"]


@pytest.fixture
def store_path(e2e_env):
    return e2e_env["store_path"]


@pytest.fixture(autouse=True)
def reset_store(store_path, e2e_env):
    """每条 E2E 用例前清空订单，保留默认商品目录。"""
    write_store(store_path)
    yield


@pytest.fixture
def rental_dates(e2e_env):
    today = e2e_env["today"]
    start = today.replace(day=10)
    end = today.replace(day=11)
    return start.isoformat(), end.isoformat()


@pytest.fixture
def rental_product_id(store_path):
    """取当前目录中第一个可租借款式（兼容图片扫描后的 r01～rN）。"""
    store = app_module.load_store()
    prod = next(p for p in store["products"] if p.get("type") == "rental")
    return prod["id"]


@pytest.fixture
def admin_credentials(e2e_env):
    return e2e_env["admin_user"], e2e_env["admin_pass"]
