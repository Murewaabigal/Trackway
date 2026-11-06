import requests

from app.core.config import BASE_URL, WEB_BASE_URL, WEB_ENDPOINTS, ENDPOINTS, API_TIMEOUT
from app.core import session

# Persistent session to retain PHPSESSID cookie for web endpoints like /api/get-notifications.php
# Web rider dashboard uses Cookie: PHPSESSID, mobile rider uses Bearer for /api/v1/* but get-notifications.php historically checks cookie — reuse Session so login's Set-Cookie is sent
_http = requests.Session()

def _restore_phpsessid():
    """Restore persisted PHPSESSID from session.json into _http jar so bell works without re-login."""
    try:
        phpsessid = session.get_phpsessid()
        if phpsessid:
            current = None
            try:
                current = _http.cookies.get("PHPSESSID", domain="trackwaylogistics.ng")
            except Exception:
                pass
            if not current:
                try:
                    for c in _http.cookies:
                        if getattr(c, "name", None) == "PHPSESSID":
                            current = getattr(c, "value", None)
                            break
                except Exception:
                    pass
            # if missing or stale, overwrite both domain variants
            if current != phpsessid:
                try:
                    _http.cookies.set("PHPSESSID", phpsessid, domain="trackwaylogistics.ng", path="/")
                    _http.cookies.set("PHPSESSID", phpsessid, domain=".trackwaylogistics.ng", path="/")
                except Exception:
                    pass
            # ensure lang cookie as web does
            try:
                lang = session.get_language() or "en"
                _http.cookies.set("lang", lang, domain="trackwaylogistics.ng", path="/")
            except Exception:
                pass
    except Exception:
        pass


def _persist_phpsessid_from_response(resp):
    """Extract PHPSESSID from Set-Cookie / cookie jar after login and persist to session.json + _http jar."""
    try:
        phpsessid = None
        # 1) resp.cookies (RequestsCookieJar)
        try:
            phpsessid = resp.cookies.get("PHPSESSID")
        except Exception:
            pass
        # 2) _http jar (already updated by Session)
        if not phpsessid:
            try:
                phpsessid = _http.cookies.get("PHPSESSID", domain="trackwaylogistics.ng")
            except Exception:
                pass
            if not phpsessid:
                try:
                    for c in _http.cookies:
                        if getattr(c, "name", None) == "PHPSESSID":
                            phpsessid = getattr(c, "value", None)
                            if phpsessid:
                                break
                except Exception:
                    pass
            if not phpsessid:
                try:
                    phpsessid = resp.cookies.get("PHPSESSID", domain=".trackwaylogistics.ng")
                except Exception:
                    pass
        # 3) fallback regex on Set-Cookie header (covers Secure/SameSite variants)
        if not phpsessid:
            try:
                import re
                # resp.headers may combine multiple Set-Cookie; also check raw headers
                set_cookie = resp.headers.get("Set-Cookie", "") or ""
                # also try get_list if available (case-insensitive)
                try:
                    # requests CaseInsensitiveDict may have joined values
                    raw_list = resp.raw.headers.getlist("Set-Cookie") if hasattr(resp, "raw") and hasattr(resp.raw, "headers") else []
                    if raw_list:
                        set_cookie = "; ".join(str(v) for v in raw_list) + "; " + set_cookie
                except Exception:
                    pass
                m = re.search(r"PHPSESSID=([^;,\s]+)", set_cookie)
                if m:
                    phpsessid = m.group(1)
            except Exception:
                pass
        if phpsessid:
            phpsessid = str(phpsessid).strip().strip('"').strip("'")
            if phpsessid and len(phpsessid) >= 8:
                session.save_phpsessid(phpsessid)
                try:
                    _http.cookies.set("PHPSESSID", phpsessid, domain="trackwaylogistics.ng", path="/")
                    _http.cookies.set("PHPSESSID", phpsessid, domain=".trackwaylogistics.ng", path="/")
                except Exception:
                    pass
                try:
                    from kivy.logger import Logger as _L
                    _L.info(f"api_client: PHPSESSID persisted {phpsessid[:6]}... len={len(phpsessid)}")
                except Exception:
                    pass
    except Exception:
        pass

def fetch_web_phpsessid(username, password):
    """
    Log in via the web rider portal (rider/index.php) purely to obtain a
    PHPSESSID that get-notifications.php actually recognizes. The API login
    (api/v1/rider/login.php) issues a cookie too, but it's not accepted by
    that endpoint — this mirrors what the web dashboard does.
    """
    url = "https://trackwaylogistics.ng/rider/index.php"
    headers = {
        "User-Agent": "TrackwayMobile/1.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://trackwaylogistics.ng",
        "Referer": "https://trackwaylogistics.ng/rider/index.php",
    }
    try:
        resp = _http.post(
            url,
            data={"username": username, "password": password},
            headers=headers,
            timeout=API_TIMEOUT,
            allow_redirects=False,  # we only care about the Set-Cookie on the 302
        )
        _persist_phpsessid_from_response(resp)
        try:
            from kivy.logger import Logger as _L
            _L.info(f"api_client: web PHPSESSID login status={resp.status_code}")
        except Exception:
            pass
        return resp.status_code in (200, 302)
    except requests.RequestException:
        return False


def _persist_csrf_from_response(resp, html_text=None):
    """Extract csrf_token from HTML hidden input and persist to session.json."""
    try:
        import re as _re
        txt = html_text if html_text is not None else (resp.text if hasattr(resp, "text") else "")
        if txt:
            m = _re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', txt, _re.I)
            if not m:
                m = _re.search(r'name=["\']_token["\']\s+value=["\']([^"\']+)["\']', txt, _re.I)
            if m:
                tok = m.group(1).strip()
                if tok and len(tok) >= 8:
                    try:
                        session.save_csrf_token(tok)
                    except Exception:
                        pass
                    try:
                        from kivy.logger import Logger as _L
                        _L.debug(f"api_client: csrf_token persisted {tok[:6]}... len={len(tok)}")
                    except Exception:
                        pass
                    return tok
    except Exception:
        pass
    return None


def fetch_customer_csrf():
    """GET customer/request-ride.php HTML and extract csrf_token hidden input."""
    try:
        _restore_phpsessid()
    except Exception:
        pass
    url = f"{WEB_BASE_URL}/customer/request-ride.php"
    headers = BASE_HEADERS.copy()
    headers["Referer"] = f"{WEB_BASE_URL}/customer/dashboard.php"
    headers.pop("Authorization", None)
    headers.pop("X-Authorization", None)
    try:
        resp = _http.get(url, headers=headers, timeout=API_TIMEOUT)
        try:
            _persist_phpsessid_from_response(resp)
        except Exception:
            pass
        tok = _persist_csrf_from_response(resp)
        return tok
    except requests.RequestException:
        return None


# restore on import (fresh login and without re-login after restart)
try:
    _restore_phpsessid()
except Exception:
    pass

# One-time build verification — cheap insurance to confirm new code loaded (remove after confirming)
try:
    from kivy.logger import Logger as _InitLogger
    _InitLogger.info("Loaded api_client with _is_login_html + one-retry per call (build verification)")
except Exception:
    pass


BASE_HEADERS = {
    "User-Agent": "TrackwayMobile/1.0",
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://trackwaylogistics.ng",
    "Referer": "https://trackwaylogistics.ng/",
}


def _build_url(endpoint_key):
    path = ENDPOINTS.get(endpoint_key)
    if not path:
        return None
    # Absolute URLs are returned as-is (surgical override)
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = WEB_BASE_URL if endpoint_key in WEB_ENDPOINTS else BASE_URL
    return f"{base}/{path.lstrip('/')}"


def _is_unauthorized_error(err):
    """Detect JSON Unauthorized variants without clearing session for rider notifications."""
    if not err or not isinstance(err, str):
        return False
    low = err.strip().lower()
    return low in ("unauthorized", "unauthenticated") or "unauthorized" in low or "unauthenticated" in low or "not authenticated" in low


def _auth_headers(token, as_multipart=False):
    headers = BASE_HEADERS.copy()
    if as_multipart:
        headers.pop("Content-Type", None)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _is_login_html(text):
    """Detect Customer Login page HTML (unauthenticated redirect) — not a delivery/ride response."""
    if not text:
        return False
    low = text.lower()
    # Login page contains these three distinct markers together; avoids false-positives on normal alert pages
    return ("customer portal" in low and "welcome back" in low and "email or phone number" in low)


def _extract_html_alert(text):
    """General rule: find div.alert-danger/success and extract span text inside. Fallback to any visible body text."""
    import re
    import html as _html

    if not text:
        return None, None
    # Sanity check: login page HTML is not a delivery/ride response — treat as session expired
    if _is_login_html(text):
        return "Your session has expired, please log in again.", False
    # 1. Primary: div with alert-danger or alert-success containing a span
    m = re.search(
        r'<div[^>]*class="[^"]*alert-(?:danger|success)[^"]*"[^>]*>.*?<span[^>]*>(.*?)</span>',
        text,
        re.I | re.S,
    )
    raw_open = None
    msg_raw = None
    if m:
        msg_raw = m.group(1)
        raw_open = m.group(0)
    else:
        # Fallback 2: any alert div without span, capture inner
        m2 = re.search(r'<div[^>]*class="[^"]*alert[^"]*"[^>]*>(.*?)</div>', text, re.I | re.S)
        if m2:
            msg_raw = m2.group(1)
            raw_open = m2.group(0)
        else:
            # Fallback 3: tertiary – any visible text if no alert div (malformed/unexpected response)
            # Extract body content and strip all tags – guarantees every possible HTML error shows readable text
            body_m = re.search(r"<body[^>]*>(.*?)</body>", text, re.I | re.S)
            raw_body = body_m.group(1) if body_m else text
            # Also try to find any element with id message/alert/error
            m3 = re.search(r'<(?:p|span|div)[^>]*id="(?:message|alert|error|msg)"[^>]*>(.*?)</(?:p|span|div)>', text, re.I | re.S)
            if m3:
                msg_raw = m3.group(1)
                raw_open = m3.group(0)
            else:
                msg_raw = raw_body
                raw_open = raw_body
    if msg_raw is None:
        return None, None
    # Strip any remaining tags and decode entities, normalize whitespace
    msg = re.sub(r"<[^>]+>", " ", msg_raw)
    msg = _html.unescape(msg)
    msg = " ".join(msg.split())
    # Sanitize confusing web redirect artifact – show exact requested text
    low = msg.lower()
    if "register.php?success=1" in low or "window.location.href" in low:
        return "Registration successful, user can now login", True
    # Truncate very long unexpected pages to 300 chars readable excerpt, keep full alert span intact
    if len(msg) > 300 and raw_open and "alert-" not in raw_open.lower():
        msg = msg[:300].rsplit(" ", 1)[0] + "…"
    if not msg:
        return None, None
    is_success = bool(raw_open and "alert-success" in raw_open.lower())
    # For fallback body text, heuristically detect success vs error
    if not is_success and raw_open and "alert-danger" in raw_open.lower():
        is_success = False
    elif not raw_open or "alert-" not in raw_open.lower():
        low = msg.lower()
        # Heuristic for non-alert fallback: look for success keywords
        if any(k in low for k in ("registration successful", "account created", "successfully")) and not any(
            k in low for k in ("error", "failed", "invalid", "already")
        ):
            is_success = True
        else:
            is_success = False
    else:
        is_success = is_success and "alert-danger" not in raw_open.lower()
    return msg, is_success


def _handle_response(resp, endpoint_key=None):
    try:
        data = resp.json()
    except ValueError:
        from kivy.logger import Logger as _Logger
        text = resp.text or ""
        # Rider profile GET is HTML by design (not JSON) — treat 200 HTML page as success for scraping, BEFORE alert parsing
        # This must come before _extract_html_alert which would otherwise treat body text as fake error
        if endpoint_key == "rider_profile" and 200 <= resp.status_code < 300 and "rider profile" in text.lower():
            _Logger.debug(f"rider_profile HTML success len={len(text)} (suppressed chunk dump)")
            return {"ok": True, "data": {"raw_html": text, "message": "OK"}, "error": None, "warning": None}
        # Rider wallet HTML page (without ?ajax=1) is also HTML by design — suppress noisy dump, treat as debug
        if endpoint_key in ("rider_wallet", "rider_wallet_json") and 200 <= resp.status_code < 300 and "available balance" in text.lower():
            # This is the HTML wallet page, not JSON. Caller should use ?ajax=1 for JSON. Suppress full dump.
            _Logger.debug(f"rider_wallet HTML page len={len(text)} (no ajax param — use ajax=1 for JSON)")
            # Return as error with limited preview to avoid 80-chunk spam
            _Logger.info(f"rider_wallet HTML page without ajax — suppressing full dump, preview: {text[:300]!r}")
            return {"ok": False, "data": {"raw_html": text[:2000]}, "error": "Wallet HTML page (use ajax=1 for JSON)"}
        # Customer request-ride form HTML validation error — suppress 28-chunk dump, show clean Snackbar
        if endpoint_key == "request_ride" and 200 <= resp.status_code < 300 and "request a ride" in text.lower():
            _Logger.debug(f"request_ride HTML form len={len(text)} (validation error, not 302 — suppressed dump)")
            msg, is_success = _extract_html_alert(text)
            if msg:
                _Logger.info(f"request_ride validation error: {msg!r}")
                return {"ok": False, "data": {"raw_html": text[:2000], "message": msg}, "error": msg}
            _Logger.info(f"request_ride HTML without alert — preview: {text[:300]!r}")
            return {"ok": False, "data": {"raw_html": text[:2000]}, "error": "Please check your inputs"}
        # Customer dashboard HTML server-rendered stats — success for HTML scrape, not error
        if endpoint_key == "customer_dashboard_html" and 200 <= resp.status_code < 300 and "stat-card" in text.lower():
            _Logger.debug(f"customer_dashboard_html HTML success len={len(text)} (suppressed chunk dump)")
            return {"ok": True, "data": {"raw_html": text, "message": "OK"}, "error": None, "warning": None}
        _Logger.info(f"RAW HTML CT={resp.headers.get('Content-Type')} status={resp.status_code} len={len(resp.text)}")
        for i in range(0, len(resp.text), 2000):
            _Logger.info(f"RAW HTML chunk {i//2000}: {resp.text[i:i+2000]!r}")
        # Sanity: login page HTML means not authenticated — don't scrape it as error wall
        if _is_login_html(text):
            _Logger.info("HTML login page detected — treating as session expired")
            return {"ok": False, "data": {"raw_html": text[:800]}, "error": "Your session has expired, please log in again."}
        msg, is_success = _extract_html_alert(text)
        if msg:
            if is_success and 200 <= resp.status_code < 300:
                _Logger.info(f"HTML alert-success parsed: {msg!r}")
                return {"ok": True, "data": {"message": msg, "raw_html": text[:800]}, "error": None, "warning": None}
            else:
                _Logger.info(f"HTML alert parsed (error): {msg!r}")
                # Unify shape: error is the real span/body text, data.message same – customer_register_screen shows result["error"]
                return {"ok": False, "data": {"message": msg, "raw_html": text[:800]}, "error": msg}
        # True fallback – still readable even if extractor returned None (e.g., empty body)
        import re as _re
        import html as _html2

        fallback_raw = text.strip()
        fallback = _html2.unescape(_re.sub(r"<[^>]+>", " ", fallback_raw))
        fallback = " ".join(fallback.split())[:300] or f"Error {resp.status_code}"
        low_fb = fallback.lower()
        if "register.php?success=1" in low_fb or "window.location.href" in low_fb:
            _Logger.info(f"HTML redirect sanitized to success")
            return {"ok": True, "data": {"message": "Registration successful, user can now login", "raw_html": text[:800]}, "error": None, "warning": None}
        _Logger.info(f"HTML fallback parsed: {fallback!r}")
        return {"ok": False, "data": {"raw_html": text[:800]}, "error": fallback}

    if 200 <= resp.status_code < 300:
        return {"ok": True, "data": data, "error": None}

    error_msg = (
        data.get("message")
        or data.get("error")
        or f"Error {resp.status_code}"
    )
    # Surface field-level validation errors (e.g., {"errors": {"phone": ["already taken"]}})
    errors = None
    if isinstance(data, dict):
        errors = data.get("errors") or data.get("Errors")
        if not errors and isinstance(data.get("data"), dict):
            errors = data["data"].get("errors") or data["data"].get("Errors")
        # Some APIs nest under data.data.errors
        if not errors and isinstance(data.get("data"), dict) and isinstance(data["data"].get("data"), dict):
            errors = data["data"]["data"].get("errors")
    if errors and isinstance(errors, dict):
        try:
            details_parts = []
            for k, v in errors.items():
                if isinstance(v, list):
                    msg = ", ".join(str(x) for x in v)
                else:
                    msg = str(v)
                details_parts.append(f"{k}: {msg}")
            details = "; ".join(details_parts)
            if details:
                error_msg = f"{error_msg}: {details}" if error_msg else details
        except Exception:
            pass
    elif errors and isinstance(errors, list):
        try:
            details = "; ".join(str(x) for x in errors)
            if details:
                error_msg = f"{error_msg}: {details}" if error_msg else details
        except Exception:
            pass
    elif isinstance(errors, str) and errors:
        error_msg = f"{error_msg}: {errors}" if error_msg else errors
    else:
        # Generic fallback: surface any field-level clue for any error type (phone, password, name, referral, etc.)
        # Covers {"data":"..."}, {"detail":"..."}, {"details":[...]}, {"reason":"..."}
        fallback = None
        if isinstance(data.get("data"), str) and data["data"]:
            fallback = data["data"]
        elif isinstance(data.get("detail"), str) and data["detail"]:
            fallback = data["detail"]
        elif isinstance(data.get("details"), str) and data["details"]:
            fallback = data["details"]
        elif isinstance(data.get("details"), list):
            try:
                fallback = "; ".join(str(x) for x in data["details"])
            except Exception:
                fallback = None
        elif isinstance(data.get("reason"), str) and data["reason"]:
            fallback = data["reason"]
        if fallback:
            # Avoid duplicating if fallback already contained in error_msg
            if fallback not in error_msg:
                error_msg = f"{error_msg}: {fallback}" if error_msg else fallback
    return {"ok": False, "data": data, "error": error_msg}


def _attempt_refresh():
    refresh = session.get_refresh_token()
    role = session.get_role()
    if not refresh:
        return False

    refresh_key = "refresh_rider_token" if role == "rider" else "refresh_token"
    url = _build_url(refresh_key)
    if not url:
        return False

    try:
        resp = _http.post(
            url,
            data={"refresh_token": refresh},
            headers=_auth_headers(None),
            timeout=API_TIMEOUT,
        )
        # persist refreshed PHPSESSID if server rotates it
        try:
            _persist_phpsessid_from_response(resp)
        except Exception:
            pass
        if resp.status_code == 200:
            data = resp.json()
            new_access = (
                data.get("access_token")
                or data.get("data", {}).get("access_token")
            )
            if new_access:
                # Preserve customer_name on refresh — don't clear it
                try:
                    name = session.get_customer_name()
                except Exception:
                    name = ""
                session.save_tokens(new_access, refresh, role, name)
                return new_access
    except requests.RequestException:
        pass
    return False


def api_get(endpoint_key, params=None, token=None):
    url = _build_url(endpoint_key)
    if not url:
        return {"ok": False, "data": None, "error": f"Unknown endpoint: {endpoint_key}"}

    if token is None:
        token = session.get_access_token()

    retried = False
    # Ensure persisted PHPSESSID is in jar before any get-notifications call (without re-login)
    try:
        _restore_phpsessid()
    except Exception:
        pass
    # Rider get-notifications.php is cookie-only — never send Bearer. Only "cookie-only" has been
    # tested and confirmed working; "Bearer alone" fails; "Cookie+Bearer" untested → avoid.
    # This replicates the real web app (no Authorization header on this call).
    def _headers_for_get(tok):
        is_customer_web = endpoint_key in ("customer_dashboard_html",)
        is_rider_web = endpoint_key in ("get_notifications", "rider_notifications", "customer_notifications", "rider_profile", "rider_wallet", "rider_wallet_json")
        try:
            role = session.get_role() if is_rider_web else None
            is_rider = role and str(role).lower() == "rider"
        except Exception:
            is_rider = False
        if is_rider_web and is_rider:
            try:
                phpsessid = session.get_phpsessid()
            except Exception:
                phpsessid = None
            if phpsessid:
                # Cookie-only: strip any Authorization/X-Authorization, use web Referer, keep jar cookies
                h = BASE_HEADERS.copy()
                # wallet/profile referer is itself for GET/POST; dashboard for notifications
                if endpoint_key == "rider_profile":
                    h["Referer"] = "https://trackwaylogistics.ng/rider/profile.php"
                elif endpoint_key in ("rider_wallet", "rider_wallet_json"):
                    h["Referer"] = "https://trackwaylogistics.ng/rider/wallet.php"
                else:
                    h["Referer"] = "https://trackwaylogistics.ng/rider/dashboard.php"
                h.pop("Authorization", None)
                h.pop("X-Authorization", None)
                return h
            # No PHPSESSID yet (e.g. legacy session) — fall through to Bearer but will map to retry UI
        # customer dashboard HTML is also cookie-only WEB
        if is_customer_web:
            try:
                role_c = session.get_role()
                is_cust = role_c and str(role_c).lower() == "customer"
            except Exception:
                is_cust = False
            if is_cust:
                try:
                    phpsessid_c = session.get_phpsessid()
                except Exception:
                    phpsessid_c = None
                if phpsessid_c:
                    h = BASE_HEADERS.copy()
                    h["Referer"] = "https://trackwaylogistics.ng/customer/dashboard.php"
                    h.pop("Authorization", None)
                    h.pop("X-Authorization", None)
                    return h
                # fall through to Bearer if no phpsessid but still set Referer
        h = _auth_headers(tok)
        if is_rider_web and is_rider:
            try:
                if endpoint_key == "rider_profile":
                    h["Referer"] = "https://trackwaylogistics.ng/rider/profile.php"
                elif endpoint_key in ("rider_wallet", "rider_wallet_json"):
                    h["Referer"] = "https://trackwaylogistics.ng/rider/wallet.php"
                else:
                    h["Referer"] = "https://trackwaylogistics.ng/rider/dashboard.php"
            except Exception:
                pass
        elif is_customer_web:
            try:
                h["Referer"] = "https://trackwaylogistics.ng/customer/dashboard.php"
            except Exception:
                pass
        return h

    # debug for verify_payment to compare vs web without needing browser devtools next capture
    if endpoint_key == "verify_payment":
        try:
            from kivy.logger import Logger as _L
            _L.info(f"[DEBUG verify_payment] GET url={url!r} params={params!r}")
        except Exception:
            pass
    try:
        resp = _http.get(
            url,
            params=params,
            headers=_headers_for_get(token),
            timeout=API_TIMEOUT,
        )
        if endpoint_key == "verify_payment":
            try:
                from kivy.logger import Logger as _L
                _L.info(f"[DEBUG verify_payment] response status={resp.status_code} ct={resp.headers.get('Content-Type')} len={len(resp.text)} preview={resp.text[:300]!r}")
            except Exception:
                pass
    except requests.Timeout:
        return {"ok": False, "data": None, "error": "Connection timed out"}
    except requests.ConnectionError:
        return {"ok": False, "data": None, "error": "No internet connection"}

    if resp.status_code == 401 and token and not retried:
        new_token = _attempt_refresh()
        if new_token:
            retried = True
            try:
                resp = _http.get(
                    url,
                    params=params,
                    headers=_headers_for_get(new_token),
                    timeout=API_TIMEOUT,
                )
            except requests.RequestException:
                return {"ok": False, "data": None, "error": "Connection failed"}
        else:
            session.clear_session()
            return {
                "ok": False,
                "data": None,
                "error": "Session expired. Please log in again.",
            }

    result = _handle_response(resp, endpoint_key)
    # HTML login page comes as 200 (not 401) for WEB endpoints — treat as session expired and try refresh (one retry total per call)
    if not result.get("ok") and result.get("error") == "Your session has expired, please log in again." and token and not retried:
        new_token = _attempt_refresh()
        if new_token:
            retried = True
            try:
                resp = _http.get(
                    url,
                    params=params,
                    headers=_headers_for_get(new_token),
                    timeout=API_TIMEOUT,
                )
                result = _handle_response(resp, endpoint_key)
                # If still login HTML after refresh, clear and inform
                if not result.get("ok") and result.get("error") == "Your session has expired, please log in again.":
                    session.clear_session()
            except requests.RequestException:
                return {"ok": False, "data": None, "error": "Connection failed"}
        else:
            session.clear_session()
    elif not result.get("ok") and result.get("error") == "Your session has expired, please log in again." and retried:
        session.clear_session()

    # JSON Unauthorized for notification endpoints — keep session alive, try one refresh without clearing
    # Rider dashboard deliveries/wallet already proved Bearer works, so get-notifications.php Unauthorized is likely token scope mismatch — retry once with fresh token but do NOT clear session on second failure (show retry UI instead)
    if not result.get("ok") and _is_unauthorized_error(result.get("error")) and token and not retried:
        # Only for notification endpoints keep session; for others preserve existing Session expired behavior
        if endpoint_key in ("get_notifications", "rider_notifications", "customer_notifications"):
            new_token = _attempt_refresh()
            if new_token:
                retried = True
                try:
                    resp = _http.get(
                        url,
                        params=params,
                        headers=_headers_for_get(new_token),
                        timeout=API_TIMEOUT,
                    )
                    result = _handle_response(resp, endpoint_key)
                    # If still unauthorized after refresh, keep session and surface retry-friendly error
                    if not result.get("ok") and _is_unauthorized_error(result.get("error")):
                        return {"ok": False, "data": result.get("data"), "error": "Unable to load notifications. Tap Retry."}
                except requests.RequestException:
                    return {"ok": False, "data": None, "error": "Connection failed"}
            else:
                # No refresh token — keep session, show retry instead of forcing login
                return {"ok": False, "data": result.get("data"), "error": "Unable to load notifications. Tap Retry."}
        # For non-notification endpoints, if still unauthorized after potential refresh above, let normal Session expired flow handle? keep as is
    elif not result.get("ok") and _is_unauthorized_error(result.get("error")) and retried:
        if endpoint_key in ("get_notifications", "rider_notifications", "customer_notifications"):
            return {"ok": False, "data": result.get("data"), "error": "Unable to load notifications. Tap Retry."}
    # Also handle Unauthorized that arrived with 200 success:false payload without prior 401
    if not result.get("ok") and _is_unauthorized_error(result.get("error")) and endpoint_key in ("get_notifications", "rider_notifications", "customer_notifications"):
        # Ensure raw "Unauthorized" never bubbles to UI
        if result.get("error") and result["error"].strip().lower() == "unauthorized":
            result["error"] = "Unable to load notifications. Tap Retry."
    return result


def api_post(endpoint_key, payload=None, token=None, files=None, as_multipart=False):
    url = _build_url(endpoint_key)
    if not url:
        return {"ok": False, "data": None, "error": f"Unknown endpoint: {endpoint_key}"}

    if token is None:
        token = session.get_access_token()

    retried = False
    use_multipart = as_multipart or files is not None
    # Rider profile and customer request-ride are cookie-only WEB pages — use Referer + strip Bearer when PHPSESSID exists
    is_rider_profile = endpoint_key == "rider_profile"
    is_request_ride = endpoint_key == "request_ride"
    try:
        _restore_phpsessid()
    except Exception:
        pass
    # Ensure customer request-ride includes csrf_token (session/cookie-based, like register_customer)
    if is_request_ride and payload is not None and isinstance(payload, dict) and "csrf_token" not in payload:
        try:
            tok = session.get_csrf_token() if hasattr(session, "get_csrf_token") else None
            if not tok:
                tok = fetch_customer_csrf()
            if tok:
                payload = dict(payload)
                payload["csrf_token"] = tok
        except Exception:
            pass
    if is_rider_profile:
        try:
            role = session.get_role()
            is_rider = role and str(role).lower() == "rider"
        except Exception:
            is_rider = False
        if is_rider:
            try:
                phpsessid = session.get_phpsessid()
            except Exception:
                phpsessid = None
            if phpsessid:
                headers = BASE_HEADERS.copy()
                if use_multipart:
                    headers.pop("Content-Type", None)
                headers["Referer"] = "https://trackwaylogistics.ng/rider/profile.php"
                headers.pop("Authorization", None)
                headers.pop("X-Authorization", None)
            else:
                headers = _auth_headers(token, as_multipart=use_multipart)
                headers["Referer"] = "https://trackwaylogistics.ng/rider/profile.php"
        else:
            headers = _auth_headers(token, as_multipart=use_multipart)
    elif is_request_ride:
        # Customer request-ride WEB session/cookie — same as register_customer, not api/v1 Bearer
        try:
            phpsessid = session.get_phpsessid()
        except Exception:
            phpsessid = None
        if phpsessid:
            headers = BASE_HEADERS.copy()
            if use_multipart:
                headers.pop("Content-Type", None)
            headers["Referer"] = "https://trackwaylogistics.ng/customer/request-ride.php"
            headers["Origin"] = "https://trackwaylogistics.ng"
            headers.pop("Authorization", None)
            headers.pop("X-Authorization", None)
        else:
            headers = BASE_HEADERS.copy()
            if not use_multipart:
                # keep x-www-form-urlencoded
                pass
            else:
                headers.pop("Content-Type", None)
            headers["Referer"] = "https://trackwaylogistics.ng/customer/request-ride.php"
            headers["Origin"] = "https://trackwaylogistics.ng"
            headers.pop("Authorization", None)
            headers.pop("X-Authorization", None)
    else:
        headers = _auth_headers(token, as_multipart=use_multipart)

    def _do_post(hdrs):
        # For customer request-ride WEB 302 → Paystack, we need allow_redirects=False to capture Location header
        allow_redir = False if is_request_ride else True
        if use_multipart:
            if files:
                return _http.post(
                    url,
                    data=payload or {},
                    files=files,
                    headers=hdrs,
                    timeout=API_TIMEOUT,
                    allow_redirects=allow_redir,
                )
            else:
                from urllib3.filepost import encode_multipart_formdata

                body, content_type = encode_multipart_formdata(payload or {})
                hdrs = hdrs.copy()
                hdrs["Content-Type"] = content_type
                return _http.post(
                    url,
                    data=body,
                    headers=hdrs,
                    timeout=API_TIMEOUT,
                    allow_redirects=allow_redir,
                )
        else:
            return _http.post(
                url,
                data=payload or {},
                headers=hdrs,
                timeout=API_TIMEOUT,
                allow_redirects=allow_redir,
            )

    try:
        resp = _do_post(headers)
        # Persist PHPSESSID right after receiving Set-Cookie — login_rider relies on this for get-notifications.php
        try:
            if endpoint_key in ("login_rider", "login_customer", "refresh_rider_token", "refresh_token"):
                _persist_phpsessid_from_response(resp)
        except Exception:
            pass
    except requests.Timeout:
        return {"ok": False, "data": None, "error": "Connection timed out"}
    except requests.ConnectionError:
        return {"ok": False, "data": None, "error": "No internet connection"}

    # WEB customer request-ride returns 302 Found with Location: https://checkout.paystack.com/{ref}
    if is_request_ride and resp.status_code in (301, 302, 303, 307, 308):
        try:
            _persist_phpsessid_from_response(resp)
        except Exception:
            pass
        try:
            _persist_csrf_from_response(resp, resp.text if hasattr(resp, "text") else "")
        except Exception:
            pass
        location = resp.headers.get("Location") or resp.headers.get("location") or ""
        if location:
            import re as _re2
            ref = ""
            m = _re2.search(r"(?:reference|trxref|access_code)=([^&]+)", location)
            if m:
                ref = m.group(1)
            else:
                m2 = _re2.search(r"paystack\.com/([^/?&#]+)", location)
                if m2:
                    ref = m2.group(1)
            # consider any 302 with Location as success for this endpoint
            return {"ok": True, "data": {"authorization_url": location, "reference": ref, "paystack_url": location, "url": location, "raw_html": ""}, "error": None}

    if resp.status_code == 401 and token and not retried:
        new_token = _attempt_refresh()
        if new_token:
            retried = True
            try:
                if is_rider_profile:
                    try:
                        role2 = session.get_role()
                        is_r2 = role2 and str(role2).lower() == "rider"
                    except Exception:
                        is_r2 = False
                    if is_r2:
                        try:
                            phpsessid2 = session.get_phpsessid()
                        except Exception:
                            phpsessid2 = None
                        if phpsessid2:
                            retry_headers = BASE_HEADERS.copy()
                            if use_multipart:
                                retry_headers.pop("Content-Type", None)
                            retry_headers["Referer"] = "https://trackwaylogistics.ng/rider/profile.php"
                            retry_headers.pop("Authorization", None)
                            retry_headers.pop("X-Authorization", None)
                        else:
                            retry_headers = _auth_headers(new_token, as_multipart=use_multipart)
                            retry_headers["Referer"] = "https://trackwaylogistics.ng/rider/profile.php"
                    else:
                        retry_headers = _auth_headers(new_token, as_multipart=use_multipart)
                else:
                    retry_headers = _auth_headers(new_token, as_multipart=use_multipart)
                resp = _do_post(retry_headers)
                try:
                    if endpoint_key in ("login_rider", "login_customer", "refresh_rider_token", "refresh_token"):
                        _persist_phpsessid_from_response(resp)
                except Exception:
                    pass
            except requests.RequestException:
                return {"ok": False, "data": None, "error": "Connection failed"}
        else:
            session.clear_session()
            return {
                "ok": False,
                "data": None,
                "error": "Session expired. Please log in again.",
            }

    result = _handle_response(resp, endpoint_key)
    # After successful handle, persist again if result ok (covers case where Set-Cookie arrived with 200)
    try:
        if result.get("ok") and endpoint_key in ("login_rider", "login_customer", "refresh_rider_token", "refresh_token"):
            _persist_phpsessid_from_response(resp)
    except Exception:
        pass
    # HTML login page comes as 200 for WEB endpoints — treat as session expired (one retry total per call)
    if not result.get("ok") and result.get("error") == "Your session has expired, please log in again." and token and not retried:
        new_token = _attempt_refresh()
        if new_token:
            retried = True
            try:
                if is_rider_profile:
                    try:
                        role3 = session.get_role()
                        is_r3 = role3 and str(role3).lower() == "rider"
                    except Exception:
                        is_r3 = False
                    if is_r3:
                        try:
                            phpsessid3 = session.get_phpsessid()
                        except Exception:
                            phpsessid3 = None
                        if phpsessid3:
                            retry_headers = BASE_HEADERS.copy()
                            if use_multipart:
                                retry_headers.pop("Content-Type", None)
                            retry_headers["Referer"] = "https://trackwaylogistics.ng/rider/profile.php"
                            retry_headers.pop("Authorization", None)
                            retry_headers.pop("X-Authorization", None)
                        else:
                            retry_headers = _auth_headers(new_token, as_multipart=use_multipart)
                            retry_headers["Referer"] = "https://trackwaylogistics.ng/rider/profile.php"
                    else:
                        retry_headers = _auth_headers(new_token, as_multipart=use_multipart)
                else:
                    retry_headers = _auth_headers(new_token, as_multipart=use_multipart)
                resp = _do_post(retry_headers)
                result = _handle_response(resp, endpoint_key)
                if not result.get("ok") and result.get("error") == "Your session has expired, please log in again.":
                    session.clear_session()
            except requests.RequestException:
                return {"ok": False, "data": None, "error": "Connection failed"}
        else:
            session.clear_session()
    elif not result.get("ok") and result.get("error") == "Your session has expired, please log in again." and retried:
        session.clear_session()

    # JSON Unauthorized for notifications — keep session alive, surface retry
    if not result.get("ok") and _is_unauthorized_error(result.get("error")) and token and not retried and endpoint_key in ("get_notifications", "rider_notifications", "customer_notifications"):
        new_token = _attempt_refresh()
        if new_token:
            retried = True
            try:
                retry_headers = _auth_headers(new_token, as_multipart=use_multipart)
                if endpoint_key in ("get_notifications", "rider_notifications", "customer_notifications"):
                    from app.core import session as _sess2
                    role2 = _sess2.get_role()
                    if role2 and str(role2).lower() == "rider":
                        retry_headers["Referer"] = "https://trackwaylogistics.ng/rider/dashboard.php"
                resp = _do_post(retry_headers)
                result = _handle_response(resp, endpoint_key)
                if not result.get("ok") and _is_unauthorized_error(result.get("error")):
                    return {"ok": False, "data": result.get("data"), "error": "Unable to load notifications. Tap Retry."}
            except requests.RequestException:
                return {"ok": False, "data": None, "error": "Connection failed"}
        else:
            return {"ok": False, "data": result.get("data"), "error": "Unable to load notifications. Tap Retry."}
    elif not result.get("ok") and _is_unauthorized_error(result.get("error")) and retried and endpoint_key in ("get_notifications", "rider_notifications", "customer_notifications"):
        return {"ok": False, "data": result.get("data"), "error": "Unable to load notifications. Tap Retry."}
    if not result.get("ok") and _is_unauthorized_error(result.get("error")) and endpoint_key in ("get_notifications", "rider_notifications", "customer_notifications"):
        if result.get("error") and result["error"].strip().lower() == "unauthorized":
            result["error"] = "Unable to load notifications. Tap Retry."
    return result
