import json
import os
import pytest

from app.i18n.translator import tr

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name):
    path = os.path.join(FIXTURES_DIR, name)
    with open(path) as f:
        return json.load(f)


class TestTrackingService:
    def test_track_waybill_returns_expected_shape(self):
        data = _load_fixture("track_success.json")
        assert data["status"] == "success"
        assert "data" in data
        d = data["data"]
        assert "waybill_number" in d
        assert "current_status" in d
        assert "timeline" in d
        assert isinstance(d["timeline"], list)

    def test_track_not_found(self):
        data = _load_fixture("track_not_found.json")
        assert data["status"] == "error"
        assert "message" in data

    def test_timeline_has_expected_fields(self):
        data = _load_fixture("track_success.json")
        for step in data["data"]["timeline"]:
            assert "status" in step
            assert "label" in step
            assert "timestamp" in step
            assert "completed" in step

    def test_result_has_route_fields(self):
        data = _load_fixture("track_success.json")
        d = data["data"]
        assert "origin_city" in d
        assert "destination_city" in d
        assert "estimated_delivery" in d

    def test_result_has_sender_recipient(self):
        data = _load_fixture("track_success.json")
        d = data["data"]
        assert "sender_name" in d
        assert "recipient_name" in d

    def test_track_service_importable(self):
        from app.services.tracking_service import track_waybill, get_rider_location
        assert callable(track_waybill)
        assert callable(get_rider_location)

    def test_track_service_connectivity(self):
        from app.services.tracking_service import track_waybill
        result = track_waybill("TRACK-0000-0000")
        assert result["ok"] is False
        assert result["error"] is not None


class TestTrackingScreens:
    def test_tracking_search_screen_importable(self):
        from app.views.shared.tracking_screen import TrackingSearchScreen
        assert TrackingSearchScreen is not None

    def test_tracking_result_screen_importable(self):
        from app.views.shared.tracking_result_screen import TrackingResultScreen
        assert TrackingResultScreen is not None

    def test_status_timeline_importable(self):
        from app.views.shared.status_timeline import StatusTimeline
        assert StatusTimeline is not None

    def test_nav_shell_importable(self):
        from app.views.shared.nav_shell import NavShell
        assert NavShell is not None

    def test_welcome_landing_builds(self):
        import os
        os.environ.setdefault("KIVY_NO_ARGS", "1")
        os.environ.setdefault("KIVY_WINDOW", "sdl2")
        from kivy.config import Config
        Config.set("graphics", "width", "400")
        Config.set("graphics", "height", "700")
        from kivymd.app import MDApp
        from app.core.theme import apply_theme
        from app.i18n.translator import init_translator
        from app.views.auth.welcome_screen import WelcomeScreen

        class T(MDApp):
            def build(self):
                apply_theme(self)
                init_translator("en")
                return WelcomeScreen(name="welcome")

        screen = T().build()
        assert len(screen.children) == 1
        nav_layout = screen.children[0]
        assert hasattr(nav_layout, "screen_manager") or nav_layout.__class__.__name__ == "MDNavigationLayout"
        assert screen.drawer is not None

    def test_landing_drawer_has_login_items(self):
        import os
        os.environ.setdefault("KIVY_NO_ARGS", "1")
        os.environ.setdefault("KIVY_WINDOW", "sdl2")
        from kivy.config import Config
        Config.set("graphics", "width", "400")
        Config.set("graphics", "height", "700")
        from kivymd.app import MDApp
        from app.core.theme import apply_theme
        from app.i18n.translator import init_translator
        from app.views.auth.welcome_screen import WelcomeScreen

        class T(MDApp):
            def build(self):
                apply_theme(self)
                init_translator("en")
                return WelcomeScreen(name="welcome")

        screen = T().build()
        texts = [w.text for w in screen.drawer.walk() if hasattr(w, "text")]
        assert any("Login" in t for t in texts)
        assert any("login_customer" in t or "Customer" in t for t in texts)
        items = [w for w in screen.drawer.walk()
                 if type(w).__name__ == "OneLineListItem"]
        assert len(items) == 2
        assert [i.text for i in items][0] == tr("login_customer")
        assert [i.text for i in items][1] == tr("login_rider")
        assert not any(type(w).__name__ == "MDNavigationDrawerItem"
                       for w in screen.drawer.walk())

    def test_tracking_search_and_result_build(self):
        import os
        os.environ.setdefault("KIVY_NO_ARGS", "1")
        os.environ.setdefault("KIVY_WINDOW", "sdl2")
        from kivy.config import Config
        Config.set("graphics", "width", "400")
        Config.set("graphics", "height", "700")
        from app.views.shared.tracking_screen import TrackingSearchScreen
        from app.views.shared.tracking_result_screen import TrackingResultScreen

        ts = TrackingSearchScreen(name="tracking_search")
        assert ts is not None
        tr_screen = TrackingResultScreen(name="tracking_result")
        tr_screen.on_pre_enter()
        assert tr_screen is not None


class TestTrackingLoginGate:
    def _make_screen(self):
        import os
        os.environ.setdefault("KIVY_NO_ARGS", "1")
        os.environ.setdefault("KIVY_WINDOW", "sdl2")
        from kivy.config import Config
        Config.set("graphics", "width", "400")
        Config.set("graphics", "height", "700")
        from app.views.shared.tracking_screen import TrackingSearchScreen
        screen = TrackingSearchScreen(name="tracking_search")
        screen.waybill_field.text = "TW26082691536A"
        return screen

    class _FakeManager:
        def __init__(self):
            self.current = None
            self.screens = {
                "tracking_result": type(
                    "_StubResult",
                    (),
                    {"set_data": lambda self, d: None},
                )(),
            }
        def get_screen(self, name):
            return self.screens.get(name)

    def test_logged_out_redirects_to_login_and_stores_waybill(self, monkeypatch):
        import app.views.shared.tracking_screen as mod
        monkeypatch.setattr(mod, "is_logged_in", lambda: False)
        screen = self._make_screen()
        manager = self._FakeManager()
        screen.manager = manager
        screen._do_search()
        assert manager.current == "customer_login"
        assert screen._pending_waybill == "TW26082691536A"

    def test_logged_in_does_not_stash_pending(self, monkeypatch):
        import app.views.shared.tracking_screen as mod
        import app.services.tracking_service as svc
        monkeypatch.setattr(mod, "is_logged_in", lambda: True)
        monkeypatch.setattr(
            svc, "track_waybill",
            lambda w: {"ok": True, "data": {}, "error": None},
        )
        screen = self._make_screen()
        manager = self._FakeManager()
        screen.manager = manager
        screen._do_search()
        assert screen._pending_waybill is None

    def test_pending_waybill_consumed_on_pre_enter(self, monkeypatch):
        import app.views.shared.tracking_screen as mod
        import app.services.tracking_service as svc
        monkeypatch.setattr(mod, "is_logged_in", lambda: True)
        monkeypatch.setattr(
            svc, "track_waybill",
            lambda w: {"ok": True, "data": {}, "error": None},
        )
        screen = self._make_screen()
        manager = self._FakeManager()
        screen.manager = manager
        screen._pending_waybill = "TW26082691536A"
        screen.on_pre_enter()
        assert screen._pending_waybill is None
        assert manager.current == "tracking_result"

    def test_auth_error_routes_to_login_and_stashes_waybill(self, monkeypatch):
        import app.views.shared.tracking_screen as mod
        import app.services.tracking_service as svc
        monkeypatch.setattr(mod, "is_logged_in", lambda: True)
        monkeypatch.setattr(
            svc, "track_waybill",
            lambda w: {"ok": False, "data": None,
                        "error": "Authorization token required"},
        )
        screen = self._make_screen()
        manager = self._FakeManager()
        screen.manager = manager
        screen._do_search()
        assert manager.current == "customer_login"
        assert screen._pending_waybill == "TW26082691536A"

    def test_non_auth_error_shows_message(self, monkeypatch):
        import app.views.shared.tracking_screen as mod
        import app.services.tracking_service as svc
        monkeypatch.setattr(mod, "is_logged_in", lambda: True)
        monkeypatch.setattr(
            svc, "track_waybill",
            lambda w: {"ok": False, "data": None, "error": "Waybill not found"},
        )
        screen = self._make_screen()
        manager = self._FakeManager()
        screen.manager = manager
        screen._do_search()
        assert manager.current != "customer_login"
        assert screen._pending_waybill is None
        assert "not found" in screen.error_label.text.lower()
