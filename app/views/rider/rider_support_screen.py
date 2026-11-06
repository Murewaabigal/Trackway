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

from app.core.theme import PRIMARY, DARK, MUTED, BACKGROUND, CARD_BG, SUCCESS, ERROR
from app.core import session
from app.views.base_screen import BaseScreen


RIDER_SUPPORT_TYPES = {
    "delivery_issue": "Delivery Issue",
    "payment_wallet_issue": "Payment/Wallet Issue",
    "technical_app_issue": "Technical/App Issue",
    "account_issue": "Account Issue",
    "vehicle_bike_issue": "Vehicle/Bike Issue",
    "customer_related_issue": "Customer-Related Issue",
    "other": "Other",
}
# Only delivery_issue verified vs live rider/support/submit.php 2026-09-23; other 6 pending backend


class RiderSupportScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._type = ""
        self._type_label = ""
        self._waybill_id = ""
        self._waybill_label = ""
        self._waybill_items = []
        self._tickets = []
        self._submitting = False
        self._profile_menu = None
        self._type_menu = None
        self._waybill_menu = None

        self._outer = MDBoxLayout(orientation="vertical", spacing="0dp")
        self._scroll = ScrollView(do_scroll_x=False, bar_width=dp(4), size_hint_y=1, effect_cls="DampedScrollEffect")
        try:
            # clip overscroll so green banner never enters header's 48dp rect, keep damped feel
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
        self._build_form()
        self._build_assistance()
        self._build_resources()
        self._build_tickets()
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
        card = MDCard(orientation="vertical", padding="16dp", spacing="6dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        row = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_y=None, height="28dp")
        row.add_widget(MDIcon(icon="headset", theme_text_color="Custom", text_color="white", font_size="20sp", size_hint_x=None, width="24dp"))
        row.add_widget(MDLabel(text="Rider Support", font_style="H6", bold=True, theme_text_color="Custom", text_color="white", halign="left"))
        card.add_widget(row)
        card.add_widget(MDLabel(text="Need help with deliveries, payments, or have any questions? We're here to assist you.", font_style="Body2", theme_text_color="Custom", text_color=rgba("#e8f0e3"), adaptive_height=True))
        self._content.add_widget(card)

    # ---------- Section 1: Form ----------
    def _build_form(self):
        banner = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="72dp", md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        banner.add_widget(MDLabel(text="🎧 Submit a Support Request", font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color="white", halign="center"))
        banner.add_widget(MDLabel(text="Fill out the form below and our support team will get back to you within 24 hours.", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), halign="center", adaptive_height=True))
        self._content.add_widget(banner)

        card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        # Request Details
        rd = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_y=None, height="22dp")
        rd.add_widget(MDIcon(icon="information-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="18dp"))
        rd.add_widget(MDLabel(text="Request Details", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        card.add_widget(rd)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba("#e0e0e0")))

        card.add_widget(MDLabel(text="Request Type", font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp"))
        self._type_field = MDTextField(hint_text="Select request type", mode="rectangle", readonly=True)
        self._type_field.bind(on_touch_down=self._maybe_open_type_menu)
        card.add_widget(self._type_field)
        self._type_error = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        card.add_widget(self._type_error)

        card.add_widget(MDLabel(text="Related Waybill (Optional)", font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp"))
        self._waybill_field = MDTextField(hint_text="Select a waybill (if applicable)", mode="rectangle", readonly=True)
        self._waybill_field.bind(on_touch_down=self._maybe_open_waybill_menu)
        card.add_widget(self._waybill_field)
        helper = MDLabel(text="Only select if your issue is related to a specific delivery", font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color=MUTED, adaptive_height=True)
        card.add_widget(helper)

        card.add_widget(MDLabel(text="Subject", font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp"))
        self._subject_field = MDTextField(hint_text="Brief summary of your issue", mode="rectangle", multiline=False)
        card.add_widget(self._subject_field)
        self._subject_error = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        card.add_widget(self._subject_error)

        card.add_widget(MDLabel(text="Message", font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp"))
        self._message_field = MDTextField(hint_text="Please describe your issue in detail...", mode="rectangle", multiline=True, size_hint_y=None, height="100dp")
        card.add_widget(self._message_field)
        self._message_error = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        card.add_widget(self._message_error)

        btn_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, size_hint_y=None, height="44dp", spacing="8dp")
        btn_row.add_widget(MDLabel(text=""))
        self._submit_btn = MDRaisedButton(text="✈ Submit Request", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="160dp", on_release=lambda x: self._submit())
        btn_row.add_widget(self._submit_btn)
        card.add_widget(btn_row)
        self._form_status = MDLabel(text="", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba(SUCCESS), size_hint_y=None, height="0dp")
        card.add_widget(self._form_status)
        self._submit_spinner = MDSpinner(size_hint=(None,None), size=("24dp","24dp"), active=False, color=rgba(PRIMARY), pos_hint={"center_x":0.5})
        card.add_widget(self._submit_spinner)

        self._form_card = card
        self._content.add_widget(card)

    def _maybe_open_type_menu(self, instance, touch):
        if instance != self._type_field or not instance.collide_point(*touch.pos):
            return False
        self._show_type_menu()
        return True

    def _show_type_menu(self):
        items = []
        for slug, label in RIDER_SUPPORT_TYPES.items():
            items.append({"text": label, "viewclass": "OneLineListItem", "on_release": lambda k=slug, lbl=label: self._select_type(k, lbl)})
        try:
            if self._type_menu:
                self._type_menu.dismiss()
        except Exception:
            pass
        self._type_menu = MDDropdownMenu(caller=self._type_field, items=items, width_mult=4, max_height="280dp")
        self._type_menu.open()

    def _select_type(self, key, label):
        self._type = key
        self._type_label = label
        self._type_field.text = label
        self._type_error.text = ""
        self._type_error.height = "0dp"
        try:
            if self._type_menu:
                self._type_menu.dismiss()
        except Exception:
            pass

    def _maybe_open_waybill_menu(self, instance, touch):
        if instance != self._waybill_field or not instance.collide_point(*touch.pos):
            return False
        self._show_waybill_menu()
        return True

    def _show_waybill_menu(self):
        items = []
        items.append({"text": "Select a waybill (if applicable)", "viewclass": "OneLineListItem", "on_release": lambda: self._select_waybill("", "")})
        for wb in (self._waybill_items or [])[:30]:
            # wb is parsed dict from service
            label = wb.get("label") or wb.get("waybill_number") or str(wb)
            wid = wb.get("waybill_id") or wb.get("waybill_number") or ""
            items.append({"text": label, "viewclass": "OneLineListItem", "on_release": lambda wid=wid, lbl=label: self._select_waybill(wid, lbl)})
        try:
            if self._waybill_menu:
                self._waybill_menu.dismiss()
        except Exception:
            pass
        self._waybill_menu = MDDropdownMenu(caller=self._waybill_field, items=items, width_mult=4, max_height="280dp")
        self._waybill_menu.open()

    def _select_waybill(self, wid, label):
        self._waybill_id = wid
        self._waybill_field.text = label if label != "Select a waybill (if applicable)" else ""
        try:
            if self._waybill_menu:
                self._waybill_menu.dismiss()
        except Exception:
            pass

    def _submit(self, *args):
        if self._submitting:
            return
        has_error = False
        if not self._type:
            self._type_error.text = "Please select a request type"
            self._type_error.height = "18dp"
            has_error = True
        else:
            self._type_error.text = ""
            self._type_error.height = "0dp"
        subj = self._subject_field.text.strip()
        if len(subj) < 3:
            self._subject_error.text = "Subject must be at least 3 characters"
            self._subject_error.height = "18dp"
            has_error = True
        else:
            self._subject_error.text = ""
            self._subject_error.height = "0dp"
        msg = self._message_field.text.strip()
        if len(msg) < 10:
            self._message_error.text = "Message must be at least 10 characters"
            self._message_error.height = "18dp"
            has_error = True
        else:
            self._message_error.text = ""
            self._message_error.height = "0dp"
        if has_error:
            return
        self._submitting = True
        self._submit_btn.disabled = True
        self._submit_spinner.active = True
        self._form_status.text = ""
        self._form_status.height = "0dp"
        payload = {"type": self._type, "subject": subj, "message": msg}
        if self._waybill_id:
            payload["waybill_id"] = self._waybill_id
        import threading
        def do():
            result = {"ok": False, "error": "Failed"}
            try:
                from app.services.rider_service import submit_rider_support
                result = submit_rider_support(payload)
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            Clock.schedule_once(lambda dt: self._on_submit_done(result), 0)
        threading.Thread(target=do, daemon=True).start()

    def _on_submit_done(self, result):
        self._submit_spinner.active = False
        self._submitting = False
        self._submit_btn.disabled = False
        if result.get("ok"):
            self._form_status.text = "Support request submitted"
            self._form_status.text_color = rgba(SUCCESS)
            self._form_status.height = "22dp"
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text="Support request submitted").open()
            except Exception:
                pass
            self._type = ""
            self._type_label = ""
            self._type_field.text = ""
            self._waybill_id = ""
            self._waybill_field.text = ""
            self._subject_field.text = ""
            self._message_field.text = ""
            Clock.schedule_once(lambda dt: self._clear_status(), 3)
            self._load_tickets()
        else:
            err = result.get("error") or "Submission failed"
            self._form_status.text = err
            self._form_status.text_color = rgba(ERROR)
            self._form_status.height = "28dp"
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text=err).open()
            except Exception:
                pass
            if "Session expired" in str(err):
                try:
                    session.clear_session()
                except Exception:
                    pass
                if self.manager:
                    self.manager.current = "rider_login"

    def _clear_status(self):
        try:
            self._form_status.text = ""
            self._form_status.height = "0dp"
        except Exception:
            pass

    # ---------- Section 2: Need Immediate Assistance ----------
    def _build_assistance(self):
        banner = MDCard(orientation="vertical", padding="16dp", spacing="12dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        head = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="24dp", pos_hint={"center_x": 0.5})
        head.add_widget(MDIcon(icon="phone", theme_text_color="Custom", text_color="white", font_size="20sp", halign="center", size_hint_x=None, width="24dp", pos_hint={"center_y": 0.5}))
        head.add_widget(MDLabel(text="Need Immediate Assistance?", font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color="white", halign="center", size_hint_x=1, valign="middle"))
        banner.add_widget(head)
        banner.add_widget(MDLabel(text="Contact us directly through these channels for urgent matters", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), halign="center", adaptive_height=True))
        spacer = MDBoxLayout(size_hint_y=None, height="4dp")
        banner.add_widget(spacer)
        row = MDBoxLayout(orientation="horizontal", spacing="12dp", adaptive_height=True, size_hint_y=None, height="122dp", padding=["0dp","4dp","0dp","0dp"])
        # Dispatch — circular icon container 36dp #E8F5E9
        c1 = MDCard(orientation="vertical", padding="8dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="114dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, ripple_behavior=True)
        c1.bind(on_release=lambda x: self._stub_contact("phone"))
        _c1_icon_bg = MDCard(size_hint=(None, None), size=("36dp", "36dp"), md_bg_color=rgba("#E8F5E9"), radius=[18], elevation=0, pos_hint={"center_x": 0.5})
        _c1_icon_bg.add_widget(MDIcon(icon="phone", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="18sp", pos_hint={"center_x": 0.5, "center_y": 0.5}))
        c1.add_widget(_c1_icon_bg)
        _c1_title = MDLabel(text="Dispatch Center", font_style="Caption", font_size="9sp", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _c1_phone = MDLabel(text="+234 903 008 3790", font_style="Caption", font_size="9sp", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _c1_sub = MDLabel(text="24/7 Emergency Support", font_style="Caption", font_size="8sp", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        c1.add_widget(_c1_title)
        c1.add_widget(_c1_phone)
        c1.add_widget(_c1_sub)
        try:
            c1.bind(width=lambda inst, w, a=_c1_title, b=_c1_phone, c=_c1_sub: [setattr(a,"text_size",(w-dp(16),None)), setattr(b,"text_size",(w-dp(16),None)), setattr(c,"text_size",(w-dp(16),None))])
        except Exception:
            pass
        row.add_widget(c1)
        # WhatsApp — circular 36dp SUCCESS tint
        c2 = MDCard(orientation="vertical", padding="8dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="114dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, ripple_behavior=True)
        c2.bind(on_release=lambda x: self._stub_contact("whatsapp"))
        _c2_icon_bg = MDCard(size_hint=(None, None), size=("36dp", "36dp"), md_bg_color=rgba("#E8F5E9"), radius=[18], elevation=0, pos_hint={"center_x": 0.5})
        _c2_icon_bg.add_widget(MDIcon(icon="whatsapp", halign="center", theme_text_color="Custom", text_color=rgba(SUCCESS), font_size="18sp", pos_hint={"center_x": 0.5, "center_y": 0.5}))
        c2.add_widget(_c2_icon_bg)
        _c2_title = MDLabel(text="WhatsApp Support", font_style="Caption", font_size="9sp", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _c2_phone = MDLabel(text="+234 903 008 3790", font_style="Caption", font_size="9sp", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _c2_sub = MDLabel(text="Fastest response", font_style="Caption", font_size="8sp", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        c2.add_widget(_c2_title)
        c2.add_widget(_c2_phone)
        c2.add_widget(_c2_sub)
        try:
            c2.bind(width=lambda inst, w, a=_c2_title, b=_c2_phone, c=_c2_sub: [setattr(a,"text_size",(w-dp(16),None)), setattr(b,"text_size",(w-dp(16),None)), setattr(c,"text_size",(w-dp(16),None))])
        except Exception:
            pass
        row.add_widget(c2)
        # Email — 7sp for full email legibility, circular 36dp
        c3 = MDCard(orientation="vertical", padding="8dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="114dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, ripple_behavior=True)
        c3.bind(on_release=lambda x: self._stub_contact("email"))
        _c3_icon_bg = MDCard(size_hint=(None, None), size=("36dp", "36dp"), md_bg_color=rgba("#E8F5E9"), radius=[18], elevation=0, pos_hint={"center_x": 0.5})
        _c3_icon_bg.add_widget(MDIcon(icon="email-outline", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="18sp", pos_hint={"center_x": 0.5, "center_y": 0.5}))
        c3.add_widget(_c3_icon_bg)
        _c3_title = MDLabel(text="Email Support", font_style="Caption", font_size="9sp", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _c3_email = MDLabel(text="trackway@trackwaylogistics.ng", font_style="Caption", font_size="7sp", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _c3_sub = MDLabel(text="Response within 24h", font_style="Caption", font_size="8sp", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        c3.add_widget(_c3_title)
        c3.add_widget(_c3_email)
        c3.add_widget(_c3_sub)
        try:
            c3.bind(width=lambda inst, w, a=_c3_title, b=_c3_email, c=_c3_sub: [setattr(a,"text_size",(w-dp(16),None)), setattr(b,"text_size",(w-dp(16),None)), setattr(c,"text_size",(w-dp(16),None))])
        except Exception:
            pass
        row.add_widget(c3)
        banner.add_widget(row)
        self._content.add_widget(banner)

    def _stub_contact(self, kind):
        try:
            from kivymd.uix.snackbar import Snackbar
            if kind == "phone":
                Snackbar(text="Dispatch Center: +234 903 008 3790").open()
            elif kind == "whatsapp":
                Snackbar(text="WhatsApp: +234 903 008 3790").open()
            else:
                Snackbar(text="Email: trackway@trackwaylogistics.ng").open()
        except Exception:
            pass

    # ---------- Section 3: Quick Resources ----------
    def _build_resources(self):
        banner = MDCard(orientation="vertical", padding="16dp", spacing="12dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        banner.add_widget(MDLabel(text="ℹ️ Quick Resources", font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color="white", halign="center"))
        banner.add_widget(MDLabel(text="Helpful information for riders", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), halign="center", adaptive_height=True))
        spacer = MDBoxLayout(size_hint_y=None, height="4dp")
        banner.add_widget(spacer)
        row = MDBoxLayout(orientation="horizontal", spacing="12dp", adaptive_height=True, size_hint_y=None, height="122dp", padding=["0dp","4dp","0dp","0dp"])
        # Rider Guide — title inside card (was floating above row)
        r1 = MDCard(orientation="vertical", padding="8dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="114dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, ripple_behavior=True)
        r1.bind(on_release=lambda x: self._stub_resource("guide"))
        _r1_icon_bg = MDCard(size_hint=(None, None), size=("36dp", "36dp"), md_bg_color=rgba("#E8F5E9"), radius=[18], elevation=0, pos_hint={"center_x": 0.5})
        _r1_icon_bg.add_widget(MDIcon(icon="file-document-outline", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="18sp", pos_hint={"center_x": 0.5, "center_y": 0.5}))
        r1.add_widget(_r1_icon_bg)
        _r1_title = MDLabel(text="Rider Guide", font_style="Caption", font_size="9sp", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _r1_desc = MDLabel(text="Download the complete rider handbook", font_style="Caption", font_size="9sp", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _r1_btn = MDFlatButton(text="Download PDF", font_size="9sp", theme_text_color="Custom", text_color=rgba(PRIMARY), line_color=rgba(PRIMARY), line_width=1, md_bg_color=rgba(CARD_BG), size_hint=(None, None), size=("96dp", "26dp"), pos_hint={"center_x": 0.5}, on_release=lambda x: self._stub_resource("guide"))
        try:
            _r1_btn.radius = [14]
        except Exception:
            pass
        r1.add_widget(_r1_title)
        r1.add_widget(_r1_desc)
        r1.add_widget(_r1_btn)
        try:
            r1.bind(width=lambda inst, w, a=_r1_title, b=_r1_desc: [setattr(a,"text_size",(w-dp(16),None)), setattr(b,"text_size",(w-dp(16),None))])
        except Exception:
            pass
        row.add_widget(r1)
        r2 = MDCard(orientation="vertical", padding="8dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="114dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, ripple_behavior=True)
        r2.bind(on_release=lambda x: self._stub_resource("faq"))
        _r2_icon_bg = MDCard(size_hint=(None, None), size=("36dp", "36dp"), md_bg_color=rgba("#E8F5E9"), radius=[18], elevation=0, pos_hint={"center_x": 0.5})
        _r2_icon_bg.add_widget(MDIcon(icon="help-circle-outline", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="18sp", pos_hint={"center_x": 0.5, "center_y": 0.5}))
        r2.add_widget(_r2_icon_bg)
        _r2_title = MDLabel(text="FAQ", font_style="Caption", font_size="9sp", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _r2_desc = MDLabel(text="Frequently asked questions", font_style="Caption", font_size="9sp", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _r2_btn = MDFlatButton(text="View FAQs", font_size="9sp", theme_text_color="Custom", text_color=rgba(PRIMARY), line_color=rgba(PRIMARY), line_width=1, md_bg_color=rgba(CARD_BG), size_hint=(None, None), size=("88dp", "26dp"), pos_hint={"center_x": 0.5}, on_release=lambda x: self._stub_resource("faq"))
        try:
            _r2_btn.radius = [14]
        except Exception:
            pass
        r2.add_widget(_r2_title)
        r2.add_widget(_r2_desc)
        r2.add_widget(_r2_btn)
        try:
            r2.bind(width=lambda inst, w, a=_r2_title, b=_r2_desc: [setattr(a,"text_size",(w-dp(16),None)), setattr(b,"text_size",(w-dp(16),None))])
        except Exception:
            pass
        row.add_widget(r2)
        r3 = MDCard(orientation="vertical", padding="8dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="114dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, ripple_behavior=True)
        r3.bind(on_release=lambda x: self._stub_resource("videos"))
        _r3_icon_bg = MDCard(size_hint=(None, None), size=("36dp", "36dp"), md_bg_color=rgba("#E8F5E9"), radius=[18], elevation=0, pos_hint={"center_x": 0.5})
        _r3_icon_bg.add_widget(MDIcon(icon="video-outline", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="18sp", pos_hint={"center_x": 0.5, "center_y": 0.5}))
        r3.add_widget(_r3_icon_bg)
        _r3_title = MDLabel(text="Video Tutorials", font_style="Caption", font_size="9sp", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _r3_desc = MDLabel(text="Watch how-to guides", font_style="Caption", font_size="9sp", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, max_lines=1, shorten=True, text_size=(dp(88), None))
        _r3_btn = MDFlatButton(text="Watch Now", font_size="9sp", theme_text_color="Custom", text_color=rgba(PRIMARY), line_color=rgba(PRIMARY), line_width=1, md_bg_color=rgba(CARD_BG), size_hint=(None, None), size=("90dp", "26dp"), pos_hint={"center_x": 0.5}, on_release=lambda x: self._stub_resource("videos"))
        try:
            _r3_btn.radius = [14]
        except Exception:
            pass
        r3.add_widget(_r3_title)
        r3.add_widget(_r3_desc)
        r3.add_widget(_r3_btn)
        try:
            r3.bind(width=lambda inst, w, a=_r3_title, b=_r3_desc: [setattr(a,"text_size",(w-dp(16),None)), setattr(b,"text_size",(w-dp(16),None))])
        except Exception:
            pass
        row.add_widget(r3)
        banner.add_widget(row)
        self._content.add_widget(banner)

    def _stub_resource(self, kind):
        try:
            from kivymd.uix.snackbar import Snackbar
            if kind == "guide":
                Snackbar(text="Rider Guide — coming soon").open()
            elif kind == "faq":
                Snackbar(text="FAQs — coming soon").open()
            else:
                Snackbar(text="Video Tutorials — coming soon").open()
        except Exception:
            pass

    # ---------- Tickets history (flat, no pagination) ----------
    def _build_tickets(self):
        card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="ticket-confirmation-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Your Support Requests", font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color=DARK))
        card.add_widget(header)
        self._tickets_box = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True)
        card.add_widget(self._tickets_box)
        self._tickets_spinner = MDSpinner(size_hint=(None,None), size=("24dp","24dp"), active=False, color=rgba(PRIMARY), pos_hint={"center_x":0.5})
        card.add_widget(self._tickets_spinner)
        self._tickets_card = card
        self._content.add_widget(card)
        self._render_tickets()

    def _render_tickets(self):
        self._tickets_box.clear_widgets()
        items = getattr(self, "_tickets", []) or []
        if not items:
            empty = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, padding=["0dp","12dp","0dp","4dp"])
            empty.add_widget(MDIcon(icon="ticket-confirmation-outline", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), font_size="36sp", size_hint_y=None, height="36dp"))
            empty.add_widget(MDLabel(text="No support requests yet", font_style="Body2", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            self._tickets_box.add_widget(empty)
            return
        for t in items:
            self._tickets_box.add_widget(self._create_ticket_card(t))

    def _create_ticket_card(self, t):
        subject = t.get("subject") or t.get("title") or ""
        msg = t.get("message") or t.get("description") or ""
        status = (t.get("status") or "open").lower()
        date = t.get("created_at") or t.get("date") or ""
        if "T" in str(date):
            date = str(date).split("T")[0]
        # BUG: list.php returns type/type_name empty even when submit sends type — hide placeholder
        type_val = t.get("type_name") or t.get("type") or ""
        # Defensive: show — if empty
        if status in ("resolved", "closed", "completed"):
            chip_color = SUCCESS
        elif status in ("pending", "open", "in_progress"):
            chip_color = PRIMARY
        else:
            chip_color = MUTED
        card = MDCard(orientation="vertical", padding="12dp", spacing="6dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=0, line_color=rgba(chip_color), line_width=0.6)
        top = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp")
        top.add_widget(MDLabel(text=subject or "Support Request", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1, adaptive_height=True))
        chip = MDCard(size_hint=(None,None), size=("80dp","22dp"), md_bg_color=rgba(CARD_BG), line_color=rgba(chip_color), radius=[12], elevation=0)
        chip.add_widget(MDLabel(text=status.capitalize(), halign="center", font_style="Caption", theme_text_color="Custom", text_color=rgba(chip_color), font_size="11sp"))
        top.add_widget(chip)
        card.add_widget(top)
        # type — hide if empty or show —
        if type_val and type_val.strip():
            disp = RIDER_SUPPORT_TYPES.get(type_val.strip(), type_val.strip())
            card.add_widget(MDLabel(text=disp, font_style="Caption", theme_text_color="Custom", text_color=rgba(PRIMARY), adaptive_height=True))
        else:
            card.add_widget(MDLabel(text="—", font_style="Caption", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
        if msg:
            preview = msg[:120] + ("..." if len(msg) > 120 else "")
            card.add_widget(MDLabel(text=preview, font_style="Body2", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
        if date:
            card.add_widget(MDLabel(text=str(date), font_style="Caption", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, halign="right"))
        return card

    # ---------- Footer ----------
    def _build_footer(self):
        card = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="72dp", md_bg_color=rgba(DARK), radius=[0], elevation=0)
        card.add_widget(MDLabel(text="© 2026 Trackway Logistics. Trackway Smart Logistics. All rights reserved.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        card.add_widget(MDLabel(text="Delivering Excellence, One Parcel at a Time.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        card.add_widget(MDLabel(text="Rider Support: trackway@trackwaylogistics.ng | +234 903 008 3790", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="10sp", adaptive_height=True))
        self._content.add_widget(card)

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
        self._load_waybills()
        self._load_tickets()

    def _load_waybills(self):
        import threading
        def do():
            try:
                from app.services.rider_service import get_rider_support_waybills
                r = get_rider_support_waybills(limit=20)
                items = r.get("data", {}).get("items", []) if r.get("ok") else []
                Clock.schedule_once(lambda dt: self._on_waybills(items), 0)
            except Exception:
                Clock.schedule_once(lambda dt: self._on_waybills([]), 0)
        threading.Thread(target=do, daemon=True).start()

    def _on_waybills(self, items):
        self._waybill_items = items or []

    def _load_tickets(self):
        if getattr(self, "_loading_tickets", False):
            return
        self._loading_tickets = True
        self._tickets_spinner.active = True
        import threading
        def do():
            result = {"ok": False, "data": {"items": []}}
            try:
                from app.services.rider_service import get_rider_support_list
                result = get_rider_support_list()
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            Clock.schedule_once(lambda dt: self._on_tickets(result), 0)
        threading.Thread(target=do, daemon=True).start()

    def _on_tickets(self, result):
        self._tickets_spinner.active = False
        self._loading_tickets = False
        if result.get("ok"):
            self._tickets = result["data"].get("items", []) or []
            self._render_tickets()
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
            self._tickets = []
            self._render_tickets()
            if err and "No" not in err:
                try:
                    from kivymd.uix.snackbar import Snackbar
                    Snackbar(text=err).open()
                except Exception:
                    pass

    def rebuild_ui(self):
        try:
            self._render_tickets()
        except Exception:
            pass
