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
from kivymd.uix.menu import MDDropdownMenu

from app.core.theme import PRIMARY, DARK, MUTED, BACKGROUND, CARD_BG, SUCCESS, ERROR
from app.core import session
from app.views.base_screen import BaseScreen


class RiderEarningsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._data = {"total_earnings": "0.00", "display_total": "₦0.00", "completed_deliveries": 0, "avg_earning": "0.00", "display_avg": "₦0.00", "commission_percentage": "80%", "chart_data": {"labels": [], "values": [], "type": "bar"}, "recent_earnings": []}
        self._profile_menu = None
        self._loading = False
        self._period = "month"
        self._year = 2026
        self._month = 9
        self._month_names = ["January","February","March","April","May","June","July","August","September","October","November","December"]
        self._period_btns = {}
        self._month_menu = None
        self._year_menu = None

        self._outer = MDBoxLayout(orientation="vertical", spacing="0dp")
        self._scroll = ScrollView(do_scroll_x=False, bar_width=dp(4), size_hint_y=1, effect_cls="DampedScrollEffect")
        try:
            self._scroll.effect_y.allow_overscroll = False
            self._scroll.effect_x.allow_overscroll = False
        except Exception:
            pass
        self._content = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp", adaptive_height=True, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        self._outer.add_widget(self._build_top_nav())
        self._outer.add_widget(self._scroll)
        self.add_widget(self._outer)

        self._build_header()
        self._build_stats_row()
        self._build_filter_row()
        self._build_overview()
        self._build_commission()
        self._build_recent()
        self._build_footer()

        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

    # ---------- Top nav ----------
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

    def _menu_coming_soon(self, label):
        try:
            if self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text=f"{label} — coming soon").open()
        except Exception:
            pass

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

    # ---------- Header ----------
    def _build_header(self):
        box = MDBoxLayout(orientation="vertical", spacing="4dp", adaptive_height=True, padding=["2dp","4dp","0dp","4dp"])
        row = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_y=None, height="24dp")
        row.add_widget(MDIcon(icon="chart-line", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="18sp", size_hint_x=None, width="22dp"))
        row.add_widget(MDLabel(text="My Earnings", font_style="H6", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1, halign="left"))
        box.add_widget(row)
        box.add_widget(MDLabel(text="Track your delivery earnings and performance", font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
        self._content.add_widget(box)

    # ---------- Section 1: Four stats 2x2 ----------
    def _build_stats_row(self):
        self._stats_grid = GridLayout(cols=2, spacing="10dp", size_hint_y=None, row_default_height="72dp", row_force_default=True)
        self._stats_grid.bind(minimum_height=self._stats_grid.setter("height"))
        self._content.add_widget(self._stats_grid)
        self._render_stats()

    def _render_stats(self):
        try:
            self._stats_grid.clear_widgets()
        except Exception:
            pass
        d = self._data or {}
        items = [
            ("Total Earnings", d.get("display_total", "₦0.00"), SUCCESS),
            ("Completed Deliveries", str(d.get("completed_deliveries", 0)), SUCCESS),
            ("Average Per Delivery", d.get("display_avg", "₦0.00"), "#1976D2"),
            ("Your Commission Rate", d.get("commission_percentage", "80%"), "#8B5CF6"),
        ]
        for label, value, color in items:
            card = MDCard(orientation="vertical", padding="8dp", spacing="2dp", size_hint_y=None, height="72dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
            val_lbl = MDLabel(text=value, font_style="Subtitle1", font_size="13sp", bold=True, theme_text_color="Custom", text_color=rgba(color), halign="center", valign="middle", max_lines=1, shorten=True, adaptive_height=True, text_size=(dp(140), None))
            lbl = MDLabel(text=label.upper(), font_style="Caption", font_size="7sp", theme_text_color="Custom", text_color=MUTED, halign="center", valign="middle", max_lines=1, shorten=True, adaptive_height=True, text_size=(dp(140), None))
            try:
                card.bind(width=lambda inst, w, vl=val_lbl, ll=lbl: (setattr(vl, "text_size", (w - dp(16), None)), setattr(ll, "text_size", (w - dp(16), None))))
            except Exception:
                pass
            card.add_widget(val_lbl)
            card.add_widget(lbl)
            self._stats_grid.add_widget(card)

    # ---------- Section 2: Filter ----------
    def _build_filter_row(self):
        card = MDCard(orientation="vertical", padding="8dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        # period toggles
        toggle_row = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="36dp")
        for key, label in [("week","This Week"), ("month","This Month"), ("year","This Year")]:
            btn = MDFlatButton(text=label, font_size="11sp", size_hint_x=1, size_hint_y=None, height="32dp", theme_text_color="Custom")
            # store
            self._period_btns[key] = btn
            btn.bind(on_release=lambda x, k=key: self._on_filter_period(k))
            toggle_row.add_widget(btn)
        card.add_widget(toggle_row)
        # month/year dropdowns
        drop_row = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_x=1, size_hint_y=None, height="36dp")
        self._month_field = MDFlatButton(text=self._month_names[self._month-1], font_size="11sp", theme_text_color="Custom", text_color=DARK, size_hint_x=1, size_hint_y=None, height="32dp", line_color=rgba("#e0e0e0"), on_release=lambda x: self._show_month_menu())
        self._year_field = MDFlatButton(text=str(self._year), font_size="11sp", theme_text_color="Custom", text_color=DARK, size_hint_x=None, width="80dp", size_hint_y=None, height="32dp", line_color=rgba("#e0e0e0"), on_release=lambda x: self._show_year_menu())
        drop_row.add_widget(self._month_field)
        drop_row.add_widget(self._year_field)
        card.add_widget(drop_row)
        self._filter_card = card
        self._content.add_widget(card)
        self._update_filter_buttons()

    def _update_filter_buttons(self):
        for k, btn in self._period_btns.items():
            is_active = (k == self._period)
            try:
                if is_active:
                    btn.md_bg_color = rgba(PRIMARY)
                    btn.text_color = "white"
                    btn.line_color = rgba(PRIMARY)
                else:
                    btn.md_bg_color = [1,1,1,0]
                    btn.text_color = rgba(PRIMARY)
                    btn.line_color = rgba("#e0e0e0")
            except Exception:
                pass
        # disable month picker when period is year or week? Keep enabled but all use month+year per spec
        # no special handling

    def _on_filter_period(self, period):
        self._period = period
        self._update_filter_buttons()
        self._load_earnings()

    def _show_month_menu(self):
        items = [{"text": name, "on_release": lambda x, idx=i+1, n=name: self._on_month_selected(idx, n)} for i, name in enumerate(self._month_names)]
        try:
            if self._month_menu:
                self._month_menu.dismiss()
        except Exception:
            pass
        self._month_menu = MDDropdownMenu(caller=self._month_field, items=items, width_mult=4, max_height="300dp")
        self._month_menu.open()

    def _on_month_selected(self, idx, name):
        try:
            if self._month_menu:
                self._month_menu.dismiss()
        except Exception:
            pass
        self._month = idx
        self._month_field.text = name
        self._load_earnings()

    def _show_year_menu(self):
        years = [2024, 2025, 2026, 2027]
        items = [{"text": str(y), "on_release": lambda x, yy=y: self._on_year_selected(yy)} for y in years]
        try:
            if self._year_menu:
                self._year_menu.dismiss()
        except Exception:
            pass
        self._year_menu = MDDropdownMenu(caller=self._year_field, items=items, width_mult=3, max_height="200dp")
        self._year_menu.open()

    def _on_year_selected(self, y):
        try:
            if self._year_menu:
                self._year_menu.dismiss()
        except Exception:
            pass
        self._year = y
        self._year_field.text = str(y)
        self._load_earnings()

    # ---------- Section 3: Overview ----------
    def _build_overview(self):
        card = MDCard(orientation="vertical", padding="12dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        head = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="22dp")
        head.add_widget(MDIcon(icon="chart-line", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="18dp", font_size="14sp"))
        head.add_widget(MDLabel(text="Earnings Overview", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1))
        card.add_widget(head)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba("#e0e0e0")))
        self._overview_box = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, padding=["0dp","8dp","0dp","4dp"])
        card.add_widget(self._overview_box)
        self._content.add_widget(card)
        self._render_overview()

    def _render_overview(self):
        try:
            self._overview_box.clear_widgets()
        except Exception:
            pass
        cd = (self._data.get("chart_data") or {}) if isinstance(self._data, dict) else {}
        labels = cd.get("labels") or []
        values = cd.get("values") or []
        if not labels and not values:
            empty = MDBoxLayout(orientation="vertical", spacing="8dp", padding=["0dp","16dp","0dp","16dp"], adaptive_height=True)
            empty.add_widget(MDIcon(icon="chart-line", halign="center", theme_text_color="Custom", text_color=rgba("#d5e8d0"), font_size="36sp", size_hint_y=None, height="36dp"))
            empty.add_widget(MDLabel(text="No earnings data available for this period", font_style="Body2", theme_text_color="Custom", text_color=MUTED, halign="center", adaptive_height=True))
            self._overview_box.add_widget(empty)
        else:
            # placeholder for future chart rendering
            ctype = cd.get("type", "bar")
            self._overview_box.add_widget(MDLabel(text=f"Chart: {ctype} ({len(labels)} points)", font_style="Caption", theme_text_color="Custom", text_color=MUTED, halign="center", adaptive_height=True))
            # TODO: render actual chart using labels/values

    # ---------- Section 4: Commission ----------
    def _build_commission(self):
        card = MDCard(orientation="vertical", padding="12dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        head = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="22dp")
        head.add_widget(MDIcon(icon="chart-pie", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="18dp", font_size="14sp"))
        head.add_widget(MDLabel(text="Commission Breakdown", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1))
        card.add_widget(head)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba("#e0e0e0")))
        self._commission_bar = MDBoxLayout(orientation="horizontal", size_hint_x=1, size_hint_y=None, height="16dp", spacing="0dp")
        card.add_widget(self._commission_bar)
        self._commission_legend = MDBoxLayout(orientation="horizontal", spacing="12dp", adaptive_height=True, size_hint_y=None, height="20dp")
        card.add_widget(self._commission_legend)
        self._commission_card = card
        self._content.add_widget(card)
        self._render_commission()

    def _render_commission(self):
        try:
            self._commission_bar.clear_widgets()
            self._commission_legend.clear_widgets()
        except Exception:
            pass
        perc_str = str(self._data.get("commission_percentage", "80%"))
        try:
            your = int(float(perc_str.replace("%","").strip() or 80))
        except Exception:
            your = 80
        your = max(0, min(100, your))
        track = 100 - your
        # bar segments — use size_hint_x proportional
        left = MDBoxLayout(md_bg_color=rgba(SUCCESS), radius=[8,0,0,8] if track>0 else [8], size_hint_x=your, size_hint_y=None, height="16dp")
        left.add_widget(MDLabel(text=f"{your}% - Your Share", font_style="Caption", font_size="7sp", theme_text_color="Custom", text_color="white", halign="center", valign="middle"))
        right = MDBoxLayout(md_bg_color=rgba(DARK), radius=[0,8,8,0] if your>0 else [8], size_hint_x=track, size_hint_y=None, height="16dp")
        right.add_widget(MDLabel(text=f"{track}% - Trackway Share", font_style="Caption", font_size="7sp", theme_text_color="Custom", text_color="white", halign="center", valign="middle"))
        # handle 0% edge
        if your > 0:
            self._commission_bar.add_widget(left)
        if track > 0:
            self._commission_bar.add_widget(right)
        if your == 0 and track == 0:
            self._commission_bar.add_widget(MDLabel(text="No commission data", halign="center", font_style="Caption", theme_text_color="Custom", text_color=MUTED))
        # legend
        for color, label in [(SUCCESS, f"Your Earnings ({your}%)"), (DARK, f"Platform Fee ({track}%)")]:
            row = MDBoxLayout(orientation="horizontal", spacing="4dp", adaptive_height=True, size_hint_x=1)
            box = MDBoxLayout(size_hint=(None,None), size=("12dp","12dp"), md_bg_color=rgba(color), radius=[2])
            row.add_widget(box)
            row.add_widget(MDLabel(text=label, font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color=MUTED, halign="left"))
            self._commission_legend.add_widget(row)

    # ---------- Section 5: Recent Earnings ----------
    def _build_recent(self):
        card = MDCard(orientation="vertical", padding="12dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        head = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="22dp")
        head.add_widget(MDIcon(icon="history", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="18dp", font_size="14sp"))
        head.add_widget(MDLabel(text="Recent Earnings", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1))
        card.add_widget(head)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba("#e0e0e0")))
        self._recent_box = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, padding=["0dp","8dp","0dp","4dp"])
        card.add_widget(self._recent_box)
        self._content.add_widget(card)
        self._render_recent()

    def _render_recent(self):
        try:
            self._recent_box.clear_widgets()
        except Exception:
            pass
        items = self._data.get("recent_earnings") or []
        if not items:
            empty = MDBoxLayout(orientation="vertical", spacing="8dp", padding=["0dp","16dp","0dp","16dp"], adaptive_height=True)
            empty.add_widget(MDIcon(icon="chart-line", halign="center", theme_text_color="Custom", text_color=rgba("#d5e8d0"), font_size="36sp", size_hint_y=None, height="36dp"))
            empty.add_widget(MDLabel(text="No Earnings Yet", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, halign="center", adaptive_height=True))
            empty.add_widget(MDLabel(text="Complete deliveries to start earning and see your earnings here.", font_style="Caption", theme_text_color="Custom", text_color=MUTED, halign="center", adaptive_height=True))
            btn_wrap = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_y=None, height="36dp", padding=["0dp","8dp","0dp","0dp"])
            btn_wrap.add_widget(MDLabel(text=""))
            btn = MDRaisedButton(text="View Deliveries", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="140dp", on_release=lambda x: self._go_deliveries())
            btn_wrap.add_widget(btn)
            btn_wrap.add_widget(MDLabel(text=""))
            empty.add_widget(btn_wrap)
            self._recent_box.add_widget(empty)
        else:
            self._recent_box.add_widget(MDLabel(text=f"{len(items)} earning(s)", font_style="Body2", theme_text_color="Custom", text_color=MUTED, halign="center", adaptive_height=True))
            # TODO: render per-earning rows once populated sample captured

    def _go_deliveries(self, *args):
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="All deliveries — coming soon").open()
        except Exception:
            pass
        if self.manager:
            try:
                self.manager.current = "rider_home"
            except Exception:
                pass

    def _build_footer(self):
        footer = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="56dp", md_bg_color=rgba(DARK), radius=[0], elevation=0)
        footer.add_widget(MDLabel(text="© 2026 Trackway Logistics. Trackway Smart Logistics. All rights reserved.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        footer.add_widget(MDLabel(text="Delivering Excellence, One Parcel at a Time.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        self._content.add_widget(footer)

    # ---------- Lifecycle ----------
    def on_pre_enter(self, *args):
        from app.core import session as _sess
        if not _sess.is_logged_in() or _sess.get_role() != "rider":
            if self.manager:
                self.manager.current = "rider_login"
            return
        super().on_pre_enter(*args)

    def on_enter(self, *args):
        from app.core import session as _sess
        if not _sess.is_logged_in() or _sess.get_role() != "rider":
            if self.manager:
                self.manager.current = "rider_login"
            return
        try:
            name = session.get_customer_name() or ""
            self.top_name_label.text = name
            if hasattr(self, "_avatar_card"):
                self._avatar_card.children[0].text = (name.strip()[0].upper() if name else "A")
        except Exception:
            pass
        # default to current month/year
        try:
            import datetime
            now = datetime.datetime.now()
            self._month = now.month
            self._year = now.year
            self._month_field.text = self._month_names[self._month-1]
            self._year_field.text = str(self._year)
        except Exception:
            pass
        self._load_earnings()

    def _load_earnings(self):
        if self._loading:
            return
        self._loading = True
        import threading
        period = self._period
        year = self._year
        month = self._month
        def do():
            data = {}
            err = None
            try:
                from app.services.rider_service import get_rider_earnings
                r = get_rider_earnings(period=period, year=year, month=month)
                if r.get("ok"):
                    data = r.get("data") or {}
                else:
                    err = r.get("error")
            except Exception as e:
                err = str(e)
            Clock.schedule_once(lambda dt: self._apply_earnings(data, err), 0)
        threading.Thread(target=do, daemon=True).start()

    def _apply_earnings(self, data, err):
        self._loading = False
        if data and isinstance(data, dict):
            self._data.update({k: v for k, v in data.items() if v is not None})
            self._render_all()
        if err and "Session expired" in str(err):
            try:
                session.clear_session()
            except Exception:
                pass
            if self.manager:
                self.manager.current = "rider_login"

    def _render_all(self):
        self._render_stats()
        self._render_overview()
        self._render_commission()
        self._render_recent()

    def rebuild_ui(self):
        try:
            self._render_all()
        except Exception:
            pass
