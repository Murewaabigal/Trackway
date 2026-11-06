import json
import os

from kivy.app import App


SESSION_FILE = "session.json"


def _session_path():
    try:
        data_dir = App.get_running_app().user_data_dir
    except Exception:
        data_dir = os.path.dirname(__file__)
    return os.path.join(data_dir, SESSION_FILE)


def save_tokens(access_token, refresh_token, role, customer_name=None):
    path = _session_path()
    existing = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                existing = json.load(f) or {}
        except Exception:
            existing = {}
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": role,
        "customer_name": customer_name or "",
        "language": existing.get("language", "en"),
        "phpsessid": existing.get("phpsessid"),
        "phpsessid_expires": existing.get("phpsessid_expires"),
        "csrf_token": existing.get("csrf_token"),
    }
    with open(path, "w") as f:
        json.dump(data, f)


def save_csrf_token(csrf_token):
    path = _session_path()
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f) or {}
        except Exception:
            data = {}
    if csrf_token:
        data["csrf_token"] = str(csrf_token).strip()
    else:
        data.pop("csrf_token", None)
    with open(path, "w") as f:
        json.dump(data, f)


def get_csrf_token():
    sess = load_session()
    if sess:
        return sess.get("csrf_token")
    return None


def save_phpsessid(phpsessid, expires=None):
    path = _session_path()
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f) or {}
        except Exception:
            data = {}
    if phpsessid:
        data["phpsessid"] = phpsessid
        if expires is not None:
            data["phpsessid_expires"] = expires
    else:
        data.pop("phpsessid", None)
        data.pop("phpsessid_expires", None)
    with open(path, "w") as f:
        json.dump(data, f)


def get_phpsessid():
    sess = load_session()
    if sess:
        return sess.get("phpsessid")
    return None


def save_language(lang_code):
    path = _session_path()
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f) or {}
        except Exception:
            data = {}
    data["language"] = lang_code
    with open(path, "w") as f:
        json.dump(data, f)


def get_language():
    sess = load_session()
    if sess:
        return sess.get("language", "en")
    return "en"


def load_session():
    path = _session_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def clear_session():
    path = _session_path()
    if os.path.exists(path):
        os.remove(path)


def is_logged_in():
    session = load_session()
    return bool(session and session.get("access_token"))


def get_role():
    session = load_session()
    if session:
        return session.get("role")
    return None


def get_access_token():
    session = load_session()
    if session:
        return session.get("access_token")
    return None


def get_refresh_token():
    session = load_session()
    if session:
        return session.get("refresh_token")
    return None


def get_customer_name():
    session = load_session()
    if session:
        return session.get("customer_name") or ""
    return ""
