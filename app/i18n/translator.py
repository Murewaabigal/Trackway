import json
import os
from kivy.event import EventDispatcher

_locales = {}
_current_lang = "en"
_fallback = {}

LOCALES_DIR = os.path.join(
    os.path.dirname(__file__), "locales"
)

AVAILABLE_LANGUAGES = {
    "en": "English",
    "yo": "Yoruba",
    "ha": "Hausa",
    "ig": "Igbo",
}


def _load_json(lang_code):
    path = os.path.join(LOCALES_DIR, f"{lang_code}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


class Translator(EventDispatcher):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_language_changed')
        self._locales = {}
        self._fallback = {}
        self._current_lang = "en"

    def init_translator(self, default_lang="en"):
        self._fallback = self._load_json("en")
        self._current_lang = default_lang
        self._locales = self._load_json(default_lang)

    def set_language(self, lang_code):
        self._current_lang = lang_code
        self._locales = self._load_json(lang_code)
        self.dispatch('on_language_changed', lang_code)

    def on_language_changed(self, lang_code):
        pass

    def get_language(self):
        return self._current_lang

    def get_available_languages(self):
        return AVAILABLE_LANGUAGES.copy()

    def tr(self, key):
        value = self._locales.get(key)
        if value:
            return value
        value = self._fallback.get(key)
        if value:
            return value
        return key

    @staticmethod
    def _load_json(lang_code):
        import json
        import os
        path = os.path.join(LOCALES_DIR, f"{lang_code}.json")
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}


# Global translator instance
_translator = Translator()

# Convenience functions for backward compatibility
def init_translator(default_lang="en"):
    _translator.init_translator(default_lang)


def set_language(lang_code):
    _translator.set_language(lang_code)
    try:
        from app.core.session import save_language
        save_language(lang_code)
    except Exception:
        pass


def get_language():
    return _translator.get_language()


def get_available_languages():
    return _translator.get_available_languages()


def tr(key):
    return _translator.tr(key)


def bind_language_change(callback):
    """Bind a callback to the language change event.
    Returns the callback for later unbinding.
    """
    _translator.bind(on_language_changed=callback)
    return callback  # Return the callback itself for unbinding


def unbind_language_change(callback):
    """Unbind a callback from the language change event."""
    _translator.unbind(on_language_changed=callback)