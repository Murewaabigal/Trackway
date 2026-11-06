from kivy.properties import StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.menu import MDDropdownMenu
from kivy.utils import rgba
from app.core.theme import MUTED

from app.i18n.translator import (
    tr,
    set_language,
    get_language,
    get_available_languages,
)


class LanguagePicker(MDBoxLayout):
    current_label = StringProperty("English")

    def __init__(self, compact=False, **kwargs):
        self.compact = compact
        width = "36dp" if compact else "180dp"
        # Fixed height 32dp for shared center line with bell/avatar
        if compact:
            kwargs.setdefault("size_hint_y", None)
            kwargs.setdefault("height", "32dp")
            kwargs.setdefault("spacing", "2dp")
            kwargs.setdefault("pos_hint", {"center_y": 0.5})
        super().__init__(orientation="horizontal", size_hint_x=None, width=width, **kwargs)
        self._build_menu()
        self._update_label()
        if compact:
            self.bind(on_touch_down=self._on_touch_down)

    def _on_touch_down(self, instance, touch):
        if self.compact and self.collide_point(*touch.pos):
            self.open_menu()
            return True
        return False

    def _build_menu(self):
        langs = get_available_languages()
        items = []
        for code, name in langs.items():
            items.append(
                {
                    "text": name,
                    "viewclass": "OneLineListItem",
                    "on_release": lambda c=code: self._select(c),
                }
            )
        self.menu = MDDropdownMenu(
            caller=self,
            items=items,
            width_mult=2 if self.compact else 3,
        )

        if self.compact:
            # Minimal EN style: EN + chevron inline, same 32dp center line
            self.icon_label = MDLabel(
                text="EN",
                font_style="Caption",
                font_size="12sp",
                halign="center",
                valign="middle",
                theme_text_color="Custom",
                text_color=rgba(MUTED),
                size_hint_x=None,
                width="22dp",
                size_hint_y=None,
                height="32dp",
                pos_hint={"center_y": 0.5},
            )
            self.chevron = MDIcon(
                icon="chevron-down",
                theme_text_color="Custom",
                text_color=rgba(MUTED),
                font_size="14sp",
                size_hint_x=None,
                width="12dp",
                size_hint_y=None,
                height="32dp",
                pos_hint={"center_y": 0.5},
            )
            self.add_widget(self.icon_label)
            self.add_widget(self.chevron)
            # Dummy btn for compatibility (not shown)
            self.btn = self.icon_label
        else:
            self.btn = MDRaisedButton(
                text=self.current_label,
                on_release=self.open_menu,
                font_size="14sp",
            )
            self.add_widget(self.btn)

    def _update_label(self):
        code = get_language()
        langs = get_available_languages()
        label = langs.get(code, code)
        self.current_label = label
        if self.compact:
            # Show short code EN/YO/HA/IG
            short = code.upper() if len(code) <= 3 else label[:2].upper()
            self.icon_label.text = short
            # Also update btn alias for tests
            try:
                self.btn.text = short
            except Exception:
                pass
        else:
            self.btn.text = label

    def open_menu(self, *args):
        self.menu.open()

    def _select(self, lang_code):
        set_language(lang_code)
        self._update_label()
        self.menu.dismiss()
