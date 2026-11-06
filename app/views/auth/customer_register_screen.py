import re

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from app.views.base_screen import BaseScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy.uix.boxlayout import BoxLayout

from app.i18n.translator import tr
from app.core.theme import PRIMARY, DARK, MUTED, ERROR, SUCCESS

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email(v):
    return bool(v and EMAIL_RE.match(v.strip()))


class CustomerRegisterScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(DARK)

        root = MDBoxLayout(orientation="vertical")
        scroll = ScrollView(do_scroll_x=False, bar_width="4dp", effect_cls="ScrollEffect")
        anchor = AnchorLayout(anchor_x="center", anchor_y="top", size_hint_y=None)
        content = MDBoxLayout(
            orientation="vertical",
            padding="24dp",
            spacing="12dp",
            size_hint_x=0.92,
            adaptive_height=True,
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))
        content.bind(height=anchor.setter("height"))

        content.add_widget(Widget(size_hint_y=None, height="24dp"))

        logo = MDLabel(
            text="TRACKWAY",
            font_style="H5",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color="white",
            size_hint_y=None,
            height="40dp",
        )
        sub = MDLabel(
            text="CUSTOMER PORTAL",
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=PRIMARY,
            size_hint_y=None,
            height="24dp",
        )
        content.add_widget(logo)
        content.add_widget(sub)
        content.add_widget(Widget(size_hint_y=None, height="12dp"))

        card = MDBoxLayout(
            orientation="vertical",
            padding="24dp",
            spacing="14dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color="white",
            radius=[16],
        )

        title = MDLabel(
            text=f"[b]{tr('register')}[/b]",
            font_style="H5",
            halign="center",
            markup=True,
            size_hint_y=None,
            height="40dp",
        )
        subtitle = MDLabel(
            text="Create your Trackway account",
            font_style="Body2",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="24dp",
        )

        self.name_field = MDTextField(
            hint_text=tr("full_name"),
            icon_right="account-outline",
            size_hint_x=1,
            mode="rectangle",
        )
        self.phone_field = MDTextField(
            hint_text=tr("phone"),
            icon_right="phone-outline",
            size_hint_x=1,
            mode="rectangle",
        )
        self.email_field = MDTextField(
            hint_text=tr("email"),
            icon_right="email-outline",
            size_hint_x=1,
            mode="rectangle",
        )
        self.password_field = MDTextField(
            hint_text=tr("password"),
            password=True,
            icon_right="lock-outline",
            size_hint_x=1,
            mode="rectangle",
        )
        self.confirm_field = MDTextField(
            hint_text=tr("confirm_password"),
            password=True,
            icon_right="lock-outline",
            size_hint_x=1,
            mode="rectangle",
        )
        # Referral tinted box – matches web: light green rgba(86,127,48,0.04), gift icon + inline Apply via check-referral.php
        self.referral_field = MDTextField(
            hint_text=tr("referral_code"),
            icon_right="gift-outline",
            size_hint_x=1,
            mode="rectangle",
        )
        self.referral_apply_btn = MDRaisedButton(
            text="✓ Apply",
            size_hint=(None, None),
            size=("84dp", "48dp"),
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            font_size="13sp",
            on_release=lambda x: self._check_referral(),
        )
        self.referral_status_label = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=MUTED,
            halign="left",
            size_hint_y=None,
            height="0dp",
            text_size=(None, None),
        )
        referral_input_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height="48dp",
            spacing="8dp",
        )
        referral_input_row.add_widget(self.referral_field)
        referral_input_row.add_widget(self.referral_apply_btn)

        referral_header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height="24dp",
            spacing="6dp",
        )
        referral_header.add_widget(
            MDLabel(
                text="Have a referral code? Enter it below to get started!",
                font_style="Caption",
                theme_text_color="Custom",
                text_color=DARK,
                halign="left",
                valign="center",
                size_hint_y=None,
                height="24dp",
            )
        )

        self.referral_box = MDBoxLayout(
            orientation="vertical",
            padding="12dp",
            spacing="6dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=[0.337, 0.498, 0.188, 0.04],
            radius=[12],
        )
        self.referral_box.add_widget(referral_header)
        self.referral_box.add_widget(referral_input_row)
        self.referral_box.add_widget(
            MDLabel(
                text="Enter a referral code to connect with the person who referred you.",
                font_style="Caption",
                theme_text_color="Custom",
                text_color=MUTED,
                halign="left",
                size_hint_y=None,
                height="20dp",
                text_size=(None, None),
            )
        )
        self.referral_box.add_widget(self.referral_status_label)

        # send_welcome_email checkbox – matches web's checkbox but default off: backend mail unreliable even with valid email (confirmed live, not client validation) – TODO backend mail fix
        self.welcome_checkbox = MDCheckbox(
            size_hint=(None, None),
            size=("28dp", "28dp"),
            active=False,
        )
        self.welcome_label = MDLabel(
            text="Send welcome email",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=MUTED,
            halign="left",
            valign="center",
            size_hint_y=None,
            height="28dp",
        )
        self.welcome_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height="32dp",
            spacing="8dp",
            padding=[4, 0, 0, 0],
        )
        self.welcome_row.add_widget(self.welcome_checkbox)
        self.welcome_row.add_widget(self.welcome_label)

        self.welcome_box = MDBoxLayout(
            orientation="vertical",
            padding="12dp",
            spacing="6dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=[0.337, 0.498, 0.188, 0.04],
            radius=[12],
        )
        self.welcome_box.add_widget(self.welcome_row)
        # Update label text to match web spec exactly
        self.welcome_label.text = "Send welcome email with login credentials"
        self.welcome_box.add_widget(
            MDLabel(
                text="A welcome email will be sent to your email address with your login credentials and account details.",
                font_style="Caption",
                theme_text_color="Custom",
                text_color=MUTED,
                halign="left",
                size_hint_y=None,
                height="28dp",
                text_size=(None, None),
            )
        )

        self.success_label = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=SUCCESS,
            halign="center",
            size_hint_y=None,
            height="0dp",
            text_size=(None, None),
        )
        self.warning_label = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=MUTED,
            halign="center",
            size_hint_y=None,
            height="0dp",
            text_size=(None, None),
        )
        self.error_label = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=ERROR,
            halign="center",
            size_hint_y=None,
            height="0dp",
            text_size=(None, None),
        )

        self.register_btn = MDRaisedButton(
            text=tr("create_account"),
            size_hint_x=1,
            height="48dp",
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            font_size="16sp",
            on_release=self._do_register,
        )
        # Proceed button shown only after success (with or without warning) – requires manual tap per web UX
        self.proceed_login_btn = MDRaisedButton(
            text=tr("login"),
            size_hint_x=1,
            height="0dp",
            opacity=0,
            disabled=True,
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            font_size="16sp",
            on_release=lambda x: self._go("customer_login"),
        )

        login_btn = MDFlatButton(
            text=tr("already_have_account") + " " + tr("login"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            size_hint_x=1,
            height="40dp",
            font_size="13sp",
            on_release=lambda x: self._go("customer_login"),
        )

        card.add_widget(title)
        card.add_widget(subtitle)
        card.add_widget(self.name_field)
        card.add_widget(self.phone_field)
        card.add_widget(self.email_field)
        card.add_widget(self.password_field)
        card.add_widget(self.confirm_field)
        card.add_widget(self.referral_box)
        card.add_widget(self.welcome_box)
        card.add_widget(self.success_label)
        card.add_widget(self.warning_label)
        card.add_widget(self.error_label)
        card.add_widget(self.register_btn)
        card.add_widget(self.proceed_login_btn)
        card.add_widget(login_btn)

        content.add_widget(card)
        content.add_widget(Widget(size_hint_y=None, height="24dp"))

        anchor.add_widget(content)
        scroll.add_widget(anchor)
        root.add_widget(scroll)

        self.add_widget(root)
        # Update welcome checkbox state when email changes – mirrors web HTML5 validation UX
        try:
            self.email_field.bind(text=lambda inst, val: self._update_welcome_state())
            self.welcome_checkbox.bind(active=lambda inst, val: self._update_welcome_state())
            self.referral_field.bind(text=lambda inst, val: self._clear_referral_status())
        except Exception:
            pass
        self._update_welcome_state()

    def _update_welcome_state(self):
        # Visual hint: if checkbox checked but email invalid, keep checkbox enabled but highlight label
        # Do not silently uncheck – user explicitly chose to send email, so show block later on submit
        try:
            if self.welcome_checkbox.active and not _is_valid_email(self.email_field.text):
                self.welcome_label.text_color = ERROR
            else:
                self.welcome_label.text_color = MUTED
        except Exception:
            pass

    def _clear_referral_status(self, *args):
        try:
            self.referral_status_label.text = ""
            self.referral_status_label.height = "0dp"
        except Exception:
            pass

    def _check_referral(self, *args):
        from app.services.auth_service import check_referral

        code = self.referral_field.text.strip()
        if not code:
            self.referral_status_label.text = "Please enter referral code"
            self.referral_status_label.text_color = ERROR
            self.referral_status_label.height = "20dp"
            self.referral_status_label.halign = "left"
            return
        # Disable button while checking
        try:
            self.referral_apply_btn.disabled = True
            self.referral_status_label.text = "Checking..."
            self.referral_status_label.text_color = MUTED
            self.referral_status_label.height = "20dp"
        except Exception:
            pass
        result = check_referral(code)
        # Real message from backend – JSON or HTML alert span via api_client parser
        if result.get("ok"):
            data = result.get("data") or {}
            # Try to extract referrer name from various keys
            name = None
            if isinstance(data, dict):
                name = (
                    data.get("referrer_name")
                    or data.get("referrer")
                    or data.get("name")
                    or data.get("full_name")
                    or (data.get("data") or {}).get("referrer_name") if isinstance(data.get("data"), dict) else None
                )
                if not name:
                    nested = data.get("data") if isinstance(data.get("data"), dict) else None
                    if nested:
                        name = nested.get("name") or nested.get("referrer_name")
                msg = data.get("message") or data.get("msg") or ""
                if not name and msg:
                    # Sometimes message itself contains referrer info
                    name = msg
            display = f"✓ {name}" if name else "✓ Referral code valid"
            self.referral_status_label.text = display
            self.referral_status_label.text_color = SUCCESS
            self.referral_status_label.height = "20dp" if len(display) <= 40 else "36dp"
            self.referral_status_label.halign = "left"
            self.referral_field.line_color_focus = SUCCESS
        else:
            err = result.get("error") or "Invalid referral code"
            self.referral_status_label.text = err
            self.referral_status_label.text_color = ERROR
            self.referral_status_label.height = "36dp" if len(err) > 40 else "20dp"
            self.referral_status_label.halign = "left"
            self.referral_status_label.text_size = (self.referral_status_label.width or 280, None)
        try:
            self.referral_apply_btn.disabled = False
        except Exception:
            pass

    def _do_register(self, *args):
        from app.services.auth_service import register_customer
        name = self.name_field.text.strip()
        phone = self.phone_field.text.strip()
        email = self.email_field.text.strip() or None
        password = self.password_field.text.strip()
        confirm = self.confirm_field.text.strip()
        referral = self.referral_field.text.strip() or None
        send_welcome = bool(self.welcome_checkbox.active)

        if not name or not phone or not password:
            self._show_error("Please fill in all required fields")
            return
        if password != confirm:
            self._show_error("Passwords do not match")
            return
        # Hard block – matches web HTML5 validation: checked requires valid email, do not silently override
        if send_welcome and not _is_valid_email(email or ""):
            self._show_error("Please provide a valid email address to send welcome email, or uncheck 'Send welcome email'.")
            self._update_welcome_state()
            return

        # profile_picture not yet from UI – pass None for now (wiring deferred)
        result = register_customer(name, phone, password, confirm, email, referral, send_welcome_email=send_welcome, profile_picture_path=None)
        if result["ok"]:
            # Stay on page, show success + optional warning, require manual Login tap – matches web
            warning = result.get("warning")
            # Try to pick server message if available
            data = result.get("data") or {}
            server_msg = None
            if isinstance(data, dict):
                server_msg = data.get("message") or data.get("msg") or (data.get("data") or {}).get("message") if isinstance(data.get("data"), dict) else None
            success_msg = server_msg or "Account created successfully. Please log in."
            if warning:
                self._show_success_with_warning(success_msg, warning)
            else:
                self._show_success(success_msg)
        else:
            # Now surfaces field-level errors like "phone: already taken" (api_client surfaced errors)
            import json as _json
            from kivy.logger import Logger as _Logger
            try:
                _Logger.info(f"Register failed: {result['error']} | data={_json.dumps(result.get('data') or {}, default=str)[:800]}")
            except Exception:
                pass
            self._show_error(result["error"] or "Registration failed")

    def _show_error(self, msg):
        self.error_label.text = msg
        # Wrap to max 2 lines: 1 line=20dp, 2 lines=36dp, enable text wrapping
        self.error_label.text_size = (self.error_label.width or 280, None)
        # Bind wrapping on next layout pass
        try:
            self.error_label.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        except Exception:
            pass
        # Estimate lines by length; 38 chars ~ 1 line at card width 0.92*screen
        self.error_label.height = "36dp" if len(msg) > 38 else "20dp"
        self.error_label.halign = "center"
        # Clear success/warning, keep register button visible
        self._clear_success_warning()
        self._set_enter_success_state(False)

    def _show_success(self, msg):
        self.success_label.text = msg
        self.success_label.text_size = (self.success_label.width or 280, None)
        try:
            self.success_label.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        except Exception:
            pass
        self.success_label.height = "36dp" if len(msg) > 38 else "20dp"
        self.success_label.halign = "center"
        self.warning_label.text = ""
        self.warning_label.height = "0dp"
        self.error_label.text = ""
        self.error_label.height = "0dp"
        self._set_enter_success_state(True)

    def _show_success_with_warning(self, success_msg, warning_msg):
        self.success_label.text = success_msg
        self.success_label.text_size = (self.success_label.width or 280, None)
        try:
            self.success_label.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        except Exception:
            pass
        self.success_label.height = "36dp" if len(success_msg) > 38 else "20dp"
        self.success_label.halign = "center"
        self.warning_label.text = warning_msg
        self.warning_label.text_size = (self.warning_label.width or 280, None)
        try:
            self.warning_label.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        except Exception:
            pass
        self.warning_label.height = "36dp" if len(warning_msg) > 38 else "20dp"
        self.warning_label.halign = "center"
        self.error_label.text = ""
        self.error_label.height = "0dp"
        self._set_enter_success_state(True)

    def _clear_success_warning(self):
        self.success_label.text = ""
        self.success_label.height = "0dp"
        self.warning_label.text = ""
        self.warning_label.height = "0dp"

    def _set_enter_success_state(self, success):
        if success:
            # Hide register, show proceed Login button
            self.register_btn.disabled = True
            self.register_btn.opacity = 0
            self.register_btn.height = "0dp"
            self.proceed_login_btn.disabled = False
            self.proceed_login_btn.opacity = 1
            self.proceed_login_btn.height = "48dp"
        else:
            self.register_btn.disabled = False
            self.register_btn.opacity = 1
            self.register_btn.height = "48dp"
            self.proceed_login_btn.disabled = True
            self.proceed_login_btn.opacity = 0
            self.proceed_login_btn.height = "0dp"

    def _go(self, screen_name):
        self.manager.current = screen_name
