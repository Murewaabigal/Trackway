import re as _re
import html as _html

from app.core import api_client as _api_client


def _pick(data, *keys, default=None):
    for key in keys:
        if isinstance(data, dict) and data.get(key) is not None:
            return data.get(key)
    return default


def _unwrap(result):
    """Return the inner data payload from an api result, best-effort."""
    if not result["ok"]:
        return result
    data = result["data"]
    if isinstance(data, dict):
        inner = data.get("data", data)
        return {"ok": True, "data": inner, "error": None}
    return result


def _parse_customer_dashboard_html(html_text: str):
    """Parse customer/dashboard.php HTML server-rendered stat-cards: <small>Total Rides</small><h3>10</h3>"""
    if not html_text:
        return {}
    raw = html_text
    out = {}
    try:
        pairs = _re.findall(r'<div class="stat-card[^>]*>.*?<small>\s*([^<]+?)\s*</small>.*?<h3[^>]*>\s*([^<]+?)\s*</h3>', raw, _re.I | _re.S)
        for label, val in pairs:
            key = label.strip().lower()
            v = _html.unescape(val).strip()
            # normalize: remove ₦ and commas for numeric
            if "referral balance" in key or "referral" in key:
                out["referral_balance"] = v
            elif "total rides" in key:
                out["total_rides"] = v
            elif "total deliveries" in key:
                out["total_deliveries"] = v
            elif "completed" in key:
                out["completed"] = v
            elif "in progress" in key or "active" in key:
                out["in_progress"] = v
            elif "total spent" in key and "total_spent" not in out:
                out["total_spent"] = v
    except Exception:
        pass
    # normalize numeric strings
    for k in ("total_deliveries","completed","in_progress","total_rides"):
        if k in out:
            try:
                rawv = str(out[k]).replace(",", "").replace("₦","").strip() or "0"
                out[k] = int(float(rawv))
            except Exception:
                try:
                    out[k] = int(out[k])
                except Exception:
                    pass
    if "referral_balance" in out:
        try:
            rv = str(out["referral_balance"]).replace(",", "").replace("₦","").strip() or "0.00"
            # keep formatted if needed — preserve 2 decimals
            try:
                f = float(rv)
                out["referral_balance"] = f"{f:.2f}" if "." in rv else f"{f:.2f}"
                # but keep original formatted if it had ₦
            except Exception:
                pass
        except Exception:
            pass
    return out


def _parse_active_delivery_html(html_text: str):
    """Parse customer/dashboard.php active-delivery-card: div.active-delivery-card with tracking-number-large, p.mb-0 route, badge color, btn-track href"""
    if not html_text or "active-delivery-card" not in html_text:
        return None
    raw = html_text
    try:
        m = _re.search(r'<div[^>]*class="[^"]*active-delivery-card[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', raw, _re.I | _re.S)
        block = m.group(1) if m else None
        if not block:
            # fallback: capture inner after outer tag until next dashboard-card
            m2 = _re.search(r'<div[^>]*class="[^"]*active-delivery-card[^"]*"[^>]*>(.*?)(?:<div class="dashboard-card|<div class="stat-card)', raw, _re.I | _re.S)
            block = m2.group(1) if m2 else None
        if not block:
            return None
        # tracking number: .tracking-number-large
        tn_m = _re.search(r'class="[^"]*tracking-number-large[^"]*"[^>]*>\s*([^<]+?)\s*</div>', block, _re.I | _re.S)
        tracking = _html.unescape(tn_m.group(1).strip()) if tn_m else ""
        # route: p.mb-0 with icon
        route_m = _re.search(r'<p[^>]*class="[^"]*mb-0[^"]*"[^>]*>.*?<i[^>]*>.*?</i>\s*([^<]+?)\s*</p>', block, _re.I | _re.S)
        route = _html.unescape(route_m.group(1).strip()) if route_m else ""
        if not route:
            rm2 = _re.search(r'<p[^>]*class="[^"]*mb-0[^"]*"[^>]*>\s*(.*?)\s*</p>', block, _re.I | _re.S)
            if rm2:
                route = _html.unescape(_re.sub(r'<[^>]+>', '', rm2.group(1)).strip())
        # status label and inline background color
        status_m = _re.search(r'<span[^>]*style=[\'"][^\'"]*background\s*:\s*([^;\'"]+)[^\'"]*[\'"][^>]*>\s*([^<]+?)\s*</span>', block, _re.I | _re.S)
        status = ""
        color = ""
        if status_m:
            color = status_m.group(1).strip()
            status = _html.unescape(status_m.group(2).strip())
        else:
            # fallback: any span inside mb-3
            sm2 = _re.search(r'<span[^>]*>([^<]*?Pickup[^<]*?|[^<]*?In Transit[^<]*?|[^<]*?Delivered[^<]*?|[^<]*?Failed[^<]*?)</span>', block, _re.I)
            if sm2:
                status = _html.unescape(sm2.group(1).strip())
        # track href — order-agnostic (href may be before or after class)
        href_m = _re.search(r'<a[^>]*href="([^"]*track\.php\?id=[^"]+)"', block, _re.I)
        if not href_m:
            href_m = _re.search(r'<a[^>]*class="[^"]*btn-track[^"]*"[^>]*href="([^"]+)"', block, _re.I)
        if not href_m:
            href_m = _re.search(r'href="([^"]+)"[^>]*class="[^"]*btn-track', block, _re.I)
        href = _html.unescape(href_m.group(1).strip()) if href_m else ""
        if not tracking and href:
            # fallback from href id param
            hm = _re.search(r'id=([^&"\']+)', href)
            if hm:
                tracking = hm.group(1)
        if not tracking:
            return None
        # also check rider line conditional — already handled as separate field, but keep here for completeness
        rider_m = _re.search(r'<p[^>]*class="[^"]*mb-0[^"]*mt-2[^"]*small[^"]*"[^>]*>.*?<i[^>]*fa-motorcycle.*?</i>\s*Rider:\s*([^<]+?)\s*</p>', block, _re.I | _re.S)
        rider_name = _html.unescape(rider_m.group(1).strip()) if rider_m else ""
        out_rider = {"tracking_number": tracking.strip(), "tracking_number_large": tracking.strip(), "route": route.strip(), "status_label": status.strip(), "status": status.strip(), "status_color": color.strip(), "track_href": href.strip(), "rider_name": rider_name.strip(), "raw": block}
        # strip empty rider_name if not present
        if not out_rider["rider_name"]:
            out_rider.pop("rider_name", None)
        return out_rider
    except Exception:
        return None


def _parse_dashboard_delivery_table(html_text: str):
    """Parse dashboard.php tbody delivery table rows: tracking, route, status badge dynamic color, fee, date, action conditional"""
    if not html_text or "<tbody" not in html_text.lower():
        return []
    raw = html_text
    out = []
    try:
        tbody_m = _re.search(r'<tbody[^>]*>(.*?)</tbody>', raw, _re.I | _re.S)
        tbody = tbody_m.group(1) if tbody_m else raw
        rows = _re.findall(r'<tr[^>]*>(.*?)</tr>', tbody, _re.I | _re.S)
        for block in rows:
            # tracking
            tr_m = _re.search(r'data-label="Tracking"[^>]*>.*?<span[^>]*class="[^"]*tracking-code[^"]*"[^>]*>\s*([^<]+?)\s*</span>', block, _re.I | _re.S)
            tracking = _html.unescape(tr_m.group(1).strip()) if tr_m else ""
            if not tracking:
                # fallback: any tracking-code
                tr2 = _re.search(r'class="[^"]*tracking-code[^"]*"[^>]*>\s*([^<]+?)\s*</span>', block, _re.I | _re.S)
                tracking = _html.unescape(tr2.group(1).strip()) if tr2 else ""
            # route: data-label Route with fa-arrow-right between origin/dest
            origin = ""
            dest = ""
            rm = _re.search(r'data-label="Route"[^>]*>(.*?)<i[^>]*fa-arrow-right[^>]*>.*?</i>\s*(.*?)\s*</td>', block, _re.I | _re.S)
            if rm:
                origin = _html.unescape(_re.sub(r'<[^>]+>', '', rm.group(1)).strip())
                dest = _html.unescape(_re.sub(r'<[^>]+>', '', rm.group(2)).strip())
            else:
                # fallback: plain Route text with → arrow
                rm2 = _re.search(r'data-label="Route"[^>]*>\s*(.*?)\s*</td>', block, _re.I | _re.S)
                if rm2:
                    txt = _html.unescape(_re.sub(r'<[^>]+>', '', rm2.group(1)).strip())
                    if "→" in txt:
                        parts = [p.strip() for p in txt.split("→")]
                        origin = parts[0] if len(parts) > 0 else ""
                        dest = parts[1] if len(parts) > 1 else ""
                    else:
                        origin = txt
            route = f"{origin} → {dest}".strip(" →") if origin or dest else ""
            # status badge dynamic color
            st_m = _re.search(r'data-label="Status"[^>]*>.*?<span[^>]*style=[\'"][^\'"]*background\s*:\s*([^;\'"]+)[^\'"]*[\'"][^>]*>\s*([^<]+?)\s*</span>', block, _re.I | _re.S)
            status_label = ""
            status_color = ""
            if st_m:
                status_color = st_m.group(1).strip()
                status_label = _html.unescape(st_m.group(2).strip())
            else:
                st2 = _re.search(r'data-label="Status"[^>]*>.*?<span[^>]*>\s*([^<]+?)\s*</span>', block, _re.I | _re.S)
                if st2:
                    status_label = _html.unescape(st2.group(1).strip())
            # fee
            fee_m = _re.search(r'data-label="Fee"[^>]*>\s*([^<]+?)\s*</td>', block, _re.I | _re.S)
            fee = _html.unescape(fee_m.group(1).strip()) if fee_m else ""
            # date
            date_m = _re.search(r'data-label="Date"[^>]*>\s*([^<]+?)\s*</td>', block, _re.I | _re.S)
            date_text = _html.unescape(date_m.group(1).strip()) if date_m else ""
            # action conditional
            action = {"type": "unknown", "label": "", "href": "", "waybill_id": "", "tracking_number": tracking}
            if 'select-rider.php?waybill=' in block.lower():
                am = _re.search(r'href="([^"]*select-rider\.php\?waybill=([^"]+))"', block, _re.I)
                if am:
                    href = am.group(1)
                    wid = am.group(2)
                    action = {"type": "button", "label": "Select Rider", "icon": "account-plus", "href": href, "waybill_id": wid, "tracking_number": tracking}
                else:
                    action = {"type": "button", "label": "Select Rider", "icon": "account-plus", "href": "", "waybill_id": ""}
            elif 'track.php?id=' in block.lower():
                am = _re.search(r'href="([^"]*track\.php\?id=([^"]+))"', block, _re.I)
                if am:
                    href = am.group(1)
                    tid = am.group(2)
                    action = {"type": "button", "label": "Track", "icon": "eye", "href": href, "tracking_number": tid, "waybill_id": tid}
                else:
                    action = {"type": "button", "label": "Track", "icon": "eye", "href": "", "tracking_number": tracking}
            elif 'fa-ban' in block.lower() and 'cancelled' in status_label.lower():
                action = {"type": "label", "label": "Cancelled", "icon": "ban", "muted": True, "tracking_number": tracking}
            elif status_label:
                # generic status without button — e.g., Delivered
                action = {"type": "unknown", "label": status_label, "href": "", "tracking_number": tracking}
                try:
                    from kivy.logger import Logger as _L
                    _L.warning(f"Unknown Action for status {status_label!r} html snippet {block[:200]!r}")
                except Exception:
                    pass
            # waybill_id fallback from tracking
            waybill_id = action.get("waybill_id") or tracking
            out.append({"tracking_number": tracking, "waybill_number": tracking, "waybill_id": waybill_id, "route_origin": origin, "route_dest": dest, "route": route, "status": status_label, "status_label": status_label, "status_color": status_color, "fee": fee, "amount": fee, "date": date_text, "date_text": date_text, "action": action, "raw": block})
        return out
    except Exception:
        return []
    return out


def get_dashboard_stats():
    # Try WEB HTML first — server renders stats directly into dashboard.php HTML (source of truth for total_rides 10)
    try:
        html_res = _api_client.api_get("customer_dashboard_html")
        if html_res.get("ok"):
            html_text = html_res.get("data", {}).get("raw_html") if isinstance(html_res.get("data"), dict) else None
            if html_text and isinstance(html_text, str) and "stat-card" in html_text.lower():
                parsed = _parse_customer_dashboard_html(html_text)
                if parsed:
                    try:
                        from kivy.logger import Logger as _L
                        _L.info(f"[DEBUG dashboard_stats HTML] parsed={parsed} html_len={len(html_text)}")
                    except Exception:
                        pass
                    # HTML has true 2,0,1,10 — return directly, no JSON fallback needed for these 4
                    # Keep referral_code/customer_name from JSON fallback if HTML lacks
                    active = _parse_active_delivery_html(html_text)
                    delivery_items = _parse_dashboard_delivery_table(html_text)
                    out_html = {
                        "total_deliveries": int(parsed.get("total_deliveries", 0) or 0),
                        "completed": int(parsed.get("completed", 0) or 0),
                        "in_progress": int(parsed.get("in_progress", 0) or 0),
                        "total_rides": int(parsed.get("total_rides", 0) or 0),
                        "referral_balance": str(parsed.get("referral_balance", "0.00")).replace("₦","").strip() or "0.00",
                        "referral_code": "",
                        "customer_name": "",
                        "active_delivery": active,
                        "delivery_items": delivery_items,
                    }
                    # try to also get referral_code/customer_name from any embedded json in HTML? fallback to JSON later
                    # if HTML parsed has all 4, return; otherwise complement with JSON
                    if out_html["total_rides"] or out_html["total_deliveries"]:
                        # complement missing referral_code/name via JSON fallback without overwriting HTML 10
                        try:
                            j_raw = _api_client.api_get("dashboard_stats")
                            j_res = _unwrap(j_raw)
                            if j_res.get("ok"):
                                jd = j_res.get("data") or {}
                                base = jd
                                # handle nested as before
                                for nk in ("statistics","stats","dashboard","summary"):
                                    if isinstance(jd, dict) and isinstance(jd.get(nk), dict) and any(k in jd[nk] for k in ("total_deliveries","total_rides")):
                                        jd = jd[nk]
                                        break
                                if not out_html["referral_code"]:
                                    out_html["referral_code"] = _pick(jd, "referral_code","referralCode", default=_pick(base,"referral_code","referralCode", default="")) or ""
                                if not out_html["customer_name"]:
                                    out_html["customer_name"] = _pick(jd, "name","full_name","customer_name", default=_pick(base,"name","full_name","customer_name", default="")) or ""
                                # if HTML missing total_rides, fallback to JSON (should be 0, but keep HTML 10)
                                if not out_html["total_rides"]:
                                    out_html["total_rides"] = int(float(str(_pick(jd,"total_rides","totalRides","rides",default=0) or 0).replace(",","") or 0) or 0)
                        except Exception:
                            pass
                        return {"ok": True, "error": None, "data": out_html}
    except Exception as e:
        try:
            from kivy.logger import Logger as _L
            _L.warning(f"dashboard_stats HTML try failed: {e!r}")
        except Exception:
            pass
    # Fallback JSON path — dashboard-stats.php
    raw = _api_client.api_get("dashboard_stats")
    # debug: log token/role/raw keys before unwrap
    try:
        from kivy.logger import Logger as _L
        _L.info(f"[DEBUG dashboard_stats] raw ok={raw.get('ok')} error={raw.get('error')!r} data_preview={str(raw.get('data'))[:500]!r}")
    except Exception:
        pass
    result = _unwrap(raw)
    if not result["ok"]:
        try:
            from kivy.logger import Logger as _L
            _L.warning(f"dashboard_stats failed: {result.get('error')!r}")
        except Exception:
            pass
        return result
    d = result["data"]
    # handle nested envelopes: {"success":true,"data":{"statistics":{...}}} or flat
    base = d
    # unwrap one more level if needed: statistics/summary/dashboard
    for nest_key in ("statistics", "stats", "dashboard", "summary"):
        if isinstance(d, dict) and isinstance(d.get(nest_key), dict) and any(k in d[nest_key] for k in ("total_deliveries","totalDeliveries","total","deliveries_total","completed","in_progress","total_rides","referral_balance")):
            # log nested found
            try:
                from kivy.logger import Logger as _L
                _L.info(f"dashboard_stats nested envelope: {nest_key} keys={list(d[nest_key].keys())[:10]}")
            except Exception:
                pass
            d = d[nest_key]
            break
    # also handle double data wrapper like {"data":{"statistics":{...}}}
    if isinstance(d, dict) and isinstance(d.get("data"), dict) and not any(k in d for k in ("total_deliveries","totalDeliveries")):
        inner = d.get("data")
        if isinstance(inner, dict) and any(k in inner for k in ("total_deliveries","totalDeliveries","total","total_rides")):
            d = inner
    # web payload for this account shows total=2,completed=0,in_transit=1, rides 10 — handle camelCase + various keys
    def _int_pick(*keys):
        v = _pick(d, *keys, default=None)
        if v is None and isinstance(base, dict):
            v = _pick(base, *keys, default=None)
        if v is None:
            return 0
        try:
            return int(float(str(v).replace(",","").strip() or 0))
        except Exception:
            return 0
    def _str_pick(*keys, default="0.00"):
        v = _pick(d, *keys, default=None)
        if v is None and isinstance(base, dict):
            v = _pick(base, *keys, default=None)
        if v is None:
            return default
        return str(v).strip() or default

    out = {
        "total_deliveries": _int_pick("total_deliveries","totalDeliveries","total","deliveries_total","deliveries","total_deliveries_count"),
        "completed": _int_pick("completed","total_completed","delivered","completed_count","completed_deliveries"),
        "in_progress": _int_pick("in_progress","inProgress","active","in_transit","inTransit","pending","active_deliveries"),
        "total_rides": _int_pick("total_rides","totalRides","rides","rides_total","total_rides_count","rides_count"),
        "referral_balance": _str_pick("referral_balance","referralBalance","balance","referral","referral_earnings", default="0.00"),
        "referral_code": _pick(d, "referral_code","referralCode", default=_pick(base, "referral_code","referralCode", default="")) or "",
        "customer_name": _pick(d, "name","full_name","customer_name","customerName", default=_pick(base, "name","full_name","customer_name", default="")) or "",
    }
    # fallback: referral_balance may be under referral/stats nested or numeric
    if out["referral_balance"] == "0.00":
        # try referral nested
        ref_raw = None
        if isinstance(d, dict):
            ref_raw = d.get("referral") if isinstance(d.get("referral"), dict) else None
        if isinstance(ref_raw, dict):
            bal = _pick(ref_raw, "balance","referral_balance","referralBalance", default=None)
            if bal is not None:
                out["referral_balance"] = str(bal)
    # active_delivery from JSON fallback (e.g., dashboard-stats.php data.active_delivery)
    ad_json = _pick(d, "active_delivery","activeDelivery","current_delivery", default=_pick(base, "active_delivery","activeDelivery", default=None))
    if isinstance(ad_json, dict) and ad_json.get("tracking_number"):
        out["active_delivery"] = ad_json
    elif ad_json:
        out["active_delivery"] = ad_json
    try:
        from kivy.logger import Logger as _L
        _L.info(f"dashboard_stats parsed (JSON fallback): total_deliveries={out['total_deliveries']} completed={out['completed']} in_progress={out['in_progress']} total_rides={out['total_rides']} referral_balance={out['referral_balance']!r} active_delivery={bool(out.get('active_delivery'))} keys={list(d.keys())[:10] if isinstance(d,dict) else type(d)}")
    except Exception:
        pass
    return {"ok": True, "error": None, "data": out}


def get_deliveries(status=None, search=None, page=1):
    params = {"page": page}
    if status:
        params["status"] = status
    if search:
        params["search"] = search
    result = _unwrap(_api_client.api_get("customer_deliveries", params=params))
    if not result["ok"]:
        return result
    d = result["data"]
    items = _pick(d, "deliveries", "items", "data", "results", default=[])
    return {
        "ok": True,
        "error": None,
        "data": {
            "items": items if isinstance(items, list) else [],
            "has_more": _pick(d, "has_more", "hasMore", default=False),
            "page": _pick(d, "page", "current_page", default=page),
            "total": _pick(d, "total", "total_count", default=0),
        },
    }


def _norm_counts(d):
    if not isinstance(d, dict):
        return {}
    out = {}
    for k, v in d.items():
        if isinstance(v, int):
            out[k] = v
        elif isinstance(v, dict):
            out[k] = int(v.get("count", v.get("total", v.get("value", 0))) or 0)
        else:
            try:
                out[k] = int(v)
            except Exception:
                out[k] = 0
    return out


def get_status_counts():
    result = _unwrap(_api_client.api_get("status_counts"))
    if not result["ok"]:
        return result
    d = result["data"]
    return {
        "ok": True,
        "error": None,
        "data": _norm_counts(d) if isinstance(d, dict) else {},
    }


def get_history(search=None, status=None, date_from=None, date_to=None, page=1):
    params = {"page": page}
    if search:
        params["search"] = search
    if status:
        params["status"] = status
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    result = _unwrap(_api_client.api_get("customer_history", params=params))
    if not result["ok"]:
        return result
    d = result["data"]
    items = _pick(d, "deliveries", "items", "data", "results", "history", default=[])
    if not isinstance(items, list):
        items = []
    # Statistics included in same call per spec; fallback to _norm_counts
    stats_raw = _pick(d, "statistics", "stats", default=None)
    if isinstance(stats_raw, dict):
        statistics = _norm_counts(stats_raw)
    else:
        # also check pagination-level stats
        statistics = _norm_counts(_pick(d, "status_counts", default={}) if isinstance(d, dict) else {})
    # Pagination object per spec: pagination: {current_page, total_pages, total_records}
    pagination = _pick(d, "pagination", "meta", default={}) if isinstance(d, dict) else {}
    if not isinstance(pagination, dict):
        pagination = {}
    # Summary for avg_distance/total_spent (may be under summary/aggregates)
    summary_raw = _pick(d, "summary", "aggregates", "totals", default={}) if isinstance(d, dict) else {}
    if not isinstance(summary_raw, dict):
        summary_raw = {}
    avg_distance = _pick(summary_raw, "avg_distance", "avgDistance", default=None)
    total_spent = _pick(summary_raw, "total_spent", "totalSpent", "total_spent_formatted", default=None)
    # Fallback pagination fields at top-level
    has_more = False
    if pagination:
        has_more = _pick(pagination, "total_pages", default=1) > _pick(pagination, "current_page", default=page)
    else:
        has_more = _pick(d if isinstance(d, dict) else {}, "has_more", "hasMore", default=False)
    current_page = _pick(pagination, "current_page", "page", default=_pick(d if isinstance(d, dict) else {}, "page", "current_page", default=page))
    total = _pick(pagination, "total_records", "total", default=_pick(d if isinstance(d, dict) else {}, "total", "total_count", default=len(items)))
    return {
        "ok": True,
        "error": None,
        "data": {
            "items": items,
            "has_more": bool(has_more),
            "page": int(current_page) if str(current_page).isdigit() else current_page,
            "total": int(total) if isinstance(total, int) or (isinstance(total, str) and total.isdigit()) else 0,
            "statistics": statistics,
            "pagination": pagination,
            "summary": {"avg_distance": avg_distance, "total_spent": total_spent, **summary_raw},
        },
    }


def get_notifications(page=1):
    # real endpoint is https://trackwaylogistics.ng/api/get-notifications.php (no limit, page only)
    result = _unwrap(_api_client.api_get("get_notifications", params={"page": page}))
    if not result["ok"]:
        return result
    d = result["data"]
    # handle {"success":true,"notifications":[...]} vs success:false (real error)
    if isinstance(d, dict) and "success" in d:
        if d.get("success") is not True and d.get("success") not in (1, "1", "true", True):
            return {"ok": False, "data": d, "error": d.get("message") or d.get("error") or "Unable to load notifications, please try again"}
        if "notifications" in d:
            notifications = d.get("notifications") or []
            return {
                "ok": True,
                "error": None,
                "data": {
                    "items": notifications if isinstance(notifications, list) else [],
                    "unread_count": _pick(d, "unread_count", default=0),
                    "has_more": False,
                    "page": page,
                    "total": len(notifications) if isinstance(notifications, list) else 0,
                },
            }
    notifications = _pick(d, "notifications", "items", "data", default=[])
    return {
        "ok": True,
        "error": None,
        "data": {
            "items": notifications if isinstance(notifications, list) else [],
            "unread_count": _pick(d, "unread_count", default=0),
            "has_more": _pick(d, "total_pages", default=1) > _pick(d, "current_page", "page", default=1),
            "page": _pick(d, "current_page", "page", default=page),
            "total": _pick(d, "total_records", "total", default=len(notifications) if isinstance(notifications, list) else 0),
        },
    }


def get_profile():
    """Single profile.php request – populates profile hero, stats, and recent deliveries."""
    result = _unwrap(_api_client.api_get("customer_profile"))
    if not result["ok"]:
        return result
    d = result["data"]
    # Support both flat and nested shapes: data.customer / data.statistics / data.recent_deliveries
    customer = _pick(d, "customer", "Customer", "user", default={}) if isinstance(d, dict) else {}
    statistics = _pick(d, "statistics", "stats", "dashboard", default={}) if isinstance(d, dict) else {}
    recent = _pick(d, "recent_deliveries", "recentDeliveries", "deliveries", "recent", default=[]) if isinstance(d, dict) else []
    # Fallback if recent is nested under customer or statistics
    if not recent and isinstance(customer, dict):
        recent = _pick(customer, "recent_deliveries", default=[])
    if isinstance(recent, dict):
        recent = _pick(recent, "items", "data", default=[])
    return {
        "ok": True,
        "error": None,
        "data": {
            "customer": customer if isinstance(customer, dict) else {},
            "statistics": statistics if isinstance(statistics, dict) else {},
            "recent_deliveries": recent if isinstance(recent, list) else [],
        },
    }


def update_profile(payload):
    result = _api_client.api_post("update_profile", payload=payload)
    return _unwrap(result)


def change_password(payload):
    result = _api_client.api_post("change_password", payload=payload)
    return _unwrap(result)


def get_referral_stats():
    result = _unwrap(_api_client.api_get("referral_stats"))
    if not result["ok"]:
        return result
    d = result["data"]
    return {
        "ok": True,
        "error": None,
        "data": {
            "referral_code": _pick(d, "referral_code", "referralCode", default=""),
            "total_referrals": _pick(d, "total_referrals", "totalReferrals", "total", default=0),
            "pending_referrals": _pick(d, "pending_referrals", "pendingReferrals", "pending", default=0),
            "completed_referrals": _pick(d, "completed_referrals", "completedReferrals", "completed", default=0),
            "referral_balance": _pick(d, "referral_balance", "referralBalance", "balance", default=0),
            "total_reward_earned": _pick(d, "total_reward_earned", "totalRewardEarned", default=0),
            "reward_amount": _pick(d, "reward_amount", "rewardAmount", "reward", default=500),
            "share_url": _pick(d, "share_url", "shareUrl", "share_link", default=""),
        },
    }


def get_referrals(page=1):
    result = _unwrap(_api_client.api_get("referral_list", params={"page": page}))
    if not result["ok"]:
        return result
    d = result["data"]
    referrals = _pick(d, "referrals", "items", "data", "list", default=[]) if isinstance(d, dict) else []
    pagination = _pick(d, "pagination", "meta", default={}) if isinstance(d, dict) else {}
    if isinstance(referrals, dict):
        referrals = _pick(referrals, "items", "data", default=[])
    if not isinstance(referrals, list):
        referrals = []
    if not isinstance(pagination, dict):
        pagination = {}
    return {
        "ok": True,
        "error": None,
        "data": {
            "referrals": referrals,
            "pagination": pagination,
            "has_next": _pick(pagination, "has_next", "hasNext", default=False),
            "total_records": _pick(pagination, "total_records", "totalRecords", "total", default=len(referrals)),
        },
    }


def mark_notification_read(notification_id):
    result = _api_client.api_post("mark_notification_read", payload={"notification_id": notification_id})
    return _unwrap(result)


def mark_all_notifications_read():
    result = _api_client.api_post("mark_all_notifications_read", payload={})
    return _unwrap(result)


def submit_complaint(payload):
    result = _api_client.api_post("submit_complaint", payload=payload)
    return _unwrap(result)


def calculate_distance(payload):
    result = _api_client.api_post("calculate_distance", payload=payload)
    return _unwrap(result)


def request_delivery(payload):
    result = _api_client.api_post("request_delivery", payload=payload)
    return _unwrap(result)


def request_ride(payload):
    # Dedicated ride endpoint — dropoff_*/fare/estimated_duration (CSRF-free api/v1, Bearer JWT)
    result = _api_client.api_post("request_ride", payload=payload)
    return _unwrap(result)


def verify_payment(reference):
    try:
        from kivy.logger import Logger as _L
        _L.info(f"[DEBUG verify_payment GET] reference={reference!r}")
    except Exception:
        pass
    result = _api_client.api_get("verify_payment", params={"reference": reference})
    try:
        from kivy.logger import Logger as _L
        _L.info(f"[DEBUG verify_payment GET] result ok={result.get('ok')} error={result.get('error')!r} data_preview={str(result.get('data'))[:200]!r}")
    except Exception:
        pass
    return _unwrap(result)


def paystack_initialize(payload):
    result = _api_client.api_post("paystack_initialize", payload=payload)
    return _unwrap(result)


def retry_payment(reference):
    result = _api_client.api_post("retry_payment", payload={"reference": reference})
    return _unwrap(result)


def _parse_pending_payments_html(html_text: str):
    """Parse GET customer/dashboard.php HTML pending payments dashboard-card
    Each ride is <div class="unpaid-ride-card" data-ride-id="14"> ... one-card-per-ride
    Within block: .tracking-badge #14, .fw-bold.text-success ₦..., .small.text-muted route, .status-badge
    """
    if not html_text or "Pending Payments" not in html_text:
        return []
    raw = html_text
    out = []
    seen = {}
    try:
        # isolate Pending Payments section after Action Required, before next dashboard/stat card
        m = _re.search(r'Pending Payments.*?Action Required(.*?)(?:<div class="dashboard-card|<div class="stat-card)', raw, _re.I | _re.S)
        section = m.group(1) if m else raw
        # split on outer unpaid-ride-card boundary — one per ride
        blocks = _re.findall(r'<div class="unpaid-ride-card"[^>]*data-ride-id="(\d+)"[^>]*>(.*?)</div>\s*</div>', section, _re.I | _re.S)
        if not blocks:
            # fallback: split by lookahead if nested structure differs
            parts = _re.split(r'(?=<div class="unpaid-ride-card"[^>]*data-ride-id=")', section, flags=_re.I)
            blocks = []
            for p in parts:
                mm = _re.search(r'<div class="unpaid-ride-card"[^>]*data-ride-id="(\d+)"', p, _re.I)
                if mm:
                    # capture inner after outer tag
                    inner = p[mm.end():]
                    blocks.append((mm.group(1), inner))
        for ride_id, block in blocks:
            if ride_id in seen:
                continue
            # Fare: inside .fw-bold.text-success
            fare_m = _re.search(r'class="[^"]*fw-bold[^"]*text-success[^"]*"[^>]*>\s*([^<]+?)\s*</span>', block, _re.I | _re.S)
            fare = _html.unescape(fare_m.group(1).strip()) if fare_m else ""
            # also fallback plain ₦
            if not fare:
                fm2 = _re.search(r'₦\s*[0-9,\.]+', block)
                if fm2:
                    fare = fm2.group(0).strip()
            # Ride number: inside .tracking-badge #14
            tn_m = _re.search(r'class="[^"]*tracking-badge[^"]*"[^>]*>.*?#(\d+)', block, _re.I | _re.S)
            tracking = tn_m.group(1) if tn_m else ride_id
            # Route: inside .small.text-muted — use substring "small text-muted" not exact order, mt-1 extra class allowed
            route_m = _re.search(r'class="[^"]*(?:small[^"]*text-muted|text-muted[^"]*small)[^"]*"[^>]*>.*?<i[^>]*>.*?</i>\s*([^<]+?)\s*</div>', block, _re.I | _re.S)
            route = _html.unescape(route_m.group(1).strip()) if route_m else ""
            if not route:
                rm2 = _re.search(r'class="[^"]*(?:small[^"]*text-muted|text-muted[^"]*small)[^"]*"[^>]*>\s*(.*?)\s*</div>', block, _re.I | _re.S)
                if rm2:
                    route = _html.unescape(_re.sub(r'<[^>]+>', '', rm2.group(1)).strip())
            # Status: inside .status-badge
            st_m = _re.search(r'class="[^"]*status-badge[^"]*"[^>]*>\s*(?:<i[^>]*>.*?</i>\s*)?([^<]+?)\s*</span>', block, _re.I | _re.S)
            status = _html.unescape(st_m.group(1).strip()) if st_m else ""
            if not status:
                st2 = _re.search(r'class="[^"]*status-badge[^"]*"[^>]*>(.*?)</span>', block, _re.I | _re.S)
                if st2:
                    status = _html.unescape(_re.sub(r'<[^>]+>', '', st2.group(1)).strip())
            seen[ride_id] = {"ride_id": str(ride_id), "tracking_number": str(tracking).strip(), "waybill_number": str(tracking).strip(), "amount": fare, "fare": fare, "route": route.strip(), "status": status.strip(), "raw": block}
        if seen:
            return list(seen.values())
        # fallback: old generic card parsing if unpaid-ride-card not found
        cards = _re.findall(r'<div[^>]*class="[^"]*card[^"]*"[^>]*>(.*?)</div>\s*</div>', section, _re.I | _re.S)
        for c in cards:
            rid = _re.search(r'ride_id["\']?\s*[:=]\s*["\']?(\d+)', c, _re.I)
            if rid:
                out.append({"ride_id": rid.group(1), "raw": c})
    except Exception:
        pass
    return out


def get_pending_payments():
    # Primary: parse HTML from customer_dashboard_html raw_html already fetched for stats
    try:
        html_res = _api_client.api_get("customer_dashboard_html")
        if html_res.get("ok"):
            html_text = html_res.get("data", {}).get("raw_html") if isinstance(html_res.get("data"), dict) else None
            if html_text and isinstance(html_text, str) and "Pending Payments" in html_text:
                parsed = _parse_pending_payments_html(html_text)
                if parsed:
                    # parsed already contains ride_id, amount/fare, route, status scoped per unpaid-ride-card
                    return {"ok": True, "error": None, "data": {"items": parsed, "has_more": False}}
    except Exception:
        pass
    # Fallback JSON: try dashboard_stats unpaid_deliveries / pending_payments
    try:
        j_raw = _api_client.api_get("dashboard_stats")
        j_res = _unwrap(j_raw)
        if j_res.get("ok"):
            jd = j_res.get("data") or {}
            # handle nested statistics
            for nk in ("statistics", "stats", "dashboard"):
                if isinstance(jd, dict) and isinstance(jd.get(nk), dict) and any(k in jd[nk] for k in ("unpaid_deliveries","pending_payments","pending")):
                    jd = jd[nk]
                    break
            cand = _pick(jd, "unpaid_deliveries", "pending_payments", "pending", "unpaid", default=None)
            if isinstance(cand, list) and cand:
                return {"ok": True, "error": None, "data": {"items": cand, "has_more": False}}
    except Exception:
        pass
    return {"ok": True, "error": None, "data": {"items": [], "has_more": False}}


def retry_ride_payment(ride_id):
    result = _api_client.api_post("retry_ride_payment", payload={"ride_id": str(ride_id)})
    return result


def cancel_ride(ride_id):
    result = _api_client.api_post("cancel_ride", payload={"ride_id": str(ride_id)})
    return result


def get_support_tickets(page=1):
    result = _unwrap(_api_client.api_get("support_tickets", params={"page": page}))
    if not result["ok"]:
        return result
    d = result["data"]
    # Support multiple backend shapes: {complaints: []}, {tickets: []}, {data: []}, list directly
    raw = _pick(d, "complaints", "tickets", "items", "data", "results", default=None)
    if raw is None:
        raw = d if isinstance(d, list) else []
    items = raw if isinstance(raw, list) else _pick(raw, "items", "data", default=[]) if isinstance(raw, dict) else []
    if not isinstance(items, list):
        items = []
    return {
        "ok": True,
        "error": None,
        "data": {
            "items": items,
            "has_more": _pick(d if isinstance(d, dict) else {}, "has_more", "hasMore", default=False),
            "page": _pick(d if isinstance(d, dict) else {}, "page", "current_page", default=page),
            "total": _pick(d if isinstance(d, dict) else {}, "total", "total_count", "count", default=len(items)),
        },
    }
