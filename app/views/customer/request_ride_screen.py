from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import AsyncImage
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.spinner import MDSpinner

from app.core.theme import PRIMARY, PRIMARY_DARK, DARK, MUTED, BACKGROUND, CARD_BG, ERROR, SUCCESS, BLUE
from app.i18n.translator import tr
from app.views.base_screen import BaseScreen


class RequestRideScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._pickup_meta = {}  # {lat, lng, address, city, place_id}
        self._dropoff_meta = {}
        self._pickup_clock = None
        self._dropoff_clock = None
        self._distance = None
        self._fee = None
        self._loading = False
        self._loading_ride = False
        self._loading_paystack = False
        self._auto_ride_clock = None
        self._last_ride_payload = None
        self._pending_ride_data = None
        self._paystack_modal_visible = False
        self._pending_reference = None
        self._pending_authorization_url = None
        self._paystack_screen = None
        self._paystack_webview = None
        self._pickup_menu = None
        self._dropoff_menu = None

        self._outer = MDBoxLayout(orientation="vertical")
        self._scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self._content = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp", adaptive_height=True, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        top_nav = self._build_standard_header()
        self._outer.add_widget(top_nav)
        self._outer.add_widget(self._scroll)
        self.add_widget(self._outer)

        self._build_page_card()
        self._build_footer()

        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

    # ---------- 1. Header — Dashboard-style (not Delivery variant) ----------
    def _build_standard_header(self):
        nav = MDCard(orientation="horizontal", padding="6dp", spacing="8dp", size_hint_x=1, size_hint_y=None, height="48dp", md_bg_color=rgba(CARD_BG), radius=[0], elevation=1)
        logo = MDLabel(text="Trackway", font_style="H6", bold=True, theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=1, size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5}, valign="middle")
        right_cluster = MDBoxLayout(orientation="horizontal", size_hint_x=None, width="160dp", spacing="12dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        try:
            from app.views.shared.language_picker import LanguagePicker
            self.language_picker = LanguagePicker(compact=True)
            self.language_picker.size_hint_x = None
            self.language_picker.width = "36dp"
            right_cluster.add_widget(self.language_picker)
        except Exception:
            right_cluster.add_widget(MDLabel(text="EN", font_style="Caption", font_size="12sp", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=None, width="32dp", halign="center"))

        bell_box = MDBoxLayout(orientation="horizontal", size_hint_x=None, width="24dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        bell_btn = MDIconButton(icon="bell-outline", theme_icon_color="Custom", icon_color=rgba(MUTED), icon_size="22sp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5}, on_release=self._go_notifications)
        bell_box.add_widget(bell_btn)
        right_cluster.add_widget(bell_box)
        # keep unread badge for parity but hidden until loaded
        self.bell_count_label = MDLabel(text="", font_style="Caption", bold=True, theme_text_color="Custom", text_color=rgba(ERROR), size_hint_x=None, width="16dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5}, halign="center", valign="middle")
        right_cluster.add_widget(self.bell_count_label)

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

    def _open_profile_menu(self, *args):
        try:
            from app.views.customer.customer_home_screen import CustomerHomeScreen
            # reuse home's menu by delegating to home screen if present
            home = None
            try:
                if self.manager:
                    home = self.manager.get_screen("customer_home")
            except Exception:
                home = None
            if home and hasattr(home, "_open_profile_menu"):
                home._open_profile_menu(*args)
                return
        except Exception:
            pass
        # fallback: go profile
        if self.manager:
            try:
                self.manager.current = "profile"
            except Exception:
                pass

    def _go_notifications(self, *args):
        if self.manager:
            self.manager.current = "notifications"

    def _on_window_width(self, instance, width):
        try:
            hide = width < 360
            if hasattr(self, "top_name_label"):
                self.top_name_label.opacity = 0 if hide else 1
                self.top_name_label.width = "0dp" if hide else "70dp"
        except Exception:
            pass

    # ---------- 2. Page Card (single white card, no green hero) ----------
    def _build_page_card(self):
        self._ride_card = MDCard(orientation="vertical", padding="16dp", spacing="12dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        # Heading: car icon + Request a Ride + green underline + subtitle
        head = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="22dp")
        head.add_widget(MDIcon(icon="car-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="22dp", font_size="20sp"))
        self._ride_title = MDLabel(text=tr("request_ride"), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK)
        head.add_widget(self._ride_title)
        self._ride_card.add_widget(head)
        self._ride_card.add_widget(MDBoxLayout(size_hint_x=1, height="1dp", size_hint_y=None, md_bg_color=rgba(PRIMARY)))
        self._ride_sub = MDLabel(text="Book a ride to your destination", font_style="Body2", theme_text_color="Custom", text_color=MUTED, adaptive_height=True)
        self._ride_card.add_widget(self._ride_sub)

        # 3. Pickup Location with red * and blue pin
        pickup_head = MDBoxLayout(orientation="horizontal", spacing="4dp", adaptive_height=True, size_hint_y=None, height="20dp")
        pickup_head.add_widget(MDLabel(text=tr("pickup_location") if tr("pickup_location") != "pickup_location" else "Pickup Location", font_style="Caption", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=None, width="110dp"))
        pickup_head.add_widget(MDLabel(text="*", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_x=None, width="10dp"))
        self._ride_card.add_widget(pickup_head)
        # input row with blue circular pin icon
        pickup_row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="48dp")
        pin_blue = MDCard(size_hint=(None, None), size=("28dp", "28dp"), md_bg_color=rgba("#E3F2FD"), radius=[14], elevation=0, pos_hint={"center_y": 0.5})
        pin_blue.add_widget(MDIcon(icon="map-marker", theme_text_color="Custom", text_color=rgba(BLUE), font_size="16sp", halign="center"))
        pickup_row.add_widget(pin_blue)
        self.pickup_field = MDTextField(hint_text="Search for pickup location...", mode="rectangle", size_hint_x=1)
        self.pickup_field.bind(text=self._on_pickup_text)
        self.pickup_field.bind(on_touch_down=self._maybe_open_pickup_menu)
        pickup_row.add_widget(self.pickup_field)
        self._ride_card.add_widget(pickup_row)
        self._pickup_error = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        self._ride_card.add_widget(self._pickup_error)

        # 4. Swap icon
        swap_row = MDBoxLayout(orientation="horizontal", size_hint_x=1, size_hint_y=None, height="40dp", padding=["0dp", "4dp", "0dp", "4dp"])
        swap_row.add_widget(MDLabel(text=""))
        btn = MDIconButton(icon="arrow-down", theme_icon_color="Custom", icon_color=rgba(PRIMARY), icon_size="20sp", size_hint=(None, None), size=("36dp", "36dp"), pos_hint={"center_y": 0.5}, md_bg_color=rgba(CARD_BG), on_release=lambda x: self._swap_locations())
        wrap = MDCard(size_hint=(None, None), size=("36dp", "36dp"), md_bg_color=rgba(CARD_BG), radius=[18], elevation=1, line_color=rgba(PRIMARY), line_width=0.8)
        wrap.add_widget(btn)
        swap_row.add_widget(wrap)
        swap_row.add_widget(MDLabel(text=""))
        self._ride_card.add_widget(swap_row)

        # 5. Dropoff Location with red * and green pin
        dropoff_head = MDBoxLayout(orientation="horizontal", spacing="4dp", adaptive_height=True, size_hint_y=None, height="20dp")
        dropoff_head.add_widget(MDLabel(text="Dropoff Location", font_style="Caption", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=None, width="120dp"))
        dropoff_head.add_widget(MDLabel(text="*", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_x=None, width="10dp"))
        self._ride_card.add_widget(dropoff_head)
        dropoff_row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="48dp")
        pin_green = MDCard(size_hint=(None, None), size=("28dp", "28dp"), md_bg_color=rgba("#E8F5E9"), radius=[14], elevation=0, pos_hint={"center_y": 0.5})
        pin_green.add_widget(MDIcon(icon="map-marker-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="16sp", halign="center"))
        dropoff_row.add_widget(pin_green)
        self.dropoff_field = MDTextField(hint_text="Search for dropoff location...", mode="rectangle", size_hint_x=1)
        self.dropoff_field.bind(text=self._on_dropoff_text)
        self.dropoff_field.bind(on_touch_down=self._maybe_open_dropoff_menu)
        dropoff_row.add_widget(self.dropoff_field)
        self._ride_card.add_widget(dropoff_row)
        self._dropoff_error = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        self._ride_card.add_widget(self._dropoff_error)

        # 6. Special Instructions (optional)
        instr_head = MDBoxLayout(orientation="horizontal", spacing="4dp", adaptive_height=True, size_hint_y=None, height="20dp")
        instr_head.add_widget(MDLabel(text=tr("special_instructions") if tr("special_instructions") != "special_instructions" else "Special Instructions", font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_x=None, width="150dp"))
        self._ride_card.add_widget(instr_head)
        self.instr_field = MDTextField(hint_text="Gate code, landmark, etc.", mode="rectangle", multiline=True, size_hint_y=None, height="70dp")
        self._ride_card.add_widget(self.instr_field)

        # Map (MC static image 320dp, full width, baked Google attribution — Ride only)
        self._map_card = MDCard(orientation="vertical", size_hint_x=1, size_hint_y=None, height="0dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, opacity=0)
        self._map_image = AsyncImage(source="", size_hint_x=1, size_hint_y=None, height="320dp", allow_stretch=True, keep_ratio=False)
        self._map_card.add_widget(self._map_image)
        self._ride_card.add_widget(self._map_card)

        # Preview — green card exact visual: distance+duration top, large fare, breakdown on green (no #e8f0e3 box)
        self._preview_card = MDCard(orientation="vertical", padding="16dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        self._preview_distance = MDLabel(text="", font_style="Body2", theme_text_color="Custom", text_color="white", adaptive_height=True, halign="center")
        self._preview_fee = MDLabel(text="", font_style="H6", bold=True, theme_text_color="Custom", text_color="white", font_size="22sp", adaptive_height=True, halign="center")
        self._preview_breakdown = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e0e0e0"), adaptive_height=True, halign="center")
        self._preview_referral = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e0e0e0"), font_size="10sp", adaptive_height=True, halign="center")
        self._preview_card.add_widget(self._preview_distance)
        self._preview_card.add_widget(self._preview_fee)
        self._preview_card.add_widget(self._preview_breakdown)
        self._preview_card.add_widget(self._preview_referral)
        self._preview_card.opacity = 0
        self._preview_card.height = "0dp"
        self._preview_card.size_hint_y = None
        self._ride_card.add_widget(self._preview_card)

        # 7. Action Buttons bottom right
        btn_row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="48dp", padding=["0dp", "8dp", "0dp", "0dp"])
        btn_row.add_widget(MDLabel(text=""))  # spacer pushes buttons right
        self._cancel_btn = MDFlatButton(text="\u2715 Cancel", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=None, width="100dp", on_release=lambda x: self._do_cancel())
        btn_row.add_widget(self._cancel_btn)
        self._submit_btn = MDRaisedButton(text="\U0001f4b3 Proceed to Payment", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="180dp", size_hint_y=None, height="48dp", on_release=lambda x: self._on_submit())
        self._submit_btn.disabled = True
        self._submit_btn.opacity = 0.5
        try:
            self._submit_btn.md_bg_color = rgba(PRIMARY)
            Clock.schedule_once(lambda dt: setattr(self._submit_btn, "md_bg_color", rgba(PRIMARY)), 0)
        except Exception:
            pass
        btn_row.add_widget(self._submit_btn)
        self._ride_card.add_widget(btn_row)
        self._submit_spinner = MDSpinner(size_hint=(None, None), size=("28dp", "28dp"), active=False, color=rgba(PRIMARY), pos_hint={"center_x": 0.5})
        self._ride_card.add_widget(self._submit_spinner)
        self._submit_error = MDLabel(text="", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        self._ride_card.add_widget(self._submit_error)

        # Bind for disabled state (strictly 4 lat/lng)
        try:
            self.pickup_field.bind(text=self._update_submit_state)
            self.dropoff_field.bind(text=self._update_submit_state)
            self._update_submit_state()
        except Exception:
            pass

        self._content.add_widget(self._ride_card)

    def _update_submit_state(self, *args):
        try:
            if getattr(self, "_loading", False) or getattr(self, "_loading_ride", False):
                self._submit_btn.disabled = True
                self._submit_btn.opacity = 0.5
                self._submit_btn.md_bg_color = rgba(PRIMARY)
                Clock.schedule_once(lambda dt: setattr(self._submit_btn, "md_bg_color", rgba(PRIMARY)), 0)
                return
            # Ready only when all 4 lat/lng present
            ready = bool(
                self._pickup_meta.get("lat") and self._pickup_meta.get("lng") and
                self._dropoff_meta.get("lat") and self._dropoff_meta.get("lng")
            )
            # also show enabled hint via fields filled — but lat/lng is strict
            self._submit_btn.disabled = not ready
            self._submit_btn.opacity = 1 if ready else 0.5
            self._submit_btn.md_bg_color = rgba(PRIMARY)
            Clock.schedule_once(lambda dt: setattr(self._submit_btn, "md_bg_color", rgba(PRIMARY)), 0)
        except Exception:
            pass

    # ---------- Auto-fare via Directions (fare card only, no map) ----------
    def _schedule_auto_ride(self, *args):
        try:
            if self._auto_ride_clock:
                try:
                    self._auto_ride_clock.cancel()
                except Exception:
                    pass
                self._auto_ride_clock = None
            plat = self._pickup_meta.get("lat")
            plng = self._pickup_meta.get("lng")
            dlat = self._dropoff_meta.get("lat")
            dlng = self._dropoff_meta.get("lng")
            if not plat or not plng or not dlat or not dlng:
                try:
                    self._preview_card.opacity = 0
                    self._preview_card.height = "0dp"
                except Exception:
                    pass
                return
            payload = {"pickup_lat": str(plat), "pickup_lng": str(plng), "delivery_lat": str(dlat), "delivery_lng": str(dlng)}
            if payload == self._last_ride_payload:
                return
            self._auto_ride_clock = Clock.schedule_once(lambda dt: self._do_auto_ride(payload), 0.6)
        except Exception:
            pass

    def _do_auto_ride(self, payload):
        try:
            self._loading_ride = True
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
                res = None
                try:
                    from app.services.places_service import directions
                    res = directions(payload["pickup_lat"], payload["pickup_lng"], payload["delivery_lat"], payload["delivery_lng"])
                except Exception:
                    res = None
                Clock.schedule_once(lambda dt: self._apply_auto_ride(res, payload), 0)
            threading.Thread(target=do, daemon=True).start()
        except Exception:
            pass

    def _apply_auto_ride(self, res, payload):
        try:
            self._loading_ride = False
            try:
                self._submit_spinner.active = False
            except Exception:
                pass
            self._update_submit_state()
            if not res:
                self._preview_distance.text = "Could not calculate fare"
                self._preview_fee.text = ""
                self._preview_breakdown.text = "Check locations and try again"
                self._preview_referral.text = ""
                self._preview_card.height = "72dp"
                self._preview_card.opacity = 1
                # hide map on failure
                try:
                    self._map_card.opacity = 0
                    self._map_card.height = "0dp"
                    self._map_image.source = ""
                except Exception:
                    pass
                return
            distance_km = res.get("distance_km") or 0
            duration_min = res.get("duration_min") or 0
            polyline = res.get("polyline") or ""
            # Client-side formula Base ₦500 + km×₦150 + min×₦20
            try:
                fee = 500 + float(distance_km) * 150 + float(duration_min) * 20
            except Exception:
                fee = 500
            formatted_fee = f"\u20a6{fee:,.2f}"
            distance_text = f"Distance: {float(distance_km):.2f} km (Est. Duration: {int(round(float(duration_min)))} min)"
            breakdown_text = f"Base: \u20a6500 + {float(distance_km):.2f}km \u00d7 \u20a6150 + {int(round(float(duration_min)))}min \u00d7 \u20a620"
            self._pending_ride_data = {"distance_km": distance_km, "duration_min": duration_min, "fee": fee, "formatted_fee": formatted_fee, "distance_text": distance_text, "breakdown_text": breakdown_text, "polyline": polyline}
            self._last_ride_payload = dict(payload)
            # Map — MC static image 320dp full width, baked Google attribution (no duplicate label)
            try:
                from app.services.places_service import static_map_url
                url = static_map_url(payload["pickup_lat"], payload["pickup_lng"], payload["delivery_lat"], payload["delivery_lng"], polyline)
                if url:
                    self._map_image.source = url
                    self._map_card.opacity = 1
                    self._map_card.height = "320dp"
                    self._map_card.size_hint_y = None
                else:
                    self._map_card.opacity = 0
                    self._map_card.height = "0dp"
            except Exception:
                try:
                    self._map_card.opacity = 0
                    self._map_card.height = "0dp"
                except Exception:
                    pass
            self._show_ride_preview(distance_text, formatted_fee, breakdown_text)
        except Exception:
            try:
                self._submit_spinner.active = False
            except Exception:
                pass
            self._loading_ride = False

    def _show_ride_preview(self, distance_text, fee, breakdown):
        try:
            self._preview_distance.text = distance_text
            self._preview_fee.text = fee
            self._preview_breakdown.text = breakdown
            self._preview_referral.text = ""
            has_breakdown = bool(breakdown)
            self._preview_card.height = "88dp" if has_breakdown else "64dp"
            self._preview_card.opacity = 1
            self._preview_card.size_hint_y = None
        except Exception:
            pass

    # ---------- Autocomplete (live on every partial edit, 0.4s debounce) ----------
    def _on_pickup_text(self, instance, value):
        v = (value or "").strip()
        stored = self._pickup_meta.get("address", "") if isinstance(self._pickup_meta, dict) else ""
        if not v:
            # cleared to empty — reset everything and hide menu
            self._pickup_meta = {}
            self._update_submit_state()
            self._clear_preview()
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
            return
        if stored and v == stored:
            # exact selection text — don't re-fetch same
            return
        if stored and v != stored:
            # mid-edit (e.g. Akure -> Akur) — clear stale lat/lng even if still Fetching (lat is None)
            self._pickup_meta = {}
            self._update_submit_state()
            self._clear_preview()
        if self._pickup_clock:
            try:
                self._pickup_clock.cancel()
            except Exception:
                pass
        self._pickup_clock = Clock.schedule_once(lambda dt: self._fetch_pickup_places(value), 0.4)

    def _on_dropoff_text(self, instance, value):
        v = (value or "").strip()
        stored = self._dropoff_meta.get("address", "") if isinstance(self._dropoff_meta, dict) else ""
        if not v:
            self._dropoff_meta = {}
            self._update_submit_state()
            self._clear_preview()
            try:
                if self._dropoff_menu:
                    self._dropoff_menu.dismiss()
            except Exception:
                pass
            if self._dropoff_clock:
                try:
                    self._dropoff_clock.cancel()
                except Exception:
                    pass
            return
        if stored and v == stored:
            return
        if stored and v != stored:
            self._dropoff_meta = {}
            self._update_submit_state()
            self._clear_preview()
        if self._dropoff_clock:
            try:
                self._dropoff_clock.cancel()
            except Exception:
                pass
        self._dropoff_clock = Clock.schedule_once(lambda dt: self._fetch_dropoff_places(value), 0.4)

    def _fetch_pickup_places(self, query):
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
            Clock.schedule_once(lambda dt: self._show_pickup_places(q, places), 0)
        threading.Thread(target=do, daemon=True).start()

    def _show_pickup_places(self, q, places):
        try:
            if not places:
                if q.lower() in ("ike", "ikeja", "lag", "lagos"):
                    places = [{"description": "Ikeja, Lagos, Nigeria", "place_id": "stub_ikeja", "lat": 6.6018, "lng": 3.3515, "city": "Lagos"}, {"description": "Ikeja GRA, Lagos", "place_id": "stub_ikeja_gra", "lat": 6.605, "lng": 3.355, "city": "Lagos"}]
                elif q.lower() in ("abu", "abuja"):
                    places = [{"description": "Abuja, FCT, Nigeria", "place_id": "stub_abuja", "lat": 9.0765, "lng": 7.3986, "city": "Abuja"}]
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

    def _fetch_dropoff_places(self, query):
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
            Clock.schedule_once(lambda dt: self._show_dropoff_places(q, places), 0)
        threading.Thread(target=do, daemon=True).start()

    def _show_dropoff_places(self, q, places):
        try:
            if not places:
                if q.lower() in ("abu", "abuja"):
                    places = [{"description": "Abuja, FCT, Nigeria", "place_id": "stub_abuja", "lat": 9.0765, "lng": 7.3986, "city": "Abuja"}]
                elif q.lower() in ("ike", "ikeja"):
                    places = [{"description": "Ikeja, Lagos, Nigeria", "place_id": "stub_ikeja", "lat": 6.6018, "lng": 3.3515, "city": "Lagos"}]
                else:
                    return
            items = []
            for p in places[:5]:
                desc = p.get("description") or ""
                items.append({"text": desc, "viewclass": "OneLineListItem", "on_release": lambda d=desc, m=p: self._select_dropoff(d, m)})
            if self._dropoff_menu:
                try:
                    self._dropoff_menu.dismiss()
                except Exception:
                    pass
            self._dropoff_menu = MDDropdownMenu(caller=self.dropoff_field, items=items, width_mult=4, max_height="220dp")
            self._dropoff_menu.open()
        except Exception:
            pass

    def _maybe_open_pickup_menu(self, instance, touch):
        if instance != self.pickup_field:
            return False
        if not instance.collide_point(*touch.pos):
            return False
        # give field keyboard focus so Backspace/Delete/Ctrl+A and mobile long-press Select All work
        try:
            instance.focus = True
        except Exception:
            pass
        if self._pickup_menu and not self._pickup_menu.parent:
            try:
                self._pickup_menu.caller = self.pickup_field
                self._pickup_menu.open()
            except Exception:
                pass
        return False

    def _maybe_open_dropoff_menu(self, instance, touch):
        if instance != self.dropoff_field:
            return False
        if not instance.collide_point(*touch.pos):
            return False
        try:
            instance.focus = True
        except Exception:
            pass
        if self._dropoff_menu and not self._dropoff_menu.parent:
            try:
                self._dropoff_menu.caller = self.dropoff_field
                self._dropoff_menu.open()
            except Exception:
                pass
        return False

    def _extract_meta(self, desc, raw):
        # Normalize raw to our 4-field store, keep address/city for UI but fare uses only lat/lng
        lat = raw.get("lat") or raw.get("latitude") or raw.get("geometry", {}).get("location", {}).get("lat")
        lng = raw.get("lng") or raw.get("lon") or raw.get("longitude") or raw.get("geometry", {}).get("location", {}).get("lng")
        # try geocode lookup if missing
        if (lat is None or lng is None) and raw.get("place_id"):
            try:
                from app.services.places_service import geocode
                g = geocode(raw.get("place_id")) or geocode(desc)
                if g:
                    lat = g.get("lat") or lat
                    lng = g.get("lng") or lng
            except Exception:
                pass
        city = raw.get("city") or raw.get("locality") or ""
        return {"address": desc, "city": city, "lat": lat, "lng": lng, "place_id": raw.get("place_id")}

    def _select_pickup(self, desc, raw):
        # Cancel any pending fetch from the text change that triggered this selection
        if self._pickup_clock:
            try:
                self._pickup_clock.cancel()
            except Exception:
                pass
            self._pickup_clock = None
        self.pickup_field.text = desc
        # restore keyboard focus so immediate Backspace/Delete/Ctrl+A and mobile long-press work without extra tap
        try:
            self.pickup_field.focus = True
            self.pickup_field.cursor = (len(desc), 0)
        except Exception:
            pass
        # fast path: stub already has lat/lng
        lat = raw.get("lat") or raw.get("geometry", {}).get("location", {}).get("lat")
        lng = raw.get("lng") or raw.get("geometry", {}).get("location", {}).get("lng")
        if lat is not None and lng is not None:
            self._pickup_meta = {"address": desc, "city": raw.get("city") or "", "lat": lat, "lng": lng, "place_id": raw.get("place_id")}
            self._pickup_error.text = ""
            self._pickup_error.height = "0dp"
            try:
                if self._pickup_menu:
                    self._pickup_menu.dismiss()
            except Exception:
                pass
            # Cancel the fetch that _on_pickup_text just scheduled for this exact text
            if self._pickup_clock:
                try:
                    self._pickup_clock.cancel()
                except Exception:
                    pass
                self._pickup_clock = None
            self._update_submit_state()
            self._clear_preview()
            self._schedule_auto_ride()
            return
        # async geocode for real Google place_id
        self._pickup_meta = {"address": desc, "city": raw.get("city") or "", "lat": None, "lng": None, "place_id": raw.get("place_id")}
        self._pickup_error.text = "Fetching coordinates..."
        self._pickup_error.height = "18dp"
        try:
            if self._pickup_menu:
                self._pickup_menu.dismiss()
        except Exception:
            pass
        # Cancel fetch scheduled by _on_pickup_text for this exact text
        if self._pickup_clock:
            try:
                self._pickup_clock.cancel()
            except Exception:
                pass
            self._pickup_clock = None
        import threading
        def do_geocode():
            g = None
            try:
                from app.services.places_service import geocode
                g = geocode(raw.get("place_id") or desc)
            except Exception:
                g = None
            def apply(dt):
                if g and g.get("lat") is not None:
                    self._pickup_meta = {"address": desc, "city": g.get("city") or raw.get("city") or "", "lat": g.get("lat"), "lng": g.get("lng"), "place_id": raw.get("place_id")}
                    self._pickup_error.text = ""
                    self._pickup_error.height = "0dp"
                else:
                    self._pickup_error.text = "Could not fetch coordinates, try another suggestion"
                    self._pickup_error.height = "18dp"
                self._update_submit_state()
                self._clear_preview()
                self._schedule_auto_ride()
            Clock.schedule_once(apply, 0)
        threading.Thread(target=do_geocode, daemon=True).start()

    def _select_dropoff(self, desc, raw):
        if self._dropoff_clock:
            try:
                self._dropoff_clock.cancel()
            except Exception:
                pass
            self._dropoff_clock = None
        self.dropoff_field.text = desc
        try:
            self.dropoff_field.focus = True
            self.dropoff_field.cursor = (len(desc), 0)
        except Exception:
            pass
        lat = raw.get("lat") or raw.get("geometry", {}).get("location", {}).get("lat")
        lng = raw.get("lng") or raw.get("geometry", {}).get("location", {}).get("lng")
        if lat is not None and lng is not None:
            self._dropoff_meta = {"address": desc, "city": raw.get("city") or "", "lat": lat, "lng": lng, "place_id": raw.get("place_id")}
            self._dropoff_error.text = ""
            self._dropoff_error.height = "0dp"
            try:
                if self._dropoff_menu:
                    self._dropoff_menu.dismiss()
            except Exception:
                pass
            if self._dropoff_clock:
                try:
                    self._dropoff_clock.cancel()
                except Exception:
                    pass
                self._dropoff_clock = None
            self._update_submit_state()
            self._clear_preview()
            self._schedule_auto_ride()
            return
        self._dropoff_meta = {"address": desc, "city": raw.get("city") or "", "lat": None, "lng": None, "place_id": raw.get("place_id")}
        self._dropoff_error.text = "Fetching coordinates..."
        self._dropoff_error.height = "18dp"
        try:
            if self._dropoff_menu:
                self._dropoff_menu.dismiss()
        except Exception:
            pass
        if self._dropoff_clock:
            try:
                self._dropoff_clock.cancel()
            except Exception:
                pass
            self._dropoff_clock = None
        import threading
        def do_geocode():
            g = None
            try:
                from app.services.places_service import geocode
                g = geocode(raw.get("place_id") or desc)
            except Exception:
                g = None
            def apply(dt):
                if g and g.get("lat") is not None:
                    self._dropoff_meta = {"address": desc, "city": g.get("city") or raw.get("city") or "", "lat": g.get("lat"), "lng": g.get("lng"), "place_id": raw.get("place_id")}
                    self._dropoff_error.text = ""
                    self._dropoff_error.height = "0dp"
                else:
                    self._dropoff_error.text = "Could not fetch coordinates, try another suggestion"
                    self._dropoff_error.height = "18dp"
                self._update_submit_state()
                self._clear_preview()
                self._schedule_auto_ride()
            Clock.schedule_once(apply, 0)
        threading.Thread(target=do_geocode, daemon=True).start()

    def _swap_locations(self, *args):
        try:
            pt = self.pickup_field.text
            dt = self.dropoff_field.text
            self.pickup_field.text = dt
            self.dropoff_field.text = pt
            pm = self._pickup_meta
            self._pickup_meta = self._dropoff_meta
            self._dropoff_meta = pm
            self._update_submit_state()
            self._clear_preview()
            self._schedule_auto_ride()
        except Exception:
            pass

    # ---------- Preview ----------
    def _show_preview(self, data):
        try:
            # data contains pre-formatted strings from API
            self._preview_distance.text = data.get("distance") or data.get("formatted_distance") or (f"Distance: {data.get('distance_km')} km" if data.get("distance_km") else "")
            self._preview_fee.text = data.get("fee") or data.get("formatted_fee") or data.get("fee_text") or ""
            self._preview_breakdown.text = data.get("breakdown_text") or data.get("breakdown") or ""
            # referral/discount
            ref = data.get("referral_balance") or data.get("referral") or ""
            disc = data.get("discount") or data.get("referral_discount") or ""
            ref_text = ""
            if ref:
                ref_text = f"Referral balance: {ref}"
            if disc:
                ref_text = (ref_text + "  " if ref_text else "") + f"Discount: {disc}"
            self._preview_referral.text = ref_text
            # Also try combined fields
            if not ref_text:
                combined = data.get("referral_balance_text") or data.get("discount_text") or ""
                self._preview_referral.text = combined
            self._preview_card.opacity = 1
            # expand height based on content
            has_breakdown = bool(self._preview_breakdown.text)
            has_ref = bool(self._preview_referral.text)
            self._preview_card.height = "96dp" if has_breakdown and has_ref else "72dp" if has_breakdown or has_ref else "48dp"
            self._preview_card.size_hint_y = None
        except Exception:
            pass

    def _clear_preview(self):
        try:
            self._distance = None
            self._fee = None
            self._preview_distance.text = ""
            self._preview_fee.text = ""
            self._preview_breakdown.text = ""
            self._preview_referral.text = ""
            self._preview_card.opacity = 0
            self._preview_card.height = "0dp"
            try:
                if hasattr(self, "_map_card"):
                    self._map_card.opacity = 0
                    self._map_card.height = "0dp"
                    self._map_image.source = ""
            except Exception:
                pass
            try:
                if self._auto_ride_clock:
                    self._auto_ride_clock.cancel()
                    self._auto_ride_clock = None
            except Exception:
                pass
        except Exception:
            pass

    # ---------- Actions ----------
    def _do_cancel(self, *args):
        if self.manager:
            self.manager.current = "customer_home"

    def _on_submit(self, *args):
        if self._loading:
            return
        has_err = False
        # Validate pickup lat/lng (strict)
        if not self._pickup_meta.get("lat") or not self._pickup_meta.get("lng"):
            # also check if field empty
            if not self.pickup_field.text.strip():
                self._pickup_error.text = "Pickup location is required"
            else:
                self._pickup_error.text = "Please select pickup from suggestions"
            self._pickup_error.height = "18dp"
            has_err = True
        else:
            try:
                float(self._pickup_meta.get("lat"))
                float(self._pickup_meta.get("lng"))
                self._pickup_error.text = ""
                self._pickup_error.height = "0dp"
            except Exception:
                self._pickup_error.text = "Invalid pickup coordinates"
                self._pickup_error.height = "18dp"
                has_err = True
        if not self._dropoff_meta.get("lat") or not self._dropoff_meta.get("lng"):
            if not self.dropoff_field.text.strip():
                self._dropoff_error.text = "Dropoff location is required"
            else:
                self._dropoff_error.text = "Please select dropoff from suggestions"
            self._dropoff_error.height = "18dp"
            has_err = True
        else:
            try:
                float(self._dropoff_meta.get("lat"))
                float(self._dropoff_meta.get("lng"))
                self._dropoff_error.text = ""
                self._dropoff_error.height = "0dp"
            except Exception:
                self._dropoff_error.text = "Invalid dropoff coordinates"
                self._dropoff_error.height = "18dp"
                has_err = True
        if has_err:
            return

        # If auto-ride already fetched fare for same coordinates, reuse (no second Directions call)
        try:
            cur_plat = self._pickup_meta.get("lat")
            cur_plng = self._pickup_meta.get("lng")
            cur_dlat = self._dropoff_meta.get("lat")
            cur_dlng = self._dropoff_meta.get("lng")
            cur_payload = {"pickup_lat": str(cur_plat) if cur_plat else "", "pickup_lng": str(cur_plng) if cur_plng else "", "delivery_lat": str(cur_dlat) if cur_dlat else "", "delivery_lng": str(cur_dlng) if cur_dlng else ""}
            if self._pending_ride_data and self._last_ride_payload == cur_payload and cur_plat and cur_plng and cur_dlat and cur_dlng:
                # Ensure preview visible
                try:
                    self._show_ride_preview(self._pending_ride_data.get("distance_text") or "", self._pending_ride_data.get("formatted_fee") or "", self._pending_ride_data.get("breakdown_text") or "")
                except Exception:
                    pass
                self._show_payment_dialog(dict(cur_payload), dict(self._pending_ride_data))
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

        pickup = self._pickup_meta
        dropoff = self._dropoff_meta

        def do_calc(dt):
            # Ride fare is client-side Directions (distance + duration), not backend calculate-distance
            payload = {
                "pickup_lat": str(pickup.get("lat")),
                "pickup_lng": str(pickup.get("lng")),
                "delivery_lat": str(dropoff.get("lat")),
                "delivery_lng": str(dropoff.get("lng")),
            }
            try:
                from app.services.places_service import directions
                res = directions(payload["pickup_lat"], payload["pickup_lng"], payload["delivery_lat"], payload["delivery_lng"])
                self._submit_spinner.active = False
                self._loading = False
                self._update_submit_state()
                if res:
                    distance_km = res.get("distance_km") or 0
                    duration_min = res.get("duration_min") or 0
                    try:
                        fee = 500 + float(distance_km) * 150 + float(duration_min) * 20
                    except Exception:
                        fee = 500
                    formatted_fee = f"\u20a6{fee:,.2f}"
                    distance_text = f"Distance: {float(distance_km):.2f} km (Est. Duration: {int(round(float(duration_min)))} min)"
                    breakdown_text = f"Base: \u20a6500 + {float(distance_km):.2f}km \u00d7 \u20a6150 + {int(round(float(duration_min)))}min \u00d7 \u20a620"
                    data = {"distance_km": distance_km, "duration_min": duration_min, "formatted_fee": formatted_fee, "distance_text": distance_text, "breakdown_text": breakdown_text, "fee": fee}
                    self._show_ride_preview(distance_text, formatted_fee, breakdown_text)
                    self._pending_ride_data = dict(data)
                    self._last_ride_payload = dict(payload)
                    # Also keep preview data for consistency
                    self._pending_payload = dict(payload)
                    self._show_payment_dialog(dict(payload), data)
                else:
                    self._submit_error.text = "Could not calculate fare — check locations and try again"
                    self._submit_error.height = "28dp"
                    try:
                        from kivymd.uix.snackbar import Snackbar
                        Snackbar(text="Could not calculate ride fare").open()
                    except Exception:
                        pass
            except Exception as e:
                self._submit_spinner.active = False
                self._loading = False
                self._update_submit_state()
                self._submit_error.text = str(e)
                self._submit_error.height = "28dp"
        Clock.schedule_once(do_calc, 0.1)

    def _show_payment_dialog(self, payload, data):
        # Directly initialize Paystack hosted checkout (WebView full-screen) — ride uses same 4 tabs inside Paystack
        self._do_request_ride(payload, "paystack")

    # ---------- Paystack WebView full-screen modal (Ride, same 4 tabs) ----------
    def _open_paystack_modal(self, authorization_url, reference):
        try:
            self._pending_reference = reference
            self._pending_authorization_url = authorization_url
            self._paystack_modal_visible = True
            try:
                Window.bind(on_keyboard=self._on_keyboard)
            except Exception:
                pass
            # Open system browser instead of in-app WebView (kivy_garden.webview is Android-only, needs cef on desktop)
            try:
                import webbrowser
                webbrowser.open(authorization_url)
            except Exception:
                pass
            from kivymd.uix.card import MDCard as _MDCard
            from kivy.uix.modalview import ModalView
            from kivymd.uix.boxlayout import MDBoxLayout as _Box
            from kivymd.uix.button import MDIconButton as _IconBtn, MDRaisedButton as _RaisedBtn
            from kivymd.uix.label import MDLabel as _Lbl
            modal = ModalView(size_hint=(1, 1), background_color=[0, 0, 0, 0.6], auto_dismiss=False)
            root = _MDCard(orientation="vertical", size_hint=(0.95, 0.6), pos_hint={"center_x": 0.5, "center_y": 0.5}, radius=[14], elevation=8, md_bg_color=rgba(CARD_BG), padding="16dp", spacing="12dp")
            top = _Box(orientation="horizontal", size_hint_y=None, height="48dp", spacing="6dp")
            top.add_widget(_Lbl(text="Secure Checkout — Paystack", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, halign="left"))
            close_btn = _IconBtn(icon="close", theme_icon_color="Custom", icon_color=rgba(MUTED), on_release=lambda x: self._dismiss_paystack_modal())
            top.add_widget(close_btn)
            root.add_widget(top)
            root.add_widget(_Lbl(text="Paystack checkout opened in your browser.\nComplete payment there, then return here.", font_style="Body2", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            root.add_widget(_Lbl(text=f"Reference: {reference}", font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, font_size="10sp"))
            verify_btn = _RaisedBtn(text="Verify Payment", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=1, size_hint_y=None, height="44dp", on_release=lambda x: self._verify_paystack_reference(reference))
            root.add_widget(verify_btn)
            root.add_widget(_Lbl(text="Secured by paystack", font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, font_size="10sp", adaptive_height=True))
            modal.add_widget(root)
            self._paystack_screen = modal
            self._paystack_webview = None
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
            has_real = bool(self._pending_reference and self._pending_authorization_url)
            if not has_real:
                try:
                    self._submit_spinner.active = False
                    # hide spinner + preview/map immediately — clean return (no Pending stub)
                    self._preview_card.opacity = 0 if not self._pending_ride_data else 1
                    if hasattr(self, "_map_card"):
                        self._map_card.opacity = 0 if not self._pending_ride_data else 1
                        if not self._pending_ride_data:
                            self._map_card.height = "0dp"
                            try:
                                self._map_image.source = ""
                            except Exception:
                                pass
                except Exception:
                    pass
                self._loading = False
                self._loading_paystack = False
                self._loading_ride = False
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
            Clock.schedule_once(lambda dt: self._update_submit_state(), 0)
        except Exception:
            pass

    def _on_keyboard(self, window, key, scancode, codepoint, modifier):
        if self._paystack_modal_visible and key in (27, 1001):
            self._dismiss_paystack_modal()
            return True
        return False

    def _do_request_ride(self, payload, method):
        # Ride request-ride.php must send BOTH address/city + lat/lng plus distance_km/estimated_duration/fare as strings (form-data)
        # No payment_method unless separate evidence — capture showed absent
        try:
            if hasattr(self, "_pay_dialog") and self._pay_dialog:
                try:
                    self._pay_dialog.dismiss()
                except Exception:
                    pass
        except Exception:
            pass
        # Build exact payload as captured: pickup_address/city/lat/lng + dropoff_* + special_instructions + distance_km/estimated_duration/fare (strings)
        # Use current metas + pending ride data (precise raw values), not formatted display strings
        try:
            # Prefer pending_ride_data for precise distance/fare, fallback to payload data
            pending = getattr(self, "_pending_ride_data", None) or {}
            # distance_km raw precise (preserve exact Directions value, e.g. 178.1300001)
            dk = pending.get("distance_km") if pending else payload.get("distance_km")
            if dk is None:
                dk = payload.get("distance_km") or self._pending_ride_data.get("distance_km") if hasattr(self, "_pending_ride_data") and self._pending_ride_data else None
            dm = pending.get("duration_min") if pending else payload.get("duration_min")
            fee_val = pending.get("fee") if pending else payload.get("fee")
            # Fallback if still None try to derive from stored metas (should not happen)
        except Exception:
            dk, dm, fee_val = None, None, None
        payload_with_pay = {}
        try:
            payload_with_pay["pickup_address"] = self._pickup_meta.get("address") or self.pickup_field.text.strip()
            payload_with_pay["pickup_city"] = self._pickup_meta.get("city") or ""
            payload_with_pay["pickup_lat"] = str(self._pickup_meta.get("lat") or "")
            payload_with_pay["pickup_lng"] = str(self._pickup_meta.get("lng") or "")
            payload_with_pay["dropoff_address"] = self._dropoff_meta.get("address") or self.dropoff_field.text.strip()
            payload_with_pay["dropoff_city"] = self._dropoff_meta.get("city") or ""
            payload_with_pay["dropoff_lat"] = str(self._dropoff_meta.get("lat") or "")
            payload_with_pay["dropoff_lng"] = str(self._dropoff_meta.get("lng") or "")
            # Exact string representations — preserve precise raw (not :.2f rounded display)
            if dk is not None:
                payload_with_pay["distance_km"] = str(dk)
            if dm is not None:
                # estimated_duration as plain int string (e.g. "208")
                try:
                    payload_with_pay["estimated_duration"] = str(int(round(float(dm))))
                except Exception:
                    payload_with_pay["estimated_duration"] = str(dm)
            if fee_val is not None:
                # Paystack amount must be naira integer, no decimals, no kobo *100 (confirmed 50000 → NGN 50,000)
                try:
                    payload_with_pay["fare"] = str(int(round(float(fee_val))))
                except Exception:
                    try:
                        payload_with_pay["fare"] = str(int(round(float(str(fee_val).replace(",", "").replace("₦","").strip() or 0))))
                    except Exception:
                        payload_with_pay["fare"] = str(int(float(str(fee_val).replace(",", "").replace("₦","").strip().split()[0] or 0))) if str(fee_val).strip() else "0"
            instr = self.instr_field.text.strip() or None
            if instr:
                payload_with_pay["special_instructions"] = instr
            # Clean empty/None
            payload_with_pay = {k: v for k, v in payload_with_pay.items() if v not in (None, "", "None")}
        except Exception:
            payload_with_pay = dict(payload)
            instr = self.instr_field.text.strip() or None
            if instr:
                payload_with_pay["special_instructions"] = instr
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
        def do_req(dt):
            try:
                # Try dedicated ride endpoint, fallback to request_delivery
                try:
                    from app.services.customer_service import request_ride
                    result = request_ride(payload_with_pay)
                except Exception:
                    from app.services.customer_service import request_delivery
                    result = request_delivery(payload_with_pay)
                self._submit_spinner.active = False
                self._loading = False
                self._loading_paystack = False
                self._update_submit_state()
                if result.get("ok"):
                    data = result.get("data") or {}
                    auth_url = data.get("authorization_url") or data.get("authorizationUrl") or data.get("paystack_url") or data.get("url") or ""
                    ref = data.get("reference") or data.get("paystack_reference") or data.get("trxref") or data.get("access_code") or ""
                    if auth_url:
                        self._open_paystack_modal(auth_url, ref or data.get("waybill_number") or "")
                        return
                    wb = data.get("waybill_number") or data.get("waybill") or data.get("tracking_number") or data.get("ride_id") or ""
                    msg = f"Ride {wb} created" if wb else "Ride requested"
                    try:
                        from kivymd.uix.snackbar import Snackbar
                        Snackbar(text=msg).open()
                    except Exception:
                        pass
                    self.pickup_field.text = ""
                    self.dropoff_field.text = ""
                    self.instr_field.text = ""
                    self._pickup_meta = {}
                    self._dropoff_meta = {}
                    self._clear_preview()
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
                self._update_submit_state()
                self._submit_error.text = str(e)
                self._submit_error.height = "28dp"
        Clock.schedule_once(do_req, 0.1)

    # ---------- Footer ----------
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
        self._clear_preview()
        self._submit_error.text = ""
        self._submit_error.height = "0dp"
        try:
            self._on_window_width(Window, Window.width if hasattr(Window, "width") else 400)
        except Exception:
            pass
        try:
            self._update_submit_state()
        except Exception:
            pass

    def rebuild_ui(self):
        try:
            self._ride_title.text = tr("request_ride")
            self._ride_sub.text = "Book a ride to your destination"
            self.pickup_field.hint_text = "Search for pickup location..."
            self.dropoff_field.hint_text = "Search for dropoff location..."
            self.instr_field.hint_text = "Gate code, landmark, etc."
            self._submit_btn.text = "\U0001f4b3 Proceed to Payment"
            self.top_name_label.text = ""
        except Exception:
            pass
