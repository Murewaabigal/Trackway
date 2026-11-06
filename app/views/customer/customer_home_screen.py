from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.utils import rgba
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu

from app.i18n.translator import tr
from app.core.theme import (
    PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, DARK, MUTED, BACKGROUND, CARD_BG, ERROR, TEAL, BLUE,
)
from app.core import session
from app.views.shared.waybill_card import WaybillCard
from app.views.shared.language_picker import LanguagePicker
from app.views.base_screen import BaseScreen


class CustomerHomeScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._stats = {}
        self._status_counts = {}
        self._counts_loaded = False
        self._loading = False
        self._active_tab = "deliveries"
        self._filter_status = ""
        self._search = ""
        self._all_items = []
        self._filtered_items = []
        self._search_clock = None
        self._unread_count = 0

        # Outer layout: fixed top nav + scrollable content
        self._outer = MDBoxLayout(orientation="vertical")
        self._scroll = ScrollView()
        self._content = MDBoxLayout(
            orientation="vertical",
            padding="12dp",
            spacing="10dp",
            adaptive_height=True,
            size_hint_y=None,
        )
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        # Build fixed top nav outside scroll
        top_nav = self._build_top_nav()
        self._outer.add_widget(top_nav)
        self._outer.add_widget(self._scroll)
        self.add_widget(self._outer)

        # Bind window width to hide name on narrow phones
        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

        self._build_welcome_banner()
        self._build_stat_cards_placeholder()
        self._build_referral_banner_placeholder()
        self._build_pending_payments_section()
        self._build_current_delivery_status_section()
        self._build_tabs()
        self._build_filter_search()
        self._build_deliveries_header()
        self._build_distribution_section()
        self._build_quick_actions()
        self._build_support_links()
        # Initial visibility check
        self._on_window_width(Window, Window.width if hasattr(Window, "width") else 400)

    def _on_window_width(self, instance, width):
        # Hide name on narrow phones <360dp only
        try:
            hide = width < 360
            if hasattr(self, "top_name_label"):
                self.top_name_label.opacity = 0 if hide else 1
                self.top_name_label.size_hint_x = None
                self.top_name_label.width = "0dp" if hide else "70dp"
                self.top_name_label.disabled = hide
        except Exception:
            pass

    def rebuild_ui(self):
        """Rebuild all UI text elements when language changes."""
        # Update welcome banner
        if hasattr(self, 'welcome_label'):
            name = self._stats.get("customer_name") or ""
            if name:
                self.welcome_label.text = tr("welcome_back").format(name=name)
            else:
                base = tr("welcome_back")
                if "{name}" in base:
                    self.welcome_label.text = base.split(",")[0] if "," in base else base.replace("{name}", "").strip()
                else:
                    self.welcome_label.text = base
        if hasattr(self, 'welcome_sub_label'):
            self.welcome_sub_label.text = tr("track_your_parcels_subtext")
        # Update buttons in welcome banner — keep white pills on green
        if hasattr(self, '_welcome_banner'):
            for child in self._welcome_banner.children:
                if isinstance(child, MDBoxLayout):
                    for btn in child.children:
                        if isinstance(btn, (MDRaisedButton, MDFlatButton)):
                            if "request_delivery" in btn.text or "+" in btn.text:
                                btn.text = "+ " + tr("request_delivery")
                                try:
                                    btn.md_bg_color = rgba(CARD_BG)
                                    btn.text_color = rgba(PRIMARY)
                                except Exception:
                                    pass
                            elif "request_ride" in btn.text or "Ride" in btn.text:
                                btn.text = tr("request_ride")
                                try:
                                    btn.md_bg_color = rgba(CARD_BG)
                                    btn.text_color = rgba(PRIMARY)
                                except Exception:
                                    pass
            # Lock banner green
            try:
                self._welcome_banner.md_bg_color = rgba(PRIMARY)
            except Exception:
                pass
        
        # Update stat cards
        self._render_stat_cards()
        
        # Update referral banner
        self._render_referral_banner()
        
        # Update tabs
        if hasattr(self, '_deliveries_tab_btn'):
            self._deliveries_tab_btn.text = tr("deliveries_tab")
        if hasattr(self, '_rides_tab_btn'):
            self._rides_tab_btn.text = tr("rides_tab")
        
        # Update filter chips
        self._bind_filter_chips()
        
        # Update search field hint
        if hasattr(self, 'search_field'):
            self.search_field.hint_text = tr("search_by_tracking")
        
        # Update deliveries section
        self._render_deliveries_section()
        
        # Update quick actions
        self._rebuild_quick_actions()

        # Update distribution title
        if hasattr(self, '_distribution_title'):
            self._distribution_title.text = tr("delivery_status_distribution")
        
        # Update support links
        if hasattr(self, '_quick_card'):
            # Find and update support labels
            for child in self._content.children:
                if isinstance(child, MDBoxLayout):
                    for subchild in child.children:
                        if isinstance(subchild, MDLabel) and "Need immediate" in subchild.text:
                            subchild.text = tr("need_immediate_help")
                        if isinstance(subchild, MDBoxLayout):
                            for btn in subchild.children:
                                if isinstance(btn, MDFlatButton):
                                    if "Call" in btn.text:
                                        btn.text = tr("call_support")
                                    elif "Email" in btn.text:
                                        btn.text = tr("email_support")

    def _toggle_notif_dropdown(self, *args):
        try:
            if not hasattr(self, '_notif_dropdown') or not self._notif_dropdown:
                from app.views.shared.notification_dropdown import NotificationDropdown
                self._notif_dropdown = NotificationDropdown(caller=getattr(self, '_bell_box', None), bell_count_label=getattr(self, 'bell_count_label', None))
            if self._notif_dropdown.parent:
                self._notif_dropdown.dismiss()
            else:
                self._notif_dropdown.open(caller=getattr(self, '_bell_box', None))
        except Exception:
            try:
                if self.manager:
                    self.manager.current = "notifications"
            except Exception:
                pass

    # ---------- Top nav (fixed, not inside scroll) ----------
    def _build_top_nav(self):
        nav = MDCard(
            orientation="horizontal",
            padding="6dp",
            spacing="8dp",
            size_hint_x=1,
            size_hint_y=None,
            height="48dp",
            md_bg_color=rgba(CARD_BG),
            radius=[0],
            elevation=1,
        )
        logo = MDLabel(
            text="Trackway",
            font_style="H6",
            bold=True,
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            size_hint_x=1,
            size_hint_y=None,
            height="32dp",
            pos_hint={"center_y": 0.5},
            valign="middle",
        )
        # Right cluster grouped evenly - single row EN • bell • avatar • name, even 12dp spacing, same center line
        right_cluster = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=None,
            width="160dp",
            spacing="12dp",
            size_hint_y=None,
            height="32dp",
            pos_hint={"center_y": 0.5},
        )
        try:
            self.language_picker = LanguagePicker(compact=True)
            self.language_picker.size_hint_x = None
            self.language_picker.width = "36dp"
            right_cluster.add_widget(self.language_picker)
        except Exception:
            right_cluster.add_widget(MDLabel(text="EN", font_style="Caption", font_size="12sp", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=None, width="32dp", halign="center"))

        bell_box = MDBoxLayout(orientation="horizontal", size_hint_x=None, width="24dp", size_hint_y=None, height="32dp", adaptive_height=False, pos_hint={"center_y": 0.5})
        bell_btn = MDIconButton(
            icon="bell-outline",
            theme_icon_color="Custom",
            icon_color=rgba(MUTED),
            icon_size="22sp",
            size_hint_y=None,
            height="32dp",
            pos_hint={"center_y": 0.5},
            on_release=self._toggle_notif_dropdown,
        )
        bell_box.add_widget(bell_btn)
        right_cluster.add_widget(bell_box)
        self._bell_box = bell_box
        self.bell_count_label = MDLabel(
            text="",
            font_style="Caption",
            bold=True,
            theme_text_color="Custom",
            text_color=rgba(ERROR),
            size_hint_x=None,
            width="16dp",
            size_hint_y=None,
            height="32dp",
            pos_hint={"center_y": 0.5},
            halign="center",
            valign="middle",
        )
        right_cluster.add_widget(self.bell_count_label)

        avatar = MDCard(
            size_hint=(None, None),
            size=("28dp", "28dp"),
            md_bg_color=rgba(PRIMARY),
            radius=[14],
            elevation=0,
            ripple_behavior=True,
            pos_hint={"center_y": 0.5},
        )
        avatar.add_widget(MDLabel(text="A", halign="center", valign="middle", theme_text_color="Custom", text_color="white", bold=True))
        right_cluster.add_widget(avatar)
        self._avatar_card = avatar

        # Name label wrapped in tappable card to make A + name both open menu (web parity)
        name_card = MDCard(
            size_hint=(None, None),
            size=("70dp", "32dp"),
            md_bg_color=[0, 0, 0, 0],
            radius=[6],
            elevation=0,
            ripple_behavior=True,
            pos_hint={"center_y": 0.5},
        )
        self.top_name_label = MDLabel(
            text="",
            font_style="Caption",
            bold=True,
            theme_text_color="Custom",
            text_color=DARK,
            halign="left",
            valign="middle",
        )
        name_card.add_widget(self.top_name_label)
        right_cluster.add_widget(name_card)
        self._name_card = name_card

        # Avatar + name open profile dropdown (web parity) – reuse existing screens/dialogs, no duplicate Refer/Support screens
        avatar.bind(on_release=lambda x: self._open_profile_menu())
        name_card.bind(on_release=lambda x: self._open_profile_menu())

        nav.add_widget(logo)
        nav.add_widget(right_cluster)
        self._top_nav = nav
        return nav

    # ---------- Profile dropdown (web parity) ----------
    def _create_profile_menu(self):
        if hasattr(self, "_profile_menu") and self._profile_menu:
            return
        items = [
            {
                "text": "My Profile",
                "leading_icon": "account-outline",
                "on_release": lambda: self._menu_navigate("profile"),
            },
            {
                "text": "Refer & Earn",
                "leading_icon": "gift-outline",
                "on_release": lambda: self._menu_action_refer(),
            },
            {
                "text": "Support",
                "leading_icon": "headset",
                "on_release": lambda: self._menu_action_support(),
            },
            {
                "text": "Notifications",
                "leading_icon": "bell-outline",
                "on_release": lambda: self._menu_navigate("notifications"),
            },
            {
                "text": "Full History",
                "leading_icon": "history",
                "on_release": lambda: self._menu_navigate("customer_history"),
            },
            {
                "viewclass": "MDSeparator",
                "height": dp(1),
            },
            {
                "text": "Logout",
                "leading_icon": "logout",
                "text_color": rgba(ERROR),
                "leading_icon_color": rgba(ERROR),
                "on_release": lambda: self._menu_logout(),
            },
        ]
        # Use avatar card as caller for positioning
        caller = getattr(self, "_avatar_card", self._top_nav)
        self._profile_menu = MDDropdownMenu(caller=caller, items=items, width_mult=4, max_height="320dp")
        # Add divider visually before Logout via menu item styling handled by width/height – separator is implicit via Logout red distinction

    def _open_profile_menu(self, *args):
        try:
            self._create_profile_menu()
            # Ensure caller is current avatar for correct positioning
            self._profile_menu.caller = getattr(self, "_avatar_card", self._top_nav)
            self._profile_menu.open()
        except Exception as e:
            # Fallback to direct profile if menu fails
            try:
                from kivy.logger import Logger
                Logger.warning(f"ProfileMenu open failed: {e}")
            except Exception:
                pass
            self._go_profile()

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

    def _menu_action_support(self):
        try:
            if hasattr(self, "_profile_menu") and self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", "support") if self.manager else None, 0.2)

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

    # ---------- Welcome banner ----------
    def _build_welcome_banner(self):
        banner = MDCard(
            orientation="vertical",
            padding="12dp",
            spacing="6dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba(PRIMARY),
            radius=[14],
            elevation=0,
        )
        self.welcome_label = MDLabel(
            text=tr("welcome_back").format(name=""),
            font_style="H6",
            bold=True,
            theme_text_color="Custom",
            text_color="white",
            adaptive_height=True,
        )
        self.welcome_sub_label = MDLabel(
            text=tr("track_your_parcels_subtext"),
            font_style="Body2",
            theme_text_color="Custom",
            text_color=rgba("#e8f0e3"),
            adaptive_height=True,
        )
        btn_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", padding=["0dp", "8dp", "0dp", "0dp"])
        # Both pills white/light on green banner — web parity (Option A: default rectangle, no radius to avoid KivyMD 1.2.0 crash)
        req_delivery_btn = MDRaisedButton(
            text="+ " + tr("request_delivery"),
            md_bg_color=rgba(CARD_BG),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            elevation=0,
            size_hint_x=None,
            width="170dp",
            size_hint_y=None,
            height="36dp",
            on_release=lambda x: self._go_request_delivery(),
        )
        req_ride_btn = MDRaisedButton(
            text=tr("request_ride"),
            md_bg_color=rgba(CARD_BG),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            elevation=0,
            size_hint_x=None,
            width="150dp",
            size_hint_y=None,
            height="36dp",
            on_release=lambda x: self._go_request_ride(),
        )
        btn_row.add_widget(req_delivery_btn)
        btn_row.add_widget(req_ride_btn)
        banner.add_widget(self.welcome_label)
        banner.add_widget(self.welcome_sub_label)
        banner.add_widget(btn_row)
        self._content.add_widget(banner)
        self._welcome_banner = banner

    def _show_ride_stub(self, *args):
        from kivymd.uix.dialog import MDDialog
        if hasattr(self, "_ride_dialog") and self._ride_dialog:
            try:
                self._ride_dialog.dismiss()
            except Exception:
                pass
        self._ride_dialog = MDDialog(
            title=tr("request_ride"),
            text="Ride-hailing booking coming in a later phase. Use Request Delivery for now.",
            buttons=[MDFlatButton(text=tr("ok"), on_release=lambda x: self._ride_dialog.dismiss())],
        )
        self._ride_dialog.open()

    # ---------- Stat cards ----------
    def _build_stat_cards_placeholder(self):
        self._stat_container = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing="8dp",
        )
        self._content.add_widget(self._stat_container)
        self._render_stat_cards()

    def _render_stat_cards(self):
        self._stat_container.clear_widgets()
        s = self._stats
        items = [
            ("total_deliveries", s.get("total_deliveries", 0), "package-variant-closed", PRIMARY),
            ("completed_stats", s.get("completed", 0), "check-circle-outline", PRIMARY),
            ("in_progress_stats", s.get("in_progress", 0), "progress-clock", MUTED),
            ("total_rides", s.get("total_rides", 0), "car-outline", PRIMARY),
            ("referral_balance", s.get("referral_balance", "0.00"), "gift-outline", PRIMARY),
        ]
        grid = GridLayout(cols=2, spacing="8dp", size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for key, value, icon, color in items:
            card = MDCard(
                orientation="vertical",
                padding="12dp",
                spacing="4dp",
                size_hint_x=1,
                size_hint_y=None,
                height="90dp",
                md_bg_color=rgba(CARD_BG),
                radius=[12],
                elevation=1,
            )
            top_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp")
            val_label = MDLabel(
                text=str(value),
                font_style="H6",
                bold=True,
                halign="left",
                theme_text_color="Custom",
                text_color=rgba(PRIMARY),
                size_hint_x=1,
                adaptive_height=True,
            )
            icon_widget = MDIcon(
                icon=icon,
                theme_text_color="Custom",
                text_color=rgba(color),
                halign="right",
                size_hint_x=None,
                width="28dp",
                font_size="20sp",
            )
            top_row.add_widget(val_label)
            top_row.add_widget(icon_widget)
            lab = MDLabel(
                text=tr(key) if key != "referral_balance" else tr("referral_balance"),
                font_style="Caption",
                halign="left",
                theme_text_color="Custom",
                text_color=MUTED,
                adaptive_height=True,
            )
            card.add_widget(top_row)
            card.add_widget(lab)
            grid.add_widget(card)
        self._stat_container.add_widget(grid)

    def _build_referral_banner_placeholder(self):
        self._referral_container = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="4dp")
        self._content.add_widget(self._referral_container)
        self._render_referral_banner()

    def _render_referral_banner(self):
        self._referral_container.clear_widgets()
        code = self._stats.get("referral_code") or "REF------"
        balance = self._stats.get("referral_balance", "0.00")
        banner = MDCard(
            orientation="horizontal",
            padding="10dp",
            spacing="6dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba("#e8f0e3"),
            radius=[12],
            elevation=0,
        )
        left_col = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="2dp", size_hint_x=1)
        line1 = MDLabel(
            text=tr("refer_earn_banner") + f" {code} " + tr("and_earn") + f" \u20a6500.00 " + tr("for_each_friend"),
            font_style="Body2",
            theme_text_color="Custom",
            text_color=rgba(PRIMARY_DARK),
            adaptive_height=True,
        )
        line2 = MDLabel(
            text=f"{tr('referral_balance')}: \u20a6{balance}",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=MUTED,
            adaptive_height=True,
        )
        left_col.add_widget(line1)
        left_col.add_widget(line2)
        refer_btn = MDRaisedButton(
            text=tr("refer_now"),
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            size_hint_x=None,
            width="100dp",
            on_release=lambda x: self._go("refer_earn"),
        )
        banner.add_widget(left_col)
        banner.add_widget(refer_btn)
        self._referral_container.add_widget(banner)

    def _show_refer_stub(self, *args):
        from kivymd.uix.dialog import MDDialog
        code = self._stats.get("referral_code") or ""
        self._refer_dialog = MDDialog(
            title=tr("refer_and_earn"),
            text=f"{tr('refer_earn_banner')} {code}. Share with friends!",
            buttons=[MDFlatButton(text=tr("ok"), on_release=lambda x: self._refer_dialog.dismiss())],
        )
        self._refer_dialog.open()

    # ---------- Pending Payments (new) ----------
    def _build_pending_payments_section(self):
        self._pending_container = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="8dp")
        self._content.add_widget(self._pending_container)
        self._pending_items = []
        self._render_pending_payments()

    def _render_pending_payments(self):
        self._pending_container.clear_widgets()
        # Header dashboard-card style border-left 4px brand-green
        header = MDCard(orientation="vertical", padding="12dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        # left bar simulation via line
        header_line = MDBoxLayout(size_hint_x=1, size_hint_y=None, height="4dp", md_bg_color=rgba(PRIMARY), radius=[2])
        header.add_widget(header_line)
        top = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="24dp")
        top.add_widget(MDIcon(icon="clock-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="20dp", font_size="16sp"))
        top.add_widget(MDLabel(text="Pending Payments", font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1))
        badge = MDCard(size_hint=(None,None), size=("90dp","20dp"), md_bg_color=rgba(PRIMARY), radius=[10], elevation=0)
        badge.add_widget(MDLabel(text="Action Required", halign="center", font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color="white"))
        top.add_widget(badge)
        header.add_widget(top)
        self._pending_container.add_widget(header)
        items = getattr(self, "_pending_items", []) or []
        if not items:
            # keep section hidden when empty? show placeholder similar to web empty?
            empty = MDBoxLayout(orientation="vertical", spacing="6dp", adaptive_height=True, padding=["0dp","8dp","0dp","0dp"])
            empty.add_widget(MDLabel(text="No pending payments", font_style="Body2", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            self._pending_container.add_widget(empty)
            return
        for it in items:
            ride_id = it.get("ride_id") or it.get("id") or ""
            route = it.get("route") or f"{it.get('pickup_city','')} → {it.get('delivery_city','')}".strip(" →")
            amount = it.get("amount") or it.get("fare") or it.get("price") or ""
            if amount and "₦" not in str(amount):
                try:
                    amount = f"₦{float(str(amount).replace(',','')):,.2f}"
                except Exception:
                    amount = f"₦{amount}"
            card = MDCard(orientation="vertical", padding="12dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
            row = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_y=None, height="22dp")
            row.add_widget(MDLabel(text=f"Ride #{ride_id}" if ride_id else route or "Ride", font_style="Body2", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1, adaptive_height=True, shorten=True))
            row.add_widget(MDLabel(text=str(amount), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="90dp", halign="right"))
            card.add_widget(row)
            # Route row — small muted with location-dot icon, under ride number/fare (was missing)
            if route and route.strip() and route.strip() != f"Ride #{ride_id}":
                route_row = MDBoxLayout(orientation="horizontal", spacing="4dp", size_hint_x=1, size_hint_y=None, height="18dp", adaptive_height=True)
                route_row.add_widget(MDIcon(icon="map-marker-outline", theme_text_color="Custom", text_color=rgba(MUTED), font_size="12sp", size_hint_x=None, width="14dp"))
                route_lbl = MDLabel(text=route.strip(), font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color=MUTED, halign="left", adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(300), None))
                try:
                    card.bind(width=lambda inst, w, lbl=route_lbl: setattr(lbl, "text_size", (w - dp(12*2 + 14 + 4), None)))
                except Exception:
                    pass
                route_row.add_widget(route_lbl)
                card.add_widget(route_row)
            btn_row = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_x=1, size_hint_y=None, height="36dp")
            btn_row.add_widget(MDLabel(text=""))
            cancel_btn = MDFlatButton(text="Cancel Request", theme_text_color="Custom", text_color=rgba(ERROR), line_color=rgba(ERROR), size_hint_x=None, width="120dp", size_hint_y=None, height="32dp", font_size="11sp", on_release=lambda x, rid=ride_id: self._cancel_pending(rid))
            complete_btn = MDRaisedButton(text="Complete Payment", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="140dp", size_hint_y=None, height="32dp", font_size="11sp", on_release=lambda x, rid=ride_id: self._complete_pending(rid))
            btn_row.add_widget(cancel_btn)
            btn_row.add_widget(complete_btn)
            card.add_widget(btn_row)
            self._pending_container.add_widget(card)

    def _load_pending_payments(self):
        import threading
        def do():
            try:
                from app.services.customer_service import get_pending_payments
                r = get_pending_payments()
                items = r.get("data", {}).get("items", []) if r.get("ok") else []
                Clock.schedule_once(lambda dt: self._on_pending_loaded(items), 0)
            except Exception:
                Clock.schedule_once(lambda dt: self._on_pending_loaded([]), 0)
        threading.Thread(target=do, daemon=True).start()

    def _on_pending_loaded(self, items):
        self._pending_items = items or []
        self._render_pending_payments()

    def _complete_pending(self, ride_id):
        if not ride_id:
            return
        import threading
        def do():
            try:
                from app.services.customer_service import retry_ride_payment
                r = retry_ride_payment(ride_id)
                if r.get("ok"):
                    d = r.get("data") or {}
                    url = d.get("redirect_url") or d.get("authorization_url") or d.get("url") or ""
                    if url and "paystack" in url.lower():
                        Clock.schedule_once(lambda dt: self._open_paystack_from_pending(url, ride_id), 0)
                    else:
                        # fallback to polling pending list
                        Clock.schedule_once(lambda dt: self._load_pending_payments(), 0)
                    try:
                        from kivymd.uix.snackbar import Snackbar
                        Clock.schedule_once(lambda dt: Snackbar(text=r.get("data",{}).get("message") or "Redirecting to payment...").open(), 0)
                    except Exception:
                        pass
                else:
                    err = r.get("error") or "Payment retry failed"
                    try:
                        from kivymd.uix.snackbar import Snackbar
                        Clock.schedule_once(lambda dt: Snackbar(text=err).open(), 0)
                    except Exception:
                        pass
            except Exception as e:
                try:
                    from kivymd.uix.snackbar import Snackbar
                    Clock.schedule_once(lambda dt: Snackbar(text=str(e)).open(), 0)
                except Exception:
                    pass
        threading.Thread(target=do, daemon=True).start()

    def _open_paystack_from_pending(self, url, ride_id):
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
        # also offer verify button reuse? For pending we just open; verify handled via reference in url
        try:
            import re
            m = re.search(r"(?:reference|trxref)=([^&]+)", url)
            ref = m.group(1) if m else str(ride_id)
            # store for manual verify if needed
            self._pending_verify_ref = ref
        except Exception:
            pass

    def _cancel_pending(self, ride_id):
        if not ride_id:
            return
        import threading
        def do():
            try:
                from app.services.customer_service import cancel_ride
                r = cancel_ride(ride_id)
                if r.get("ok"):
                    try:
                        from kivymd.uix.snackbar import Snackbar
                        Clock.schedule_once(lambda dt: Snackbar(text="Ride cancelled successfully.").open(), 0)
                    except Exception:
                        pass
                    Clock.schedule_once(lambda dt: self._load_pending_payments(), 0)
                    # also refresh stats
                    Clock.schedule_once(lambda dt: self._load_dashboard(), 0)
                else:
                    err = r.get("error") or "Cancel failed"
                    try:
                        from kivymd.uix.snackbar import Snackbar
                        Clock.schedule_once(lambda dt: Snackbar(text=err).open(), 0)
                    except Exception:
                        pass
            except Exception as e:
                try:
                    from kivymd.uix.snackbar import Snackbar
                    Clock.schedule_once(lambda dt: Snackbar(text=str(e)).open(), 0)
                except Exception:
                    pass
        threading.Thread(target=do, daemon=True).start()

    # ---------- Current Delivery Status (green banner between Pending Payments and Tabs) ----------
    def _build_current_delivery_status_section(self):
        self._current_delivery_container = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="0dp")
        self._content.add_widget(self._current_delivery_container)
        self._current_delivery = None
        self._render_current_delivery_status()

    def _render_current_delivery_status(self):
        self._current_delivery_container.clear_widgets()
        ad = getattr(self, "_current_delivery", None) or (self._stats.get("active_delivery") if isinstance(self._stats, dict) else None)
        # also check stats.active_delivery from HTML parse: _stats may contain active_delivery dict
        if isinstance(ad, dict) and not ad.get("tracking_number") and ad.get("tracking_number_large"):
            ad["tracking_number"] = ad["tracking_number_large"]
        if not ad or not isinstance(ad, dict) or not ad.get("tracking_number"):
            # hide banner entirely when no active delivery, matching web
            return
        tracking = str(ad.get("tracking_number") or ad.get("tracking_number_large") or "").strip()
        status_label = str(ad.get("status_label") or ad.get("status") or "Pending Pickup").strip()
        status_color = str(ad.get("status_color") or "#FF9800").strip() or "#FF9800"
        route = str(ad.get("route") or f"{ad.get('pickup_city','')} → {ad.get('delivery_city','')}".strip(" →") or "").strip()
        track_href = str(ad.get("track_href") or f"../track.php?id={tracking}").strip()
        # normalize color
        try:
            # ensure # prefix
            if status_color and not status_color.startswith("#") and not status_color.startswith("rgba"):
                status_color = "#" + status_color.lstrip("#")
        except Exception:
            status_color = "#FF9800"
        card = MDCard(orientation="vertical", padding="16dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        # Header row: small truck icon + CURRENT DELIVERY STATUS muted white + status badge orange pill top-right
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="truck", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="12sp", size_hint_x=None, width="16dp"))
        header.add_widget(MDLabel(text="CURRENT DELIVERY STATUS", font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color=rgba("#e8f0e3"), halign="left", size_hint_x=1, bold=True))
        # status badge pill
        try:
            badge_bg = rgba(status_color) if status_color.startswith("#") else rgba(PRIMARY)
        except Exception:
            badge_bg = rgba("#FF9800")
        badge = MDCard(size_hint=(None,None), size=("110dp","20dp"), md_bg_color=badge_bg, radius=[10], elevation=0)
        badge.add_widget(MDLabel(text=status_label or "Pending Pickup", halign="center", font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color="white", bold=True))
        header.add_widget(badge)
        card.add_widget(header)
        # Tracking number large bold in translucent white pill
        pill = MDCard(size_hint=(None,None), size=("180dp","28dp"), md_bg_color=[1,1,1,0.15], radius=[14], elevation=0, line_color=[1,1,1,0.3], line_width=1)
        pill.add_widget(MDLabel(text=tracking, halign="center", font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color="white", font_size="13sp"))
        card.add_widget(pill)
        # Route line: location pin + Origin → Destination white
        if route:
            route_row = MDBoxLayout(orientation="horizontal", spacing="4dp", size_hint_x=1, size_hint_y=None, height="18dp")
            route_row.add_widget(MDIcon(icon="map-marker-outline", theme_text_color="Custom", text_color="white", font_size="12sp", size_hint_x=None, width="14dp"))
            route_lbl = MDLabel(text=route, font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color="white", halign="left", adaptive_height=True, max_lines=1, shorten=True)
            try:
                card.bind(width=lambda inst, w, lbl=route_lbl: setattr(lbl, "text_size", (w - dp(16*2 + 14 + 4), None)))
            except Exception:
                pass
            route_row.add_widget(route_lbl)
            card.add_widget(route_row)
        # Track Live button bottom-right white pill
        btn_row = MDBoxLayout(orientation="horizontal", size_hint_x=1, size_hint_y=None, height="36dp", spacing="8dp")
        btn_row.add_widget(MDLabel(text=""))
        track_btn = MDFlatButton(text="Track Live", icon="map-marker-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), line_color=[1,1,1,1], md_bg_color=[1,1,1,1], size_hint_x=None, width="120dp", size_hint_y=None, height="32dp", font_size="11sp", on_release=lambda x, tn=tracking: self._on_track_live(tn))
        try:
            track_btn.radius = [16]
            track_btn.line_width = 1
        except Exception:
            pass
        # add pin icon manually if MDFlatButton icon not supported
        try:
            track_btn.icon = "map-marker-outline"
        except Exception:
            pass
        btn_row.add_widget(track_btn)
        card.add_widget(btn_row)
        self._current_delivery_container.add_widget(card)

    def _on_track_live(self, tracking_number):
        if not tracking_number:
            return
        # wire to existing tracking flow: tracking_search → tracking_result using tracking/details.php
        try:
            if self.manager:
                # try to set tracking search field and navigate
                try:
                    ts = self.manager.get_screen("tracking_search")
                    if hasattr(ts, "set_tracking_number"):
                        ts.set_tracking_number(tracking_number)
                    elif hasattr(ts, "search_field"):
                        ts.search_field.text = tracking_number
                except Exception:
                    pass
                self.manager.current = "tracking_search"
                # small delay then trigger search if available
                try:
                    Clock.schedule_once(lambda dt: getattr(self.manager.get_screen("tracking_search"), "_do_search", lambda: None)(), 0.3)
                except Exception:
                    pass
                return
        except Exception:
            pass
        # fallback: open track.php in browser
        try:
            import webbrowser
            webbrowser.open(f"https://trackwaylogistics.ng/track.php?id={tracking_number}")
        except Exception:
            pass

    def _on_select_rider(self, waybill_id):
        if not waybill_id:
            return
        # open select-rider page WEB with waybill id, same as web href select-rider.php?waybill=10
        try:
            import webbrowser
            webbrowser.open(f"https://trackwaylogistics.ng/customer/select-rider.php?waybill={waybill_id}")
        except Exception:
            pass
        # also try in-app navigation if screen exists
        try:
            if self.manager and "select_rider" in [s.name for s in self.manager.screens]:
                self.manager.current = "select_rider"
        except Exception:
            pass

    # ---------- Tabs ----------
    def _build_tabs(self):
        if not hasattr(self, "_filter_status"):
            self._filter_status = ""
        if not hasattr(self, "_active_tab"):
            self._active_tab = "deliveries"
        self._tabs_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", padding=["0dp", "2dp", "0dp", "0dp"])
        self._deliveries_tab_btn = MDFlatButton(
            text=tr("deliveries_tab"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            on_release=lambda x: self._switch_tab("deliveries"),
        )
        self._rides_tab_btn = MDFlatButton(
            text=tr("rides_tab"),
            theme_text_color="Custom",
            text_color=rgba(MUTED),
            on_release=lambda x: self._switch_tab("rides"),
        )
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
            self._tab_underline.md_bg_color = rgba(PRIMARY)
        else:
            self._rides_tab_btn.text_color = rgba(PRIMARY)
            self._deliveries_tab_btn.text_color = rgba(MUTED)
            self._tab_underline.md_bg_color = rgba(PRIMARY)
        self._render_deliveries_section()

    # ---------- Filter + Search ----------
    # Dashboard web parity: only search box (All [count] pill handled in deliveries header).
    # Fuller filter chips belong on History — removed from Dashboard.
    def _build_filter_search(self):
        # Filter pills All/Pending Pickup/Cancelled + search bar (web: tabs + filter pills + search + table)
        self._filter_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", padding=["0dp", "2dp", "0dp", "4dp"])
        self._content.add_widget(self._filter_row)
        self.search_field = MDTextField(
            hint_text=tr("search_by_tracking"),
            icon_right="magnify",
            size_hint_x=1,
            mode="round",
        )
        self.search_field.bind(text=self._on_search_text)
        self._content.add_widget(self.search_field)

    def _get_count(self, v):
        if isinstance(v, int):
            return v
        if isinstance(v, dict):
            return int(v.get("count", v.get("total", v.get("value", 0))) or 0)
        try:
            return int(v)
        except Exception:
            return 0

    def _bind_filter_chips(self):
        try:
            if not hasattr(self, "_filter_row"):
                return
            self._filter_row.clear_widgets()
            # status filter pills: All / Pending Pickup / Cancelled (web dashboard)
            # Q1 folded mapping: Pending → pending_pickup, Cancelled → cancelled, All → ""
            pill_defs = [
                ("all", "All", ""),
                ("pending_pickup", "Pending Pickup", "pending_pickup"),
                ("cancelled", "Cancelled", "cancelled"),
            ]
            for key, label, api_val in pill_defs:
                active = (self._filter_status == ("" if key=="all" else api_val)) or (self._filter_status=="" and key=="all")
                # count per Q3: show on all pills once loaded
                badge = ""
                if self._counts_loaded:
                    if key == "all":
                        total = sum(self._get_count(x) for x in self._status_counts.values()) if self._status_counts else len(getattr(self, "_all_items", []))
                        # also try delivery_items count
                        if not total and isinstance(self._stats, dict) and self._stats.get("delivery_items"):
                            total = len(self._stats.get("delivery_items"))
                        badge = f" ({total})"
                    else:
                        cnt = self._get_count(self._status_counts.get(api_val, 0))
                        # fold counts for in_transit already handled in service, but for pending/cancelled direct
                        badge = f" ({cnt})"
                text = f"{label}{badge}"
                btn = MDFlatButton(text=text, font_size="11sp", size_hint_x=None, width="110dp", size_hint_y=None, height="28dp", theme_text_color="Custom", text_color=rgba("#FFFFFF" if active else DARK), md_bg_color=rgba(PRIMARY if active else CARD_BG), line_color=rgba(PRIMARY))
                try:
                    btn.radius = [16]
                    btn.line_width = 1 if not active else 1
                    if active:
                        btn.line_color = rgba(PRIMARY)
                    else:
                        btn.line_color = rgba("#e0e0e0")
                except Exception:
                    pass
                # need to capture api_val correctly for all
                val = "" if key=="all" else api_val
                btn.bind(on_release=lambda x, v=val: self._set_filter(v))
                self._filter_row.add_widget(btn)
        except Exception:
            pass

    def _set_filter(self, value):
        self._filter_status = value
        self._bind_filter_chips()
        self._apply_filter_search()

    def _on_search_text(self, instance, value):
        if self._search_clock:
            try:
                self._search_clock.cancel()
            except Exception:
                pass
        self._search_clock = Clock.schedule_once(self._do_search_debounced, 0.5)

    def _do_search_debounced(self, dt):
        self._search = self.search_field.text.strip().lower()
        self._apply_filter_search()

    def _apply_filter_search(self):
        items = self._all_items
        # prefer delivery_items from HTML stats if available and items empty
        if not items and isinstance(self._stats, dict) and self._stats.get("delivery_items"):
            items = self._stats.get("delivery_items")
        filtered = items or []
        if self._filter_status:
            target = self._filter_status.strip().lower()
            def _norm_status(wb):
                s = str(wb.get("status") or wb.get("status_label") or "").strip().lower()
                # normalize spaces/underscores
                s2 = s.replace(" ", "_")
                return s, s2
            filtered = [wb for wb in filtered if target in _norm_status(wb) or _norm_status(wb)[0] == target or _norm_status(wb)[1] == target]
        if self._search:
            q = self._search.lower()
            filtered = [wb for wb in filtered if q in str(wb.get("waybill_number") or wb.get("tracking_number") or "").lower() or q in str(wb.get("route") or "").lower() or q in str(wb.get("origin") or "").lower() or q in str(wb.get("destination") or "").lower()]
        self._filtered_items = filtered
        self._render_deliveries_section()

    # ---------- Deliveries header + list ----------
    def _build_deliveries_header(self):
        self._deliveries_section = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="8dp")
        self._content.add_widget(self._deliveries_section)

    def _render_deliveries_section(self):
        self._deliveries_section.clear_widgets()
        # Rides tab still shows rides info placeholder
        if self._active_tab == "rides":
            empty = MDLabel(
                text=tr("no_rides"),
                font_style="Body2",
                halign="center",
                theme_text_color="Custom",
                text_color=MUTED,
                size_hint_y=None,
                height="80dp",
            )
            self._deliveries_section.add_widget(empty)
            rides_info = MDLabel(
                text=f"{tr('total_rides')}: {self._stats.get('total_rides', 0)}",
                font_style="Caption",
                halign="center",
                theme_text_color="Custom",
                text_color=MUTED,
                size_hint_y=None,
                height="24dp",
            )
            self._deliveries_section.add_widget(rides_info)
            return

        # Deliveries tab: rebuild as tbody table list (6 fields per row, web parity) filtered by status pills
        # Use delivery_items from HTML scrape if available, else fallback to _filtered_items/_all_items
        items = None
        if isinstance(self._stats, dict) and isinstance(self._stats.get("delivery_items"), list) and self._stats.get("delivery_items"):
            items = self._stats.get("delivery_items")
            # also respect search/status filter if any (client-side)
            if self._filter_status:
                status_map = {"all": "", "pending_pickup": "pending pickup", "cancelled": "cancelled", "in_transit": "in transit", "delivered": "delivered", "failed": "failed"}
                target = status_map.get(self._filter_status, self._filter_status).lower()
                if target:
                    items = [it for it in items if target in str(it.get("status","") or it.get("status_label","")).lower() or target in str(it.get("status_color","")).lower()]
            if self._search:
                q = self._search.lower()
                items = [it for it in items if q in str(it.get("tracking_number","") or it.get("waybill_number","")).lower() or q in str(it.get("route","")).lower()]
        else:
            items = self._filtered_items if self._filtered_items else self._all_items
            # apply same filter for fallback list (Waybill dicts)
            if self._filter_status:
                items = [wb for wb in items if (wb.get("status") or "") == self._filter_status]
            if self._search:
                q = self._search.lower()
                items = [wb for wb in items if q in str(wb.get("waybill_number","")).lower() or q in str(wb.get("origin","")).lower() or q in str(wb.get("destination","")).lower()]
        if not items:
            empty = MDBoxLayout(orientation="vertical", spacing="12dp", adaptive_height=True, padding=["12dp", "24dp", "12dp", "24dp"], size_hint_y=None)
            empty.bind(minimum_height=empty.setter("height"))
            empty.add_widget(MDIcon(icon="package-variant-closed", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), font_size="48sp", size_hint_y=None, height="48dp"))
            empty.add_widget(MDLabel(text=tr("no_deliveries_found") if tr("no_deliveries_found") != "no_deliveries_found" else "No deliveries found", font_style="Subtitle1", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True))
            empty.add_widget(MDLabel(text=tr("no_deliveries_subtitle") if tr("no_deliveries_subtitle") != "no_deliveries_subtitle" else "You haven't made any deliveries yet or no results match your filters.", font_style="Body2", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            cta = MDRaisedButton(text=self._cta_label(), md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", pos_hint={"center_x": 0.5}, size_hint_x=None, width="220dp", on_release=self._on_empty_cta)
            empty.add_widget(cta)
            self._deliveries_section.add_widget(empty)
            return
        # Render each tbody row as mobile card with 6 fields: tracking, route, status badge dynamic color, fee, date, conditional action
        for it in items:
            # normalize fields from HTML parse or fallback Waybill
            tracking = it.get("tracking_number") or it.get("waybill_number") or it.get("tracking_code") or ""
            route = it.get("route") or f"{it.get('route_origin','')} → {it.get('route_dest','')}".strip(" →") or f"{it.get('origin','')} → {it.get('destination','')}".strip(" →")
            status_label = it.get("status_label") or it.get("status") or ""
            status_color = it.get("status_color") or ""
            fee = it.get("fee") or it.get("amount") or it.get("price") or ""
            date_text = it.get("date") or it.get("date_text") or it.get("created_at") or ""
            action = it.get("action") or {}
            # fallback fee formatting
            if fee and "₦" not in str(fee):
                try:
                    fee = f"₦{float(str(fee).replace(',','')):,.2f}"
                except Exception:
                    fee = f"₦{fee}"
            # status color fallback to PRIMARY/MUTED mapping if not extracted
            if not status_color:
                try:
                    from app.core.constants import STATUS_LABELS
                    # map pending->FF9800, cancelled->9E9E9E, in_transit->00BCD4 etc. use dynamic if available
                    lc = status_label.lower()
                    if "pending" in lc:
                        status_color = "#FF9800"
                    elif "cancel" in lc:
                        status_color = "#9E9E9E"
                    elif "transit" in lc:
                        status_color = "#00BCD4"
                    elif "delivered" in lc:
                        status_color = "#4CAF50"
                    else:
                        status_color = PRIMARY
                except Exception:
                    status_color = PRIMARY
            try:
                badge_bg = rgba(status_color) if status_color.startswith("#") else rgba(PRIMARY)
            except Exception:
                badge_bg = rgba(PRIMARY)
            card = MDCard(orientation="vertical", padding="12dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
            # Row1: tracking monospace + status badge
            top = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_y=None, height="24dp")
            top.add_widget(MDLabel(text=tracking, font_style="Caption", theme_text_color="Custom", text_color=DARK, size_hint_x=1, halign="left", shorten=True, font_name="RobotoMono-Regular" if tracking else None))
            pill = MDCard(size_hint=(None,None), size=("110dp","22dp"), md_bg_color=badge_bg, radius=[10], elevation=0)
            pill.add_widget(MDLabel(text=status_label or "—", halign="center", font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color="white"))
            top.add_widget(pill)
            card.add_widget(top)
            # Row2: route with arrow icon
            if route:
                route_row = MDBoxLayout(orientation="horizontal", spacing="4dp", size_hint_x=1, size_hint_y=None, height="18dp")
                route_row.add_widget(MDIcon(icon="arrow-right", theme_text_color="Custom", text_color=rgba(MUTED), font_size="12sp", size_hint_x=None, width="14dp"))
                route_lbl = MDLabel(text=route, font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color=MUTED, halign="left", adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(300), None))
                try:
                    card.bind(width=lambda inst, w, lbl=route_lbl: setattr(lbl, "text_size", (w - dp(12*2 + 14 + 4), None)))
                except Exception:
                    pass
                route_row.add_widget(route_lbl)
                card.add_widget(route_row)
            # Row3: fee + date
            mid = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_x=1, size_hint_y=None, height="18dp")
            mid.add_widget(MDLabel(text=str(fee), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1, halign="left", shorten=True))
            mid.add_widget(MDLabel(text=str(date_text), font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color=MUTED, size_hint_x=None, width="90dp", halign="right"))
            card.add_widget(mid)
            # Row4: conditional action
            act_type = (action.get("type") or "").lower() if isinstance(action, dict) else ""
            act_label = (action.get("label") or "") if isinstance(action, dict) else ""
            href = (action.get("href") or "") if isinstance(action, dict) else ""
            waybill_id = (action.get("waybill_id") or tracking) if isinstance(action, dict) else tracking
            btn_row = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_x=1, size_hint_y=None, height="36dp")
            btn_row.add_widget(MDLabel(text=""))
            if act_type == "button" and "select rider" in act_label.lower():
                btn = MDRaisedButton(text="Select Rider", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="120dp", size_hint_y=None, height="32dp", font_size="11sp", on_release=lambda x, wid=waybill_id: self._on_select_rider(wid))
                btn_row.add_widget(btn)
            elif act_type == "button" and "track" in act_label.lower():
                btn = MDRaisedButton(text="Track", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="100dp", size_hint_y=None, height="32dp", font_size="11sp", on_release=lambda x, tn=tracking: self._on_track_live(tn))
                btn_row.add_widget(btn)
            elif act_type == "label" or "cancel" in act_label.lower():
                btn_row.add_widget(MDLabel(text=act_label or "Cancelled", font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_x=None, width="90dp", halign="right", font_size="11sp"))
            else:
                # unknown status — show muted label fallback and log warning once
                try:
                    from kivy.logger import Logger as _L
                    _L.warning(f"Unknown Action for status {status_label!r} action {action!r}")
                except Exception:
                    pass
                if act_label:
                    btn_row.add_widget(MDLabel(text=act_label, font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_x=None, width="90dp", halign="right", font_size="11sp"))
            card.add_widget(btn_row)
            card.bind(on_release=lambda x, wb=it: self._open_detail(wb) if hasattr(self, "_open_detail") else None)
            self._deliveries_section.add_widget(card)

    def _cta_label(self):
        for k in ("send_first_parcel", "request_first_delivery", "history.request_first_delivery"):
            v = tr(k)
            if v != k:
                return v
        return "Send Your First Parcel"

    def _on_empty_cta(self, *args):
        if self.manager:
            self.manager.current = "request_delivery"
            return
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="Coming soon — Request Delivery will be available shortly.").open()
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

    # ---------- Quick Actions ----------
    def _build_quick_actions(self):
        self._quick_card = MDCard(
            orientation="vertical",
            padding="12dp",
            spacing="8dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba(CARD_BG),
            radius=[12],
            elevation=1,
        )
        self._quick_card.add_widget(MDLabel(text=tr("quick_actions"), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, adaptive_height=True))
        grid = GridLayout(cols=2, spacing="8dp", size_hint_y=None, row_default_height="48dp", row_force_default=False)
        grid.bind(minimum_height=grid.setter("height"))
        # Web parity distinct colors: green / teal / blue / black / red / green
        actions = [
            ("request_delivery", PRIMARY, self._go_request_delivery),
            ("request_ride", TEAL, lambda x: self._go_request_ride()),
            ("track_parcel", BLUE, self._go_track),
            ("history", DARK, self._go_history),
            ("support", ERROR, self._show_support_stub),
            ("refer_and_earn", PRIMARY, lambda x: self._go("refer_earn")),
        ]
        for key, color, cb in actions:
            btn = MDRaisedButton(
                text=tr(key),
                md_bg_color=rgba(color),
                theme_text_color="Custom",
                text_color="white",
                size_hint_x=1,
                on_release=cb,
            )
            grid.add_widget(btn)
        self._quick_card.add_widget(grid)
        self._content.add_widget(self._quick_card)

    def _rebuild_quick_actions(self):
        """Rebuild quick actions buttons with new language."""
        if not hasattr(self, '_quick_card'):
            return
        # Find the grid inside the quick card and rebuild
        grid = None
        for child in self._quick_card.children:
            if isinstance(child, GridLayout):
                grid = child
                break
        if grid:
            grid.clear_widgets()
            actions = [
                ("request_delivery", PRIMARY, self._go_request_delivery),
                ("request_ride", TEAL, lambda x: self._go_request_ride()),
                ("track_parcel", BLUE, self._go_track),
                ("history", DARK, self._go_history),
                ("support", ERROR, self._show_support_stub),
                ("refer_and_earn", PRIMARY, lambda x: self._go("refer_earn")),
            ]
            for key, color, cb in actions:
                btn = MDRaisedButton(
                    text=tr(key),
                    md_bg_color=rgba(color),
                    theme_text_color="Custom",
                    text_color="white",
                    size_hint_x=1,
                    on_release=cb,
                )
                grid.add_widget(btn)

    def _build_distribution_section(self):
        # Known gap per web — flagged placeholder (can build full chart later)
        self._distribution_card = MDCard(
            orientation="vertical",
            padding="12dp",
            spacing="8dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba(CARD_BG),
            radius=[12],
            elevation=1,
        )
        self._distribution_title = MDLabel(
            text=tr("delivery_status_distribution"),
            font_style="Subtitle2",
            bold=True,
            theme_text_color="Custom",
            text_color=DARK,
            adaptive_height=True,
        )
        self._distribution_card.add_widget(self._distribution_title)
        # Placeholder content — chart to be built when data viz decided
        placeholder = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="6dp", padding=["0dp", "8dp", "0dp", "8dp"])
        placeholder.add_widget(MDIcon(icon="chart-donut", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), font_size="36sp", size_hint_y=None, height="36dp"))
        placeholder.add_widget(MDLabel(text="Chart coming soon — distribution data will appear here", font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
        placeholder.add_widget(MDLabel(text="Tracked from Recent Deliveries", font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, font_size="10sp", adaptive_height=True))
        self._distribution_card.add_widget(placeholder)
        self._content.add_widget(self._distribution_card)

    def _show_support_stub(self, *args):
        if self.manager:
            self.manager.current = "support"
            return
        from kivymd.uix.dialog import MDDialog
        self._support_dialog = MDDialog(
            title=tr("support"),
            text=f"{tr('need_immediate_help')}\n{tr('call_support')}: +234 800 000 0000\n{tr('email_support')}: support@trackwaylogistics.ng",
            buttons=[MDFlatButton(text=tr("ok"), on_release=lambda x: self._support_dialog.dismiss())],
        )
        self._support_dialog.open()

    def _build_support_links(self):
        box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="4dp", padding=["0dp", "8dp", "0dp", "0dp"])
        box.add_widget(MDLabel(text=tr("need_immediate_help"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
        row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp")
        row.add_widget(MDFlatButton(text=tr("call_support"), theme_text_color="Custom", text_color=rgba(PRIMARY), on_release=lambda x: self._show_support_stub()))
        row.add_widget(MDFlatButton(text=tr("email_support"), theme_text_color="Custom", text_color=rgba(PRIMARY), on_release=lambda x: self._show_support_stub()))
        box.add_widget(row)
        self._content.add_widget(box)

    # ---------- Lifecycle (gated — matches tracking flow) ----------
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
        self._load_dashboard()

    def _load_dashboard(self, *args):
        if self._loading:
            return
        self._loading = True
        from app.services.customer_service import (
            get_dashboard_stats,
            get_deliveries,
            get_status_counts,
            get_notifications,
        )
        try:
            stats = get_dashboard_stats()
            if stats.get("ok"):
                self._stats = stats["data"]
            elif stats.get("error") and "Session expired" in str(stats.get("error")):
                from app.core import session
                session.clear_session()
                if self.manager:
                    self.manager.current = "customer_login"
                self._loading = False
                return
            else:
                # surface non-session errors so silent 0 is visible
                try:
                    from kivy.logger import Logger as _L
                    _L.warning(f"customer dashboard_stats non-session error: {stats.get('error')!r} — stats will show 0")
                    from kivymd.uix.snackbar import Snackbar
                    Snackbar(text=stats.get("error") or "Could not load dashboard stats").open()
                except Exception:
                    pass
                # keep _stats {} → will show 0, but now visible as failure vs real 0
        except Exception as e:
            try:
                from kivy.logger import Logger as _L
                _L.warning(f"customer dashboard_stats exception: {e!r}")
            except Exception:
                pass
        # referral_balance may live only at referral/stats.php — merge if still 0.00
        try:
            rb = str(self._stats.get("referral_balance", "0.00"))
            if rb in ("0.00", "0", "", "0.0"):
                from app.services.customer_service import get_referral_stats
                ref = get_referral_stats()
                if ref.get("ok"):
                    d = ref.get("data") or {}
                    bal = d.get("referral_balance")
                    if bal is not None:
                        self._stats["referral_balance"] = str(bal)
                    if not self._stats.get("referral_code"):
                        code = d.get("referral_code")
                        if code:
                            self._stats["referral_code"] = code
        except Exception:
            pass
        # pending payments — fire and forget, renders when loaded
        try:
            self._load_pending_payments()
        except Exception:
            pass
        # delivery list: prefer HTML tbody parsed delivery_items from dashboard.php (single source with 6 fields), fallback to API
        html_items = None
        if isinstance(self._stats, dict):
            html_items = self._stats.get("delivery_items")
        if isinstance(html_items, list) and html_items:
            self._all_items = html_items
            self._filtered_items = html_items
        else:
            try:
                delivers = get_deliveries(page=1)
                items = []
                if delivers.get("ok"):
                    items = delivers["data"]["items"]
                    self._all_items = items
                    self._filtered_items = items
                elif delivers.get("error") and "Session expired" in str(delivers.get("error")):
                    from app.core import session
                    session.clear_session()
                    if self.manager:
                        self.manager.current = "customer_login"
                    self._loading = False
                    return
            except Exception:
                items = []
                self._all_items = []
                self._filtered_items = []
        try:
            counts = get_status_counts()
            if counts.get("ok"):
                self._status_counts = counts.get("data", {}) or {}
                self._counts_loaded = True
            elif counts.get("error") and "Session expired" in str(counts.get("error")):
                from app.core import session
                session.clear_session()
                if self.manager:
                    self.manager.current = "customer_login"
                self._loading = False
                return
        except Exception:
            pass
        try:
            notif_result = get_notifications(page=1)
            if notif_result.get("ok"):
                self._unread_count = notif_result["data"].get("unread_count", 0)
            else:
                self._unread_count = 0
        except Exception:
            self._unread_count = 0

        try:
            # Prefer dashboard stats, fallback to session stored data.name
            from app.core import session as sess_mod
            sess_name = ""
            try:
                sess_name = sess_mod.get_customer_name() or ""
            except Exception:
                sess_name = ""
            name = self._stats.get("customer_name") or self._stats.get("name") or sess_name or ""
            if name:
                self.welcome_label.text = tr("welcome_back").format(name=name)
            else:
                base = tr("welcome_back")
                if "{name}" in base:
                    self.welcome_label.text = base.split(",")[0] if "," in base else base.replace("{name}", "").strip()
                else:
                    self.welcome_label.text = base
        except Exception:
            try:
                self.welcome_label.text = tr("welcome_back").split(",")[0]
            except Exception:
                self.welcome_label.text = tr("welcome_back")
        try:
            from app.core import session as sess_mod2
            sess_name2 = sess_mod2.get_customer_name() or ""
            self.top_name_label.text = self._stats.get("customer_name") or self._stats.get("name") or sess_name2 or ""
        except Exception:
            pass
        try:
            self.bell_count_label.text = str(self._unread_count) if self._unread_count > 0 else ""
        except Exception:
            pass
        try:
            self._on_window_width(Window, Window.width)
        except Exception:
            pass

        self._render_stat_cards()
        self._render_referral_banner()
        # current delivery status banner between pending payments and tabs
        try:
            self._current_delivery = self._stats.get("active_delivery") if isinstance(self._stats, dict) else None
            self._render_current_delivery_status()
        except Exception:
            pass
        self._bind_filter_chips()
        self._render_deliveries_section()
        self._loading = False

    def _go_notifications(self, *args):
        if self.manager:
            self.manager.current = "notifications"

    def _logout(self, *args):
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

    def _go(self, screen_name):
        if self.manager:
            self.manager.current = screen_name

    def _go_track(self, *args):
        if self.manager:
            self.manager.current = "tracking_search"

    def _go_request_delivery(self, *args):
        if self.manager:
            self.manager.current = "request_delivery"

    def _go_request_ride(self, *args):
        if self.manager:
            self.manager.current = "request_ride"

    def _go_deliveries(self, *args):
        if self.manager:
            self.manager.current = "customer_deliveries"

    def _go_history(self, *args):
        if self.manager:
            self.manager.current = "customer_history"

    def _go_profile(self, *args):
        if self.manager:
            self.manager.current = "profile"
