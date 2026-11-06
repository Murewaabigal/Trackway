from kivy.uix.widget import Widget
from kivy.utils import rgba
from app.views.base_screen import BaseScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton

from app.i18n.translator import tr
from app.core.theme import PRIMARY, DARK, MUTED, ERROR


class RiderLoginScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(DARK)

        outer = MDBoxLayout(
            orientation="vertical",
            padding="24dp",
            spacing="12dp",
            size_hint_x=0.92,
            adaptive_height=True,
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )

        outer.add_widget(Widget())

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
            text="DELIVERY PARTNER LOGIN",
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=PRIMARY,
            size_hint_y=None,
            height="24dp",
        )
        outer.add_widget(logo)
        outer.add_widget(sub)
        outer.add_widget(Widget())

        card = MDBoxLayout(
            orientation="vertical",
            padding="24dp",
            spacing="16dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color="white",
            radius=[16],
        )

        title = MDLabel(
            text=f"[b]Rider {tr('login')}[/b]",
            font_style="H5",
            halign="center",
            markup=True,
            size_hint_y=None,
            height="40dp",
        )
        subtitle = MDLabel(
            text="Enter your credentials to access the rider portal",
            font_style="Body2",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="24dp",
        )

        self.username_field = MDTextField(
            hint_text="Username / Email / Phone",
            helper_text="Username, Email or Phone *",
            helper_text_mode="on_focus",
            icon_right="account-outline",
            size_hint_x=1,
            mode="rectangle",
        )
        self.password_field = MDTextField(
            hint_text="Enter your password",
            helper_text="Password *",
            helper_text_mode="on_focus",
            password=True,
            icon_right="eye-outline",
            size_hint_x=1,
            mode="rectangle",
        )

        self.error_label = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=ERROR,
            halign="center",
            size_hint_y=None,
            height="0dp",
        )

        login_btn = MDRaisedButton(
            text="  Login to Rider Portal",
            size_hint_x=1,
            height="48dp",
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            font_size="16sp",
            on_release=self._do_login,
        )

        forgot_btn = MDFlatButton(
            text=tr("forgot_password"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            size_hint_x=1,
            height="36dp",
            font_size="13sp",
            on_release=lambda x: self._go("forgot_password"),
        )

        divider = MDLabel(
            text="─────────────────────────",
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="20dp",
        )

        apply_btn = MDFlatButton(
            text=tr("no_account") + " Apply here",
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            size_hint_x=1,
            height="40dp",
            font_size="13sp",
            on_release=lambda x: self._show_apply_stub(),
        )

        card.add_widget(title)
        card.add_widget(subtitle)
        card.add_widget(self.username_field)
        card.add_widget(self.password_field)
        card.add_widget(self.error_label)
        card.add_widget(login_btn)
        card.add_widget(forgot_btn)
        card.add_widget(divider)
        card.add_widget(apply_btn)

        outer.add_widget(card)
        outer.add_widget(Widget())

        footer = MDLabel(
            text="© 2026 Trackway Smart Logistics",
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="30dp",
        )
        outer.add_widget(footer)

        self.add_widget(outer)

    def _do_login(self, *args):
        from app.services.auth_service import login_rider
        username = self.username_field.text.strip()
        password = self.password_field.text.strip()
        if not username or not password:
            self._show_error("Please fill in all fields")
            return
        result = login_rider(username, password)
        if result["ok"]:
            self.manager.current = "rider_home"
        else:
            self._show_error(result["error"] or "Login failed")

    def _show_error(self, msg):
        self.error_label.text = msg
        self.error_label.height = "20dp"

    def _show_apply_stub(self):
        self._show_error("Rider application coming soon — visit trackwaylogistics.ng")

    def _go(self, screen_name):
        self.manager.current = screen_name
