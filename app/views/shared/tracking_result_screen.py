from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from app.views.base_screen import BaseScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFlatButton

from app.i18n.translator import tr
from app.core.theme import PRIMARY, DARK, MUTED, CARD_BG
from app.views.shared.status_timeline import StatusTimeline


class TrackingResultScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(DARK)
        self._built = False

    def on_pre_enter(self):
        if not self._built:
            self._build_ui()
            self._built = True

    def _build_ui(self):
        self._scroll = ScrollView()
        self._content = MDBoxLayout(
            orientation="vertical",
            padding="16dp",
            spacing="16dp",
            size_hint_x=1,
            adaptive_height=True,
            size_hint_y=None,
        )
        self._content.bind(minimum_height=self._content.setter("height"))

        self._header = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=1,
            adaptive_height=True,
            padding=[0, "8dp"],
        )
        self._back_btn = MDFlatButton(
            text="< " + tr("back"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            on_release=self._go_back,
        )
        self._header.add_widget(self._back_btn)
        self._header.add_widget(MDLabel())

        self._status_card = MDBoxLayout(
            orientation="vertical",
            padding="20dp",
            spacing="8dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color="white",
            radius=[16],
        )

        self._status_label = MDLabel(
            text="",
            font_style="H5",
            halign="center",
            bold=True,
            size_hint_y=None,
            height="36dp",
        )
        self._waybill_label = MDLabel(
            text="",
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="20dp",
        )
        self._route_label = MDLabel(
            text="",
            font_style="Body1",
            halign="center",
            size_hint_y=None,
            height="28dp",
        )
        self._sender_recipient = MDLabel(
            text="",
            font_style="Body2",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="24dp",
        )
        self._eta_label = MDLabel(
            text="",
            font_style="Body2",
            halign="center",
            theme_text_color="Custom",
            text_color=PRIMARY,
            size_hint_y=None,
            height="24dp",
        )

        self._status_card.add_widget(self._status_label)
        self._status_card.add_widget(self._waybill_label)
        self._status_card.add_widget(self._route_label)
        self._status_card.add_widget(self._sender_recipient)
        self._status_card.add_widget(self._eta_label)

        self._timeline_card = MDBoxLayout(
            orientation="vertical",
            padding="16dp",
            spacing="4dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color="white",
            radius=[16],
        )
        self._timeline_title = MDLabel(
            text="[b]Delivery Timeline[/b]",
            font_style="Body1",
            markup=True,
            size_hint_y=None,
            height="28dp",
            padding=["8dp", 0],
        )
        self._timeline_widget = StatusTimeline()
        self._timeline_card.add_widget(self._timeline_title)
        self._timeline_card.add_widget(self._timeline_widget)

        self._content.add_widget(self._header)
        self._content.add_widget(self._status_card)
        self._content.add_widget(self._timeline_card)
        self._content.add_widget(MDLabel(size_hint_y=None, height="16dp"))

        self._scroll.add_widget(self._content)
        self.add_widget(self._scroll)

    def set_data(self, data):
        if not self._built:
            self._build_ui()

        status = data.get("current_status", "")
        status_label = data.get("status_label", status.replace("_", " ").title())
        color = self._status_color(status)
        self._status_label.text = f"[color={color}]{status_label}[/color]"
        self._status_label.markup = True

        self._waybill_label.text = data.get("waybill_number", "")

        origin = data.get("origin_city", "")
        dest = data.get("destination_city", "")
        self._route_label.text = f"{origin}  ->  {dest}" if origin and dest else ""

        sender = data.get("sender_name", "")
        recipient = data.get("recipient_name", "")
        if sender and recipient:
            self._sender_recipient.text = f"From {sender} to {recipient}"
        else:
            self._sender_recipient.text = ""

        eta = data.get("estimated_delivery", "")
        if eta:
            self._eta_label.text = f"Estimated Delivery: {eta}"
        else:
            self._eta_label.text = ""

        timeline = data.get("timeline", [])
        if timeline:
            self._timeline_widget.set_timeline(timeline)
            self._timeline_card.opacity = 1
            self._timeline_card.disabled = False
        else:
            self._timeline_widget.set_timeline([])
            self._timeline_card.opacity = 0
            self._timeline_card.disabled = True

    def _status_color(self, status):
        colors = {
            "pending_pickup": "#859393",
            "picked_up": "#567f30",
            "in_transit": "#567f30",
            "arrived_destination_city": "#567f30",
            "out_for_delivery": "#567f30",
            "delivered": "#388e3c",
            "failed": "#d32f2f",
            "cancelled": "#d32f2f",
        }
        return colors.get(status, "#859393")

    def _go_back(self, *args):
        self.manager.current = "tracking_search"
