from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.screen import MDScreen

from app.i18n.translator import tr
from app.core.theme import (
    PRIMARY, DARK, MUTED, BACKGROUND, CARD_BG,
)
from app.views.shared.waybill_card import WaybillCard
from app.views.base_screen import BaseScreen

FILTERS = [
    ("all", ""),
    ("pending_pickup", ""),
    ("in_transit", ""),
    ("delivered", ""),
    ("cancelled", ""),
]


class CustomerDeliveriesScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._items = []
        self._page = 1
        self._has_more = False
        self._loading = False
        self._status = ""
        self._search = ""

        outer = MDBoxLayout(orientation="vertical", padding="12dp", spacing="8dp")

        header = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp")
        back_btn = MDFlatButton(
            text="< " + tr("back"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            on_release=self._go_back,
        )
        title = MDLabel(
            text=tr("delivery_list"),
            font_style="H6",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=DARK,
            size_hint_x=1,
            adaptive_height=True,
        )
        header.add_widget(back_btn)
        header.add_widget(title)
        header.add_widget(MDFlatButton(text=""))

        self.search_field = MDTextField(
            hint_text=tr("search_by_tracking"),
            icon_right="magnify",
            size_hint_x=1,
            mode="round",
            on_text_validate=self._do_search,
        )
        self.search_field.bind(text=self._on_search_text)
        self._search_clock = None

        self._filter_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing="6dp",
        )

        self._list_scroll = ScrollView()
        self._list_scroll.bind(scroll_y=self._on_scroll_y)
        self._list_content = MDBoxLayout(
            orientation="vertical",
            spacing="10dp",
            adaptive_height=True,
            size_hint_y=None,
        )
        self._list_content.bind(minimum_height=self._list_content.setter("height"))
        self._list_scroll.add_widget(self._list_content)
        self._status_counts = {}
        self._counts_loaded = False

        self.spinner = MDSpinner(
            size_hint=(None, None), size=(32, 32),
            active=False, color=rgba(PRIMARY),
            pos_hint={"center_x": 0.5},
        )

        outer.add_widget(header)
        outer.add_widget(self.search_field)
        outer.add_widget(self._filter_row)
        outer.add_widget(self._list_scroll)
        outer.add_widget(self.spinner)
        self.add_widget(outer)

        self._bind_filters()

    def _get_count(self, v):
        if isinstance(v, int):
            return v
        if isinstance(v, dict):
            return int(v.get("count", v.get("total", v.get("value", 0))) or 0)
        try:
            return int(v)
        except Exception:
            return 0

    def _bind_filters(self):
        self._filter_row.clear_widgets()
        for key, value in FILTERS:
            active = (self._status == value)
            base_label = tr("all") if key == "all" else tr(key)
            badge = ""
            if self._counts_loaded and value:
                cnt = self._get_count(self._status_counts.get(value, 0))
                if cnt > 0:
                    badge = f" ({cnt})"
            elif self._counts_loaded and key == "all":
                total = sum(self._get_count(x) for x in self._status_counts.values()) if self._status_counts else 0
                if total > 0:
                    badge = f" ({total})"
            label = f"{base_label}{badge}"
            btn = MDFlatButton(
                text=label,
                font_size="12sp",
                theme_text_color="Custom",
                text_color=rgba(PRIMARY if active else MUTED),
                md_bg_color=rgba("#e8f0e3" if active else CARD_BG),
                on_release=lambda x, v=value: self._set_filter(v),
            )
            self._filter_row.add_widget(btn)

    def _load_status_counts(self):
        try:
            from app.services.customer_service import get_status_counts
            result = get_status_counts()
            if result.get("ok"):
                self._status_counts = result.get("data", {}) or {}
                self._counts_loaded = True
                self._bind_filters()
        except Exception:
            pass

    def on_pre_enter(self, *args):
        from app.core import session
        if not session.is_logged_in() or session.get_role() != "customer":
            if self.manager:
                self.manager.current = "customer_login"
            return
        super().on_pre_enter(*args)

    def on_enter(self, *args):
        from app.core import session
        if not session.is_logged_in() or session.get_role() != "customer":
            if self.manager:
                self.manager.current = "customer_login"
            return
        self._load_status_counts()
        self._refresh()

    def _set_filter(self, value):
        self._status = value
        self._bind_filters()
        self._refresh()

    def _do_search(self, *args):
        self._search = self.search_field.text.strip()
        self._refresh()

    def _on_search_text(self, instance, value):
        if self._search_clock:
            try:
                self._search_clock.cancel()
            except Exception:
                pass
        self._search_clock = Clock.schedule_once(self._do_search_debounced, 0.5)

    def _do_search_debounced(self, dt):
        new_search = self.search_field.text.strip()
        if new_search == self._search:
            return
        self._search = new_search
        self._refresh()

    def _on_scroll_y(self, instance, value):
        # Reached near bottom -> load next page
        if value <= 0.05:
            self.scroll_to_load_more()

    def _refresh(self):
        self._items = []
        self._page = 1
        self._list_content.clear_widgets()
        self._has_more = False
        self._load_page()

    def _load_page(self):
        if self._loading:
            return
        self._loading = True
        self.spinner.active = True
        from app.services.customer_service import get_deliveries
        result = get_deliveries(status=self._status or None, search=self._search or None, page=self._page)
        if result["ok"]:
            data = result["data"]
            page_items = data["items"]
            self._items.extend(page_items)
            self._has_more = data["has_more"]
            self._render_items(page_items)
        else:
            empty = MDLabel(
                text=result["error"] or tr("no_deliveries"),
                font_style="Body2",
                halign="center",
                theme_text_color="Custom",
                text_color=MUTED,
                size_hint_y=None,
                height="80dp",
            )
            self._list_content.add_widget(empty)
        self.spinner.active = False
        self._loading = False

    def _render_items(self, items):
        if not items and not self._items:
            self._list_content.add_widget(
                MDLabel(
                    text=tr("no_deliveries"),
                    font_style="Body2",
                    halign="center",
                    theme_text_color="Custom",
                    text_color=MUTED,
                    size_hint_y=None,
                    height="80dp",
                )
            )
            return
        for wb in items:
            self._list_content.add_widget(WaybillCard(waybill=wb, on_tap=self._open_detail))

    def _open_detail(self, waybill):
        if not self.manager:
            return
        try:
            detail = self.manager.get_screen("waybill_detail")
            if hasattr(detail, "set_waybill"):
                detail.set_waybill(waybill)
            self.manager.current = "waybill_detail"
        except Exception:
            pass

    def on_scroll_end(self):
        pass

    def scroll_to_load_more(self, *args):
        if self._has_more and not self._loading:
            self._page += 1
            self._load_page()

    def _go_back(self, *args):
        self.manager.current = "customer_home"

    def rebuild_ui(self):
        """Rebuild UI when language changes."""
        try:
            self._bind_filters()
            if hasattr(self, 'search_field'):
                self.search_field.hint_text = tr("search_by_tracking")
            # re-render list headers where tr is used
            # header title is second child of outer's first header
            for child in self.walk():
                if isinstance(child, MDLabel) and child.text:
                    # best-effort update known header texts
                    if child.text.strip() in ["Delivery List", "All Deliveries", "Deliveries"]:
                        try:
                            child.text = tr("delivery_list")
                        except Exception:
                            pass
        except Exception:
            pass
