import os
import sys
import json
import tempfile
import shutil

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestTranslator:
    def test_tr_english_returns_value(self):
        from app.i18n.translator import init_translator, tr
        init_translator("en")
        assert tr("login") == "Login"

    def test_tr_fallback_to_key(self):
        from app.i18n.translator import init_translator, tr
        init_translator("en")
        assert tr("nonexistent_key_xyz") == "nonexistent_key_xyz"

    def test_switch_language(self):
        from app.i18n.translator import init_translator, set_language, tr, get_language
        init_translator("en")
        assert tr("login") == "Login"
        set_language("yo")
        assert get_language() == "yo"
        assert tr("login") == "Wọ inú"
        set_language("en")

    def test_get_available_languages(self):
        from app.i18n.translator import get_available_languages
        langs = get_available_languages()
        assert "en" in langs
        assert "yo" in langs
        assert "ha" in langs
        assert "ig" in langs
        assert len(langs) == 4

    def test_landing_keys_resolve_in_english(self):
        from app.i18n.translator import init_translator, tr
        init_translator("en")
        keys = [
            "trusted_partner", "hero_1", "hero_2", "hero_3",
            "enter_tracking_number", "track_parcel_btn", "send_parcel",
            "request_rider_ride", "stats_deliveries", "stats_customers",
            "stats_drivers", "login_customer", "login_rider",
            "footer_tagline", "track_requires_login", "track_public",
            "track_login_required",
            "waybill_not_found",
        ]
        for key in keys:
            assert tr(key) != key, f"Landing key not localized: {key}"


class TestSession:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_fn = None

    def teardown_method(self):
        if self._orig_fn and os.path.exists(self._orig_fn):
            os.remove(self._orig_fn)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _patch_session(self):
        import app.core.session as sess
        self._orig_fn = os.path.join(self.tmpdir, "session.json")
        original_fn = sess._session_path
        sess._session_path = lambda: self._orig_fn
        return sess, original_fn

    def test_save_and_load(self):
        sess, orig = self._patch_session()
        sess.save_tokens("access123", "refresh456", "customer")
        data = sess.load_session()
        assert data is not None
        assert data["access_token"] == "access123"
        assert data["refresh_token"] == "refresh456"
        assert data["role"] == "customer"
        sess._session_path = orig

    def test_clear_session(self):
        sess, orig = self._patch_session()
        sess.save_tokens("a", "b", "rider")
        assert sess.is_logged_in() is True
        sess.clear_session()
        assert sess.load_session() is None
        assert sess.is_logged_in() is False
        sess._session_path = orig

    def test_load_empty(self):
        sess, orig = self._patch_session()
        assert sess.load_session() is None
        assert sess.is_logged_in() is False
        assert sess.get_role() is None
        sess._session_path = orig

    def test_get_role(self):
        sess, orig = self._patch_session()
        sess.save_tokens("a", "b", "rider")
        assert sess.get_role() == "rider"
        sess.clear_session()
        assert sess.get_role() is None
        sess._session_path = orig


class TestConstants:
    def test_all_statuses_have_labels(self):
        from app.core.constants import WAYBILL_STATUSES, STATUS_LABELS
        for status in WAYBILL_STATUSES:
            assert status in STATUS_LABELS, f"Missing label for {status}"

    def test_every_active_status_has_transition(self):
        from app.core.constants import WAYBILL_STATUSES, STATUS_TRANSITIONS
        active = [
            s for s in WAYBILL_STATUSES
            if s not in ("delivered", "failed", "cancelled")
        ]
        for status in active:
            assert status in STATUS_TRANSITIONS, f"No transitions for {status}"
            transitions = STATUS_TRANSITIONS[status]
            assert len(transitions) > 0, f"Empty transitions for {status}"

    def test_roles_defined(self):
        from app.core.constants import ROLES
        assert "customer" in ROLES
        assert "rider" in ROLES
        assert "driver" in ROLES


class TestConfig:
    def test_base_url(self):
        from app.core.config import BASE_URL
        assert BASE_URL.startswith("https://")
        assert BASE_URL.endswith("/api/v1")

    def test_endpoints_not_empty(self):
        from app.core.config import ENDPOINTS
        assert len(ENDPOINTS) > 30

    def test_all_endpoints_have_php_extension(self):
        from app.core.config import ENDPOINTS
        for key, path in ENDPOINTS.items():
            assert path.endswith(".php"), f"{key} -> {path} missing .php"


class TestApiClient:
    def test_build_url(self):
        from app.core.api_client import _build_url
        url = _build_url("login_customer")
        assert url is not None
        assert "customer/login.php" in url

    def test_unknown_endpoint(self):
        from app.core.api_client import _build_url
        assert _build_url("nonexistent") is None

    def test_api_connectivity(self):
        from app.core.api_client import api_get
        result = api_get("track_details", params={"waybill_number": "TEST"})
        assert result["ok"] is False
        assert result["error"] is not None
