from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.spinner import MDSpinner

from app.core.theme import PRIMARY, DARK, MUTED, BACKGROUND, CARD_BG, SUCCESS, ERROR
from app.core import session
from app.views.base_screen import BaseScreen

# ui slug -> api slug folded assumption 2026-09-23 pending verification
FILTERS = [
    ("all", "", "package-variant-closed"),  # All
    ("pending", "pending_pickup", "clock-outline"),  # Pending
    ("picked_up", "picked_up", "check-circle-outline"),  # Picked Up
    ("in_transit", "in_transit", "truck-delivery"),  # In Transit (folds arrived/out_for_delivery)
    ("delivered", "delivered", "check-decagram"),  # Delivered
    ("failed", "failed", "alert-circle-outline"),  # Failed (folds cancelled)
]


class RiderDeliveriesScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._items = []
        self._page = 1
        self._has_more = False
        self._loading = False
        self._status = "all"
        self._secondary = "all"
        self._status_counts = {}
        self._counts_loaded = False
        self._search = ""
        self._secondary_menu = None
        self._profile_menu = None

        self._outer = MDBoxLayout(orientation="vertical", spacing="0dp")
        self._scroll = ScrollView(do_scroll_x=False, bar_width=dp(4), size_hint_y=1, effect_cls="DampedScrollEffect")
        try:
            self._scroll.effect_y.allow_overscroll = False
            self._scroll.effect_x.allow_overscroll = False
        except Exception:
            pass
        self._scroll.bind(scroll_y=self._on_scroll_y)
        self._content = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp", adaptive_height=True, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        self._outer.add_widget(self._build_top_nav())
        self._outer.add_widget(self._scroll)
        self.add_widget(self._outer)

        self._build_content_header()
        self._build_filter_tabs()
        self._build_secondary_bar()
        self._build_results_header()
        self._build_list()
        self._build_footer()

        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass
        self._bind_filters()

    # ---------- Top nav (standard parity) ----------
    def _build_top_nav(self):
        nav = MDCard(orientation="horizontal", padding="6dp", spacing="6dp", size_hint_x=1, size_hint_y=None, height="48dp", md_bg_color=rgba(CARD_BG), radius=[0], elevation=2)
        logo_box = MDBoxLayout(orientation="vertical", size_hint_x=1, size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5}, spacing="0dp")
        _track = MDLabel(text="TRACKWAY", font_style="Subtitle2", bold=True, font_size="12sp", theme_text_color="Custom", text_color=DARK, size_hint_y=None, height="16dp", halign="left", shorten=True, max_lines=1)
        _smart = MDLabel(text="SMART LOGISTICS", font_style="Caption", font_size="6.5sp", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="9dp", halign="left", shorten=False, max_lines=1)
        logo_box.add_widget(_track)
        logo_box.add_widget(_smart)
        try:
            logo_box.bind(width=lambda inst, w, lbl=_smart: setattr(lbl, "text_size", (w - dp(4), None)))
            _smart.text_size = (logo_box.width - dp(4), None) if logo_box.width else (dp(90), None)
        except Exception:
            pass
        right = MDBoxLayout(orientation="horizontal", size_hint_x=None, width="250dp", spacing="6dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        try:
            from app.views.shared.language_picker import LanguagePicker
            lp = LanguagePicker(compact=True)
            lp.size_hint_x = None
            lp.width = "36dp"
            right.add_widget(lp)
        except Exception:
            right.add_widget(MDLabel(text="EN", font_style="Caption", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=None, width="32dp", halign="center"))
        dash_btn = MDFlatButton(text="← Dashboard", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="12sp", size_hint_x=None, width="90dp", on_release=lambda x: self._go_dashboard())
        right.add_widget(dash_btn)
        avatar = MDCard(size_hint=(None,None), size=("28dp","28dp"), md_bg_color=rgba(PRIMARY), radius=[14], elevation=0, ripple_behavior=True, pos_hint={"center_y": 0.5})
        avatar.add_widget(MDLabel(text="A", halign="center", theme_text_color="Custom", text_color="white", bold=True))
        right.add_widget(avatar)
        self._avatar_card = avatar
        name_card = MDCard(size_hint=(None,None), size=("90dp","32dp"), md_bg_color=[0,0,0,0], radius=[6], elevation=0, ripple_behavior=True, pos_hint={"center_y": 0.5})
        self.top_name_label = MDLabel(text="", font_style="Caption", bold=True, theme_text_color="Custom", text_color=DARK, halign="left")
        name_card.add_widget(self.top_name_label)
        right.add_widget(name_card)
        self._name_card = name_card
        avatar.bind(on_release=lambda x: self._open_profile_menu())
        name_card.bind(on_release=lambda x: self._open_profile_menu())
        nav.add_widget(logo_box)
        nav.add_widget(right)
        self._top_nav = nav
        return nav

    def _create_profile_menu(self):
        if hasattr(self, "_profile_menu") and self._profile_menu:
            return
        items = [
            {"text": "My Profile", "leading_icon": "account-outline", "on_release": lambda: self._menu_navigate("rider_profile")},
            {"text": "My Wallet", "leading_icon": "wallet-outline", "on_release": lambda: self._menu_navigate("rider_wallet")},
            {"text": "Earnings", "leading_icon": "cash", "on_release": lambda: self._menu_navigate("rider_earnings")},
            {"text": "Support", "leading_icon": "headset", "on_release": lambda: self._menu_navigate("rider_support")},
            {"text": "Notifications", "leading_icon": "bell-outline", "on_release": lambda: self._menu_navigate("rider_notifications")},
            {"viewclass": "MDSeparator", "height": dp(1)},
            {"text": "Logout", "leading_icon": "logout", "text_color": rgba(ERROR), "leading_icon_color": rgba(ERROR), "on_release": lambda: self._menu_logout()},
        ]
        caller = getattr(self, "_avatar_card", self._top_nav)
        self._profile_menu = MDDropdownMenu(caller=caller, items=items, width_mult=4, max_height="320dp", border_margin=dp(8))

    def _open_profile_menu(self, *args):
        try:
            self._create_profile_menu()
            self._profile_menu.caller = getattr(self, "_avatar_card", self._top_nav)
            self._profile_menu.open()
        except Exception:
            pass

    def _menu_navigate(self, route):
        try:
            if self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", route) if self.manager else None, 0.15)

    def _menu_logout(self):
        try:
            if self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        def do(dt):
            try:
                from app.services.auth_service import logout
                logout()
            except Exception:
                try:
                    session.clear_session()
                except Exception:
                    pass
            if self.manager:
                self.manager.current = "welcome"
        Clock.schedule_once(do, 0.2)

    def _go_dashboard(self, *args):
        if self.manager:
            self.manager.current = "rider_home"

    def _on_window_width(self, instance, width):
        try:
            hide = width < 360
            if hasattr(self, "top_name_label"):
                self.top_name_label.opacity = 0 if hide else 1
        except Exception:
            pass

    # ---------- Content header ----------
    def _build_content_header(self):
        box = MDBoxLayout(orientation="vertical", spacing="4dp", adaptive_height=True, padding=["2dp","4dp","0dp","4dp"])
        row = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_y=None, height="24dp")
        row.add_widget(MDIcon(icon="truck-delivery-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="18sp", size_hint_x=None, width="22dp"))
        row.add_widget(MDLabel(text="My Deliveries", font_style="H6", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1, halign="left"))
        box.add_widget(row)
        box.add_widget(MDLabel(text="View and manage all your assigned deliveries", font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
        self._content.add_widget(box)

    # ---------- Status filter tabs (6 pills, horizontal scroll) ----------
    def _build_filter_tabs(self):
        wrap = ScrollView(do_scroll_x=True, do_scroll_y=False, size_hint_y=None, height="36dp", bar_width=0)
        self._filter_row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_x=None)
        self._filter_row.bind(minimum_width=self._filter_row.setter("width"))
        wrap.add_widget(self._filter_row)
        self._filter_wrap = wrap
        self._content.add_widget(wrap)

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
        try:
            self._filter_row.clear_widgets()
        except Exception:
            return
        for key, api_val, icon in FILTERS:
            active = (self._status == key)
            # Q3: show counts on all 6 pills once loaded (e.g., Pending (3))
            badge = ""
            if self._counts_loaded:
                if key == "all":
                    total = sum(self._get_count(x) for x in self._status_counts.values()) if self._status_counts else 0
                    # per spec empty shows 0
                    badge = f" ({total})" if total is not None else " (0)"
                else:
                    cnt = self._get_count(self._status_counts.get(api_val, self._status_counts.get(key, 0)))
                    # also fold counts per Q1: in_transit includes arrived/out, failed includes cancelled
                    if key == "in_transit":
                        cnt = cnt + self._get_count(self._status_counts.get("arrived_destination_city", 0)) + self._get_count(self._status_counts.get("out_for_delivery", 0))
                    if key == "failed":
                        cnt = cnt + self._get_count(self._status_counts.get("cancelled", 0))
                    badge = f" ({cnt})"
            # Q1 mapping comment retained in FILTERS definition
            label_map = {"all":"All","pending":"Pending","picked_up":"Picked Up","in_transit":"In Transit","delivered":"Delivered","failed":"Failed"}
            base = label_map.get(key, key.replace("_"," ").title())
            label = f"{base}{badge}"
            btn = MDFlatButton(text=label, font_size="11sp", size_hint_x=None, width="110dp", size_hint_y=None, height="28dp", theme_text_color="Custom", text_color=rgba("#FFFFFF" if active else DARK), md_bg_color=rgba(PRIMARY if active else CARD_BG), line_color=rgba(PRIMARY if not active else "#00000000"))
            try:
                btn.radius = [16]
                btn.line_width = 1
            except Exception:
                pass
            # icon left — MDFlatButton has no icon, prepend via text
            # Use unicode icon + label for simplicity, keep icon param for future
            btn.bind(on_release=lambda x, k=key: self._set_filter(k))
            self._filter_row.add_widget(btn)

    def _set_filter(self, key):
        self._status = key
        self._bind_filters()
        self._refresh()

    def _load_status_counts(self):
        try:
            from app.services.rider_service import get_rider_delivery_status_counts
            result = get_rider_delivery_status_counts()
            if result.get("ok"):
                self._status_counts = result.get("data", {}) or {}
                self._counts_loaded = True
                self._bind_filters()
            else:
                # fallback: derive counts as 0 (empty state) — still show (0) on all pills per Q3
                self._status_counts = {"all":0}
                self._counts_loaded = True
                self._bind_filters()
        except Exception:
            self._status_counts = {}
            self._counts_loaded = True
            self._bind_filters()

    # ---------- Secondary filter bar (stub Q2) ----------
    def _build_secondary_bar(self):
        # TODO Q2: dropdown options not yet captured — hold, ship with single "All" item, Filter just refreshes current status
        card = MDCard(orientation="horizontal", padding="8dp", spacing="8dp", size_hint_x=1, size_hint_y=None, height="48dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        self._secondary_field = MDFlatButton(text="All", font_size="11sp", theme_text_color="Custom", text_color=DARK, size_hint_x=1, size_hint_y=None, height="32dp", line_color=rgba("#e0e0e0"), md_bg_color=rgba(CARD_BG), on_release=lambda x: self._show_secondary_menu())
        try:
            self._secondary_field.radius = [8]
        except Exception:
            pass
        card.add_widget(self._secondary_field)
        filt_btn = MDRaisedButton(text="▼ Filter", font_size="11sp", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="90dp", size_hint_y=None, height="32dp", on_release=lambda x: self._apply_secondary())
        card.add_widget(filt_btn)
        self._secondary_card = card
        self._content.add_widget(card)

    def _show_secondary_menu(self, *args):
        # Q2 hold: only All
        items = [{"text": "All", "viewclass": "OneLineListItem", "on_release": lambda: self._select_secondary("all")}]
        try:
            if self._secondary_menu:
                self._secondary_menu.dismiss()
        except Exception:
            pass
        self._secondary_menu = MDDropdownMenu(caller=self._secondary_field, items=items, width_mult=4, max_height="200dp")
        self._secondary_menu.open()

    def _select_secondary(self, val):
        self._secondary = val
        self._secondary_field.text = "All"
        try:
            if self._secondary_menu:
                self._secondary_menu.dismiss()
        except Exception:
            pass

    def _apply_secondary(self, *args):
        # currently no second-tier filtering — just refresh with status
        self._refresh()

    # ---------- Results count ----------
    def _build_results_header(self):
        row = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="20dp")
        row.add_widget(MDIcon(icon="view-list", theme_text_color="Custom", text_color=rgba(MUTED), font_size="14sp", size_hint_x=None, width="18dp"))
        self._results_label = MDLabel(text="Showing 0 of 0 deliveries", font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=MUTED, halign="left", size_hint_x=1)
        row.add_widget(self._results_label)
        self._content.add_widget(row)

    def _update_results_header(self):
        try:
            total = getattr(self, "_total", len(self._items))
            showing = len(self._items)
            self._results_label.text = f"Showing {showing} of {total} deliveries"
        except Exception:
            pass

    # ---------- List ----------
    def _build_list(self):
        self._list_box = MDBoxLayout(orientation="vertical", spacing="10dp", adaptive_height=True, size_hint_y=None)
        self._list_box.bind(minimum_height=self._list_box.setter("height"))
        self._content.add_widget(self._list_box)
        self._spinner = MDSpinner(size_hint=(None,None), size=("24dp","24dp"), active=False, color=rgba(PRIMARY), pos_hint={"center_x":0.5})
        self._content.add_widget(self._spinner)
        self._render_list()

    def _render_list(self):
        try:
            self._list_box.clear_widgets()
        except Exception:
            pass
        if not self._items:
            empty = MDBoxLayout(orientation="vertical", spacing="8dp", padding=["0dp","16dp","0dp","16dp"], adaptive_height=True)
            empty.add_widget(MDIcon(icon="inbox-outline", halign="center", theme_text_color="Custom", text_color=rgba("#d5e8d0"), font_size="48sp", size_hint_y=None, height="48dp"))
            empty.add_widget(MDLabel(text="No Deliveries Found", font_style="Subtitle1", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True))
            empty.add_widget(MDLabel(text="You don't have any deliveries in this category yet.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            btn_wrap = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_y=None, height="36dp", padding=["0dp","8dp","0dp","0dp"])
            btn_wrap.add_widget(MDLabel(text=""))
            btn = MDRaisedButton(text="Back to Dashboard", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="160dp", size_hint_y=None, height="36dp", on_release=lambda x: self._go_dashboard())
            try:
                btn.radius = [20]
            except Exception:
                pass
            btn_wrap.add_widget(btn)
            btn_wrap.add_widget(MDLabel(text=""))
            empty.add_widget(btn_wrap)
            self._list_box.add_widget(empty)
        else:
            # TODO Q5: populated waybill card layout not visible yet — needs funded account sample (waybill_number/status/origin/destination/date/fee)
            try:
                from app.views.shared.waybill_card import WaybillCard
                for wb in self._items:
                    self._list_box.add_widget(WaybillCard(waybill=wb, on_tap=self._open_detail))
            except Exception:
                for wb in self._items:
                    self._list_box.add_widget(MDLabel(text=str(wb), adaptive_height=True))
        self._update_results_header()

    def _open_detail(self, waybill):
        # TODO populated detail — stub until waybill detail field mapping confirmed
        try:
            if self.manager:
                detail = self.manager.get_screen("rider_delivery_details") if "rider_delivery_details" in [s.name for s in self.manager.screens] else None
                if detail and hasattr(detail, "set_waybill"):
                    detail.set_waybill(waybill)
                    self.manager.current = "rider_delivery_details"
                    return
        except Exception:
            pass
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="Delivery details — coming soon").open()
        except Exception:
            pass

    def _build_footer(self):
        footer = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="56dp", md_bg_color=rgba(DARK), radius=[0], elevation=0)
        footer.add_widget(MDLabel(text="© 2026 Trackway Logistics. Trackway Smart Logistics. All rights reserved.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        footer.add_widget(MDLabel(text="Delivering Excellence, One Parcel at a Time.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        self._content.add_widget(footer)

    # ---------- Lifecycle ----------
    def on_pre_enter(self, *args):
        from app.core import session as sess
        if not sess.is_logged_in() or sess.get_role() != "rider":
            if self.manager:
                self.manager.current = "rider_login"
            return
        super().on_pre_enter(*args)

    def on_enter(self, *args):
        from app.core import session as sess
        if not sess.is_logged_in() or sess.get_role() != "rider":
            if self.manager:
                self.manager.current = "rider_login"
            return
        try:
            name = sess.get_customer_name() or ""
            self.top_name_label.text = name
            if hasattr(self, "_avatar_card"):
                self._avatar_card.children[0].text = (name.strip()[0].upper() if name else "A")
        except Exception:
            pass
        self._load_status_counts()
        self._refresh()
        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

    def _refresh(self):
        self._items = []
        self._page = 1
        try:
            self._list_box.clear_widgets()
        except Exception:
            pass
        self._has_more = False
        self._load_page()

    def _load_page(self):
        if self._loading:
            return
        self._loading = True
        self._spinner.active = True
        import threading
        def do():
            result = {"ok": False, "data": {"items": []}, "error": "Failed"}
            try:
                from app.services.rider_service import get_rider_deliveries
                # Q1 folded mapping: _status is UI slug (all/pending/picked_up/in_transit/delivered/failed)
                result = get_rider_deliveries(status=self._status, page=self._page)
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            Clock.schedule_once(lambda dt: self._on_page(result), 0)
        threading.Thread(target=do, daemon=True).start()

    def _on_page(self, result):
        self._spinner.active = False
        self._loading = False
        if result.get("ok"):
            data = result.get("data") or {}
            page_items = data.get("items") or []
            total = data.get("total", 0)
            self._total = total
            self._items.extend(page_items)
            self._has_more = data.get("has_more", False)
            self._render_list()
        else:
            err = result.get("error") or ""
            if "Session expired" in str(err):
                try:
                    session.clear_session()
                except Exception:
                    pass
                if self.manager:
                    self.manager.current = "rider_login"
                return
            self._items = []
            self._total = 0
            self._render_list()
            if err and "No" not in err:
                try:
                    from kivymd.uix.snackbar import Snackbar
                    Snackbar(text=err).open()
                except Exception:
                    pass

    def _on_scroll_y(self, instance, value):
        if value <= 0.05:
            if self._has_more and not self._loading:
                self._page += 1
                self._load_page()

    def rebuild_ui(self):
        try:
            self._bind_filters()
            self._render_list()
        except Exception:
            pass
