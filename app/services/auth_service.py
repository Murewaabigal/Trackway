import os
import re

from app.core.api_client import api_get, api_post
from app.core import session

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _extract_token(data):
    return (
        data.get("token")
        or data.get("access_token")
        or (data.get("data") or {}).get("token")
        or (data.get("data") or {}).get("access_token")
    )


def _extract_refresh(data):
    return (
        data.get("refresh_token")
        or (data.get("data") or {}).get("refresh_token")
    )


def _extract_name(data):
    # Primary key is data.name as confirmed: data.name = "Akinpelu Faith" alongside data.token
    return (
        data.get("name")
        or data.get("full_name")
        or (data.get("data") or {}).get("name")
        or (data.get("data") or {}).get("full_name")
        or (data.get("data") or {}).get("customer_name")
        or ""
    )


def _is_email_warning(data, error_msg):
    """Detect 'account created, email failed' soft-warning pattern."""
    candidates = []
    if error_msg:
        candidates.append(str(error_msg))
    if isinstance(data, dict):
        for key in ("message", "warning", "email_error", "detail", "msg", "error", "data"):
            v = data.get(key)
            if isinstance(v, str):
                candidates.append(v)
            elif isinstance(v, dict):
                candidates.append(str(v))
        inner = data.get("data") if isinstance(data.get("data"), dict) else None
        if inner:
            for key in ("message", "warning", "email_error", "error"):
                v = inner.get(key)
                if isinstance(v, str):
                    candidates.append(v)
    combined = " ".join(candidates).lower()
    has_email = "email" in combined
    has_fail = any(k in combined for k in ("fail", "could not", "not sent", "not send", "error", "unable", "unsent"))
    return has_email and has_fail


def _extract_warning(data, error_msg):
    if isinstance(data, dict):
        for key in ("warning", "email_error", "email_warning"):
            v = data.get(key)
            if isinstance(v, str) and v:
                return v
            inner = data.get("data") if isinstance(data.get("data"), dict) else None
            if inner and isinstance(inner.get(key), str) and inner.get(key):
                return inner.get(key)
    # fallback to error_msg if it looks like email warning
    if _is_email_warning(data, error_msg):
        return error_msg or "Account created, but welcome email failed to send."
    return None


def register_customer(full_name, phone, password, password_confirm, email=None, referral_code=None, send_welcome_email=False, profile_picture_path=None):
    # Hard block defense: do not send welcome flag without valid email (matches web HTML5 validation)
    if send_welcome_email and (not email or not _EMAIL_RE.match(email.strip())):
        return {"ok": False, "data": None, "error": "Please provide a valid email address to send welcome email, or uncheck 'Send welcome email'."}
    # Strict web parity: exact field names from cURL export
    payload = {
        "full_name": full_name,
        "phone": phone,
        "password": password,
        "confirm_password": password_confirm,
    }
    if email:
        payload["email"] = email
    if referral_code:
        payload["referral_code"] = referral_code
    if send_welcome_email:
        payload["send_welcome_email"] = "on"
    # profile_picture is optional file field – no UI yet, just plumbing

    files = None
    fh = None
    try:
        if profile_picture_path and os.path.exists(profile_picture_path):
            try:
                fh = open(profile_picture_path, "rb")
                # Guess mime; default to image/jpeg if unknown
                fname = os.path.basename(profile_picture_path)
                files = {"profile_picture": (fname, fh, "image/jpeg")}
            except Exception:
                files = None
                fh = None

        result = api_post("register_customer", payload=payload, files=files, as_multipart=True)

        # Success path – also check for embedded warning even on 2xx
        if result["ok"]:
            data = result["data"]
            warning = _extract_warning(data, None)
            # If warning present, surface it alongside success
            if warning and _is_email_warning(data, warning):
                access = _extract_token(data)
                refresh = _extract_refresh(data)
                name = _extract_name(data)
                if access:
                    session.save_tokens(access, refresh, "customer", name)
                result = {"ok": True, "data": data, "error": None, "warning": warning}
                return result
            # Normal success
            access = _extract_token(data)
            refresh = _extract_refresh(data)
            name = _extract_name(data)
            if access:
                session.save_tokens(access, refresh, "customer", name)
            # Ensure warning key exists for caller convenience
            if "warning" not in result:
                result["warning"] = warning
            return result

        # Failure path – check if it's actually a soft warning (account created, email failed)
        data = result.get("data")
        err = result.get("error")
        if _is_email_warning(data, err):
            access = _extract_token(data if isinstance(data, dict) else {})
            if access:
                refresh = _extract_refresh(data if isinstance(data, dict) else {})
                name = _extract_name(data if isinstance(data, dict) else {})
                session.save_tokens(access, refresh, "customer", name)
                warning = _extract_warning(data, err)
                return {"ok": True, "data": data, "error": None, "warning": warning or err}

        return result
    finally:
        if fh:
            try:
                fh.close()
            except Exception:
                pass


def login_customer(email_or_phone, password):
    payload = {
        "username": email_or_phone,
        "password": password,
    }
    result = api_post("login_customer", payload=payload)
    if result["ok"]:
        data = result["data"]
        access = _extract_token(data)
        refresh = _extract_refresh(data)
        name = _extract_name(data)
        if access:
            session.save_tokens(access, refresh, "customer", name)
        # Customer notifications also use get-notifications.php which checks cookie —
        # try web login as well if credentials work there (best-effort, same endpoint family)
        try:
            from app.core.api_client import fetch_web_phpsessid
            fetch_web_phpsessid(email_or_phone, password)
        except Exception:
            pass
    return result


def login_rider(email_or_phone, password):
    payload = {
        "username": email_or_phone,
        "password": password,
    }
    result = api_post("login_rider", payload=payload)
    if result["ok"]:
        data = result["data"]
        access = _extract_token(data)
        refresh = _extract_refresh(data)
        name = _extract_name(data)
        if access:
            session.save_tokens(access, refresh, "rider", name)
        # Separately obtain a working PHPSESSID via the web login flow,
        # since the API login's cookie isn't accepted by get-notifications.php
        try:
            from app.core.api_client import fetch_web_phpsessid
            fetch_web_phpsessid(email_or_phone, password)
        except Exception:
            pass
    return result


def refresh_access_token():
    refresh = session.get_refresh_token()
    role = session.get_role()
    if not refresh:
        return {"ok": False, "data": None, "error": "No refresh token"}

    refresh_key = "refresh_rider_token" if role == "rider" else "refresh_token"
    result = api_post(refresh_key, payload={"refresh_token": refresh})
    if result["ok"]:
        data = result["data"]
        new_access = data.get("access_token") or data.get("data", {}).get("access_token")
        if new_access:
            # Preserve existing name on refresh
            try:
                name = session.get_customer_name()
            except Exception:
                name = ""
            session.save_tokens(new_access, refresh, role, name)
            return {"ok": True, "data": {"access_token": new_access}, "error": None}
    return {"ok": False, "data": None, "error": "Token refresh failed"}


def check_referral(referral_code):
    """Inline validation via check-referral.php – mirrors web JS Apply flow."""
    code = (referral_code or "").strip()
    if not code:
        return {"ok": False, "data": None, "error": "Please enter referral code"}
    result = api_post("check_referral", payload={"referral_code": code})
    # api_client already extracts real error/success text (JSON or HTML alert span)
    return result


def logout():
    role = session.get_role()
    logout_key = "logout_rider" if role == "rider" else "logout_customer"
    api_post(logout_key)
    session.clear_session()
    return {"ok": True, "data": None, "error": None}
