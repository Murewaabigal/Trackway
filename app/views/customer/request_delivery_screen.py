from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.spinner import MDSpinner

from app.core.theme import PRIMARY, PRIMARY_DARK, DARK, MUTED, BACKGROUND, CARD_BG, ERROR, SUCCESS
from app.i18n.translator import tr
from app.views.base_screen import BaseScreen


class RequestDeliveryScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._pickup_meta = {}
        self._delivery_meta = {}
        self._pickup_clock = None
        self._delivery_clock = None
        self._distance = None
        self._fee = None
        self._loading = False
        self._loading_fare = False
        self._auto_fare_clock = None
        self._last_fare_payload = None
        self._pending_fare_data = None
        self._paystack_modal_visible = False
        self._pending_reference = None
        self._pending_authorization_url = None
        self._paystack_screen = None
        self._paystack_webview = None
        self._loading_paystack = False
        self._pickup_menu = None
        self._delivery_menu = None
        self._profile_menu = None  # not used for this variant header, kept for parity

        self._outer = MDBoxLayout(orientation="vertical")
        self._scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self._content = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp", adaptive_height=True, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        top_nav = self._build_variant_header()
        self._outer.add_widget(top_nav)
        self._outer.add_widget(self._scroll)
        self.add_widget(self._outer)

        self._build_hero()
        self._build_pickup_section()
        self._build_swap_row()
        self._build_delivery_section()
        self._build_parcel_details()
        self._build_distance_preview()
        self._build_submit()
        self._build_trust_row()
        self._build_footer()

        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

    # ---------- 1. Variant Header ----------
    def _build_variant_header(self):
        nav = MDCard(orientation="horizontal", padding="6dp", spacing="6dp", size_hint_x=1, size_hint_y=None, height="48dp", md_bg_color=rgba(CARD_BG), radius=[0], elevation=1)
        logo = MDLabel(text="TRACKWAY / SMART LOGISTICS", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=1, size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5}, valign="middle")
        nav.add_widget(logo)

        right = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=None, width="400dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        # EN dropdown
        try:
            from app.views.shared.language_picker import LanguagePicker
            self.language_picker = LanguagePicker(compact=True)
            self.language_picker.size_hint_x = None
            self.language_picker.width = "36dp"
            right.add_widget(self.language_picker)
        except Exception:
            right.add_widget(MDLabel(text="EN", font_style="Caption", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=None, width="32dp", halign="center"))

        # Pay pill — compact single-line pill matching header button proportions (web parity) — no wrap
        # 160dp + 6.5sp ensures 26-char copy fits in one line without wrapping
        self._pay_pill = MDCard(size_hint=(None, None), size=("160dp", "24dp"), md_bg_color=rgba("#e8f0e3"), radius=[12], elevation=0, line_color=rgba(PRIMARY), line_width=0.8)
        pill_box = MDBoxLayout(orientation="horizontal", spacing="1dp", padding=["3dp", "0dp"], adaptive_height=True, pos_hint={"center_y": 0.5})
        pill_box.add_widget(MDIcon(icon="credit-card-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="10sp", size_hint_x=None, width="14dp"))
        self._pay_label = MDLabel(text=tr("pay_with_card_bank_ussd"), font_style="Caption", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="6.5sp", halign="center", size_hint_x=None, width="130dp", shorten=False, text_size=(None, None))
        pill_box.add_widget(self._pay_label)
        self._pay_pill.add_widget(pill_box)
        right.add_widget(self._pay_pill)

        self._dash_btn = MDFlatButton(text="\u2190 Dashboard", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="12sp", size_hint_x=None, width="90dp", on_release=lambda x: self._go_dashboard())
        right.add_widget(self._dash_btn)

        self._logout_btn = MDFlatButton(text="\u2192 Logout", theme_text_color="Custom", text_color=rgba(ERROR), font_size="12sp", size_hint_x=None, width="80dp", on_release=lambda x: self._do_logout())
        right.add_widget(self._logout_btn)

        nav.add_widget(right)
        self._top_nav = nav
        self._right_cluster = right
        self._on_window_width(Window, Window.width if hasattr(Window, "width") else 400)
        return nav

    def _on_window_width(self, instance, width):
        try:
            # Below 480dp, hide pay pill to stay within 400dp budget
            if hasattr(self, "_pay_pill"):
                if width < 480:
                    self._pay_pill.opacity = 0
                    self._pay_pill.disabled = True
                    self._pay_pill.width = "0dp"
                else:
                    self._pay_pill.opacity = 1
                    self._pay_pill.disabled = False
                    self._pay_pill.width = "160dp"
        except Exception:
            pass

    def _go_dashboard(self, *args):
        if self.manager:
            self.manager.current = "customer_home"

    def _do_logout(self, *args):
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

    # ---------- 2. Hero Banner ----------
    def _build_hero(self):
        self._hero_card = MDCard(orientation="vertical", padding="16dp", spacing="6dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="28dp")
        row.add_widget(MDIcon(icon="truck-delivery-outline", theme_text_color="Custom", text_color="white", size_hint_x=None, width="28dp", font_size="22sp", pos_hint={"center_y": 0.5}))
        self._hero_title = MDLabel(text=tr("request_new_delivery"), font_style="H6", bold=True, theme_text_color="Custom", text_color="white", adaptive_height=True, pos_hint={"center_y": 0.5})
        row.add_widget(self._hero_title)
        self._hero_card.add_widget(row)
        self._hero_sub = MDLabel(text=tr("search_pickup_delivery_subtitle"), font_style="Body2", theme_text_color="Custom", text_color=rgba("#e8f0e3"), adaptive_height=True)
        self._hero_card.add_widget(self._hero_sub)
        self._content.add_widget(self._hero_card)

    # ---------- 3. Pickup ----------
    def _build_pickup_section(self):
        self._pickup_card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        head = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="22dp")
        head.add_widget(MDIcon(icon="map-marker", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="22dp"))
        self._pickup_label = MDLabel(text=tr("pickup_location"), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK)
        head.add_widget(self._pickup_label)
        self._pickup_card.add_widget(head)
        self._pickup_card.add_widget(MDBoxLayout(size_hint_x=1, height="1dp", size_hint_y=None, md_bg_color=rgba(PRIMARY)))
        self.pickup_field = MDTextField(hint_text=tr("search_pickup_placeholder"), mode="rectangle")
        self.pickup_field.bind(text=self._on_pickup_text)
        self.pickup_field.bind(on_touch_down=self._maybe_open_pickup_menu)
        self._pickup_card.add_widget(self.pickup_field)
        self._pickup_error = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        self._pickup_card.add_widget(self._pickup_error)
        self._content.add_widget(self._pickup_card)

    def _on_pickup_text(self, instance, value):
        v = (value or "").strip()
        stored = self._pickup_meta.get("description") or self._pickup_meta.get("address", "") if isinstance(self._pickup_meta, dict) else ""
        if not v:
            self._pickup_meta = {}
            try:
                if self._pickup_menu:
                    self._pickup_menu.dismiss()
            except Exception:
                pass
            if self._pickup_clock:
                try:
                    self._pickup_clock.cancel()
                except Exception:
                    pass
            self._clear_preview()
            self._update_submit_state()
            return
        if stored and v == stored:
            return
        if stored and v != stored:
            self._pickup_meta = {}
            self._clear_preview()
            self._update_submit_state()
        if self._pickup_clock:
            try:
                self._pickup_clock.cancel()
            except Exception:
                pass
        self._pickup_clock = Clock.schedule_once(lambda dt: self._fetch_pickup_places(value), 0.4)

    def _fetch_pickup_places(self, query):
        q = (query or "").strip()
        if len(q) < 2:
            return
        import threading
        def do():
            try:
                from app.services.places_service import autocomplete  # optional
                places = autocomplete(q)
            except Exception:
                places = []
            Clock.schedule_once(lambda dt: self._show_pickup_places(q, places), 0)
        threading.Thread(target=do, daemon=True).start()

    def _show_pickup_places(self, q, places):
        try:
            if not places:
                if q.lower() in ("ike", "ikeja", "lag", "lagos"):
                    places = [{"description": "Ikeja, Lagos, Nigeria", "place_id": "stub_ikeja"}, {"description": "Ikeja GRA, Lagos", "place_id": "stub_ikeja_gra"}]
                elif q.lower() in ("abu", "abuja"):
                    places = [{"description": "Abuja, FCT, Nigeria", "place_id": "stub_abuja"}]
                else:
                    return
            items = []
            for p in places[:5]:
                desc = p.get("description") or p.get("main_text") or ""
                items.append({"text": desc, "viewclass": "OneLineListItem", "on_release": lambda d=desc, m=p: self._select_pickup(d, m)})
            if self._pickup_menu:
                try:
                    self._pickup_menu.dismiss()
                except Exception:
                    pass
            self._pickup_menu = MDDropdownMenu(caller=self.pickup_field, items=items, width_mult=4, max_height="220dp")
            self._pickup_menu.open()
        except Exception:
            pass

    def _maybe_open_pickup_menu(self, instance, touch):
        if instance != self.pickup_field:
            return False
        if instance.collide_point(*touch.pos) and self._pickup_menu:
            try:
                self._pickup_menu.caller = self.pickup_field
                self._pickup_menu.open()
                return True
            except Exception:
                pass
        return False

    def _select_pickup(self, desc, meta):
        if self._pickup_clock:
            try:
                self._pickup_clock.cancel()
            except Exception:
                pass
            self._pickup_clock = None
        self.pickup_field.text = desc
        # Keep address/place_id primary, additionally capture lat/lng for fare
        self._pickup_meta = dict(meta) if isinstance(meta, dict) else {"description": desc}
        self._pickup_meta["description"] = desc
        self._pickup_error.text = ""
        self._pickup_error.height = "0dp"
        try:
            if self._pickup_menu:
                self._pickup_menu.dismiss()
        except Exception:
            pass
        if self._pickup_clock:
            try:
                self._pickup_clock.cancel()
            except Exception:
                pass
            self._pickup_clock = None
        # If lat/lng missing and place_id present, fetch via geocode (unless stub)
        if not self._pickup_meta.get("lat") and self._pickup_meta.get("place_id") and "stub_" not in str(self._pickup_meta.get("place_id")):
            import threading
            pid = self._pickup_meta.get("place_id")
            def do_geo():
                g = None
                try:
                    from app.services.places_service import geocode
                    g = geocode(pid) or geocode(desc)
                except Exception:
                    g = None
                def apply(dt):
                    if g and g.get("lat") is not None:
                        self._pickup_meta["lat"] = g.get("lat")
                        self._pickup_meta["lng"] = g.get("lng")
                        if g.get("city"):
                            self._pickup_meta["city"] = g.get("city")
                    self._schedule_auto_fare()
                Clock.schedule_once(apply, 0)
            threading.Thread(target=do_geo, daemon=True).start()
        else:
            # Stub already has no lat — inject demo lat/lng for auto-fare demo
            if "stub_" in str(self._pickup_meta.get("place_id")) and not self._pickup_meta.get("lat"):
                low = desc.lower()
                if "ikeja" in low:
                    self._pickup_meta["lat"], self._pickup_meta["lng"] = 6.6018, 3.3515
                elif "abuja" in low:
                    self._pickup_meta["lat"], self._pickup_meta["lng"] = 9.0765, 7.3986
                elif "lag" in low:
                    self._pickup_meta["lat"], self._pickup_meta["lng"] = 6.5244, 3.3792
            self._clear_preview()
            self._schedule_auto_fare()

    # ---------- 4. Swap + Delivery ----------
    def _build_swap_row(self):
        row = MDBoxLayout(orientation="horizontal", size_hint_x=1, size_hint_y=None, height="40dp", padding=["0dp", "4dp", "0dp", "4dp"])
        row.add_widget(MDLabel(text=""))
        btn = MDIconButton(icon="arrow-down", theme_icon_color="Custom", icon_color=rgba(PRIMARY), icon_size="20sp", size_hint=(None, None), size=("36dp", "36dp"), pos_hint={"center_y": 0.5}, md_bg_color=rgba(CARD_BG), on_release=lambda x: self._swap_locations())
        # circular via MDCard wrapper
        wrap = MDCard(size_hint=(None, None), size=("36dp", "36dp"), md_bg_color=rgba(CARD_BG), radius=[18], elevation=1, line_color=rgba(PRIMARY), line_width=0.8)
        wrap.add_widget(btn)
        row.add_widget(wrap)
        row.add_widget(MDLabel(text=""))
        self._content.add_widget(row)

    def _swap_locations(self, *args):
        try:
            pt = self.pickup_field.text
            dt = self.delivery_field.text
            self.pickup_field.text = dt
            self.delivery_field.text = pt
            pm = self._pickup_meta
            self._pickup_meta = self._delivery_meta
            self._delivery_meta = pm
            self._clear_preview()
            self._schedule_auto_fare()
        except Exception:
            pass

    def _build_delivery_section(self):
        self._delivery_card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        head = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="22dp")
        head.add_widget(MDIcon(icon="flag-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="22dp"))
        self._delivery_label = MDLabel(text=tr("delivery_location"), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK)
        head.add_widget(self._delivery_label)
        self._delivery_card.add_widget(head)
        self._delivery_card.add_widget(MDBoxLayout(size_hint_x=1, height="1dp", size_hint_y=None, md_bg_color=rgba(PRIMARY)))
        self.delivery_field = MDTextField(hint_text=tr("search_delivery_placeholder"), mode="rectangle")
        self.delivery_field.bind(text=self._on_delivery_text)
        self.delivery_field.bind(on_touch_down=self._maybe_open_delivery_menu)
        self._delivery_card.add_widget(self.delivery_field)
        self._delivery_error = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        self._delivery_card.add_widget(self._delivery_error)
        self._content.add_widget(self._delivery_card)

    def _on_delivery_text(self, instance, value):
        v = (value or "").strip()
        stored = self._delivery_meta.get("description") or self._delivery_meta.get("address", "") if isinstance(self._delivery_meta, dict) else ""
        if not v:
            self._delivery_meta = {}
            try:
                if self._delivery_menu:
                    self._delivery_menu.dismiss()
            except Exception:
                pass
            if self._delivery_clock:
                try:
                    self._delivery_clock.cancel()
                except Exception:
                    pass
            self._clear_preview()
            self._update_submit_state()
            return
        if stored and v == stored:
            return
        if stored and v != stored:
            self._delivery_meta = {}
            self._clear_preview()
            self._update_submit_state()
        if self._delivery_clock:
            try:
                self._delivery_clock.cancel()
            except Exception:
                pass
        self._delivery_clock = Clock.schedule_once(lambda dt: self._fetch_delivery_places(value), 0.4)

    def _fetch_delivery_places(self, query):
        q = (query or "").strip()
        if len(q) < 2:
            return
        import threading
        def do():
            try:
                from app.services.places_service import autocomplete
                places = autocomplete(q)
            except Exception:
                places = []
            Clock.schedule_once(lambda dt: self._show_delivery_places(q, places), 0)
        threading.Thread(target=do, daemon=True).start()

    def _show_delivery_places(self, q, places):
        try:
            if not places:
                if q.lower() in ("abu", "abuja"):
                    places = [{"description": "Abuja, FCT, Nigeria", "place_id": "stub_abuja"}]
                elif q.lower() in ("ike", "ikeja"):
                    places = [{"description": "Ikeja, Lagos, Nigeria", "place_id": "stub_ikeja"}]
                else:
                    return
            items = []
            for p in places[:5]:
                desc = p.get("description") or ""
                items.append({"text": desc, "viewclass": "OneLineListItem", "on_release": lambda d=desc, m=p: self._select_delivery(d, m)})
            if self._delivery_menu:
                try:
                    self._delivery_menu.dismiss()
                except Exception:
                    pass
            self._delivery_menu = MDDropdownMenu(caller=self.delivery_field, items=items, width_mult=4, max_height="220dp")
            self._delivery_menu.open()
        except Exception:
            pass

    def _maybe_open_delivery_menu(self, instance, touch):
        if instance != self.delivery_field:
            return False
        if instance.collide_point(*touch.pos) and self._delivery_menu:
            try:
                self._delivery_menu.caller = self.delivery_field
                self._delivery_menu.open()
                return True
            except Exception:
                pass
        return False

    def _select_delivery(self, desc, meta):
        if self._delivery_clock:
            try:
                self._delivery_clock.cancel()
            except Exception:
                pass
            self._delivery_clock = None
        self.delivery_field.text = desc
        self._delivery_meta = dict(meta) if isinstance(meta, dict) else {"description": desc}
        self._delivery_meta["description"] = desc
        self._delivery_error.text = ""
        self._delivery_error.height = "0dp"
        try:
            if self._delivery_menu:
                self._delivery_menu.dismiss()
        except Exception:
            pass
        if self._delivery_clock:
            try:
                self._delivery_clock.cancel()
            except Exception:
                pass
            self._delivery_clock = None
        if not self._delivery_meta.get("lat") and self._delivery_meta.get("place_id") and "stub_" not in str(self._delivery_meta.get("place_id")):
            import threading
            pid = self._delivery_meta.get("place_id")
            def do_geo():
                g = None
                try:
                    from app.services.places_service import geocode
                    g = geocode(pid) or geocode(desc)
                except Exception:
                    g = None
                def apply(dt):
                    if g and g.get("lat") is not None:
                        self._delivery_meta["lat"] = g.get("lat")
                        self._delivery_meta["lng"] = g.get("lng")
                        if g.get("city"):
                            self._delivery_meta["city"] = g.get("city")
                    self._schedule_auto_fare()
                Clock.schedule_once(apply, 0)
            threading.Thread(target=do_geo, daemon=True).start()
        else:
            if "stub_" in str(self._delivery_meta.get("place_id")) and not self._delivery_meta.get("lat"):
                low = desc.lower()
                if "abuja" in low:
                    self._delivery_meta["lat"], self._delivery_meta["lng"] = 9.0765, 7.3986
                elif "ikeja" in low:
                    self._delivery_meta["lat"], self._delivery_meta["lng"] = 6.6018, 3.3515
                elif "lag" in low:
                    self._delivery_meta["lat"], self._delivery_meta["lng"] = 6.5244, 3.3792
            self._clear_preview()
            self._schedule_auto_fare()

    # ---------- 5. Parcel Details ----------
    def _build_parcel_details(self):
        self._parcel_card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        head = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="22dp")
        self._parcel_icon = MDIcon(icon="package-variant", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="18sp", size_hint_x=None, width="22dp")
        head.add_widget(self._parcel_icon)
        self._parcel_label = MDLabel(text=tr("parcel_details"), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK)
        head.add_widget(self._parcel_label)
        self._parcel_card.add_widget(head)
        self._desc_label = MDLabel(text=tr("description_optional"), font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp")
        self._parcel_card.add_widget(self._desc_label)
        self.desc_field = MDTextField(hint_text=tr("describe_sending_placeholder"), mode="rectangle", multiline=True, size_hint_y=None, height="70dp")
        self._parcel_card.add_widget(self.desc_field)
        self._value_label = MDLabel(text=tr("parcel_value_label"), font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp")
        self._parcel_card.add_widget(self._value_label)
        self.value_field = MDTextField(hint_text="0", mode="rectangle", input_filter="float", helper_text=tr("parcel_value_helper"), helper_text_mode="on_focus")
        self._parcel_card.add_widget(self.value_field)
        self._instr_label = MDLabel(text=tr("special_instructions"), font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp")
        self._parcel_card.add_widget(self._instr_label)
        self.instr_field = MDTextField(hint_text=tr("gate_code_placeholder"), mode="rectangle", multiline=True, size_hint_y=None, height="70dp")
        self._parcel_card.add_widget(self.instr_field)
        self._content.add_widget(self._parcel_card)

    # ---------- Preview (green fare card — distance-only breakdown, no duration) ----------
    def _build_distance_preview(self):
        self._preview_card = MDCard(orientation="vertical", padding="16dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        self._preview_distance = MDLabel(text="", font_style="Body2", theme_text_color="Custom", text_color="white", adaptive_height=True, halign="center")
        self._preview_fee = MDLabel(text="", font_style="H6", bold=True, theme_text_color="Custom", text_color="white", font_size="22sp", adaptive_height=True, halign="center")
        self._preview_breakdown = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), adaptive_height=True, halign="center")
        self._preview_referral = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="10sp", adaptive_height=True, halign="center")
        self._preview_card.add_widget(self._preview_distance)
        self._preview_card.add_widget(self._preview_fee)
        self._preview_card.add_widget(self._preview_breakdown)
        self._preview_card.add_widget(self._preview_referral)
        self._preview_card.opacity = 0
        self._preview_card.height = "0dp"
        self._preview_card.size_hint_y = None
        self._content.add_widget(self._preview_card)

    def _show_preview(self, dist, fee):
        # Legacy helper kept for manual calls — delegates to auto-fare display
        try:
            data = {"distance_text": dist, "formatted_fee": fee, "distance_km": dist.replace(" km","") if isinstance(dist,str) else dist, "breakdown_text": "", "formatted_balance": "", "formatted_max_discount": ""}
            self._apply_auto_fare_preview(data)
        except Exception:
            pass

    def _apply_auto_fare_preview(self, data):
        try:
            distance_text = data.get("distance_text") or (f"{data.get('distance_km')} km" if data.get("distance_km") else "")
            fee = data.get("formatted_fee") or data.get("fee") or (f"₦{data.get('delivery_fee')}" if data.get("delivery_fee") else "")
            breakdown = data.get("breakdown_text") or data.get("breakdown") or ""
            bal = data.get("formatted_balance") or ""
            disc = data.get("formatted_max_discount") or ""
            self._preview_distance.text = distance_text
            self._preview_fee.text = fee
            self._preview_breakdown.text = breakdown
            ref_text = ""
            try:
                b_val = float(str(data.get("referral_balance") or 0))
            except Exception:
                b_val = 0
            try:
                d_val = float(str(data.get("max_referral_discount") or 0))
            except Exception:
                d_val = 0
            if b_val != 0 or d_val != 0:
                if bal and disc:
                    ref_text = f"Balance {bal} • Max discount {disc}"
                elif bal:
                    ref_text = f"Balance {bal}"
                elif disc:
                    ref_text = f"Max discount {disc}"
            self._preview_referral.text = ref_text
            has_breakdown = bool(breakdown)
            has_ref = bool(ref_text)
            if has_breakdown and has_ref:
                self._preview_card.height = "108dp"
            elif has_breakdown or has_ref:
                self._preview_card.height = "88dp"
            else:
                self._preview_card.height = "64dp"
            self._preview_card.opacity = 1
            self._preview_card.size_hint_y = None
            # keep distance/fee for legacy
            try:
                self._distance = str(data.get("distance_km") or distance_text)
                self._fee = str(data.get("delivery_fee") or fee)
            except Exception:
                pass
        except Exception:
            pass

    def _clear_preview(self):
        try:
            self._distance = None
            self._fee = None
            self._preview_distance.text = ""
            self._preview_fee.text = ""
            try:
                self._preview_breakdown.text = ""
                self._preview_referral.text = ""
            except Exception:
                pass
            self._preview_card.opacity = 0
            self._preview_card.height = "0dp"
            # cancel pending auto-fare
            try:
                if self._auto_fare_clock:
                    self._auto_fare_clock.cancel()
                    self._auto_fare_clock = None
            except Exception:
                pass
        except Exception:
            pass

    # ---------- Auto-fare (strict 4-field, delivery_* naming) ----------
    def _schedule_auto_fare(self, *args):
        try:
            if self._auto_fare_clock:
                try:
                    self._auto_fare_clock.cancel()
                except Exception:
                    pass
                self._auto_fare_clock = None
            # Ready only when both have lat/lng (extracted from already-selected Google Places)
            plat = self._pickup_meta.get("lat")
            plng = self._pickup_meta.get("lng")
            dlat = self._delivery_meta.get("lat")
            dlng = self._delivery_meta.get("lng")
            # Try fallback: if meta has no lat/lng but has geometry, extract
            if plat is None:
                plat = (self._pickup_meta.get("geometry") or {}).get("location", {}).get("lat")
            if plng is None:
                plng = (self._pickup_meta.get("geometry") or {}).get("location", {}).get("lng")
            if dlat is None:
                dlat = (self._delivery_meta.get("geometry") or {}).get("location", {}).get("lat")
            if dlng is None:
                dlng = (self._delivery_meta.get("geometry") or {}).get("location", {}).get("lng")
            if not plat or not plng or not dlat or not dlng:
                # Not ready — hide preview (lat/lng not yet captured)
                # Don't show error here; validation handles missing selection on tap
                try:
                    self._preview_card.opacity = 0
                    self._preview_card.height = "0dp"
                except Exception:
                    pass
                return
            payload = {
                "pickup_lat": str(plat),
                "pickup_lng": str(plng),
                "delivery_lat": str(dlat),
                "delivery_lng": str(dlng),
            }
            # Dedup
            if payload == self._last_fare_payload:
                return
            self._auto_fare_clock = Clock.schedule_once(lambda dt: self._do_auto_fare(payload), 0.6)
        except Exception:
            pass

    def _do_auto_fare(self, payload):
        try:
            self._loading_fare = True
            try:
                self._preview_distance.text = "Calculating fare..."
                self._preview_fee.text = ""
                self._preview_breakdown.text = ""
                self._preview_referral.text = ""
                self._preview_card.opacity = 1
                self._preview_card.height = "72dp"
                self._preview_card.size_hint_y = None
            except Exception:
                pass
            try:
                self._submit_spinner.active = True
            except Exception:
                pass
            import threading
            def do():
                try:
                    from app.services.customer_service import calculate_distance
                    result = calculate_distance(payload)
                except Exception as e:
                    result = {"ok": False, "error": str(e), "data": None}
                Clock.schedule_once(lambda dt: self._apply_auto_fare(result, payload), 0)
            threading.Thread(target=do, daemon=True).start()
        except Exception:
            pass

    def _apply_auto_fare(self, result, payload):
        try:
            self._loading_fare = False
            try:
                self._submit_spinner.active = False
            except Exception:
                pass
            if not result.get("ok"):
                err = result.get("error") or "Could not calculate fare"
                self._preview_distance.text = err
                self._preview_fee.text = ""
                self._preview_breakdown.text = ""
                self._preview_referral.text = ""
                self._preview_card.height = "48dp"
                self._preview_card.opacity = 1
                return
            data = result.get("data") or {}
            # Success shape: {status: success, data: {distance_km, distance_text, delivery_fee, formatted_fee, breakdown_text, ...}}
            # Unwrap if nested
            if isinstance(data, dict) and data.get("data"):
                inner = data.get("data")
                if isinstance(inner, dict) and "distance_km" in inner:
                    data = inner
            self._pending_fare_data = dict(data)
            self._last_fare_payload = dict(payload)
            self._apply_auto_fare_preview(data)
        except Exception:
            try:
                self._submit_spinner.active = False
            except Exception:
                pass
            self._loading_fare = False

    # ---------- 6. Submit ----------
    def _build_submit(self):
        # Web parity: PRIMARY green with opacity 0.5 when disabled (form incomplete), full opacity when enabled.
        # Keep full-width (size_hint_x=1) inside padded content — matches web muted sage via disabled state.
        # KivyMD tints disabled buttons grey; we lock md_bg_color to PRIMARY and use opacity for fade.
        self._submit_btn = MDRaisedButton(text=tr("proceed_to_payment"), md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=1, size_hint_y=None, height="48dp", on_release=lambda x: self._on_submit())
        self._submit_btn.text = "\U0001f4b3 " + tr("proceed_to_payment")
        self._submit_btn.disabled = True
        self._submit_btn.opacity = 0.5
        # Lock green even when KivyMD tries to grey out disabled state
        try:
            self._submit_btn.md_bg_color = rgba(PRIMARY)
            Clock.schedule_once(lambda dt: setattr(self._submit_btn, "md_bg_color", rgba(PRIMARY)), 0)
        except Exception:
            pass
        self._content.add_widget(self._submit_btn)
        self._submit_spinner = MDSpinner(size_hint=(None, None), size=("28dp", "28dp"), active=False, color=rgba(PRIMARY), pos_hint={"center_x": 0.5})
        self._content.add_widget(self._submit_spinner)
        self._submit_error = MDLabel(text="", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        self._content.add_widget(self._submit_error)
        # Bind location fields to toggle disabled/opacity (deferred — fields already exist)
        try:
            if hasattr(self, "pickup_field"):
                self.pickup_field.bind(text=self._update_submit_state)
            if hasattr(self, "delivery_field"):
                self.delivery_field.bind(text=self._update_submit_state)
            self._update_submit_state()
        except Exception:
            pass

    def _update_submit_state(self, *args):
        # Enable only when both locations filled; disabled shows 0.5 opacity (faded green per DevTools)
        # KivyMD greys disabled MDRaisedButton via theme — re-lock to PRIMARY after setting disabled
        try:
            if getattr(self, "_loading", False):
                self._submit_btn.disabled = True
                self._submit_btn.opacity = 0.5
                self._submit_btn.md_bg_color = rgba(PRIMARY)
                Clock.schedule_once(lambda dt: setattr(self._submit_btn, "md_bg_color", rgba(PRIMARY)), 0)
                return
            pickup = self.pickup_field.text.strip() if hasattr(self, "pickup_field") else ""
            delivery = self.delivery_field.text.strip() if hasattr(self, "delivery_field") else ""
            ready = bool(pickup and delivery)
            self._submit_btn.disabled = not ready
            self._submit_btn.opacity = 1 if ready else 0.5
            self._submit_btn.md_bg_color = rgba(PRIMARY)
            # Defer re-lock to beat KivyMD's internal disabled tint (which runs on next frame)
            Clock.schedule_once(lambda dt: setattr(self._submit_btn, "md_bg_color", rgba(PRIMARY)), 0)
        except Exception:
            pass

    def _on_submit(self, *args):
        if self._loading:
            return
        pickup = self.pickup_field.text.strip()
        delivery = self.delivery_field.text.strip()
        has_err = False
        if not pickup:
            self._pickup_error.text = tr("validation_complaint_type") if "pickup" in tr("validation_complaint_type").lower() else "Pickup location is required"
            # reuse generic required message
            self._pickup_error.text = "Pickup location is required"
            self._pickup_error.height = "18dp"
            has_err = True
        else:
            self._pickup_error.text = ""
            self._pickup_error.height = "0dp"
        if not delivery:
            self._delivery_error.text = "Delivery location is required"
            self._delivery_error.height = "18dp"
            has_err = True
        else:
            self._delivery_error.text = ""
            self._delivery_error.height = "0dp"
        # Validate value numeric
        val_raw = self.value_field.text.strip()
        if val_raw:
            try:
                float(val_raw)
            except Exception:
                self._submit_error.text = "Parcel value must be a number"
                self._submit_error.height = "18dp"
                has_err = True
            else:
                self._submit_error.text = ""
                self._submit_error.height = "0dp"
        else:
            self._submit_error.text = ""
            self._submit_error.height = "0dp"
        if has_err:
            return

        # Step 1: calculate distance/fee — reuse auto-fare pending data if same lat/lng, else strict 4-field lat/lng
        # If auto-fare already fetched for same coordinates, skip network and use cached preview
        try:
            cur_plat = self._pickup_meta.get("lat")
            cur_plng = self._pickup_meta.get("lng")
            cur_dlat = self._delivery_meta.get("lat")
            cur_dlng = self._delivery_meta.get("lng")
            cached_payload = self._last_fare_payload
            cur_payload = {"pickup_lat": str(cur_plat) if cur_plat else "", "pickup_lng": str(cur_plng) if cur_plng else "", "delivery_lat": str(cur_dlat) if cur_dlat else "", "delivery_lng": str(cur_dlng) if cur_dlng else ""}
            if self._pending_fare_data and cached_payload == cur_payload and cur_plat and cur_plng and cur_dlat and cur_dlng:
                # Reuse cached fare — build minimal delivery payload for final request_delivery (address/place_id unchanged)
                cached_data = self._pending_fare_data
                # Ensure preview visible
                try:
                    self._apply_auto_fare_preview(cached_data)
                except Exception:
                    pass
                # Prepare exact 12-field payload as DevTools capture (address+city+lat/lng + parcel + distance/fee + referral)
                try:
                    dist_km = cached_data.get("distance_km") if isinstance(cached_data, dict) else ""
                    fee_val = cached_data.get("delivery_fee") if isinstance(cached_data, dict) else ""
                except Exception:
                    dist_km, fee_val = "", ""
                final_payload = {
                    "pickup_address": self._pickup_meta.get("address") or pickup,
                    "pickup_city": self._pickup_meta.get("city") or "",
                    "pickup_lat": str(self._pickup_meta.get("lat") or ""),
                    "pickup_lng": str(self._pickup_meta.get("lng") or ""),
                    "delivery_address": self._delivery_meta.get("address") or delivery,
                    "delivery_city": self._delivery_meta.get("city") or "",
                    "delivery_lat": str(self._delivery_meta.get("lat") or ""),
                    "delivery_lng": str(self._delivery_meta.get("lng") or ""),
                    "parcel_description": self.desc_field.text.strip() or "",
                    "parcel_value": val_raw or "0",
                    "special_instructions": self.instr_field.text.strip() or "",
                    "distance_km": str(dist_km),
                    "delivery_fee": str(fee_val),
                    "referral_discount": "0",
                    "use_referral_balance": "false",
                }
                # Clean empty strings for optional? Keep required 0/false as placeholder
                final_payload = {k: v for k, v in final_payload.items() if v is not None}
                # Show payment dialog with cached fare
                fee_str = cached_data.get("formatted_fee") or str(cached_data.get("delivery_fee") or "")
                dist_str = cached_data.get("distance_text") or str(cached_data.get("distance_km") or "")
                self._show_payment_dialog(final_payload, dist_str, fee_str)
                return
        except Exception:
            pass

        self._loading = True
        self._submit_btn.disabled = True
        self._submit_btn.opacity = 0.5
        try:
            self._submit_btn.md_bg_color = rgba(PRIMARY)
            Clock.schedule_once(lambda dt: setattr(self._submit_btn, "md_bg_color", rgba(PRIMARY)), 0)
        except Exception:
            pass
        self._submit_spinner.active = True
        self._submit_error.text = ""
        self._submit_error.height = "0dp"

        def do_calc(dt):
            # Prefer lat/lng strict 4-field if available (same as auto-fare), fallback to address
            if self._pickup_meta.get("lat") and self._delivery_meta.get("lat"):
                payload = {
                    "pickup_lat": str(self._pickup_meta.get("lat")),
                    "pickup_lng": str(self._pickup_meta.get("lng")),
                    "delivery_lat": str(self._delivery_meta.get("lat")),
                    "delivery_lng": str(self._delivery_meta.get("lng")),
                }
            else:
                payload = {
                    "pickup_address": pickup,
                    "delivery_address": delivery,
                    "description": self.desc_field.text.strip() or None,
                    "parcel_value": val_raw or "0",
                    "special_instructions": self.instr_field.text.strip() or None,
                }
                payload = {k: v for k, v in payload.items() if v is not None}
                if self._pickup_meta.get("place_id"):
                    payload["pickup_place_id"] = self._pickup_meta.get("place_id")
                if self._delivery_meta.get("place_id"):
                    payload["delivery_place_id"] = self._delivery_meta.get("place_id")
            try:
                from app.services.customer_service import calculate_distance
                result = calculate_distance(payload)
                self._submit_spinner.active = False
                self._loading = False
                self._update_submit_state()
                if result.get("ok"):
                    data = result.get("data") or {}
                    # If response is already pre-formatted (delivery_fee/formatted_fee) use directly
                    if "delivery_fee" in data or "formatted_fee" in data:
                        # cache for payment
                        try:
                            if isinstance(data, dict) and data.get("data"):
                                inner = data.get("data")
                                if isinstance(inner, dict) and "delivery_fee" in inner:
                                    data = inner
                        except Exception:
                            pass
                        self._pending_fare_data = dict(data)
                        self._last_fare_payload = dict(payload) if "pickup_lat" in payload else None
                        self._apply_auto_fare_preview(data)
                        # Build exact 15-field payload as DevTools capture
                        try:
                            dk = data.get("distance_km") or ""
                            fv = data.get("delivery_fee") or ""
                        except Exception:
                            dk, fv = "", ""
                        final_payload = {
                            "pickup_address": self._pickup_meta.get("address") or pickup,
                            "pickup_city": self._pickup_meta.get("city") or "",
                            "pickup_lat": str(self._pickup_meta.get("lat") or ""),
                            "pickup_lng": str(self._pickup_meta.get("lng") or ""),
                            "delivery_address": self._delivery_meta.get("address") or delivery,
                            "delivery_city": self._delivery_meta.get("city") or "",
                            "delivery_lat": str(self._delivery_meta.get("lat") or ""),
                            "delivery_lng": str(self._delivery_meta.get("lng") or ""),
                            "parcel_description": self.desc_field.text.strip() or "",
                            "parcel_value": val_raw or "0",
                            "special_instructions": self.instr_field.text.strip() or "",
                            "distance_km": str(dk),
                            "delivery_fee": str(fv),
                            "referral_discount": "0",
                            "use_referral_balance": "false",
                        }
                        final_payload = {k: v for k, v in final_payload.items() if v is not None}
                        fee = data.get("formatted_fee") or str(data.get("delivery_fee") or "")
                        dist = data.get("distance_text") or str(data.get("distance_km") or "")
                        self._show_payment_dialog(final_payload, dist, fee)
                        return
                    dist = data.get("distance") or data.get("distance_km") or data.get("distanceKm") or "0"
                    fee = data.get("fee") or data.get("price") or data.get("amount") or data.get("total_fee") or "0"
                    # Format
                    try:
                        dist_f = float(str(dist).replace(",", "").replace("km","").strip() or 0)
                        dist_str = f"{dist_f:.1f}"
                    except Exception:
                        dist_str = str(dist)
                    try:
                        fee_f = float(str(fee).replace(",", "").replace("\u20a6","").replace("N","").strip() or 0)
                        fee_str = f"\u20a6{fee_f:,.2f}"
                    except Exception:
                        fee_str = str(fee)
                    self._show_preview(dist_str, fee_str)
                    # Step 2: payment choice stub
                    self._show_payment_dialog(payload, dist_str, fee_str)
                else:
                    err = result.get("error") or tr("error")
                    if "Session expired" in str(err):
                        from app.core import session
                        session.clear_session()
                        if self.manager:
                            self.manager.current = "customer_login"
                        return
                    self._submit_error.text = err
                    self._submit_error.height = "28dp"
                    try:
                        from kivymd.uix.snackbar import Snackbar
                        Snackbar(text=err).open()
                    except Exception:
                        pass
            except Exception as e:
                self._submit_spinner.active = False
                self._loading = False
                self._update_submit_state()
                self._submit_error.text = str(e)
                self._submit_error.height = "28dp"

        Clock.schedule_once(do_calc, 0.1)

    def _show_payment_dialog(self, payload, dist, fee):
        # Directly initialize Paystack hosted checkout (WebView full-screen) — no recreation of Card/Transfer/Bank/USSD tabs
        self._do_request_delivery(payload, "paystack")

    # ---------- Paystack WebView full-screen modal (4 tabs inside Paystack, baked attribution) ----------
    def _open_paystack_modal(self, authorization_url, reference):
        try:
            self._pending_reference = reference
            self._pending_authorization_url = authorization_url
            self._paystack_modal_visible = True
            try:
                Window.bind(on_keyboard=self._on_keyboard)
            except Exception:
                pass
            # Try garden WebView, fallback to simple modal with link
            webview = None
            try:
                from kivy_garden.webview import WebView as GardenWebView
                webview = GardenWebView(url=authorization_url, size_hint=(1, 1))
            except Exception:
                try:
                    from kivy.uix.label import Label
                    webview = Label(text=f"Paystack Checkout\n{authorization_url}\n\nClose with × or Back", halign="center")
                except Exception:
                    webview = None
            self._paystack_webview = webview
            # Build full-screen dark backdrop modal
            from kivymd.uix.card import MDCard as _MDCard
            from kivy.uix.modalview import ModalView
            from kivymd.uix.boxlayout import MDBoxLayout as _Box
            from kivymd.uix.button import MDIconButton as _IconBtn
            from kivymd.uix.label import MDLabel as _Lbl
            modal = ModalView(size_hint=(1, 1), background_color=[0, 0, 0, 0.6], auto_dismiss=False)
            root = _MDCard(orientation="vertical", size_hint=(0.95, 0.9), pos_hint={"center_x": 0.5, "center_y": 0.5}, radius=[14], elevation=8, md_bg_color=rgba(CARD_BG), padding="6dp", spacing="6dp")
            top = _Box(orientation="horizontal", size_hint_y=None, height="48dp", spacing="6dp")
            top.add_widget(_Lbl(text="Secure Checkout — Paystack", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, halign="left"))
            close_btn = _IconBtn(icon="close", theme_icon_color="Custom", icon_color=rgba(MUTED), on_release=lambda x: self._dismiss_paystack_modal())
            top.add_widget(close_btn)
            root.add_widget(top)
            # WebView container
            container = _Box(orientation="vertical", size_hint=(1, 1))
            if webview:
                container.add_widget(webview)
            # Wrap url detection for verification (if WebView supports on_url)
            try:
                if hasattr(webview, "bind"):
                    webview.bind(on_url=lambda inst, url: self._handle_paystack_url(url))
            except Exception:
                pass
            root.add_widget(container)
            modal.add_widget(root)
            self._paystack_screen = modal
            modal.open()
        except Exception as e:
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text=f"Could not open Paystack: {e}").open()
            except Exception:
                pass
            self._paystack_modal_visible = False

    def _handle_paystack_url(self, url):
        try:
            if url and ("callback" in url or "reference=" in url or "trxref" in url or "paystack" in url and "success" in url):
                # Extract reference
                import re
                m = re.search(r"reference=([^&]+)", url) or re.search(r"trxref=([^&]+)", url)
                ref = m.group(1) if m else self._pending_reference
                self._dismiss_paystack_modal(save_pending=False)
                if ref:
                    self._verify_paystack_reference(ref)
        except Exception:
            pass

    def _verify_paystack_reference(self, reference):
        try:
            self._loading = True
            self._submit_spinner.active = True
            def do_verify(dt):
                try:
                    from app.services.customer_service import verify_payment
                    result = verify_payment(reference)
                    self._submit_spinner.active = False
                    self._loading = False
                    self._update_submit_state()
                    if result.get("ok"):
                        data = result.get("data") or {}
                        wb = data.get("waybill_number") or data.get("waybill") or data.get("tracking_number") or reference
                        msg = f"Waybill {wb} created" if wb else "Payment verified"
                        try:
                            from kivymd.uix.snackbar import Snackbar
                            Snackbar(text=msg).open()
                        except Exception:
                            pass
                        if wb and self.manager:
                            try:
                                detail = self.manager.get_screen("waybill_detail")
                                if hasattr(detail, "set_waybill"):
                                    detail.set_waybill({"waybill_number": wb, **data})
                                self.manager.current = "waybill_detail"
                            except Exception:
                                self.manager.current = "customer_history"
                    else:
                        err = result.get("error") or "Verification failed"
                        self._submit_error.text = err
                        self._submit_error.height = "28dp"
                except Exception as e:
                    self._submit_spinner.active = False
                    self._loading = False
                    self._update_submit_state()
                    self._submit_error.text = str(e)
                    self._submit_error.height = "28dp"
            Clock.schedule_once(do_verify, 0.1)
        except Exception:
            pass

    def _dismiss_paystack_modal(self, save_pending=True, *args):
        try:
            # Distinguish pre-load (no real reference) vs loaded checkout
            has_real = bool(self._pending_reference and self._pending_authorization_url)
            if not has_real:
                # clean silent return — hide spinner immediately, no Pending Payment stub
                try:
                    self._submit_spinner.active = False
                    self._preview_card.opacity = 0 if not self._pending_fare_data else 1
                except Exception:
                    pass
                self._loading = False
                self._loading_paystack = False
                self._paystack_modal_visible = False
                try:
                    if self._paystack_screen:
                        self._paystack_screen.dismiss()
                        self._paystack_screen = None
                except Exception:
                    pass
                try:
                    Window.unbind(on_keyboard=self._on_keyboard)
                except Exception:
                    pass
                self._paystack_webview = None
                return
            # already-loaded checkout → save Pending Payment with real reference
            self._paystack_modal_visible = False
            try:
                if self._paystack_screen:
                    self._paystack_screen.dismiss()
                    self._paystack_screen = None
            except Exception:
                pass
            try:
                Window.unbind(on_keyboard=self._on_keyboard)
            except Exception:
                pass
            # keep _pending_reference for Recent Deliveries
            try:
                from kivymd.uix.snackbar import Snackbar
                # No extra Snackbar — card itself is affordance (silent clean per your gate would also skip here, but pending is already saved)
                pass
            except Exception:
                pass
            # Optionally render pending card on dashboard — handled via status_counts Pending Payment pill
            Clock.schedule_once(lambda dt: self._update_submit_state(), 0)
        except Exception:
            pass

    def _on_keyboard(self, window, key, scancode, codepoint, modifier):
        if self._paystack_modal_visible and key in (27, 1001):
            # Consume even if WebView can_go_back() — dismiss → Pending/Clean as above, don't navigate Paystack history
            self._dismiss_paystack_modal()
            return True
        return False

    def _do_request_delivery(self, payload, method):
        # Delivery request-ride.php must NOT include payment_method per capture; keep exact 15-field payload as built in _on_submit
        try:
            if hasattr(self, "_pay_dialog") and self._pay_dialog:
                try:
                    self._pay_dialog.dismiss()
                except Exception:
                    pass
        except Exception:
            pass
        payload_with_pay = dict(payload)
        # Do NOT add payment_method — not in captured request-delivery.php payload
        self._loading = True
        self._loading_paystack = True
        self._submit_btn.disabled = True
        self._submit_btn.opacity = 0.5
        try:
            self._submit_btn.md_bg_color = rgba(PRIMARY)
            Clock.schedule_once(lambda dt: setattr(self._submit_btn, "md_bg_color", rgba(PRIMARY)), 0)
        except Exception:
            pass
        self._submit_spinner.active = True
        # Ensure spinner hidden immediately if dismissed pre-load (clean return)
        def do_req(dt):
            try:
                from app.services.customer_service import request_delivery
                result = request_delivery(payload_with_pay)
                self._submit_spinner.active = False
                self._loading = False
                self._loading_paystack = False
                self._update_submit_state()
                if result.get("ok"):
                    data = result.get("data") or {}
                    # Paystack hosted checkout — backend returns authorization_url + reference
                    auth_url = data.get("authorization_url") or data.get("authorizationUrl") or data.get("paystack_url") or data.get("url") or ""
                    ref = data.get("reference") or data.get("paystack_reference") or data.get("trxref") or data.get("access_code") or ""
                    if auth_url:
                        # Open full-screen WebView (4 tabs inside Paystack, baked attribution)
                        self._open_paystack_modal(auth_url, ref or data.get("waybill_number") or "")
                        return
                    wb = data.get("waybill_number") or data.get("waybill") or data.get("tracking_number") or ""
                    msg = f"Waybill {wb} created" if wb else "Delivery requested"
                    try:
                        from kivymd.uix.snackbar import Snackbar
                        Snackbar(text=msg).open()
                    except Exception:
                        pass
                    # Clear form
                    self.pickup_field.text = ""
                    self.delivery_field.text = ""
                    self.desc_field.text = ""
                    self.value_field.text = ""
                    self.instr_field.text = ""
                    self._pickup_meta = {}
                    self._delivery_meta = {}
                    self._clear_preview()
                    # Optionally go to history
                    if wb and self.manager:
                        try:
                            detail = self.manager.get_screen("waybill_detail")
                            if hasattr(detail, "set_waybill"):
                                detail.set_waybill({"waybill_number": wb, **data})
                            self.manager.current = "waybill_detail"
                        except Exception:
                            self.manager.current = "customer_history"
                else:
                    err = result.get("error") or tr("error")
                    self._submit_error.text = err
                    self._submit_error.height = "28dp"
                    try:
                        from kivymd.uix.snackbar import Snackbar
                        Snackbar(text=err).open()
                    except Exception:
                        pass
            except Exception as e:
                self._submit_spinner.active = False
                self._loading = False
                self._loading_paystack = False
                self._update_submit_state()
                self._submit_error.text = str(e)
                self._submit_error.height = "28dp"
        Clock.schedule_once(do_req, 0.1)

    # ---------- 7. Trust Row ----------
    def _build_trust_row(self):
        row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="102dp")
        # Fair pricing — verbatim duplicate title+subtitle per web screenshot
        c1 = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="96dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        c1.add_widget(MDIcon(icon="alert-outline", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="20sp", size_hint_y=None, height="24dp"))
        self._fair_title = MDLabel(text=tr("fair_pricing"), font_style="Caption", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True)
        c1.add_widget(self._fair_title)
        self._fair_sub = MDLabel(text=tr("fair_pricing"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, font_size="10sp", adaptive_height=True)
        c1.add_widget(self._fair_sub)
        row.add_widget(c1)
        # Secure Payment
        c2 = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="96dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        c2.add_widget(MDIcon(icon="lock-outline", halign="center", theme_text_color="Custom", text_color=rgba(SUCCESS), font_size="20sp", size_hint_y=None, height="24dp"))
        self._secure_title = MDLabel(text=tr("secure_payment"), font_style="Caption", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True)
        c2.add_widget(self._secure_title)
        self._secure_sub = MDLabel(text=tr("secure_payment_sub"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, font_size="10sp", adaptive_height=True)
        c2.add_widget(self._secure_sub)
        row.add_widget(c2)
        # Track live — verbatim duplicate title+subtitle per web screenshot
        c3 = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="96dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        c3.add_widget(MDIcon(icon="clock-outline", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="20sp", size_hint_y=None, height="24dp"))
        self._track_title = MDLabel(text=tr("track_live"), font_style="Caption", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True)
        c3.add_widget(self._track_title)
        self._track_sub = MDLabel(text=tr("track_live"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, font_size="10sp", adaptive_height=True)
        c3.add_widget(self._track_sub)
        row.add_widget(c3)
        self._content.add_widget(row)

    # ---------- 8. Footer ----------
    def _build_footer(self):
        card = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="56dp", md_bg_color=rgba(DARK), radius=[0], elevation=0)
        card.add_widget(MDLabel(text="\u00a9 2026 Trackway Logistics. Trackway Smart Logistics. All rights reserved.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        card.add_widget(MDLabel(text="Delivering Excellence, One Parcel at a Time.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        self._footer_card = card
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
        self._clear_preview()
        self._submit_error.text = ""
        self._submit_error.height = "0dp"
        try:
            self._on_window_width(Window, Window.width if hasattr(Window, "width") else 400)
        except Exception:
            pass
        try:
            # Force PRIMARY green like Pickup (map-marker) / Delivery (flag-outline) — prevent default multi-color fallback
            if hasattr(self, "_parcel_icon"):
                self._parcel_icon.text_color = rgba(PRIMARY)
                self._parcel_icon.theme_text_color = "Custom"
        except Exception:
            pass
        try:
            self._update_submit_state()
        except Exception:
            pass

    def rebuild_ui(self):
        try:
            self._hero_title.text = tr("request_new_delivery")
            self._hero_sub.text = tr("search_pickup_delivery_subtitle")
            self._pay_label.text = tr("pay_with_card_bank_ussd")
            self._pickup_label.text = tr("pickup_location")
            self.pickup_field.hint_text = tr("search_pickup_placeholder")
            self._delivery_label.text = tr("delivery_location")
            self.delivery_field.hint_text = tr("search_delivery_placeholder")
            self._parcel_label.text = tr("parcel_details")
            self._desc_label.text = tr("description_optional")
            self.desc_field.hint_text = tr("describe_sending_placeholder")
            self._value_label.text = tr("parcel_value_label")
            self.value_field.helper_text = tr("parcel_value_helper")
            self._instr_label.text = tr("special_instructions")
            self.instr_field.hint_text = tr("gate_code_placeholder")
            self._submit_btn.text = "\U0001f4b3 " + tr("proceed_to_payment")
            if hasattr(self, "_fair_title"):
                self._fair_title.text = tr("fair_pricing")
                self._fair_sub.text = tr("fair_pricing")
            if hasattr(self, "_secure_title"):
                self._secure_title.text = tr("secure_payment")
                self._secure_sub.text = tr("secure_payment_sub")
            if hasattr(self, "_track_title"):
                self._track_title.text = tr("track_live")
                self._track_sub.text = tr("track_live")
        except Exception:
            pass
