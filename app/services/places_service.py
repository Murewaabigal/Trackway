"""Direct Google Places (restricted Android package ng.trackway) — no backend proxy."""
import requests

from app.core.config import (
    MAPS_API_KEY,
    PLACES_AUTOCOMPLETE_URL,
    PLACES_DETAILS_URL,
    PLACES_GEOCODE_URL,
)


def _key():
    return (MAPS_API_KEY or "").strip()


def autocomplete(query, session_token=None):
    q = (query or "").strip()
    if len(q) < 2:
        return []
    key = _key()
    if not key:
        return []
    params = {
        "input": q,
        "key": key,
        "components": "country:NG",
        "language": "en",
        "types": "geocode",
    }
    if session_token:
        params["sessiontoken"] = session_token
    try:
        resp = requests.get(PLACES_AUTOCOMPLETE_URL, params=params, timeout=3)
        if resp.status_code != 200:
            try:
                from kivy.logger import Logger
                Logger.warning(f"Places autocomplete HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception:
                pass
            return []
        data = resp.json()
        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            try:
                from kivy.logger import Logger
                Logger.warning(f"Places autocomplete status {status}: {data.get('error_message') or data}")
            except Exception:
                pass
            return []
        preds = data.get("predictions") or []
        out = []
        for p in preds[:5]:
            desc = p.get("description") or ""
            pid = p.get("place_id") or ""
            main = (p.get("structured_formatting") or {}).get("main_text") or desc
            out.append({"description": desc, "place_id": pid, "main_text": main})
        return out
    except requests.ConnectionError:
        return []
    except requests.Timeout:
        return []
    except Exception:
        return []


def directions(origin_lat, origin_lng, dest_lat, dest_lng):
    """Google Directions — returns {distance_km, duration_min, polyline} or None. Used for Ride fare (distance + duration)."""
    key = _key()
    if not key or None in (origin_lat, origin_lng, dest_lat, dest_lng):
        return None
    try:
        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
            "key": key,
        }
        resp = requests.get("https://maps.googleapis.com/maps/api/directions/json", params=params, timeout=5)
        if resp.status_code != 200:
            try:
                from kivy.logger import Logger
                Logger.warning(f"Directions HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception:
                pass
            return None
        data = resp.json()
        if data.get("status") != "OK":
            try:
                from kivy.logger import Logger
                Logger.warning(f"Directions status {data.get('status')}: {data.get('error_message') or data}")
            except Exception:
                pass
            return None
        routes = data.get("routes") or []
        if not routes:
            return None
        leg = (routes[0].get("legs") or [{}])[0]
        dist_m = (leg.get("distance") or {}).get("value")  # meters
        dur_s = (leg.get("duration") or {}).get("value")  # seconds
        if dist_m is None or dur_s is None:
            return None
        distance_km = dist_m / 1000.0
        duration_min = dur_s / 60.0
        polyline = (routes[0].get("overview_polyline") or {}).get("points") or ""
        return {"distance_km": distance_km, "duration_min": duration_min, "polyline": polyline}
    except Exception:
        return None


def static_map_url(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng, polyline):
    """Google Static Maps — 320dp roadmap with dark green route + red A/B. No custom attribution needed (baked in image)."""
    key = _key()
    if not key or None in (pickup_lat, pickup_lng, dropoff_lat, dropoff_lng):
        return None
    # Use 640x320@2x for crisp 320dp, light roadmap, dark green route
    base = "https://maps.googleapis.com/maps/api/staticmap"
    # Build URL manually to keep enc: polyline intact
    try:
        import urllib.parse
        params = {
            "size": "640x320",
            "scale": "2",
            "maptype": "roadmap",
            "key": key,
        }
        # markers and path need special handling (keep enc: prefix)
        markers_a = f"color:red|label:A|{pickup_lat},{pickup_lng}"
        markers_b = f"color:red|label:B|{dropoff_lat},{dropoff_lng}"
        path = f"color:0x0B3D2E|weight:5|enc:{polyline}" if polyline else f"color:0x0B3D2E|weight:5|{pickup_lat},{pickup_lng}|{dropoff_lat},{dropoff_lng}"
        # encode but keep | and : and , for readability (Google accepts)
        query = urllib.parse.urlencode(params)
        query += "&" + urllib.parse.urlencode({"markers": markers_a})
        query += "&" + urllib.parse.urlencode({"markers": markers_b})
        # path with enc: needs not double-encode :
        query += f"&path={urllib.parse.quote(path, safe=':|,')}"
        return f"{base}?{query}"
    except Exception:
        return None


def geocode(place_id_or_address):
    """Resolve place_id or address to lat/lng/city. Prefers place_id details."""
    key = _key()
    if not key or not place_id_or_address:
        return None
    # Try place details if looks like place_id
    is_chij = place_id_or_address.startswith("ChI")
    if place_id_or_address.startswith("stub_"):
        return None
    try:
        if is_chij:
            resp = requests.get(PLACES_DETAILS_URL, params={"place_id": place_id_or_address, "fields": "geometry,address_components,formatted_address", "key": key}, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "OK":
                    result = data.get("result") or {}
                    geom = (result.get("geometry") or {}).get("location") or {}
                    lat, lng = geom.get("lat"), geom.get("lng")
                    city = ""
                    for comp in result.get("address_components") or []:
                        types = comp.get("types") or []
                        if "locality" in types or "administrative_area_level_2" in types:
                            city = comp.get("long_name") or city
                            if "locality" in types:
                                break
                    if lat is not None and lng is not None:
                        return {"lat": lat, "lng": lng, "city": city, "formatted_address": result.get("formatted_address") or ""}
        # Fallback geocode by address
        resp = requests.get(PLACES_GEOCODE_URL, params={"address": place_id_or_address, "components": "country:NG", "key": key}, timeout=3)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != "OK":
            return None
        results = data.get("results") or []
        if not results:
            return None
        r = results[0]
        geom = (r.get("geometry") or {}).get("location") or {}
        lat, lng = geom.get("lat"), geom.get("lng")
        city = ""
        for comp in r.get("address_components") or []:
            types = comp.get("types") or []
            if "locality" in types or "administrative_area_level_2" in types:
                city = comp.get("long_name") or city
                if "locality" in types:
                    break
        if lat is not None and lng is not None:
            return {"lat": lat, "lng": lng, "city": city, "formatted_address": r.get("formatted_address") or ""}
    except Exception:
        return None
    return None
