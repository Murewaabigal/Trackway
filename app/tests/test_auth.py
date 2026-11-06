import os
import sys
import json
import tempfile
import shutil

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, "r") as f:
        return json.load(f)


class TestAuthService:
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

    def test_login_customer_saves_tokens(self):
        sess, orig = self._patch_session()
        data = load_fixture("login_customer_success.json")
        sess.save_tokens(data["access_token"], data["refresh_token"], data["role"])
        loaded = sess.load_session()
        assert loaded is not None
        assert loaded["access_token"] == "test-access-token-customer"
        assert loaded["role"] == "customer"
        sess._session_path = orig

    def test_login_rider_saves_tokens(self):
        sess, orig = self._patch_session()
        data = load_fixture("login_rider_success.json")
        sess.save_tokens(data["access_token"], data["refresh_token"], data["role"])
        loaded = sess.load_session()
        assert loaded is not None
        assert loaded["role"] == "rider"
        sess._session_path = orig

    def test_logout_clears_session(self):
        sess, orig = self._patch_session()
        sess.save_tokens("a", "b", "customer")
        assert sess.is_logged_in() is True
        sess.clear_session()
        assert sess.load_session() is None
        assert sess.is_logged_in() is False
        sess._session_path = orig

    def test_session_restore_after_restart(self):
        sess, orig = self._patch_session()
        sess.save_tokens("access", "refresh", "customer")
        loaded = sess.load_session()
        assert loaded is not None
        assert loaded["access_token"] == "access"
        assert loaded["refresh_token"] == "refresh"
        assert loaded["role"] == "customer"
        sess._session_path = orig

    def test_wrong_password_fixture(self):
        data = load_fixture("login_fail.json")
        assert "message" in data
        assert data["message"] == "Invalid credentials"

    def test_refresh_fixture(self):
        data = load_fixture("refresh_success.json")
        assert "access_token" in data
        assert data["access_token"] == "new-access-token"

    def test_token_extract_from_data_token(self):
        from app.services.auth_service import _extract_token
        data = {"status": "success", "data": {"customer_id": 6, "token": "real-token-abc"}}
        assert _extract_token(data) == "real-token-abc"

    def test_token_extract_top_level_access_token(self):
        from app.services.auth_service import _extract_token
        data = {"access_token": "top-token", "refresh_token": "r"}
        assert _extract_token(data) == "top-token"

    def test_token_extract_none_when_missing(self):
        from app.services.auth_service import _extract_token
        assert _extract_token({"data": {}}) is None

    def test_is_logged_in_false_with_empty_token(self):
        sess, orig = self._patch_session()
        with open(self._orig_fn, "w") as f:
            json.dump({"access_token": "", "role": "customer"}, f)
        assert sess.is_logged_in() is False
        sess._session_path = orig


class TestAuthScreens:
    def test_welcome_screen_importable(self):
        from app.views.auth.welcome_screen import WelcomeScreen
        assert WelcomeScreen is not None

    def test_customer_login_screen_importable(self):
        from app.views.auth.customer_login_screen import CustomerLoginScreen
        assert CustomerLoginScreen is not None

    def test_customer_register_screen_importable(self):
        from app.views.auth.customer_register_screen import CustomerRegisterScreen
        assert CustomerRegisterScreen is not None

    def test_rider_login_screen_importable(self):
        from app.views.auth.rider_login_screen import RiderLoginScreen
        assert RiderLoginScreen is not None

    def test_forgot_password_screen_importable(self):
        from app.views.auth.forgot_password_screen import ForgotPasswordScreen
        assert ForgotPasswordScreen is not None

    def test_customer_home_screen_importable(self):
        from app.views.customer.customer_home_screen import CustomerHomeScreen
        assert CustomerHomeScreen is not None

    def test_rider_home_screen_importable(self):
        from app.views.rider.rider_home_screen import RiderHomeScreen
        assert RiderHomeScreen is not None

    def test_auth_service_importable(self):
        from app.services.auth_service import (
            login_customer, login_rider, logout, register_customer, refresh_access_token
        )
        assert login_customer is not None
        assert login_rider is not None
        assert logout is not None
        assert register_customer is not None
        assert refresh_access_token is not None
