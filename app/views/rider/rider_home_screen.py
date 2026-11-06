from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.menu import MDDropdownMenu

from app.i18n.translator import tr
from app.core.theme import PRIMARY, PRIMARY_DARK, DARK, MUTED, BACKGROUND, CARD_BG, ERROR
from app.views.base_screen import BaseScreen


class RiderHomeScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._stats = {"total_deliveries": 0, "completed": 0, "in_progress": 0, "total_earnings": "0.00", "rating": "0.0", "wallet_balance": "0.00", "total_earned": "0.00", "total_withdrawn": "0.00", "commission_rate": "80%", "customer_name": "", "unread_count": 0}
        self._online = True
        self._tracking = False
        self._last_update = "--"
        self._tracking_clock = None
        self._loading = False
        self._profile_menu = None
        self._unread_count = 0

        self._outer = MDBoxLayout(orientation="vertical", spacing="0dp")
        self._scroll = ScrollView(do_scroll_x=False, bar_width=dp(4), size_hint_y=1, effect_cls="DampedScrollEffect")
        try:
            self._scroll.effect_y.allow_overscroll = False
            self._scroll.effect_x.allow_overscroll = False
        except Exception:
            pass
        self._content = MDBoxLayout(orientation="vertical", padding="12dp", spacing="10dp", adaptive_height=True, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        self._outer.add_widget(self._build_top_nav())
        self._outer.add_widget(self._scroll)
        self.add_widget(self._outer)

        self._build_welcome_banner()
        self._build_map_card()
        self._build_stat_cards()
        self._build_wallet_banner()
        self._build_two_column()
        self._build_today_schedule()
        self._build_footer()

        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

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
                    self.manager.current = "rider_notifications"
            except Exception:
                pass

    # ---------- Top nav — white 48dp, logo left, EN + Online + bell + avatar right (172915) ----------
    def _build_top_nav(self):
        nav = MDCard(orientation="horizontal", padding="6dp", spacing="6dp", size_hint_x=1, size_hint_y=None, height="48dp", md_bg_color=rgba(CARD_BG), radius=[0], elevation=2)
        # Left logo — stacked two-line, 12sp/6.5sp to prevent SMART...ISTICS truncate
        logo_box = MDBoxLayout(orientation="vertical", size_hint_x=1, size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5}, spacing="0dp")
        _track = MDLabel(text="TRACKWAY", font_style="Subtitle2", bold=True, font_size="12sp", theme_text_color="Custom", text_color=DARK, size_hint_y=None, height="16dp", halign="left", shorten=True, max_lines=1)
        _smart = MDLabel(text="SMART LOGISTICS", font_style="Caption", font_size="6.5sp", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="9dp", halign="left", shorten=False, max_lines=1)
        logo_box.add_widget(_track)
        logo_box.add_widget(_smart)
        try:
            logo_box.bind(width=lambda inst, w, a=_track, b=_smart: [setattr(a, "text_size", (w - dp(4), None)), setattr(b, "text_size", (w - dp(4), None))])
            _track.text_size = (logo_box.width - dp(4), None) if logo_box.width else (dp(90), None)
            _smart.text_size = (logo_box.width - dp(4), None) if logo_box.width else (dp(90), None)
        except Exception:
            pass
        nav.add_widget(logo_box)

        right = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=None, width="250dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        try:
            from app.views.shared.language_picker import LanguagePicker
            lp = LanguagePicker(compact=True)
            lp.size_hint_x = None
            lp.width = "40dp"
            right.add_widget(lp)
        except Exception:
            right.add_widget(MDLabel(text="EN", font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_x=None, width="32dp", halign="center"))

        # Online pill — green light green bg, dark dot
        self._online_pill = MDCard(orientation="horizontal", padding=["8dp","4dp","8dp","4dp"], spacing="4dp", size_hint_x=None, width="70dp", size_hint_y=None, height="24dp", md_bg_color=rgba("#E8F5E9"), radius=[12], elevation=0, ripple_behavior=True)
        self._online_dot = MDLabel(text="●", font_style="Caption", theme_text_color="Custom", text_color=rgba(SUCCESS:=PRIMARY), size_hint_x=None, width="10dp", halign="center")
        self._online_label = MDLabel(text="Online", font_style="Caption", font_size="12sp", bold=True, theme_text_color="Custom", text_color=rgba(PRIMARY_DARK), halign="center")
        self._online_pill.add_widget(self._online_dot)
        self._online_pill.add_widget(self._online_label)
        self._online_pill.bind(on_release=lambda x: self._toggle_online())
        right.add_widget(self._online_pill)

        bell_box = MDBoxLayout(orientation="horizontal", size_hint_x=None, width="28dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        bell_box.add_widget(MDIconButton(icon="bell-outline", theme_icon_color="Custom", icon_color=rgba(MUTED), icon_size="22sp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5}, on_release=self._toggle_notif_dropdown))
        right.add_widget(bell_box)
        self._bell_box = bell_box
        self.bell_count_label = MDLabel(text="", font_style="Caption", bold=True, theme_text_color="Custom", text_color=rgba(ERROR), size_hint_x=None, width="14dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5}, halign="center")
        right.add_widget(self.bell_count_label)

        avatar = MDCard(size_hint=(None,None), size=("28dp","28dp"), md_bg_color=rgba(PRIMARY), radius=[14], elevation=0, ripple_behavior=True, pos_hint={"center_y": 0.5})
        avatar.add_widget(MDLabel(text="A", halign="center", theme_text_color="Custom", text_color="white", bold=True))
        right.add_widget(avatar)
        self._avatar_card = avatar
        name_card = MDCard(size_hint=(None,None), size=("110dp","32dp"), md_bg_color=[0,0,0,0], radius=[6], elevation=0, ripple_behavior=True, pos_hint={"center_y": 0.5})
        self.top_name_label = MDLabel(text="", font_style="Caption", bold=True, theme_text_color="Custom", text_color=DARK, halign="left")
        name_card.add_widget(self.top_name_label)
        right.add_widget(name_card)
        self._name_card = name_card
        avatar.bind(on_release=lambda x: self._open_profile_menu())
        name_card.bind(on_release=lambda x: self._open_profile_menu())
        nav.add_widget(right)
        self._top_nav = nav
        return nav

    def _on_window_width(self, instance, width):
        try:
            hide = width < 360
            if hasattr(self, "top_name_label"):
                self.top_name_label.opacity = 0 if hide else 1
                self.top_name_label.width = "0dp" if hide else "70dp"
            # compact Start/Stop at <375dp — smaller footprint proportionate to web (short label ▶Start / ■Stop, rounded-rectangle 20-25% radius)
            compact = width < 375
            if hasattr(self, "_start_btn") and hasattr(self, "_stop_btn"):
                for btn, key in ((self._start_btn, "start"), (self._stop_btn, "stop")):
                    try:
                        # no space icon-to-text, padding [10,6] makes compact unit
                        prefix = "▶" if key == "start" else "■"
                        btn.text = prefix + tr(key)
                    except Exception:
                        pass
                    btn.width = "60dp" if compact else "70dp"
                    btn.height = "26dp" if compact else "28dp"
                    btn.font_size = "11sp" if compact else "12sp"
                    try:
                        btn.elevation = 0
                        btn.rounded_button = False
                        btn._radius = dp(6)
                        btn.padding = [dp(10), dp(6), dp(10), dp(6)]
                    except Exception:
                        pass
                # tight inner gap 4dp desktop / 3dp compact for Start↔Stop pair
                if hasattr(self, "_btn_pair"):
                    try:
                        self._btn_pair.spacing = "3dp" if compact else "4dp"
                        self._btn_pair.width = "123dp" if compact else "144dp"
                        self._btn_pair.height = "26dp" if compact else "28dp"
                    except Exception:
                        pass
            if hasattr(self, "_tracking_label"):
                self._tracking_label.font_size = "10sp" if compact else "11sp"
            if hasattr(self, "_last_update_label"):
                self._last_update_label.width = "90dp" if compact else "110dp"
                self._last_update_label.font_size = "9sp" if compact else "10sp"
            if hasattr(self, "_stripe"):
                self._stripe.height = "24dp" if compact else "28dp"
                self._stripe.spacing = "4dp" if compact else "6dp"
                self._stripe.padding = ["4dp", "0dp", "4dp", "0dp"] if compact else ["6dp", "0dp", "6dp", "0dp"]
        except Exception:
            pass

    # ---------- Welcome banner — green, white View All (172915) ----------
    def _build_welcome_banner(self):
        self._banner = MDCard(orientation="vertical", padding="14dp", spacing="6dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        self.welcome_label = MDLabel(text=tr("welcome_back").format(name=""), font_style="H6", bold=True, theme_text_color="Custom", text_color="white", adaptive_height=True)
        self.welcome_sub = MDLabel(text=tr("welcome_rider_sub"), font_style="Body2", theme_text_color="Custom", text_color=rgba("#e8f0e3"), adaptive_height=True)
        btn_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", padding=["0dp","6dp","0dp","0dp"])
        btn_row.add_widget(MDLabel(text=""))
        self._view_all_btn = MDFlatButton(text="☰ " + tr("view_all_deliveries"), theme_text_color="Custom", text_color=rgba(CARD_BG), line_color=rgba(CARD_BG), line_width=1, size_hint_x=None, width="170dp", size_hint_y=None, height="36dp", on_release=lambda x: self._go_deliveries())
        try:
            self._view_all_btn.md_bg_color = [1,1,1,0.15]
        except Exception:
            pass
        btn_row.add_widget(self._view_all_btn)
        self._banner.add_widget(self.welcome_label)
        self._banner.add_widget(self.welcome_sub)
        self._banner.add_widget(btn_row)
        self._content.add_widget(self._banner)

    # ---------- Map card — static 260dp, tracking stripe below (172915) ----------
    def _build_map_card(self):
        wrap = MDCard(orientation="vertical", padding="8dp", spacing="6dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        # Map image — static Google map with pins, expand + pan controls baked as overlay icons (non-functional placeholder)
        self._map_card = MDCard(orientation="vertical", size_hint_x=1, size_hint_y=None, height="260dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=0)
        try:
            self._map_image = AsyncImage(source="", size_hint_x=1, size_hint_y=None, height="260dp", fit_mode="cover")
            # fallback source with FUTA area pins via places_service static map (Akure 7.25,5.2)
            self._map_card.add_widget(self._map_image)
        except Exception:
            self._map_image = None
            self._map_card.add_widget(MDLabel(text="Map", halign="center", theme_text_color="Custom", text_color=MUTED))
        # overlay controls (visual only)
        wrap.add_widget(self._map_card)
        stripe = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="28dp", padding=["6dp","0dp","6dp","0dp"])
        self._tracking_label = MDLabel(text=tr("location_tracking_inactive"), font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), size_hint_x=1, font_size="11sp", halign="left")
        self._last_update_label = MDLabel(text=tr("last_update"), font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=rgba("#c8d8c8"), size_hint_x=None, width="110dp", halign="right")
        stripe.add_widget(self._tracking_label)
        stripe.add_widget(self._last_update_label)
        # Start/Stop tightly paired — compact rounded rectangle (dp6 radius 20-25% of height), not pill
        self._start_btn = MDRaisedButton(text="▶" + tr("start"), md_bg_color=rgba(CARD_BG), theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="70dp", size_hint_y=None, height="28dp", font_size="12sp", elevation=0, on_release=lambda x: self._start_tracking())
        self._stop_btn = MDRaisedButton(text="■" + tr("stop"), md_bg_color=rgba(CARD_BG), theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="70dp", size_hint_y=None, height="28dp", font_size="12sp", elevation=0, on_release=lambda x: self._stop_tracking())
        for _b in (self._start_btn, self._stop_btn):
            try:
                _b.rounded_button = False
                _b._radius = dp(6)
                _b.padding = [dp(10), dp(6), dp(10), dp(6)]
            except Exception:
                pass
        # inner pair for tight gap 4dp desktop / 3dp compact (web close together)
        self._btn_pair = MDBoxLayout(orientation="horizontal", spacing="4dp", size_hint_x=None, width="144dp", size_hint_y=None, height="28dp")
        self._btn_pair.add_widget(self._start_btn)
        self._btn_pair.add_widget(self._stop_btn)
        stripe.add_widget(self._btn_pair)
        self._stripe = stripe
        wrap.add_widget(stripe)
        self._content.add_widget(wrap)
        self._map_wrap = wrap

    def _load_map(self):
        try:
            from app.services.places_service import static_map_url
            # Akure FUTA area default — South Gate Check Post 7.298,5.135
            url = static_map_url("7.298","5.135","7.305","5.145","") # short route to show pins
            if url and hasattr(self, "_map_image") and self._map_image:
                self._map_image.source = url
        except Exception:
            pass

    # ---------- 5 stat cards — white, icons top (172915/172928 TABLE 0) ----------
    def _build_stat_cards(self):
        self._stat_container = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="8dp")
        self._content.add_widget(self._stat_container)
        self._render_stat_cards()

    def _render_stat_cards(self):
        try:
            self._stat_container.clear_widgets()
        except Exception:
            pass
        s = self._stats
        container = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, size_hint_y=None, size_hint_x=1)
        try:
            container.bind(minimum_height=container.setter("height"))
        except Exception:
            pass
        items = [
            (str(s.get("total_deliveries",0)), "total_deliveries", "package-variant-closed", PRIMARY, "#E8F5E9"),
            (str(s.get("completed",0)), "completed_stats", "check-circle", PRIMARY, "#E8F5E9"),
            (str(s.get("in_progress",0)), "in_progress_stats", "progress-clock", "#FF9800", "#FFF3E0"),
            ("₦"+str(s.get("total_earnings","0.00")), "total_earnings_card", "cash", "#FF9800", "#FFF3E0"),
            (str(s.get("rating","0.0")), "rating", "star", "#FFB300", "#FFF8E1"),
        ]
        # 2x2 grid for first 4 — equal width/height, tight consistent spacing
        grid = GridLayout(cols=2, spacing="8dp", padding="0dp", size_hint_x=1, size_hint_y=None, row_force_default=True, row_default_height="72dp")
        try:
            grid.bind(minimum_height=grid.setter("height"))
        except Exception:
            pass
        for value, label, icon, icon_color, bg in items[:4]:
            try:
                card = MDCard(orientation="horizontal", padding="10dp", spacing="8dp", size_hint_x=1, size_hint_y=None, height="72dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
            except Exception:
                # fallback if BoxShadow/FBO fails
                card = MDBoxLayout(orientation="horizontal", padding="10dp", spacing="8dp", size_hint_x=1, size_hint_y=None, height="72dp", md_bg_color=rgba(CARD_BG), radius=[12])
            # icon background — MDBoxLayout to avoid BoxShadow/Fbo deadlock on Windows (was MDCard elevation=0)
            icon_bg = MDBoxLayout(size_hint=(None,None), size=("28dp","28dp"), md_bg_color=rgba(bg), radius=[8], pos_hint={"center_y": 0.5})
            try:
                icon_bg.add_widget(MDIcon(icon=icon, theme_text_color="Custom", text_color=rgba(icon_color), font_size="16sp", halign="center", pos_hint={"center_x": 0.5, "center_y": 0.5}))
            except Exception:
                pass
            card.add_widget(icon_bg)
            texts = MDBoxLayout(orientation="vertical", spacing="2dp", size_hint_x=1, size_hint_y=None, height="44dp", pos_hint={"center_y": 0.5})
            texts.add_widget(MDLabel(text=value, font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_y=None, height="20dp", halign="left"))
            texts.add_widget(MDLabel(text=tr(label).upper(), font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="14dp", halign="left"))
            card.add_widget(texts)
            card.add_widget(MDIcon(icon="chevron-right", theme_text_color="Custom", text_color=rgba(MUTED), font_size="18sp", size_hint_x=None, width="18dp", pos_hint={"center_y": 0.5}))
            grid.add_widget(card)
        container.add_widget(grid)
        # 5th card (Rating) full-width on its own row below, highlighted/secondary with icon on right
        value, label, icon, icon_color, bg = items[4]
        try:
            rating_card = MDCard(orientation="horizontal", padding="10dp", spacing="10dp", size_hint_x=1, size_hint_y=None, height="72dp", md_bg_color=rgba("#f9fdf6"), radius=[12], elevation=1, line_color=rgba("#E8F5E9"), line_width=1)
        except Exception:
            rating_card = MDBoxLayout(orientation="horizontal", padding="10dp", spacing="10dp", size_hint_x=1, size_hint_y=None, height="72dp", md_bg_color=rgba("#f9fdf6"), radius=[12])
        texts = MDBoxLayout(orientation="vertical", spacing="2dp", size_hint_x=1, size_hint_y=None, height="44dp", pos_hint={"center_y": 0.5})
        texts.add_widget(MDLabel(text=value, font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_y=None, height="20dp", halign="left"))
        texts.add_widget(MDLabel(text=label, font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="14dp", halign="left"))
        rating_card.add_widget(texts)
        icon_bg_right = MDBoxLayout(size_hint=(None,None), size=("28dp","28dp"), md_bg_color=rgba(bg), radius=[8], pos_hint={"center_y": 0.5})
        try:
            icon_bg_right.add_widget(MDIcon(icon=icon, theme_text_color="Custom", text_color=rgba(icon_color), font_size="16sp", halign="center", pos_hint={"center_x": 0.5, "center_y": 0.5}))
        except Exception:
            pass
        rating_card.add_widget(icon_bg_right)
        container.add_widget(rating_card)
        try:
            self._stat_container.add_widget(container)
        except Exception:
            pass

    # ---------- Wallet banner — green #567f30 (172928) ----------
    def _build_wallet_banner(self):
        self._wallet_card = MDCard(orientation="vertical", padding="14dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        top = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="28dp")
        top.add_widget(MDIcon(icon="wallet-outline", theme_text_color="Custom", text_color="white", size_hint_x=None, width="18dp", font_size="14sp"))
        _wallet_title = MDLabel(text=tr("wallet_balance").upper(), font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=rgba("#c8e6c9"), size_hint_x=1, halign="left", max_lines=1, shorten=True, adaptive_height=False, size_hint_y=None, height="20dp")
        try:
            self._wallet_card.bind(width=lambda inst, w, lbl=_wallet_title: setattr(lbl, "text_size", (w - dp(14*2 + 18 + 6 + 110), None)))
            _wallet_title.text_size = (dp(336 - 14*2 - 18 - 6 - 110), None)
        except Exception:
            pass
        top.add_widget(_wallet_title)
        self._wallet_title_label = _wallet_title
        self._wallet_btn = MDFlatButton(text="→ " + tr("view_wallet"), theme_text_color="Custom", text_color="white", line_color="white", size_hint_x=None, width="110dp", size_hint_y=None, height="28dp", font_size="12sp", on_release=lambda x: self._go_wallet())
        top.add_widget(self._wallet_btn)
        self._wallet_card.add_widget(top)
        self._wallet_balance = MDLabel(text="₦0.00", font_style="H5", bold=True, theme_text_color="Custom", text_color="white", size_hint_y=None, height="32dp")
        self._wallet_card.add_widget(self._wallet_balance)
        div = MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba("#6a9a3d"))
        self._wallet_card.add_widget(div)
        row = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_x=1, adaptive_height=True)
        for label, key in [(tr("wallet_total_earned"),"total_earned"), (tr("wallet_total_withdrawn"),"total_withdrawn"), (tr("wallet_commission_rate"),"commission_rate")]:
            col = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="2dp", size_hint_x=1)
            col.add_widget(MDLabel(text=label, font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color=rgba("#c8e6c9"), halign="left", adaptive_height=True))
            val = MDLabel(text=str(self._stats.get(key,"0.00" if "total" in key else "80%")), font_style="Body2", bold=True, theme_text_color="Custom", text_color="white", halign="left", adaptive_height=True, font_size="13sp")
            col.add_widget(val)
            row.add_widget(col)
            if key == "total_earned":
                setattr(self, "_wallet_earned_label", val)
            elif key == "total_withdrawn":
                setattr(self, "_wallet_withdrawn_label", val)
            elif key == "commission_rate":
                setattr(self, "_wallet_commission_label", val)
        self._wallet_card.add_widget(row)
        self._content.add_widget(self._wallet_card)

    def _render_wallet(self):
        try:
            self._wallet_balance.text = "₦" + str(self._stats.get("wallet_balance","0.00"))
            self._wallet_earned_label.text = "₦" + str(self._stats.get("total_earned","0.00"))
            self._wallet_withdrawn_label.text = "₦" + str(self._stats.get("total_withdrawn","0.00"))
            self._wallet_commission_label.text = str(self._stats.get("commission_rate","80%"))
        except Exception:
            pass

    # ---------- Two column — Active Deliveries + Recent Transactions (172928) ----------
    def _build_two_column(self):
        row = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_x=1, adaptive_height=True)
        for title, icon, empty_icon, empty_text, view_all_cb in [
            (tr("active_deliveries"),"truck-delivery-outline","inbox-outline",tr("no_active_deliveries"), self._go_deliveries),
            (tr("recent_transactions"),"history","receipt-text-outline",tr("no_transactions"), self._go_wallet),
        ]:
            card = MDCard(orientation="vertical", padding="12dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
            # stacked: title gets full card width, View All right-aligned below (prevents Acti... truncation)
            head = MDBoxLayout(orientation="vertical", spacing="2dp", adaptive_height=True, size_hint_y=None)
            head.bind(minimum_height=head.setter("height"))
            top = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="20dp")
            top.add_widget(MDIcon(icon=icon, theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="18dp", font_size="14sp"))
            title_lbl = MDLabel(text=title, font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1, halign="left", max_lines=1, shorten=False, adaptive_height=False, size_hint_y=None, height="20dp")
            try:
                card.bind(width=lambda inst, w, lbl=title_lbl: setattr(lbl, "text_size", (w - dp(12*2 + 18 + 6), None)))
                title_lbl.text_size = (dp(164 - 12*2 - 18 - 6), None)
            except Exception:
                pass
            top.add_widget(title_lbl)
            head.add_widget(top)
            btn_row = MDBoxLayout(orientation="horizontal", size_hint_x=1, size_hint_y=None, height="22dp", spacing="6dp")
            btn_row.add_widget(MDLabel(text=""))
            btn_row.add_widget(MDFlatButton(text=tr("view_all") + " →", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="11sp", size_hint_x=None, width="70dp", size_hint_y=None, height="22dp", on_release=lambda x,cb=view_all_cb: cb()))
            head.add_widget(btn_row)
            card.add_widget(head)
            card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba(PRIMARY)))
            empty = MDBoxLayout(orientation="vertical", spacing="8dp", padding=["0dp","16dp","0dp","16dp"], adaptive_height=True)
            empty.add_widget(MDIcon(icon=empty_icon, halign="center", theme_text_color="Custom", text_color=rgba("#d5e8d0"), font_size="36sp", size_hint_y=None, height="36dp"))
            empty.add_widget(MDLabel(text=empty_text, font_style="Body2", theme_text_color="Custom", text_color=MUTED, halign="center", adaptive_height=True))
            card.add_widget(empty)
            row.add_widget(card)
        self._content.add_widget(row)

    # ---------- Today's Schedule — 0 deliveries badge (172942) ----------
    def _build_today_schedule(self):
        self._schedule_card = MDCard(orientation="vertical", padding="12dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        head = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="22dp")
        head.add_widget(MDIcon(icon="calendar-check-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="18dp", font_size="14sp"))
        _sched_title = MDLabel(text=tr("todays_schedule"), font_style="Subtitle2", bold=True, font_size="11sp", theme_text_color="Custom", text_color=DARK, size_hint_x=1, halign="left", max_lines=1, shorten=True, adaptive_height=False, size_hint_y=None, height="20dp")
        try:
            self._schedule_card.bind(width=lambda inst, w, lbl=_sched_title: setattr(lbl, "text_size", (w - dp(12*2 + 18 + 6 + 80), None)))
            _sched_title.text_size = (dp(336 - 12*2 - 18 - 6 - 80), None)
        except Exception:
            pass
        head.add_widget(_sched_title)
        self._schedule_title_label = _sched_title
        self._schedule_badge = MDCard(size_hint=(None,None), size=("80dp","20dp"), md_bg_color=rgba(PRIMARY), radius=[10], elevation=0)
        self._schedule_badge.add_widget(MDLabel(text="0 " + tr("deliveries").lower(), font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color="white", halign="center"))
        head.add_widget(self._schedule_badge)
        self._schedule_card.add_widget(head)
        self._schedule_card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba(PRIMARY)))
        empty = MDBoxLayout(orientation="vertical", spacing="8dp", padding=["0dp","16dp","0dp","16dp"], adaptive_height=True)
        empty.add_widget(MDIcon(icon="calendar-check", halign="center", theme_text_color="Custom", text_color=rgba("#d5e8d0"), font_size="36sp", size_hint_y=None, height="36dp"))
        empty.add_widget(MDLabel(text=tr("no_schedule"), font_style="Body2", theme_text_color="Custom", text_color=MUTED, halign="center", adaptive_height=True))
        self._schedule_card.add_widget(empty)
        self._content.add_widget(self._schedule_card)

    def _build_footer(self):
        footer = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="56dp", md_bg_color=rgba(DARK), radius=[0], elevation=0)
        footer.add_widget(MDLabel(text="© 2026 Trackway Logistics. Trackway Smart Logistics. All rights reserved.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        footer.add_widget(MDLabel(text="Delivering Excellence, One Parcel at a Time.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        self._content.add_widget(footer)

    # ---------- Interactions ----------
    def _toggle_online(self, *args):
        self._online = not self._online
        try:
            self._online_label.text = tr("online") if self._online else tr("offline")
            self._online_dot.text_color = rgba(PRIMARY) if self._online else rgba(MUTED)
            self._online_pill.md_bg_color = rgba("#E8F5E9") if self._online else rgba("#f0f0f0")
            # optional server sync
            import threading
            def do():
                try:
                    from app.services.rider_service import update_online_status
                    update_online_status(self._online)
                except Exception:
                    pass
            threading.Thread(target=do, daemon=True).start()
        except Exception:
            pass

    def _start_tracking(self, *args):
        if self._tracking:
            return
        self._tracking = True
        try:
            self._tracking_label.text = tr("location_tracking_active")
            self._tracking_label.text_color = rgba("#a8e6a8")
        except Exception:
            pass
        self._tracking_clock = Clock.schedule_interval(self._tick_tracking, 30)

    def _stop_tracking(self, *args):
        self._tracking = False
        try:
            self._tracking_label.text = tr("location_tracking_inactive")
            self._tracking_label.text_color = rgba("#e8f0e3")
            self._last_update_label.text = tr("last_update")
        except Exception:
            pass
        if self._tracking_clock:
            try:
                self._tracking_clock.cancel()
            except Exception:
                pass
            self._tracking_clock = None

    def _tick_tracking(self, dt):
        import threading, datetime
        def do():
            try:
                from app.services.rider_service import update_location
                # placeholder Akure FUTA 7.298,5.135 — replace with actual GPS via plyer if available
                update_location("7.298","5.135")
            except Exception:
                pass
            Clock.schedule_once(lambda dt2: setattr(self._last_update_label, "text", f'{tr("last_update").split(":")[0]}: {datetime.datetime.now().strftime("%H:%M")}') if hasattr(self, "_last_update_label") else None, 0)
        threading.Thread(target=do, daemon=True).start()

    def _create_profile_menu(self):
        if hasattr(self, "_profile_menu") and self._profile_menu:
            return
        items = [
            {
                "text": "My Profile",
                "leading_icon": "account-outline",
                "text_color": rgba(DARK),
                "leading_icon_color": rgba(DARK),
                "on_release": lambda: self._menu_navigate("rider_profile"),
            },
            {
                "text": "My Wallet",
                "leading_icon": "wallet-outline",
                "text_color": rgba(DARK),
                "leading_icon_color": rgba(DARK),
                "on_release": lambda: self._menu_navigate("rider_wallet"),
            },
            {
                "text": "Earnings",
                "leading_icon": "cash",
                "text_color": rgba(DARK),
                "leading_icon_color": rgba(DARK),
                "on_release": lambda: self._menu_navigate("rider_earnings"),
            },
            {
                "text": "Support",
                "leading_icon": "headset",
                "text_color": rgba(DARK),
                "leading_icon_color": rgba(DARK),
                "on_release": lambda: self._menu_navigate("rider_support"),
            },
            {
                "text": "Notifications",
                "leading_icon": "bell-outline",
                "text_color": rgba(DARK),
                "leading_icon_color": rgba(DARK),
                "on_release": lambda: self._menu_navigate("rider_notifications"),
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
        caller = getattr(self, "_avatar_card", self._top_nav)
        self._profile_menu = MDDropdownMenu(
            caller=caller,
            items=items,
            width_mult=4,
            max_height="320dp",
            position="bottom",
            ver_growth="down",
            hor_growth="left",
            border_margin=dp(8),
        )

    def _open_profile_menu(self, *args):
        try:
            self._create_profile_menu()
            self._profile_menu.caller = getattr(self, "_avatar_card", self._top_nav)
            self._profile_menu.open()
        except Exception as e:
            try:
                from kivy.logger import Logger
                Logger.warning(f"ProfileMenu open failed: {e}")
            except Exception:
                pass

    def _menu_navigate(self, route):
        try:
            if hasattr(self, "_profile_menu") and self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", route) if self.manager else None, 0.15)

    def _menu_coming_soon(self, label):
        try:
            if hasattr(self, "_profile_menu") and self._profile_menu:
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
            if hasattr(self, "_profile_menu") and self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: self._do_logout_inner() if hasattr(self, "_do_logout_inner") else self._do_logout(), 0.15)

    def _menu_go(self, route):
        # legacy compat — delegate to _menu_navigate
        self._menu_navigate(route)

    # ---------- Lifecycle ----------
    def on_pre_enter(self, *args):
        from app.core import session
        if not session.is_logged_in() or session.get_role() != "rider":
            if self.manager:
                self.manager.current = "rider_login"
            return
        super().on_pre_enter(*args)

    def on_enter(self, *args):
        from app.core import session
        if not session.is_logged_in() or session.get_role() != "rider":
            if self.manager:
                self.manager.current = "rider_login"
            return
        try:
            name = session.get_customer_name() or ""
            self.welcome_label.text = f"Welcome back, {name}" if name else "Welcome back, Rider"
            self.top_name_label.text = name
            if hasattr(self, "_avatar_card"):
                self._avatar_card.children[0].text = (name.strip()[0].upper() if name else "A")
        except Exception:
            pass
        self._load_map()
        self._load_dashboard()
        try:
            self._on_window_width(Window, Window.width if hasattr(Window, "width") else 400)
        except Exception:
            pass

    def _load_dashboard(self):
        if self._loading:
            return
        self._loading = True
        import threading
        def do():
            data = {}
            try:
                from app.services.rider_service import get_rider_dashboard
                r = get_rider_dashboard()
                if r.get("ok"):
                    data = r.get("data") or {}
            except Exception:
                data = {}
            Clock.schedule_once(lambda dt: self._apply_dashboard(data), 0)
        threading.Thread(target=do, daemon=True).start()

    def _apply_dashboard(self, data):
        try:
            self._loading = False
            if data:
                self._stats.update({k: v for k, v in data.items() if v is not None})
                if data.get("customer_name") and not self.top_name_label.text:
                    self.top_name_label.text = data.get("customer_name")
                    self.welcome_label.text = f"Welcome back, {data.get('customer_name')}"
                try:
                    self.bell_count_label.text = str(data.get("unread_count","")) if data.get("unread_count") else ""
                except Exception:
                    pass
            self._render_stat_cards()
            self._render_wallet()
        except Exception:
            self._loading = False

    def rebuild_ui(self):
        try:
            from app.i18n.translator import tr
            # welcome
            try:
                name = ""
                try:
                    from app.core import session
                    name = session.get_customer_name() or ""
                except Exception:
                    pass
                wb = tr("welcome_back")
                self.welcome_label.text = wb.format(name=name) if "{name}" in wb and name else (f"Welcome back, {name}" if name else tr("welcome_rider"))
            except Exception:
                pass
            self.welcome_sub.text = tr("welcome_rider_sub")
            self._view_all_btn.text = "☰ " + tr("view_all_deliveries")
            self._tracking_label.text = tr("location_tracking_inactive")
            self._last_update_label.text = tr("last_update")
            self._start_btn.text = "▶" + tr("start")
            self._stop_btn.text = "■" + tr("stop")
            self._online_label.text = tr("online") if self._online else tr("offline")
            # wallet
            try:
                # top label
                for child in self._wallet_card.children:
                    pass
                # find wallet top label via walk
                for w in self._wallet_card.walk():
                    if isinstance(w, MDLabel) and w.text and "WALLET" in w.text.upper():
                        w.text = tr("wallet_balance").upper()
                        break
                self._wallet_btn.text = "→ " + tr("view_wallet")
            except Exception:
                pass
            self._render_stat_cards()
            self._render_wallet()
            # two-column and schedule need rebuild to update tr titles
            try:
                # rebuild two-column and schedule by clearing and rebuilding those sections
                # quick approach: remove last two sections before footer and rebuild
                if hasattr(self, '_content') and len(self._content.children) >= 4:
                    # _content children are in reverse order of addition (footer last)
                    # rebuild instead of surgically updating labels
                    self._content.clear_widgets()
                    self._build_welcome_banner()
                    self._build_map_card()
                    self._build_stat_cards()
                    self._build_wallet_banner()
                    self._build_two_column()
                    self._build_today_schedule()
                    self._build_footer()
                    # reload data
                    self._load_map()
                    self._load_dashboard()
                    # re-apply compact sizing at current breakpoint (was overwritten by clear_widgets rebuild)
                    try:
                        self._on_window_width(Window, Window.width if hasattr(Window, "width") else 400)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

    def _go_notifications(self, *args):
        if self.manager:
            try:
                self.manager.current = "rider_notifications"
            except Exception:
                pass

    def _go_deliveries(self, *args):
        if self.manager:
            try:
                self.manager.current = "rider_deliveries"
                return
            except Exception:
                pass
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="All deliveries — coming soon").open()
        except Exception:
            pass
        if self.manager:
            # placeholder navigation if rider deliveries screen exists
            try:
                self.manager.current = "rider_home"
            except Exception:
                pass

    def _go_wallet(self, *args):
        if self.manager:
            try:
                self.manager.current = "rider_wallet"
                return
            except Exception:
                pass
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="Wallet — coming soon").open()
        except Exception:
            pass

    def _do_logout(self, *args):
        if self._profile_menu:
            try:
                self._profile_menu.dismiss()
            except Exception:
                pass
        self._do_logout_inner()

    def _logout(self, *args):
        # legacy button compat
        self._do_logout_inner()

    def _do_logout_inner(self):
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
