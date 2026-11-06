from kivy.uix.widget import Widget
from kivy.utils import rgba
from app.views.base_screen import BaseScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton

from app.i18n.translator import tr
from app.core.theme import PRIMARY, DARK, MUTED, ERROR, SUCCESS


class ForgotPasswordScreen(BaseScreen):
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
        outer.add_widget(logo)
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
            text=f"[b]{tr('forgot_password')}[/b]",
            font_style="H5",
            halign="center",
            markup=True,
            size_hint_y=None,
            height="40dp",
        )
        subtitle = MDLabel(
            text="Enter your phone number and we'll help you reset your password",
            font_style="Body2",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="36dp",
        )

        self.phone_field = MDTextField(
            hint_text=tr("phone"),
            icon_right="phone-outline",
            size_hint_x=1,
            mode="rectangle",
        )

        send_btn = MDRaisedButton(
            text="Send Reset Link",
            size_hint_x=1,
            height="48dp",
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            font_size="16sp",
            on_release=self._send_reset,
        )

        support_label = MDLabel(
            text="Or contact support directly",
            font_style="Body2",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="24dp",
        )

        support_btn = MDFlatButton(
            text="Contact Support",
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            size_hint_x=1,
            height="40dp",
            font_size="13sp",
            on_release=lambda x: self._show_stub(),
        )

        back_btn = MDFlatButton(
            text="Back to Login",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_x=1,
            height="40dp",
            font_size="13sp",
            on_release=lambda x: self._go_back(),
        )

        self.info_label = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=MUTED,
            halign="center",
            size_hint_y=None,
            height="0dp",
        )

        card.add_widget(title)
        card.add_widget(subtitle)
        card.add_widget(self.phone_field)
        card.add_widget(self.info_label)
        card.add_widget(send_btn)
        card.add_widget(support_label)
        card.add_widget(support_btn)
        card.add_widget(back_btn)

        outer.add_widget(card)
        outer.add_widget(Widget())

        self.add_widget(outer)

    def _send_reset(self, *args):
        phone = self.phone_field.text.strip()
        if not phone:
            self._show_info("Please enter your phone number", ERROR)
            return
        self._show_info("Reset instructions sent. Check your phone.", SUCCESS)

    def _show_info(self, msg, color=MUTED):
        self.info_label.text = msg
        self.info_label.text_color = rgba(color)
        self.info_label.height = "24dp"

    def _show_stub(self):
        self._show_info("Contact support: 09041744622 / trackway@trackwaylogistics.ng")

    def _go_back(self):
        self.manager.current = "welcome"
