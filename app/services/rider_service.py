from app.core import api_client as _api_client


def _pick(data, *keys, default=None):
    for k in keys:
        if isinstance(data, dict) and data.get(k) is not None:
            return data.get(k)
    return default


def _unwrap(result):
    if not result.get("ok"):
        return result
    data = result.get("data")
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        # unwrap single nesting like {"data": {"total_deliveries":...}}
        inner = data["data"]
        # only unwrap if inner looks like payload not envelope
        if any(k in inner for k in ("total_deliveries","completed","total_earnings","wallet_balance","commission_rate")):
            return {"ok": True, "data": inner, "error": None}
    return result


def get_rider_dashboard():
    """Fetch rider dashboard stats — tries rider-specific endpoint, falls back to individual wallet/earnings."""
    result = _unwrap(_api_client.api_get("rider_deliveries"))
    # Primary is rider_deliveries info, but stats are often in wallet/earnings; merge attempt
    if not result.get("ok"):
        # empty state fallback — zeros as seen in screenshots 172915/172928 empty states
        return {"ok": True, "data": {"total_deliveries": 0, "completed": 0, "in_progress": 0, "total_earnings": "0.00", "rating": "0.0", "wallet_balance": "0.00", "total_earned": "0.00", "total_withdrawn": "0.00", "commission_rate": "80%", "customer_name": "", "unread_count": 0}, "error": None}
    d = result.get("data") or {}
    # Also try wallet for balance — use JSON variant with ajax=1 to avoid HTML page dump
    wallet = {}
    try:
        # prefer JSON wallet endpoint
        w = get_rider_wallet_json(page=1, limit=1)
        if w.get("ok"):
            wallet = w.get("data") or {}
        else:
            # fallback to old api (may be HTML) — ignore if HTML
            w2 = _unwrap(_api_client.api_get("rider_wallet", params={"ajax": 1}))
            if w2.get("ok"):
                wallet = w2.get("data") or {}
    except Exception:
        wallet = {}
    out = {
        "total_deliveries": _pick(d, "total_deliveries", "total", "deliveries_total", default=_pick(wallet, "total_deliveries", default=0)),
        "completed": _pick(d, "completed", "total_completed", "delivered", default=0),
        "in_progress": _pick(d, "in_progress", "active", "in_transit", default=0),
        "total_earnings": _pick(d, "total_earnings", "totalEarnings", "earnings", default=_pick(wallet, "total_earnings", default="0.00")),
        "rating": _pick(d, "rating", "avg_rating", "stars", default="0.0"),
        "wallet_balance": _pick(wallet, "wallet_balance", "balance", "current_balance", default=_pick(d, "wallet_balance", default="0.00")),
        "total_earned": _pick(wallet, "total_earned", "totalEarnings", default="0.00"),
        "total_withdrawn": _pick(wallet, "total_withdrawn", "totalWithdrawn", default="0.00"),
        "commission_rate": _pick(wallet, "commission_rate", "commissionRate", default="80%"),
        "customer_name": _pick(d, "name", "full_name", "rider_name", "customer_name", default=_pick(wallet, "name", default="")),
        "unread_count": _pick(d, "unread_count", default=0),
    }
    # normalize commission_rate to "80%" string
    cr = out["commission_rate"]
    if isinstance(cr, (int, float)):
        out["commission_rate"] = f"{int(cr)}%"
    elif isinstance(cr, str) and "%" not in cr and cr.replace(".","",1).isdigit():
        out["commission_rate"] = f"{cr}%"
    return {"ok": True, "data": out, "error": None}


def get_active_deliveries(page=1):
    result = _unwrap(_api_client.api_get("rider_deliveries", params={"status": "active", "page": page}))
    if not result.get("ok"):
        return result
    d = result.get("data") or {}
    items = _pick(d, "deliveries", "items", "data", "results", default=[])
    return {"ok": True, "data": {"items": items if isinstance(items, list) else [], "has_more": _pick(d, "has_more", default=False)}, "error": None}


def get_recent_transactions(page=1):
    result = _unwrap(_api_client.api_get("rider_wallet_json", params={"ajax": 1, "page": page}))
    if not result.get("ok"):
        return result
    d = result.get("data") or {}
    items = _pick(d, "transactions", "recent_transactions", "items", "data", default=[])
    return {"ok": True, "data": {"items": items if isinstance(items, list) else []}, "error": None}


def get_today_schedule(page=1):
    result = _unwrap(_api_client.api_get("rider_deliveries", params={"date": "today", "page": page}))
    if not result.get("ok"):
        return result
    d = result.get("data") or {}
    items = _pick(d, "deliveries", "items", "data", "today", default=[])
    return {"ok": True, "data": {"items": items if isinstance(items, list) else [], "count": _pick(d, "count", "total", default=len(items) if isinstance(items, list) else 0)}, "error": None}


def get_wallet():
    result = _unwrap(_api_client.api_get("rider_wallet_json", params={"ajax": 1}))
    if not result.get("ok"):
        return result
    return result


def update_online_status(online: bool):
    result = _api_client.api_post("rider_update_status" if False else "rider_update_location", payload={"online": "1" if online else "0"})
    return _unwrap(result)


def update_location(lat, lng):
    result = _api_client.api_post("rider_update_location", payload={"lat": str(lat), "lng": str(lng)})
    return _unwrap(result)


def get_rider_notifications(page=1):
    # real endpoint is https://trackwaylogistics.ng/api/get-notifications.php (no limit, page only, Bearer scoped)
    # Rider popup should match web: https://trackwaylogistics.ng/rider/dashboard.php referer + Bearer — api_client now handles referer for this key
    result = _api_client.api_get("get_notifications", params={"page": page})
    if not result.get("ok"):
        # Map raw Unauthorized to retry-friendly without clearing session (keep rider logged in as web does)
        err = result.get("error") or ""
        low = str(err).strip().lower()
        if low == "unauthorized" or "unauthorized" in low or "unauthenticated" in low:
            return {"ok": False, "data": result.get("data"), "error": "Unable to load notifications. Tap Retry."}
        return result
    d = result.get("data") or {}
    # handle {"success":true,"notifications":[...]} vs success:false (real error) — web returns success:true with notifications list
    if isinstance(d, dict) and "success" in d:
        if d.get("success") is not True and d.get("success") not in (1, "1", "true", True):
            raw = d.get("message") or d.get("error") or "Unable to load notifications, please try again"
            low2 = str(raw).strip().lower()
            if low2 == "unauthorized" or "unauthorized" in low2:
                return {"ok": False, "data": d, "error": "Unable to load notifications. Tap Retry."}
            return {"ok": False, "data": d, "error": raw}
        if "notifications" in d:
            notifs = d.get("notifications") or []
            return {
                "ok": True,
                "error": None,
                "data": {
                    "items": notifs if isinstance(notifs, list) else [],
                    "notifications": notifs if isinstance(notifs, list) else [],
                    "unread_count": _pick(d, "unread_count", default=0),
                    "total": len(notifs) if isinstance(notifs, list) else 0,
                    "has_more": False,
                    "page": page,
                },
            }
    notifs = _pick(d, "notifications", "items", "data", default=[])
    if isinstance(notifs, dict):
        notifs = _pick(notifs, "notifications", "items", "data", default=[])
    if not isinstance(notifs, list):
        notifs = []
    return {
        "ok": True,
        "error": None,
        "data": {
            "items": notifs,
            "notifications": notifs,
            "unread_count": _pick(d, "unread_count", default=0),
            "total": _pick(d, "total", "total_records", default=len(notifs)),
            "has_more": _pick(d, "has_more", default=False),
            "page": _pick(d, "page", default=page),
        },
    }


def mark_rider_notification_read(notification_id):
    result = _api_client.api_post("mark_rider_notification_read", payload={"notification_id": notification_id})
    return _unwrap(result)


def mark_all_rider_notifications_read():
    result = _api_client.api_post("mark_all_rider_notifications_read", payload={})
    return _unwrap(result)


# ── Rider Profile (rider/profile.php — WEB HTML page, same POST url for both forms) ──
import re as _re
import html as _html


def _parse_rider_profile_html(html_text: str):
    """Parse rider/profile.php HTML into structured dict. Best-effort, no bs4 dep."""
    if not html_text:
        return {}
    raw = html_text
    out = {
        "full_name": "",
        "username": "",
        "phone": "",
        "email": "",
        "rider_id": "",
        "joined": "",
        "vehicle_pill": "",
        "vehicle": {"vehicle_type": "N/A", "bike_ownership": "N/A", "bike_model": "N/A", "plate_number": "N/A"},
        "metrics": {"total_deliveries": 0, "completed": 0, "rating": "0.0", "active": 0, "failed": 0, "cancelled": 0, "total_earnings": "0.00"},
        "account": {"account_status": "Active", "verification_status": "Verified", "last_login": "-", "member_since": "-"},
    }
    try:
        # input values — live: name="full_name" value="Akinpelu Faith" etc; username has NO name attr, only value+disabled
        m = _re.search(r'name="full_name"[^>]*value="([^"]*)"', raw, _re.I | _re.S)
        if m:
            out["full_name"] = _html.unescape(m.group(1)).strip()
        # fallback to profile-name div if input missing (web vs api difference)
        if not out["full_name"]:
            m0 = _re.search(r'class="profile-name"[^>]*>\s*([^<]+?)\s*</div>', raw, _re.I | _re.S)
            if m0:
                out["full_name"] = _html.unescape(m0.group(1)).strip()
        # username live: <label>Username</label> <input value="akinpelu.faith91" disabled>  (no name attr)
        m = _re.search(r'name="username"[^>]*value="([^"]*)"', raw, _re.I | _re.S)
        if m:
            out["username"] = _html.unescape(m.group(1)).strip()
        if not out["username"]:
            m2 = _re.search(r'Username[^<]*</label>\s*<input[^>]*value="([^"]*)"', raw, _re.I | _re.S)
            if m2:
                out["username"] = _html.unescape(m2.group(1)).strip()
            else:
                m2 = _re.search(r'Username[^<]*</[^>]+>\s*<[^>]*>([^<]+)</', raw, _re.I)
                if m2:
                    out["username"] = _html.unescape(m2.group(1)).strip()
        m = _re.search(r'name="phone"[^>]*value="([^"]*)"', raw, _re.I | _re.S)
        if m:
            out["phone"] = _html.unescape(m.group(1)).strip()
        m = _re.search(r'name="email"[^>]*value="([^"]*)"', raw, _re.I | _re.S)
        if m:
            out["email"] = _html.unescape(m.group(1)).strip()
        # Rider ID — live inside profile-meta-item with icon: <i ...></i> Rider ID: RID...
        m = _re.search(r'Rider ID:\s*([A-Z0-9\-]+)', raw, _re.I)
        if m:
            out["rider_id"] = m.group(1).strip()
        # Joined — live "Joined August 2026" (no day)
        m = _re.search(r'Joined\s+([A-Za-z]+\s+\d{4})', raw, _re.I)
        if m:
            out["joined"] = m.group(1).strip()
        else:
            m = _re.search(r'Joined[^<]*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', raw, _re.I)
            if m:
                out["joined"] = m.group(1).strip()
        # Vehicle pill — live <div class="profile-badge"> <i ...></i> Own Bike Rider </div>
        m = _re.search(r'class="[^"]*profile-badge[^"]*"[^>]*>.*?([A-Za-z ]+Rider)\s*</div>', raw, _re.I | _re.S)
        if m:
            out["vehicle_pill"] = _html.unescape(m.group(1)).strip()
        if not out["vehicle_pill"]:
            m = _re.search(r'class="[^"]*badge[^"]*"[^>]*>\s*(?:&#x1f3cd;|🏍|<i[^>]*>.*?</i>)?\s*([^<]+?)\s*</', raw, _re.I | _re.S)
            if m:
                cand = _html.unescape(m.group(1)).strip()
                # strip stray tags
                cand = _re.sub(r'<[^>]+>', '', cand).strip()
                if cand:
                    out["vehicle_pill"] = cand
        if not out["vehicle_pill"]:
            m = _re.search(r'(Own Bike Rider|Company Bike Rider|Bike Rider|Vehicle Rider)', raw, _re.I)
            if m:
                out["vehicle_pill"] = m.group(1).strip()
        # Vehicle info 4 blocks — labels Vehicle Type, Bike Ownership, Bike Model, Plate Number
        for label, key in [("Vehicle Type", "vehicle_type"), ("Bike Ownership", "bike_ownership"), ("Bike Model", "bike_model"), ("Plate Number", "plate_number")]:
            pat = _re.escape(label) + r'[^<]*</[^>]+>\s*<[^>]*>([^<]+)</'
            m = _re.search(pat, raw, _re.I)
            if m:
                out["vehicle"][key] = _html.unescape(m.group(1)).strip() or "N/A"
        # Metrics — Total Deliveries / Completed / Rating (big) + Active/Failed/Cancelled/Total Earnings (small)
        # Big stats have value BEFORE label in live HTML: <div class="stat-value">0</div><div class="stat-label">Total Deliveries</div>
        def _num_near(label):
            # try label before value (info-item style)
            pat = _re.escape(label) + r'[^<]*</[^>]+>\s*<[^>]*>([^<]+)</'
            mm = _re.search(pat, raw, _re.I)
            if mm:
                cand = _html.unescape(mm.group(1)).strip()
                # ensure cand looks like value not another label
                if cand and not _re.match(r'^(Total Deliveries|Completed|Rating|Active|Failed|Cancelled|Total Earnings)$', cand, _re.I):
                    return cand
            # try value BEFORE label (stats-grid style) — search value then label
            pat_rev = r'<div[^>]*class="[^"]*stat-value[^"]*"[^>]*>.*?(?:<[^>]+>)*\s*([0-9][0-9,\.\s]*|0\.0)\s*.*?</div>\s*<div[^>]*class="[^"]*stat-label[^"]*"[^>]*>\s*' + _re.escape(label) + r'\s*</div>'
            mm2 = _re.search(pat_rev, raw, _re.I | _re.S)
            if mm2:
                return _re.sub(r'<[^>]+>', '', mm2.group(1)).strip()
            # fallback generic: value before label without stat class
            pat_rev2 = r'>([^<]*[0-9][^<]*?)</[^>]+>\s*[^<]*<[^>]*>\s*' + _re.escape(label)
            # actually search for label and look backwards 500 chars for number
            m_lbl = _re.search(_re.escape(label), raw, _re.I)
            if m_lbl:
                start = max(0, m_lbl.start() - 600)
                snippet = raw[start:m_lbl.start()]
                # find last number in snippet that looks like stat-value
                nums = _re.findall(r'<div[^>]*class="[^"]*stat-value[^"]*"[^>]*>(.*?)</div>', snippet, _re.I | _re.S)
                if nums:
                    last = _re.sub(r'<[^>]+>', '', nums[-1]).strip()
                    if last:
                        return _html.unescape(last).strip()
            # alternative: label then number div generic
            pat2 = label + r'.*?([0-9][0-9,\.\s]*|₦[0-9,\.]+|0\.0)'
            mm3 = _re.search(pat2, raw, _re.I | _re.S)
            if mm3:
                return mm3.group(1).strip()
            return ""
        # Build map of big stats by pairing stat-value -> stat-label correctly (value before label)
        _stat_map = {}
        try:
            pairs = _re.findall(r'<div[^>]*class="[^"]*stat-value[^"]*"[^>]*>(.*?)</div>\s*<div[^>]*class="[^"]*stat-label[^"]*"[^>]*>\s*([^<]+?)\s*</div>', raw, _re.I | _re.S)
            for val_html, lbl in pairs:
                lbl_clean = _html.unescape(_re.sub(r'<[^>]+>', '', lbl)).strip()
                val_clean = _html.unescape(_re.sub(r'<[^>]+>', '', val_html)).strip()
                if lbl_clean:
                    _stat_map[lbl_clean.lower()] = val_clean
        except Exception:
            _stat_map = {}
        def _big_search(label):
            low = label.lower()
            if low in _stat_map:
                return _stat_map[low]
            pat = r'<div[^>]*class="[^"]*stat-value[^"]*"[^>]*>.*?(.*?)</div>\s*<div[^>]*class="[^"]*stat-label[^"]*"[^>]*>\s*' + _re.escape(label) + r'\s*</div>'
            m = _re.search(pat, raw, _re.I | _re.S)
            if m:
                raw_val = _re.sub(r'<[^>]+>', '', m.group(1)).strip()
                return _html.unescape(raw_val).strip()
            return _num_near(label)
        td = _big_search("Total Deliveries")
        if td:
            try:
                out["metrics"]["total_deliveries"] = int(_re.sub(r"[^\d]", "", td) or 0)
            except Exception:
                out["metrics"]["total_deliveries"] = td
        comp = _big_search("Completed")
        if comp:
            try:
                out["metrics"]["completed"] = int(_re.sub(r"[^\d]", "", comp) or 0)
            except Exception:
                out["metrics"]["completed"] = comp
        rat = _big_search("Rating")
        if rat:
            # rating contains star icon HTML, strip non-numeric
            cleaned = _re.sub(r'<[^>]+>', '', rat)
            cleaned = _re.sub(r'[^\d\.]', '', cleaned) or rat
            # ensure dot
            if cleaned and cleaned.strip():
                rat = cleaned.strip()
            out["metrics"]["rating"] = rat.replace("★", "").strip() or "0.0"
        for lbl, k in [("Active", "active"), ("Failed", "failed"), ("Cancelled", "cancelled")]:
            v = _num_near(lbl)
            if v:
                try:
                    out["metrics"][k] = int(_re.sub(r"[^\d]", "", v) or 0)
                except Exception:
                    out["metrics"][k] = v
        earn = _num_near("Total Earnings")
        if earn:
            out["metrics"]["total_earnings"] = earn
        # Account status
        m = _re.search(r'Account Status[^<]*</[^>]+>\s*<[^>]*>([^<]+)</', raw, _re.I)
        if m:
            out["account"]["account_status"] = _html.unescape(m.group(1)).strip()
        else:
            if "Active" in raw:
                out["account"]["account_status"] = "Active"
        m = _re.search(r'Verification Status[^<]*</[^>]+>\s*<[^>]*>([^<]+)</', raw, _re.I)
        if m:
            out["account"]["verification_status"] = _html.unescape(m.group(1)).strip()
        m = _re.search(r'Last Login[^<]*</[^>]+>\s*<[^>]*>([^<]+)</', raw, _re.I)
        if m:
            out["account"]["last_login"] = _html.unescape(m.group(1)).strip()
        m = _re.search(r'Member Since[^<]*</[^>]+>\s*<[^>]*>([^<]+)</', raw, _re.I)
        if m:
            out["account"]["member_since"] = _html.unescape(m.group(1)).strip()
    except Exception:
        pass
    return out


def get_rider_profile():
    """GET rider/profile.php (WEB HTML) and parse into structured data."""
    result = _api_client.api_get("rider_profile")
    if not result.get("ok"):
        # api_client maps HTML login redirect to "Your session has expired..."
        try:
            from kivy.logger import Logger as _L
            _L.info(f"RIDER PROFILE fetch failed ok=False error={result.get('error')!r}")
        except Exception:
            pass
        return result
    data = result.get("data") or {}
    html_text = data.get("raw_html") if isinstance(data, dict) else None
    if html_text and isinstance(html_text, str) and "rider profile" in html_text.lower():
        parsed = _parse_rider_profile_html(html_text)
        # Debug logging: whether scrape found key fields (ask requested)
        try:
            from kivy.logger import Logger as _L
            has_name = bool(parsed.get("full_name"))
            has_rid = bool(parsed.get("rider_id"))
            has_joined = bool(parsed.get("joined"))
            has_pill = parsed.get("vehicle_pill") or ""
            has_phone = bool(parsed.get("phone"))
            has_email = bool(parsed.get("email"))
            has_user = bool(parsed.get("username"))
            _L.info(f"RIDER PROFILE scrape: profile-name={'Akinpelu' in html_text} Rider ID: found={has_rid} val={parsed.get('rider_id')!r} Joined found={has_joined} val={parsed.get('joined')!r} pill={has_pill!r} full_name={parsed.get('full_name')!r} username={parsed.get('username')!r} phone={parsed.get('phone')!r} email={parsed.get('email')!r} html_len={len(html_text)} has_name={has_name} has_phone={has_phone} has_email={has_email} has_user={has_user}")
        except Exception:
            pass
        return {"ok": True, "error": None, "data": {**parsed, "raw_html": html_text}}
    # JSON fallback (future api/v1)
    if isinstance(data, dict):
        # try to normalize JSON shape
        out = {
            "full_name": _pick(data, "full_name", "name", "rider_name", default=""),
            "username": _pick(data, "username", default=""),
            "phone": _pick(data, "phone", default=""),
            "email": _pick(data, "email", default=""),
            "rider_id": _pick(data, "rider_id", "rider_unique_id", default=""),
            "joined": _pick(data, "joined", "created_at", default=""),
            "vehicle_pill": _pick(data, "vehicle_pill", "vehicle_type_label", default=""),
            "vehicle": _pick(data, "vehicle", default={"vehicle_type": "N/A", "bike_ownership": "N/A", "bike_model": "N/A", "plate_number": "N/A"}),
            "metrics": _pick(data, "metrics", "performance", default={"total_deliveries": 0, "completed": 0, "rating": "0.0", "active": 0, "failed": 0, "cancelled": 0, "total_earnings": "0.00"}),
            "account": _pick(data, "account", default={"account_status": "Active", "verification_status": "Verified", "last_login": "-", "member_since": "-"}),
        }
        return {"ok": True, "error": None, "data": {**out, "raw_html": html_text or ""}}
    return {"ok": True, "error": None, "data": _parse_rider_profile_html(html_text or "")}


def update_rider_profile(payload: dict):
    """POST rider/profile.php with flag update_profile — saves full_name/phone/email."""
    clean = {k: v for k, v in (payload or {}).items() if v is not None}
    clean["update_profile"] = clean.get("update_profile") or "1"
    result = _api_client.api_post("rider_profile", payload=clean)
    # _handle_response already extracts alert-success/danger text into error/message
    return result


def change_rider_password(payload: dict):
    """POST rider/profile.php with flag change_password."""
    clean = {k: v for k, v in (payload or {}).items() if v is not None}
    clean["change_password"] = clean.get("change_password") or "1"
    result = _api_client.api_post("rider_profile", payload=clean)
    return result


def get_rider_banks():
    """GET rider/banks.php — returns [{bank_code,bank_name}]"""
    result = _api_client.api_get("rider_banks")
    if not result.get("ok"):
        return result
    d = result.get("data") or {}
    # handle {status,data:[...]} or {data:[...]}
    if isinstance(d, dict) and isinstance(d.get("data"), list):
        banks = d.get("data")
    elif isinstance(d, list):
        banks = d
    else:
        banks = _pick(d, "data", "banks", default=[])
        if isinstance(banks, dict) and isinstance(banks.get("data"), list):
            banks = banks["data"]
    if not isinstance(banks, list):
        banks = []
    # normalize to {bank_code,bank_name}
    out = []
    for b in banks:
        if not isinstance(b, dict):
            continue
        code = str(_pick(b, "bank_code", "bankCode", "code", default="")).strip()
        name = str(_pick(b, "bank_name", "bankName", "name", default="")).strip()
        if code and name:
            out.append({"bank_code": code, "bank_name": name})
    return {"ok": True, "error": None, "data": out}


def resolve_rider_account(account_number: str, bank_code: str):
    """GET rider/resolve-account.php?account_number=&bank_code= — returns account_name"""
    result = _api_client.api_get("rider_resolve_account", params={"account_number": str(account_number).strip(), "bank_code": str(bank_code).strip()})
    if not result.get("ok"):
        return result
    d = result.get("data") or {}
    # capture unknown field: account_name may be under data.account_name or data.data.account_name
    inner = d
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        inner = d["data"]
    # try many keys until we find something
    cand = _pick(inner, "account_name", "accountName", "account_name_verified", "name", "account_holder", "holder_name", default=None)
    if cand is None and isinstance(d, dict):
        cand = _pick(d, "account_name", "accountName", "name", default=None)
    if cand is None:
        # also check raw string data
        if isinstance(d, str) and d:
            cand = d
        else:
            cand = ""
    try:
        from kivy.logger import Logger as _L
        _L.info(f"resolve: bank={bank_code} acc={account_number} name={cand!r} raw={str(d)[:300]!r}")
    except Exception:
        pass
    if cand and str(cand).strip():
        return {"ok": True, "error": None, "data": {"account_name": str(cand).strip(), "raw": d}}
    # if no candidate but ok, treat as error to show message
    err = _pick(inner, "message", "error", default="Could not verify account")
    return {"ok": False, "error": str(err) or "Could not verify account", "data": d}


def request_rider_withdrawal(amount, bank_code: str, account_number: str, account_name: str):
    """POST rider/withdraw.php form-data {amount,bank_code,account_number,account_name}"""
    payload = {
        "amount": f"{float(str(amount).replace(',', '').strip() or 0):.2f}",
        "bank_code": str(bank_code).strip(),
        "account_number": str(account_number).strip(),
        "account_name": str(account_name).strip(),
    }
    result = _api_client.api_post("rider_withdraw", payload=payload)
    return result


def get_rider_wallet_json(page: int = 1, limit: int = 20):
    """GET rider/wallet.php?ajax=1&page=1&limit=20 — JSON, session-cookie auth."""
    result = _api_client.api_get("rider_wallet_json", params={"ajax": 1, "page": page, "limit": limit})
    if not result.get("ok"):
        try:
            from kivy.logger import Logger as _L
            _L.info(f"RIDER WALLET fetch failed ok=False error={result.get('error')!r}")
        except Exception:
            pass
        return result
    d = result.get("data") or {}
    # handle nested {"data": {...}} envelope
    if isinstance(d, dict) and isinstance(d.get("data"), dict) and "balance" in d["data"]:
        d = d["data"]
    out = {
        "balance": _pick(d, "balance", default="0.00"),
        "total_earned": _pick(d, "total_earned", "totalEarned", default="0.00"),
        "total_credit": _pick(d, "total_credit", "totalCredit", default="0.00"),
        "total_withdrawn": _pick(d, "total_withdrawn", "totalWithdrawn", default="0.00"),
        "transaction_count": _pick(d, "transaction_count", "transactionCount", default=0),
        "total_pages": _pick(d, "total_pages", "totalPages", default=0),
        "current_page": _pick(d, "current_page", "currentPage", default=page),
    }
    # normalize counts to int
    for k in ("transaction_count", "total_pages", "current_page"):
        try:
            out[k] = int(str(out[k]).strip() or 0)
        except Exception:
            try:
                out[k] = int(float(str(out[k]).strip() or 0))
            except Exception:
                out[k] = 0
    # normalize money strings to 2 decimals
    for k in ("balance", "total_earned", "total_credit", "total_withdrawn"):
        raw = str(out[k]).replace(",", "").replace("₦", "").strip() or "0.00"
        try:
            out[k] = f"{float(raw):.2f}"
        except Exception:
            out[k] = "0.00"
    try:
        from kivy.logger import Logger as _L
        _L.info(f"RIDER WALLET json: balance={out['balance']} earned={out['total_earned']} withdrawn={out['total_withdrawn']} tx={out['transaction_count']} pages={out['total_pages']}")
    except Exception:
        pass
    return {"ok": True, "error": None, "data": out}


RIDER_SUPPORT_TYPES = {
    "delivery_issue": "Delivery Issue",
    "payment_wallet_issue": "Payment/Wallet Issue",
    "technical_app_issue": "Technical/App Issue",
    "account_issue": "Account Issue",
    "vehicle_bike_issue": "Vehicle/Bike Issue",
    "customer_related_issue": "Customer-Related Issue",
    "other": "Other",
}
# Only delivery_issue verified vs live rider/support/submit.php 2026-09-23; other 6 slugs pending backend confirmation


def _parse_rider_waybill(wb: dict):
    """Isolated parser for waybills-list.php shape — one-line fix if shape changes."""
    if not isinstance(wb, dict):
        return {"waybill_id": "", "waybill_number": "", "label": str(wb), "raw": wb}
    waybill_id = str(_pick(wb, "waybill_id", "id", "waybillId", default="")).strip()
    waybill_number = str(_pick(wb, "waybill_number", "waybill", "number", "waybillNumber", default=waybill_id)).strip()
    origin = _pick(wb, "origin", "origin_city", "from", "originCity", default="")
    dest = _pick(wb, "destination", "destination_city", "to", "destinationCity", default="")
    label = f"{waybill_number}  {origin}->{dest}" if waybill_number else str(wb)
    if len(label) > 48:
        label = label[:47] + "…"
    return {"waybill_id": waybill_id, "waybill_number": waybill_number, "label": label, "raw": wb}


def get_rider_support_waybills(limit: int = 20):
    result = _api_client.api_get("rider_support_waybills", params={"limit": int(limit)})
    if not result.get("ok"):
        return result
    d = result.get("data") or {}
    # handle {data:[...]} or {data:{data:[...]}} or direct list
    items = None
    if isinstance(d, list):
        items = d
    elif isinstance(d, dict) and isinstance(d.get("data"), list):
        items = d.get("data")
    else:
        items = _pick(d, "data", "waybills", "items", "results", default=[])
        if isinstance(items, dict) and isinstance(items.get("data"), list):
            items = items["data"]
    if not isinstance(items, list):
        items = []
    parsed = [_parse_rider_waybill(wb) for wb in items if isinstance(wb, dict) or wb]
    # keep raw items also for UI but normalize
    return {"ok": True, "error": None, "data": {"items": parsed, "raw": items}}


def submit_rider_support(payload: dict):
    # payload expects type, subject, message, waybill_id optional
    result = _api_client.api_post("rider_support_submit", payload=payload or {})
    if not result.get("ok"):
        # surface clear error for unverified type slugs
        err = result.get("error") or ""
        # BUG REPORT 2026-09-23: if type is unverified and server rejects, show type-specific message
        if payload and payload.get("type") in RIDER_SUPPORT_TYPES and "type" in err.lower():
            err = f"Request type '{payload.get('type')}' not accepted: {err} — try delivery_issue or contact backend"
            result["error"] = err
        return result
    d = result.get("data") or {}
    inner = d.get("data") if isinstance(d.get("data"), dict) else d
    cid = _pick(inner, "complaint_id", "id", "complaintId", default=_pick(d, "complaint_id", "id", default=""))
    if cid:
        # normalize to ticket_id
        if isinstance(d, dict):
            d["ticket_id"] = str(cid)
        if isinstance(inner, dict):
            inner["ticket_id"] = str(cid)
    return result


def get_rider_support_list():
    # Pagination NOT implemented server-side — list.php?page=2 returns identical unpaginated list, so no page param
    result = _api_client.api_get("rider_support_list")
    if not result.get("ok"):
        return result
    d = result.get("data") or {}
    items = None
    if isinstance(d, list):
        items = d
    elif isinstance(d, dict) and isinstance(d.get("data"), list):
        items = d.get("data")
    else:
        items = _pick(d, "data", "items", "complaints", "tickets", "results", "list", default=[])
        if isinstance(items, dict) and isinstance(items.get("data"), list):
            items = items["data"]
    if not isinstance(items, list):
        items = []
    out = []
    for t in items:
        if not isinstance(t, dict):
            continue
        tid = _pick(t, "complaint_id", "id", "complaintId", default="")
        t2 = dict(t)
        t2["ticket_id"] = str(tid) if tid else ""
        # BUG REPORT 2026-09-23: rider/support/list.php returns type/type_name empty even when submit sends type=delivery_issue — backend not persisting, client hides
        out.append(t2)
    return {"ok": True, "error": None, "data": {"items": out, "has_more": False}}


def get_rider_deliveries(status=None, search=None, page=1):
    """GET /api/v1/rider/deliveries.php?status?search?page — rider View All Deliveries"""
    # Assumption 2026-09-23: spec 6 tabs fold 8 API statuses (in_transit folds arrived/out_for_delivery, failed folds cancelled) — verify vs live ?status=pending capture
    params = {"page": int(page or 1)}
    if status and status not in ("all", "", None):
        # map UI slug to API slug via folded mapping
        mapping = {"all": "", "pending": "pending_pickup", "picked_up": "picked_up", "in_transit": "in_transit", "delivered": "delivered", "failed": "failed"}
        # allow direct API slugs to pass through
        if status in mapping:
            api_status = mapping[status]
            if api_status:
                params["status"] = api_status
        elif status in ("pending_pickup", "picked_up", "in_transit", "arrived_destination_city", "out_for_delivery", "delivered", "failed", "cancelled"):
            params["status"] = status
        else:
            params["status"] = status
    if search:
        params["search"] = str(search).strip()
    result = _unwrap(_api_client.api_get("rider_deliveries", params=params))
    if not result.get("ok"):
        try:
            from kivy.logger import Logger as _L
            _L.info(f"RIDER DELIVERIES fetch failed status={status!r} search={search!r} page={page} error={result.get('error')!r}")
        except Exception:
            pass
        return result
    d = result.get("data") or {}
    # handle {data:{...}} envelope already unwrapped above, but handle pagination envelope
    items = _pick(d, "deliveries", "items", "data", "results", "list", default=[])
    if isinstance(items, dict) and isinstance(items.get("data"), list):
        items = items["data"]
    if not isinstance(items, list):
        items = []
    # TODO Q5: populated waybill card layout not visible yet — needs funded account sample (waybill_number/status/origin/destination/date/fee)
    has_more = _pick(d, "has_more", "hasMore", default=False)
    # also derive from total_pages if has_more missing
    if not isinstance(has_more, bool):
        has_more = bool(has_more)
    if not has_more:
        total = _pick(d, "total", "total_count", "count", "total_records", default=None)
        cur = _pick(d, "page", "current_page", default=page)
        total_pages = _pick(d, "total_pages", default=None)
        if total_pages is not None and cur is not None:
            try:
                has_more = int(cur) < int(total_pages)
            except Exception:
                pass
        elif total is not None:
            try:
                has_more = len(items) < int(total)
            except Exception:
                pass
    return {"ok": True, "error": None, "data": {"items": items, "has_more": bool(has_more), "page": _pick(d, "page", "current_page", default=page), "total": _pick(d, "total", "total_count", "total_records", default=len(items))}}


def get_rider_delivery_status_counts():
    # try rider-specific counts; fallback to deriving from empty (all 0) — counts show on all 6 pills per Q3
    result = _api_client.api_get("rider_deliveries", params={"counts": 1})
    if result.get("ok"):
        d = result.get("data") or {}
        if isinstance(d, dict) and isinstance(d.get("data"), dict):
            d = d["data"]
        # try to find counts dict
        counts_raw = _pick(d, "status_counts", "counts", "statusCounts", default=None)
        if isinstance(counts_raw, dict):
            # normalize folded counts (if API returns split arrived/out_for_delivery, sum into in_transit)
            out = {}
            for k, v in counts_raw.items():
                try:
                    cnt = int(v) if isinstance(v, int) else int(float(str(v).strip() or 0))
                except Exception:
                    cnt = 0
                out[k] = cnt
            # fold assumption: in_transit includes arrived + out_for_delivery; failed includes cancelled
            if "in_transit" in out or any(k in out for k in ("arrived_destination_city","out_for_delivery")):
                try:
                    out["in_transit"] = int(out.get("in_transit",0) or 0) + int(out.get("arrived_destination_city",0) or 0) + int(out.get("out_for_delivery",0) or 0)
                except Exception:
                    pass
            if "failed" in out or "cancelled" in out:
                try:
                    out["failed"] = int(out.get("failed",0) or 0) + int(out.get("cancelled",0) or 0)
                except Exception:
                    pass
            return {"ok": True, "error": None, "data": out}
    # fallback: try customer status_counts endpoint (may still work with rider token, but likely not) — skip
    return {"ok": False, "error": "Counts not available", "data": {}}


def get_rider_earnings(period: str = "month", year: int = 2026, month: int = 9):
    """GET /api/v1/rider/earnings.php?period={week|month|year}&year={int}&month={int}"""
    period = str(period or "month").strip().lower()
    if period not in ("week", "month", "year"):
        period = "month"
    try:
        year = int(year)
    except Exception:
        year = 2026
    try:
        month = int(month)
    except Exception:
        month = 9
    month = max(1, min(12, month))
    result = _api_client.api_get("rider_earnings", params={"period": period, "year": year, "month": month})
    if not result.get("ok"):
        try:
            from kivy.logger import Logger as _L
            _L.info(f"RIDER EARNINGS fetch failed period={period} {month}/{year} error={result.get('error')!r}")
        except Exception:
            pass
        return result
    d = result.get("data") or {}
    if isinstance(d, dict) and isinstance(d.get("data"), dict) and any(k in d["data"] for k in ("total_earnings", "completed_deliveries", "commission_percentage")):
        d = d["data"]
    out = {
        "total_earnings": _pick(d, "total_earnings", "totalEarnings", "total", "earnings", default="0.00"),
        "formatted_total": _pick(d, "formatted_total_earnings", "formatted_total", "total_earnings_formatted", default=None),
        "completed_deliveries": _pick(d, "completed_deliveries", "completed", "delivered", "total_completed", default=0),
        "avg_earning": _pick(d, "avg_earning", "average_per_delivery", "avgPerDelivery", "average", "avg", default="0.00"),
        "formatted_avg": _pick(d, "formatted_avg_earning", "formatted_avg", "avg_formatted", "average_formatted", default=None),
        "commission_percentage": _pick(d, "commission_percentage", "commission_rate", "rate", "commission", default="80"),
        "chart_data": _pick(d, "chart_data", "chartData", "earnings_by_period", "chart", default={"labels": [], "values": [], "type": "bar"}),
        "recent_earnings": _pick(d, "recent_earnings", "recentEarnings", "recent", "items", "data", default=[]),
    }
    # normalize
    try:
        out["completed_deliveries"] = int(str(out["completed_deliveries"]).strip() or 0)
    except Exception:
        try:
            out["completed_deliveries"] = int(float(str(out["completed_deliveries"]).strip() or 0))
        except Exception:
            out["completed_deliveries"] = 0
    # commission
    try:
        cr = str(out["commission_percentage"]).strip().replace("%", "")
        out["commission_percentage"] = f"{int(float(cr))}%"
    except Exception:
        out["commission_percentage"] = "80%"
    # display totals from formatted or raw
    for raw_key, fmt_key, disp_key in [("total_earnings", "formatted_total", "display_total"), ("avg_earning", "formatted_avg", "display_avg")]:
        fmt = out.get(fmt_key)
        if fmt and str(fmt).strip():
            out[disp_key] = str(fmt).strip()
            # ensure ₦ prefix if fmt lacks and contains numeric
            if "₦" not in out[disp_key] and any(c.isdigit() for c in out[disp_key]):
                try:
                    # if fmt already formatted, keep; else add ₦
                    if out[disp_key].replace(".", "", 1).replace(",", "",).isdigit():
                        out[disp_key] = f"₦{float(str(fmt).replace('₦','').replace(',','') or 0):.2f}"
                except Exception:
                    pass
        else:
            raw = str(out.get(raw_key, "0.00")).replace(",", "").replace("₦", "").strip() or "0.00"
            try:
                out[disp_key] = f"₦{float(raw):.2f}"
            except Exception:
                out[disp_key] = "₦0.00"
    # chart_data normalize
    cd = out.get("chart_data")
    if not isinstance(cd, dict):
        cd = {"labels": [], "values": [], "type": "bar"}
    if not isinstance(cd.get("labels"), list):
        cd["labels"] = []
    if not isinstance(cd.get("values"), list):
        cd["values"] = []
    if not isinstance(cd.get("type"), str):
        cd["type"] = "bar"
    out["chart_data"] = cd
    if not isinstance(out["recent_earnings"], list):
        out["recent_earnings"] = []
    try:
        from kivy.logger import Logger as _L
        _L.info(f"RIDER EARNINGS period={period} {month}/{year} total={out.get('display_total')} completed={out['completed_deliveries']} avg={out.get('display_avg')} commission={out['commission_percentage']} chart_len={len(cd.get('labels',[]))} recent={len(out['recent_earnings'])}")
    except Exception:
        pass
    return {"ok": True, "error": None, "data": out}
