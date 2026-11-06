import json
import os
import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name):
    path = os.path.join(FIXTURES_DIR, name)
    with open(path) as f:
        return json.load(f)


class TestCustomerService:
    def test_dashboard_stats_shape(self, monkeypatch):
        import app.core.api_client as client
        fixture = _load_fixture("dashboard_stats.json")

        def fake_get(key, params=None, token=None):
            return {"ok": True, "data": fixture, "error": None}

        monkeypatch.setattr(client, "api_get", fake_get)
        from app.services.customer_service import get_dashboard_stats
        result = get_dashboard_stats()
        assert result["ok"] is True
        d = result["data"]
        assert d["total_deliveries"] == 5
        assert d["completed"] == 3
        assert d["in_progress"] == 1
        assert d["total_rides"] == 2
        assert d["referral_balance"] == "500.00"
        assert d["customer_name"] == "Akinpelu Faith"

    def test_dashboard_stats_tolerant_alternate_keys(self, monkeypatch):
        import app.core.api_client as client

        def fake_get(key, params=None, token=None):
            return {"ok": True, "data": {
                "data": {
                    "deliveries_total": 9,
                    "total_completed": 4,
                    "rides_total": 3,
                    "referral": "100.00",
                }
            }, "error": None}

        monkeypatch.setattr(client, "api_get", fake_get)
        from app.services.customer_service import get_dashboard_stats
        result = get_dashboard_stats()
        d = result["data"]
        assert d["total_deliveries"] == 9
        assert d["completed"] == 4
        assert d["total_rides"] == 3
        assert d["referral_balance"] == "100.00"

    def test_deliveries_shape(self, monkeypatch):
        import app.core.api_client as client
        fixture = _load_fixture("deliveries.json")

        def fake_get(key, params=None, token=None):
            return {"ok": True, "data": fixture, "error": None}

        monkeypatch.setattr(client, "api_get", fake_get)
        from app.services.customer_service import get_deliveries
        result = get_deliveries(page=1)
        assert result["ok"] is True
        assert len(result["data"]["items"]) == 2
        assert result["data"]["items"][0]["waybill_number"] == "TW260811409216"

    def test_deliveries_empty(self, monkeypatch):
        import app.core.api_client as client

        def fake_get(key, params=None, token=None):
            return {"ok": True, "data": {"data": {"deliveries": []}}, "error": None}

        monkeypatch.setattr(client, "api_get", fake_get)
        from app.services.customer_service import get_deliveries
        result = get_deliveries()
        assert result["data"]["items"] == []

    def test_get_history_maps_items(self, monkeypatch):
        import app.core.api_client as client

        def fake_get(key, params=None, token=None):
            return {"ok": True, "data": {"data": {"history": [{"waybill_number": "TW1"}], "has_more": False}},
                    "error": None}

        monkeypatch.setattr(client, "api_get", fake_get)
        from app.services.customer_service import get_history
        result = get_history(page=1)
        assert result["ok"] is True
        assert result["data"]["items"][0]["waybill_number"] == "TW1"

    def test_service_importable(self):
        from app.services.customer_service import (
            get_dashboard_stats, get_deliveries, get_status_counts, get_history,
        )
        assert callable(get_dashboard_stats)
        assert callable(get_deliveries)
        assert callable(get_status_counts)
        assert callable(get_history)


class TestWaybillCard:
    def test_waybill_card_importable(self):
        from app.views.shared.waybill_card import WaybillCard, status_color, status_label
        assert WaybillCard is not None

    def test_waybill_card_renders(self):
        import os
        os.environ.setdefault("KIVY_NO_ARGS", "1")
        os.environ.setdefault("KIVY_WINDOW", "sdl2")
        from kivy.config import Config
        Config.set("graphics", "width", "400")
        Config.set("graphics", "height", "700")
        from kivy.app import App
        from kivymd.app import MDApp
        from app.i18n.translator import init_translator
        from app.core.theme import apply_theme
        if App.get_running_app() is None:
            _app = MDApp()
            apply_theme(_app)
            # Do not run, just set as running app for theming
            App._running_app = _app
        init_translator("en")
        from app.views.shared.waybill_card import WaybillCard
        card = WaybillCard(waybill={
            "waybill_number": "TW260811409216",
            "origin": "Akure",
            "destination": "Akure",
            "status": "cancelled",
            "created_at": "2026-08-11",
        })
        assert card.number_label.text == "TW260811409216"
        assert card.route_label.text == "Akure \u2192 Akure"
        assert "cancelled" in card.chip_label.text.lower()


class TestCustomerScreens:
    def test_customer_home_importable(self):
        from app.views.customer.customer_home_screen import CustomerHomeScreen
        assert CustomerHomeScreen is not None

    def test_customer_deliveries_importable(self):
        from app.views.customer.customer_deliveries_screen import CustomerDeliveriesScreen
        assert CustomerDeliveriesScreen is not None

    def test_customer_history_importable(self):
        from app.views.customer.customer_history_screen import CustomerHistoryScreen
        assert CustomerHistoryScreen is not None

    def test_customer_deliveries_builds(self):
        import os
        os.environ.setdefault("KIVY_NO_ARGS", "1")
        os.environ.setdefault("KIVY_WINDOW", "sdl2")
        from kivy.config import Config
        Config.set("graphics", "width", "400")
        Config.set("graphics", "height", "700")
        from kivy.app import App
        from kivymd.app import MDApp
        from app.core.theme import apply_theme
        if App.get_running_app() is None:
            _app = MDApp()
            apply_theme(_app)
            App._running_app = _app
        from app.views.customer.customer_deliveries_screen import CustomerDeliveriesScreen
        screen = CustomerDeliveriesScreen(name="customer_deliveries")
        assert screen is not None
