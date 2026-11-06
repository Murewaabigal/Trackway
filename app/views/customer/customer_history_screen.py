from datetime import datetime

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.spinner import MDSpinner

from app.i18n.translator import tr
from app.core.theme import PRIMARY, PRIMARY_DARK, DARK, MUTED, BACKGROUND, CARD_BG, ERROR, SUCCESS
from app.views.base_screen import BaseScreen


def _fmt_fee(v):
    try:
        f = float(str(v).replace(",", "").replace("\u20a6", "").replace("N", "").strip() or 0)
        return f"\u20a6{f:,.2f}"
    except Exception:
        return str(v)


def _fmt_avg(v):
    try:
        f = float(str(v).replace(",", "").strip() or 0)
        return f"{f:.1f}"
    except Exception:
        return str(v) if v is not None else "0.0"


def _format_date_two_lines(val):
    if not val:
        return "-"
    raw = str(val).strip()
    date_part = raw
    time_part = ""
    # Try parse ISO with T
    if "T" in raw:
        parts = raw.split("T")
        date_part = parts[0]
        time_part = parts[1][:5] if len(parts) > 1 else ""
        if time_part and "Z" in time_part:
            time_part = time_part.replace("Z", "")
    elif " " in raw and len(raw) > 10:
        # YYYY-MM-DD HH:MM:SS
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d\n%H:%M")
        except Exception:
            pass
    try:
        # Plain date
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        if time_part:
            return f"{dt.strftime('%Y-%m-%d')}\n{time_part}"
        return dt.strftime("%Y-%m-%d")
    except Exception:
        # fallback: first 10 chars date, rest time
        if len(raw) >= 10:
            d = raw[:10]
            t = raw[11:16] if len(raw) > 11 else ""
            return f"{d}\n{t}" if t else d
        return raw


FILTER_STATUSES = [
    ("all_status", ""),
    ("pending_pickup", "pending_pickup"),
    ("delivered", "delivered"),
    ("in_progress", "in_progress"),
    ("failed", "failed"),
    ("cancelled", "cancelled"),
]


class CustomerHistoryScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._items = []
        self._page = 1
        self._has_more = False
        self._loading = False
        self._statistics = {}
        self._summary = {}
        self._pagination = {}
        self._total = 0
        self._search = ""
        self._filter_status = ""
        self._date_from = ""  # YYYY-MM-DD
        self._date_to = ""
        self._active_tab = "deliveries"
        self._profile_menu = None
        self._search_clock = None

        self._outer = MDBoxLayout(orientation="vertical")
        self._scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self._content = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp", adaptive_height=True, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        top_nav = self._build_top_nav()
        self._outer.add_widget(top_nav)
        self._outer.add_widget(self._scroll)
        self.add_widget(self._outer)

        self._build_title_section()
        self._build_tabs()
        self._build_stats_section()
        self._build_filter_bar()
        self._build_summary_row()
        self._build_results_section()
        self._build_footer()

        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

    # ---------- 1. Header ----------
    def _build_top_nav(self):
        nav = MDCard(orientation="horizontal", padding="6dp", spacing="8dp", size_hint_x=1, size_hint_y=None, height="48dp", md_bg_color=rgba(CARD_BG), radius=[0], elevation=1)
        logo = MDLabel(text="TRACKWAY / SMART LOGISTICS", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=1, size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5}, valign="middle")
        right_cluster = MDBoxLayout(orientation="horizontal", size_hint_x=None, width="230dp", spacing="8dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        try:
            from app.views.shared.language_picker import LanguagePicker
            self.language_picker = LanguagePicker(compact=True)
            self.language_picker.size_hint_x = None
            self.language_picker.width = "36dp"
            right_cluster.add_widget(self.language_picker)
        except Exception:
            right_cluster.add_widget(MDLabel(text="EN", font_style="Caption", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=None, width="32dp", halign="center"))
        dash_btn = MDFlatButton(text="\u2190 Dashboard", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="12sp", size_hint_x=None, width="90dp", on_release=lambda x: self._go_back())
        right_cluster.add_widget(dash_btn)
        avatar = MDCard(size_hint=(None, None), size=("28dp", "28dp"), md_bg_color=rgba(PRIMARY), radius=[14], elevation=0, ripple_behavior=True, pos_hint={"center_y": 0.5})
        avatar.add_widget(MDLabel(text="A", halign="center", valign="middle", theme_text_color="Custom", text_color="white", bold=True))
        right_cluster.add_widget(avatar)
        self._avatar_card = avatar
        name_card = MDCard(size_hint=(None, None), size=("70dp", "32dp"), md_bg_color=[0, 0, 0, 0], radius=[6], elevation=0, ripple_behavior=True, pos_hint={"center_y": 0.5})
        self.top_name_label = MDLabel(text="", font_style="Caption", bold=True, theme_text_color="Custom", text_color=DARK, halign="left", valign="middle")
        name_card.add_widget(self.top_name_label)
        right_cluster.add_widget(name_card)
        self._name_card = name_card
        avatar.bind(on_release=lambda x: self._open_profile_menu())
        name_card.bind(on_release=lambda x: self._open_profile_menu())
        nav.add_widget(logo)
        nav.add_widget(right_cluster)
        self._top_nav = nav
        return nav

    def _create_profile_menu(self):
        if hasattr(self, "_profile_menu") and self._profile_menu:
            return
        items = [
            {"text": "My Profile", "leading_icon": "account-outline", "on_release": lambda: self._menu_navigate("profile")},
            {"text": "Refer & Earn", "leading_icon": "gift-outline", "on_release": lambda: self._menu_action_refer()},
            {"text": "Support", "leading_icon": "headset", "on_release": lambda: self._menu_navigate("support")},
            {"text": "Notifications", "leading_icon": "bell-outline", "on_release": lambda: self._menu_navigate("notifications")},
            {"text": "Full History", "leading_icon": "history", "on_release": lambda: self._menu_navigate("customer_history")},
            {"viewclass": "MDSeparator", "height": dp(1)},
            {"text": "Logout", "leading_icon": "logout", "text_color": rgba(ERROR), "leading_icon_color": rgba(ERROR), "on_release": lambda: self._menu_logout()},
        ]
        caller = getattr(self, "_avatar_card", self._top_nav)
        self._profile_menu = MDDropdownMenu(caller=caller, items=items, width_mult=4, max_height="320dp")

    def _open_profile_menu(self, *args):
        try:
            self._create_profile_menu()
            self._profile_menu.caller = getattr(self, "_avatar_card", self._top_nav)
            self._profile_menu.open()
        except Exception:
            if self.manager:
                self.manager.current = "profile"

    def _menu_navigate(self, route):
        try:
            if hasattr(self, "_profile_menu") and self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", route) if self.manager else None, 0.15)

    def _menu_action_refer(self):
        try:
            if hasattr(self, "_profile_menu") and self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", "refer_earn") if self.manager else None, 0.2)

    def _menu_logout(self):
        try:
            if hasattr(self, "_profile_menu") and self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        def do_logout(dt):
            try:
                from app.services.auth_service import logout
                logout()
            except Exception:
                try:
                    from app.core import session
                    session.clear_session()
                except Exception:
                    pass
            if self.manager:
                self.manager.current = "welcome"
        Clock.schedule_once(do_logout, 0.2)

    def _on_window_width(self, instance, width):
        try:
            hide = width < 360
            if hasattr(self, "top_name_label"):
                self.top_name_label.opacity = 0 if hide else 1
                self.top_name_label.disabled = hide
        except Exception:
            pass

    # ---------- 2. Page Title ----------
    def _build_title_section(self):
        row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="28dp")
        row.add_widget(MDIcon(icon="clock-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="28dp", font_size="22sp", pos_hint={"center_y": 0.5}))
        self._title_label = MDLabel(text=tr("delivery_history"), font_style="H6", bold=True, theme_text_color="Custom", text_color=DARK, adaptive_height=True, pos_hint={"center_y": 0.5})
        row.add_widget(self._title_label)
        self._content.add_widget(row)
        self._subtitle_label = MDLabel(text=tr("delivery_history_subtitle"), font_style="Body2", theme_text_color="Custom", text_color=MUTED, adaptive_height=True)
        self._content.add_widget(self._subtitle_label)

    # ---------- 3. Tabs ----------
    def _build_tabs(self):
        self._tabs_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", padding=["0dp", "2dp", "0dp", "0dp"])
        self._deliveries_tab_btn = MDFlatButton(text=tr("deliveries_tab"), theme_text_color="Custom", text_color=rgba(PRIMARY), on_release=lambda x: self._switch_tab("deliveries"))
        self._rides_tab_btn = MDFlatButton(text=tr("rides_tab"), theme_text_color="Custom", text_color=rgba(MUTED), on_release=lambda x: self._switch_tab("rides"))
        self._tabs_row.add_widget(self._deliveries_tab_btn)
        self._tabs_row.add_widget(self._rides_tab_btn)
        self._content.add_widget(self._tabs_row)
        self._tab_underline = MDBoxLayout(size_hint_x=1, height="2dp", size_hint_y=None, md_bg_color=rgba(PRIMARY))
        self._content.add_widget(self._tab_underline)

    def _switch_tab(self, tab):
        self._active_tab = tab
        if tab == "deliveries":
            self._deliveries_tab_btn.text_color = rgba(PRIMARY)
            self._rides_tab_btn.text_color = rgba(MUTED)
        else:
            self._rides_tab_btn.text_color = rgba(PRIMARY)
            self._deliveries_tab_btn.text_color = rgba(MUTED)
        # Update search placeholder per tab
        try:
            if hasattr(self, "search_field"):
                self.search_field.hint_text = tr("search_tracking_city") if tab == "deliveries" else tr("search_pickup_dropoff")
        except Exception:
            pass
        # Update table header per tab
        try:
            self._update_table_header()
        except Exception:
            pass
        self._render_stats()
        self._render_summary()
        self._update_tab_visibility()

    def _update_tab_visibility(self):
        # Option A: Rides is clean stub always empty but keeps filter/summary/results visible
        # No widget hiding — just re-render results to show ride-specific empty state
        if hasattr(self, '_stats_container'):
            self._render_results()

    # ---------- 4. Stats Row 5 cards ----------
    def _build_stats_section(self):
        self._stats_container = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="8dp")
        self._content.add_widget(self._stats_container)
        self._render_stats()

    def _render_stats(self):
        self._stats_container.clear_widgets()
        if self._active_tab == "rides":
            # Option A: clean stub always 0, ride-specific labels
            items = [
                ("total", 0, "package-variant-closed", PRIMARY, tr("total") if tr("total")!="total" else "Total"),
                ("completed_rides", 0, "check-circle-outline", SUCCESS, tr("completed_rides")),
                ("active_rides", 0, "progress-clock", MUTED, tr("active_rides")),
                ("failed", 0, "close-circle-outline", ERROR, tr("failed")),
                ("cancelled", 0, "cancel", ERROR, tr("cancelled")),
            ]
            grid = GridLayout(cols=3, spacing="8dp", size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            for key, value, icon, color, label_text in items:
                card = MDCard(orientation="vertical", padding="10dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="78dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
                top_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp")
                val_color = ERROR if key in ("failed", "cancelled") else PRIMARY
                val_label = MDLabel(text=str(value), font_style="H6", bold=True, halign="left", theme_text_color="Custom", text_color=rgba(val_color), size_hint_x=1, adaptive_height=True)
                icon_w = MDIcon(icon=icon, theme_text_color="Custom", text_color=rgba(color), halign="right", size_hint_x=None, width="24dp", font_size="18sp")
                top_row.add_widget(val_label)
                top_row.add_widget(icon_w)
                lab = MDLabel(text=label_text, font_style="Caption", halign="left", theme_text_color="Custom", text_color=MUTED, adaptive_height=True)
                card.add_widget(top_row)
                card.add_widget(lab)
                grid.add_widget(card)
            self._stats_container.add_widget(grid)
            return
        s = getattr(self, "_statistics", {}) or {}
        total = s.get("total", s.get("total_deliveries", s.get("totalDeliveries", 0)))
        delivered = s.get("delivered", s.get("Delivered", 0))
        in_progress = s.get("in_progress", s.get("inProgress", s.get("in_progress_count", 0)))
        failed = s.get("failed", s.get("Failed", 0))
        cancelled = s.get("cancelled", s.get("Cancelled", 0))
        if total == 0 and not s:
            total = self._total or len(self._items)
        items = [
            ("total", total, "package-variant-closed", PRIMARY),
            ("delivered", delivered, "check-circle-outline", SUCCESS),
            ("in_progress", in_progress, "progress-clock", MUTED),
            ("failed", failed, "close-circle-outline", ERROR),
            ("cancelled", cancelled, "cancel", ERROR),
        ]
        grid = GridLayout(cols=3, spacing="8dp", size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for key, value, icon, color in items:
            card = MDCard(orientation="vertical", padding="10dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="78dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
            top_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp")
            val_color = ERROR if key in ("failed", "cancelled") else PRIMARY
            val_label = MDLabel(text=str(value), font_style="H6", bold=True, halign="left", theme_text_color="Custom", text_color=rgba(val_color), size_hint_x=1, adaptive_height=True)
            icon_w = MDIcon(icon=icon, theme_text_color="Custom", text_color=rgba(color), halign="right", size_hint_x=None, width="24dp", font_size="18sp")
            top_row.add_widget(val_label)
            top_row.add_widget(icon_w)
            lab = MDLabel(text=tr(key) if tr(key)!=key else key.replace("_"," ").title(), font_style="Caption", halign="left", theme_text_color="Custom", text_color=MUTED, adaptive_height=True)
            card.add_widget(top_row)
            card.add_widget(lab)
            grid.add_widget(card)
        self._stats_container.add_widget(grid)

    # ---------- 5. Filter Bar ----------
    def _build_filter_bar(self):
        self._filter_card = MDCard(orientation="vertical", padding="12dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        self._filter_card._saved_height = "160dp"
        # Row 1: search + status dropdown
        row1 = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_y=None, height="48dp")
        self.search_field = MDTextField(hint_text=tr("search_tracking_city"), mode="round", icon_right="magnify", size_hint_x=0.6)
        self.search_field.bind(text=self._on_search_text)
        row1.add_widget(self.search_field)
        self._status_field = MDTextField(hint_text=tr("all_status"), text="", mode="rectangle", readonly=True, size_hint_x=0.4)
        self._status_field.bind(on_touch_down=self._maybe_open_status_menu)
        self._status_field.bind(on_focus=self._on_status_focus)
        row1.add_widget(self._status_field)
        self._filter_card.add_widget(row1)
        self._status_menu = None
        self._build_status_menu()

        # Row 2: two date pickers (mm/dd/yyyy display, YYYY-MM-DD sent)
        row2 = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_y=None, height="48dp")
        self._date_from_field = MDTextField(hint_text="mm/dd/yyyy", mode="rectangle", readonly=True, helper_text="From", helper_text_mode="on_focus", icon_right="calendar", size_hint_x=0.5)
        self._date_from_field.bind(on_touch_down=self._maybe_open_date_from)
        row2.add_widget(self._date_from_field)
        self._date_to_field = MDTextField(hint_text="mm/dd/yyyy", mode="rectangle", readonly=True, helper_text="To", helper_text_mode="on_focus", icon_right="calendar", size_hint_x=0.5)
        self._date_to_field.bind(on_touch_down=self._maybe_open_date_to)
        row2.add_widget(self._date_to_field)
        self._filter_card.add_widget(row2)

        # Row 3: Filter + Reset
        row3 = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_y=None, height="36dp")
        row3.add_widget(MDLabel(text=""))  # spacer
        self._filter_btn = MDRaisedButton(text=tr("filter"), md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="90dp", on_release=lambda x: self._apply_filter())
        row3.add_widget(self._filter_btn)
        self._reset_btn = MDFlatButton(text=tr("reset"), theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="60dp", on_release=lambda x: self._reset_filters())
        row3.add_widget(self._reset_btn)
        self._filter_card.add_widget(row3)

        self._content.add_widget(self._filter_card)

    def _build_status_menu(self):
        items = []
        for tr_key, val in FILTER_STATUSES:
            label = tr(tr_key) if tr(tr_key)!=tr_key else tr_key.replace("_"," ").title()
            if tr_key=="all_status":
                label = tr("all_status")
            items.append({"text": label, "viewclass": "OneLineListItem", "on_release": lambda v=val, lbl=label: self._select_status(v, lbl)})
        try:
            self._status_menu = MDDropdownMenu(caller=self._status_field, items=items, width_mult=4, max_height="280dp")
        except Exception:
            self._status_menu = None

    def _maybe_open_status_menu(self, instance, touch):
        if instance != self._status_field:
            return False
        if instance.collide_point(*touch.pos):
            try:
                if self._status_menu:
                    self._status_menu.caller = self._status_field
                    self._status_menu.open()
                    return True
            except Exception:
                pass
        return False

    def _on_status_focus(self, instance, value):
        if value:
            try:
                if self._status_menu:
                    self._status_menu.caller = self._status_field
                    self._status_menu.open()
            except Exception:
                pass

    def _select_status(self, val, label):
        self._filter_status = val
        self._status_field.text = "" if val=="" else label
        self._status_field.hint_text = tr("all_status") if val=="" else label
        try:
            if self._status_menu:
                self._status_menu.dismiss()
        except Exception:
            pass

    def _maybe_open_date_from(self, instance, touch):
        if instance != self._date_from_field:
            return False
        if instance.collide_point(*touch.pos):
            self._open_date_picker("from")
            return True
        return False

    def _maybe_open_date_to(self, instance, touch):
        if instance != self._date_to_field:
            return False
        if instance.collide_point(*touch.pos):
            self._open_date_picker("to")
            return True
        return False

    def _open_date_picker(self, which):
        try:
            from kivymd.uix.pickers import MDDatePicker
            picker = MDDatePicker()
            def on_save(inst, value, date_range):
                # value is datetime.date
                yyyy_mm_dd = value.strftime("%Y-%m-%d")
                mm_dd_yyyy = value.strftime("%m/%d/%Y")
                if which == "from":
                    self._date_from = yyyy_mm_dd
                    self._date_from_field.text = mm_dd_yyyy
                    self._date_from_field.hint_text = "mm/dd/yyyy"
                else:
                    self._date_to = yyyy_mm_dd
                    self._date_to_field.text = mm_dd_yyyy
                    self._date_to_field.hint_text = "mm/dd/yyyy"
                try:
                    picker.dismiss()
                except Exception:
                    pass
            picker.bind(on_save=on_save, on_cancel=lambda *a: picker.dismiss())
            picker.open()
        except Exception:
            # Fallback: text input hint
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text="Pick date: type mm/dd/yyyy").open()
            except Exception:
                pass

    def _on_search_text(self, instance, value):
        if self._search_clock:
            try:
                self._search_clock.cancel()
            except Exception:
                pass
        self._search_clock = Clock.schedule_once(self._do_search_debounced, 0.6)

    def _do_search_debounced(self, dt):
        self._search = self.search_field.text.strip()
        # Debounced auto-filter server-side
        self._page = 1
        self._load_page()

    def _apply_filter(self, *args):
        self._search = self.search_field.text.strip()
        self._page = 1
        self._load_page()

    def _reset_filters(self, *args):
        self._search = ""
        self._filter_status = ""
        self._date_from = ""
        self._date_to = ""
        try:
            self.search_field.text = ""
            self._status_field.text = ""
            self._status_field.hint_text = tr("all_status")
            self._date_from_field.text = ""
            self._date_to_field.text = ""
            self._build_status_menu()
        except Exception:
            pass
        self._page = 1
        self._load_page()

    # ---------- 6. Results Summary ----------
    def _build_summary_row(self):
        self._summary_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_y=None, height="36dp", padding=["0dp", "4dp", "0dp", "0dp"])
        self._summary_row._saved_height = "36dp"
        self._summary_label = MDLabel(text="", font_style="Body2", theme_text_color="Custom", text_color=DARK, size_hint_x=1, adaptive_height=True, halign="left")
        self._summary_row.add_widget(self._summary_label)
        # Avg Distance pill
        self._avg_card = MDCard(orientation="vertical", padding=["8dp", "2dp"], radius=[14], elevation=0, md_bg_color=rgba(CARD_BG), size_hint_x=None, width="130dp", size_hint_y=None, height="28dp")
        self._avg_label = MDLabel(text="", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), font_size="11sp")
        self._avg_card.add_widget(self._avg_label)
        self._summary_row.add_widget(self._avg_card)
        # Total Spent pill
        self._spent_card = MDCard(orientation="vertical", padding=["8dp", "2dp"], radius=[14], elevation=0, md_bg_color=rgba("#e8f0e3"), size_hint_x=None, width="140dp", size_hint_y=None, height="28dp")
        self._spent_label = MDLabel(text="", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="11sp", bold=True)
        self._spent_card.add_widget(self._spent_label)
        self._summary_row.add_widget(self._spent_card)
        self._content.add_widget(self._summary_row)
        self._render_summary()

    def _render_summary(self):
        try:
            if self._active_tab == "rides":
                if hasattr(self, '_summary_label'):
                    self._summary_label.text = tr("showing_x_of_y_rides").format(shown=0, total=0)
                self._avg_label.text = tr("avg_distance").format(dist="0.0")
                self._spent_label.text = tr("total_spent_label").format(amount="\u20a60.00")
                return
            total = self._total or len(self._items)
            shown = len(self._items)
            if hasattr(self, '_summary_label'):
                self._summary_label.text = tr("showing_x_of_y").format(shown=shown, total=total)
            # summary may have avg_distance/total_spent or compute client-side over items if missing
            summary = getattr(self, "_summary", {}) or {}
            avg_raw = summary.get("avg_distance") or summary.get("avgDistance")
            spent_raw = summary.get("total_spent") or summary.get("totalSpent")
            if avg_raw is None:
                # client calc over items distance fields
                try:
                    dists = []
                    for wb in self._items:
                        raw = wb.get("distance") or wb.get("distance_km") or wb.get("distanceKm") or 0
                        dists.append(float(str(raw).replace(",", "").replace("km","").strip() or 0))
                    avg_raw = sum(dists)/len(dists) if dists else 0
                except Exception:
                    avg_raw = 0
            if spent_raw is None:
                try:
                    fees = []
                    for wb in self._items:
                        raw = wb.get("fee") or wb.get("price") or wb.get("amount") or 0
                        fees.append(float(str(raw).replace(",", "").replace("\u20a6","").replace("N","").strip() or 0))
                    spent_raw = sum(fees)
                except Exception:
                    spent_raw = 0
            avg_str = _fmt_avg(avg_raw)
            spent_str = _fmt_fee(spent_raw)
            self._avg_label.text = tr("avg_distance").format(dist=avg_str)
            self._spent_label.text = tr("total_spent_label").format(amount=spent_str)
        except Exception:
            pass

    # ---------- 7. Results Table (mobile cards) ----------
    def _build_results_section(self):
        self._results_card = MDCard(orientation="vertical", padding="12dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        self._results_card._saved_height = "200dp"
        # Table header (Caption) — stored for per-tab rebuild
        self._table_header = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="4dp", size_hint_y=None, height="20dp")
        self._results_card.add_widget(self._table_header)
        self._update_table_header()
        self._results_list = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, size_hint_y=None)
        self._results_list.bind(minimum_height=self._results_list.setter("height"))
        self._results_card.add_widget(self._results_list)
        self._list_scroll_inner = ScrollView(size_hint_y=None, height="0dp")  # not used; keep for pagination scroll detection on outer _scroll
        self.spinner = MDSpinner(size_hint=(None, None), size=(28, 28), active=False, color=rgba(PRIMARY), pos_hint={"center_x": 0.5})
        self._results_card.add_widget(self.spinner)
        # Bind outer scroll for pagination
        self._scroll.bind(scroll_y=self._on_scroll_y)
        self._content.add_widget(self._results_card)

    def _update_table_header(self):
        if not hasattr(self, "_table_header"):
            return
        self._table_header.clear_widgets()
        if self._active_tab == "rides":
            cols = [tr("ride_id"), tr("route"), tr("status"), tr("distance"), tr("fare"), tr("date")]
        else:
            cols = [tr("tracking_number"), tr("route"), tr("status"), tr("distance"), tr("fee"), tr("date")]
        for col in cols:
            self._table_header.add_widget(MDLabel(text=col, font_style="Caption", bold=True, theme_text_color="Custom", text_color=MUTED, halign="center", font_size="10sp", size_hint_x=1))
        self._table_header.add_widget(MDLabel(text=tr("actions") if tr("actions")!="actions" else "Action", font_style="Caption", bold=True, theme_text_color="Custom", text_color=MUTED, halign="center", font_size="10sp", size_hint_x=1))

    def _on_scroll_y(self, instance, value):
        if value <= 0.05 and self._active_tab == "deliveries":
            self.scroll_to_load_more()

    def scroll_to_load_more(self, *args):
        if self._has_more and not self._loading:
            self._page += 1
            self._load_page()

    def _on_empty_cta(self, *args):
        if self.manager:
            self.manager.current = "request_delivery"
            return
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="Coming soon \u2014 Request Delivery will be available shortly.").open()
        except Exception:
            pass

    def _on_rides_cta(self, *args):
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="Coming soon \u2014 Request Ride will be available shortly.").open()
        except Exception:
            if self.manager:
                self.manager.current = "customer_home"

    def _cta_label(self):
        for k in ("send_first_parcel", "request_first_delivery", "history.request_first_delivery"):
            v = tr(k)
            if v != k:
                return v
        return "Send Your First Parcel"

    def _rides_cta_label(self):
        for k in ("request_first_ride", "history.request_first_ride"):
            v = tr(k)
            if v != k:
                return v
        return "Request Your First Ride"

    def _render_results(self):
        self._results_list.clear_widgets()
        if self._active_tab == "rides":
            # Option A: clean stub always empty with ride-specific 4-element empty
            empty = MDBoxLayout(orientation="vertical", spacing="12dp", adaptive_height=True, padding=["12dp", "24dp", "12dp", "24dp"], size_hint_y=None)
            empty.bind(minimum_height=empty.setter("height"))
            empty.add_widget(MDIcon(icon="car-outline", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), font_size="48sp", size_hint_y=None, height="48dp"))
            empty.add_widget(MDLabel(text=tr("no_rides_found") if tr("no_rides_found") != "no_rides_found" else "No rides found.", font_style="Subtitle1", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True))
            empty.add_widget(MDLabel(text=tr("no_rides_subtitle") if tr("no_rides_subtitle") != "no_rides_subtitle" else "You haven't requested any rides yet.", font_style="Body2", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            cta = MDRaisedButton(text=self._rides_cta_label(), md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", pos_hint={"center_x": 0.5}, size_hint_x=None, width="200dp", on_release=self._on_rides_cta)
            empty.add_widget(cta)
            self._results_list.add_widget(empty)
            return
        items = self._items
        if not items:
            empty = MDBoxLayout(orientation="vertical", spacing="12dp", adaptive_height=True, padding=["12dp", "24dp", "12dp", "24dp"], size_hint_y=None)
            empty.bind(minimum_height=empty.setter("height"))
            empty.add_widget(MDIcon(icon="package-variant-closed", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), font_size="48sp", size_hint_y=None, height="48dp"))
            empty.add_widget(MDLabel(text=tr("no_deliveries_found") if tr("no_deliveries_found") != "no_deliveries_found" else "No deliveries found", font_style="Subtitle1", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True))
            empty.add_widget(MDLabel(text=tr("no_deliveries_subtitle") if tr("no_deliveries_subtitle") != "no_deliveries_subtitle" else "You haven't made any deliveries yet or no results match your filters.", font_style="Body2", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            cta = MDRaisedButton(text=self._cta_label(), md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", pos_hint={"center_x": 0.5}, size_hint_x=None, width="200dp", on_release=self._on_empty_cta)
            empty.add_widget(cta)
            self._results_list.add_widget(empty)
            return
        for wb in items:
            self._results_list.add_widget(self._create_history_row(wb))

    def _create_history_row(self, wb):
        tracking = wb.get("waybill_number") or wb.get("tracking_number") or wb.get("waybill") or ""
        origin = wb.get("origin") or wb.get("origin_city") or ""
        dest = wb.get("destination") or wb.get("destination_city") or ""
        route = f"{origin} \u2192 {dest}" if origin or dest else ""
        status = wb.get("status") or ""
        status_label = wb.get("status_label") or tr(status) if tr(status)!=status else status
        status_color_hex = wb.get("status_color") or wb.get("statusColor")
        # Fallback colors if not provided
        if not status_color_hex:
            if status == "failed":
                status_color_hex = ERROR
            elif status == "cancelled":
                status_color_hex = MUTED
            elif status == "delivered":
                status_color_hex = SUCCESS
            elif status in ("pending_pickup",):
                status_color_hex = "#ff9800"
            else:
                status_color_hex = PRIMARY
        distance_raw = wb.get("distance") or wb.get("distance_km") or wb.get("distanceKm") or ""
        try:
            d = float(str(distance_raw).replace(",", "").replace("km","").strip() or 0)
            distance = f"{d:.1f} km"
        except Exception:
            distance = str(distance_raw)
        fee_raw = wb.get("fee") or wb.get("price") or wb.get("amount") or ""
        fee = _fmt_fee(fee_raw)
        date_raw = wb.get("created_at") or wb.get("date") or wb.get("delivery_date") or ""
        date_two = _format_date_two_lines(date_raw)

        card = MDCard(orientation="vertical", padding="10dp", spacing="6dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, line_color=rgba(status_color_hex) if status_color_hex else rgba(0,0,0,0), line_width=0.6)
        # Top grid: 2 rows emulating 6 cols
        # Row A: tracking + status pill + action
        top = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_y=None, height="28dp")
        top.add_widget(MDLabel(text=tracking, font_style="Caption", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1, adaptive_height=True, halign="left"))
        pill = MDCard(size_hint=(None, None), size=("90dp", "20dp"), md_bg_color=rgba("#fff3e0") if status=="pending_pickup" else rgba(CARD_BG), line_color=rgba(status_color_hex), radius=[12], elevation=0)
        pill.add_widget(MDLabel(text=status_label, halign="center", font_style="Caption", theme_text_color="Custom", text_color=rgba(status_color_hex), font_size="10sp"))
        top.add_widget(pill)
        # Action button
        is_pending = status == "pending_pickup"
        if is_pending:
            action_btn = MDRaisedButton(text=tr("select_rider_action"), md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", font_size="11sp", size_hint_x=None, width="90dp", size_hint_y=None, height="28dp", on_release=lambda x, w=wb: self._select_rider(w))
        else:
            action_btn = MDFlatButton(text=tr("view_details"), theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="11sp", size_hint_x=None, width="90dp", size_hint_y=None, height="28dp", on_release=lambda x, w=wb: self._open_detail(w))
        top.add_widget(action_btn)
        card.add_widget(top)

        # Row B: Route + Distance + Fee + Date (mobile 2-line)
        bottom = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp")
        bottom.add_widget(MDLabel(text=route, font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_x=0.35, adaptive_height=True, halign="left", text_size=(None, None)))
        # Distance with icon
        dist_box = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="2dp", size_hint_x=0.2)
        dist_box.add_widget(MDIcon(icon="map-marker-distance", theme_text_color="Custom", text_color=rgba(MUTED), font_size="12sp", size_hint_x=None, width="14dp"))
        dist_box.add_widget(MDLabel(text=distance, font_style="Caption", theme_text_color="Custom", text_color=MUTED, font_size="10sp", halign="left"))
        bottom.add_widget(dist_box)
        bottom.add_widget(MDLabel(text=fee, font_style="Caption", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=0.2, halign="center", font_size="10sp"))
        bottom.add_widget(MDLabel(text=date_two, font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_x=0.25, halign="right", font_size="10sp"))
        card.add_widget(bottom)
        return card

    def _select_rider(self, waybill):
        # Wire real endpoints: available_riders -> select_rider
        tracking = waybill.get("waybill_number") or waybill.get("tracking_number") or ""
        try:
            from app.core.api_client import api_get, api_post
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.list import OneLineListItem
            # Fetch riders
            resp = api_get("available_riders", params={"waybill_number": tracking} if tracking else {})
            if not resp.get("ok"):
                try:
                    from kivymd.uix.snackbar import Snackbar
                    Snackbar(text=resp.get("error") or tr("error")).open()
                except Exception:
                    pass
                return
            data = resp.get("data") or {}
            # Normalize riders list
            riders = []
            if isinstance(data, dict):
                riders = data.get("riders") or data.get("data") or data.get("items") or []
                if isinstance(riders, dict):
                    riders = riders.get("items") or []
            if not isinstance(riders, list):
                riders = []
            if not riders:
                try:
                    from kivymd.uix.snackbar import Snackbar
                    Snackbar(text="No riders available").open()
                except Exception:
                    pass
                return
            # Build dialog list
            from kivymd.uix.boxlayout import MDBoxLayout as _Box
            from kivy.uix.scrollview import ScrollView as _SV
            from kivymd.uix.list import MDList as _List
            content = _Box(orientation="vertical", size_hint_y=None, height="200dp")
            sv = _SV()
            lst = _List()
            sv.add_widget(lst)
            content.add_widget(sv)
            dialog = MDDialog(title=tr("choose_rider"), type="custom", content_cls=content, buttons=[MDFlatButton(text=tr("cancel"), on_release=lambda x: dialog.dismiss())])
            def choose(r):
                dialog.dismiss()
                rid = r.get("id") or r.get("rider_id") or ""
                payload = {"waybill_number": tracking, "rider_id": rid}
                # Also try waybill_number variations
                r2 = api_post("select_rider", payload=payload)
                try:
                    from kivymd.uix.snackbar import Snackbar
                    if r2.get("ok"):
                        Snackbar(text="Rider selected").open()
                        self._page = 1
                        self._load_page()
                    else:
                        Snackbar(text=r2.get("error") or tr("error")).open()
                except Exception:
                    pass
            for r in riders[:10]:
                name = r.get("name") or r.get("full_name") or r.get("rider_name") or f"Rider {r.get('id','')}"
                item = OneLineListItem(text=name, on_release=lambda x, rr=r: choose(rr))
                lst.add_widget(item)
            dialog.open()
        except Exception as e:
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text=str(e)).open()
            except Exception:
                pass

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

    # ---------- 8. Footer ----------
    def _build_footer(self):
        card = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="56dp", md_bg_color=rgba(DARK), radius=[0], elevation=0)
        card.add_widget(MDLabel(text="\u00a9 2026 Trackway Logistics. Trackway Smart Logistics. All rights reserved.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        card.add_widget(MDLabel(text="Delivering Excellence, One Parcel at a Time.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        self._content.add_widget(card)

    # ---------- Lifecycle ----------
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
        try:
            name = session.get_customer_name() or ""
            self.top_name_label.text = name
            if hasattr(self, "_avatar_card"):
                initial = (name.strip()[0].upper() if name else "A")
                self._avatar_card.children[0].text = initial
        except Exception:
            pass
        self._page = 1
        self._load_page()
        try:
            self._on_window_width(Window, Window.width if hasattr(Window, "width") else 400)
        except Exception:
            pass

    def _load_page(self):
        if self._loading:
            return
        self._loading = True
        self.spinner.active = True
        if self._page == 1:
            self._items = []
            self._results_list.clear_widgets()
        from app.services.customer_service import get_history
        result = get_history(search=self._search or None, status=self._filter_status or None, date_from=self._date_from or None, date_to=self._date_to or None, page=self._page)
        if result["ok"]:
            data = result["data"]
            page_items = data.get("items", []) or []
            self._items.extend(page_items)
            self._has_more = data.get("has_more", False)
            self._page = data.get("page", self._page)
            self._total = data.get("total", self._total)
            self._statistics = data.get("statistics", {}) or {}
            self._pagination = data.get("pagination", {}) or {}
            self._summary = data.get("summary", {}) or {}
            # Sync statistics fallback to status_counts style if empty but items exist
            if not self._statistics and self._items:
                # minimal total
                self._statistics = {"total": self._total or len(self._items)}
            self._render_stats()
            self._render_summary()
            self._render_results()
        else:
            err = result.get("error") or tr("error")
            if "Session expired" in str(err):
                from app.core import session
                session.clear_session()
                if self.manager:
                    self.manager.current = "customer_login"
                self._loading = False
                self.spinner.active = False
                return
            self._results_list.add_widget(MDLabel(text=err, font_style="Body2", halign="center", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="80dp"))
        self.spinner.active = False
        self._loading = False

    def _refresh(self):
        self._page = 1
        self._load_page()

    def _go_back(self, *args):
        if self.manager:
            self.manager.current = "customer_home"

    def rebuild_ui(self):
        try:
            self._title_label.text = tr("delivery_history")
            self._subtitle_label.text = tr("delivery_history_subtitle")
            self._deliveries_tab_btn.text = tr("deliveries_tab")
            self._rides_tab_btn.text = tr("rides_tab")
            self.search_field.hint_text = tr("search_tracking_city") if self._active_tab == "deliveries" else tr("search_pickup_dropoff")
            self._status_field.hint_text = tr("all_status")
            self._build_status_menu()
            self._filter_btn.text = tr("filter")
            self._reset_btn.text = tr("reset")
            self._update_table_header()
            self._render_stats()
            self._render_summary()
            self._render_results()
        except Exception:
            pass
