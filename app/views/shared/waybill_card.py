from kivy.utils import rgba
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel

from app.i18n.translator import tr
from app.core.theme import DARK, MUTED, CARD_BG, PRIMARY, ERROR, SUCCESS
from app.core.constants import STATUS_LABELS

STATUS_COLORS = {
    "pending_pickup": MUTED,
    "picked_up": PRIMARY,
    "in_transit": PRIMARY,
    "arrived_destination_city": PRIMARY,
    "out_for_delivery": PRIMARY,
    "delivered": SUCCESS,
    "failed": ERROR,
    "cancelled": ERROR,
}


def status_color(status):
    return STATUS_COLORS.get(status, "#859393")


def status_label(status):
    if status in STATUS_LABELS:
        # STATUS_LABELS gives canonical English, tr() handles i18n
        return tr(status) if tr(status) != status else STATUS_LABELS[status]
    if status in STATUS_COLORS:
        return tr(status)
    return status or ""


class WaybillCard(MDCard):
    def __init__(self, waybill=None, on_tap=None, **kwargs):
        super().__init__(
            orientation="vertical",
            padding="16dp",
            spacing="8dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=CARD_BG,
            radius=[14],
            elevation=1,
            ripple_behavior=True,
            **kwargs,
        )
        self._on_tap = on_tap
        self._waybill = waybill
        if on_tap is not None:
            self.bind(on_release=self._handle_release)

        row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing="8dp",
        )
        self.number_label = MDLabel(
            text="",
            font_style="Subtitle1",
            bold=True,
            theme_text_color="Custom",
            text_color=DARK,
            size_hint_x=0.65,
            adaptive_height=True,
        )
        self.chip_label = MDLabel(
            text="",
            font_style="Caption",
            bold=True,
            halign="center",
            size_hint_x=0.35,
            adaptive_height=True,
        )
        row.add_widget(self.number_label)
        row.add_widget(self.chip_label)
        self.add_widget(row)

        self.route_label = MDLabel(
            text="",
            font_style="Body2",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="22dp",
        )
        # Fee + date row
        fee_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing="8dp",
        )
        self.date_label = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_x=0.6,
            adaptive_height=True,
        )
        self.fee_label = MDLabel(
            text="",
            font_style="Caption",
            bold=True,
            halign="right",
            theme_text_color="Custom",
            text_color=DARK,
            size_hint_x=0.4,
            adaptive_height=True,
        )
        fee_row.add_widget(self.date_label)
        fee_row.add_widget(self.fee_label)
        self.add_widget(self.route_label)
        self.add_widget(fee_row)

        if waybill is not None:
            self.set_waybill(waybill)

    def _handle_release(self, *args):
        if self._on_tap:
            try:
                self._on_tap(self._waybill)
            except TypeError:
                self._on_tap()

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and self._on_tap and touch.grab_current is self:
            return super().on_touch_up(touch)
        return super().on_touch_up(touch)

    def set_waybill(self, waybill):
        self._waybill = waybill or {}
        wb = self._waybill
        status = wb.get("status") or ""
        self.number_label.text = wb.get("waybill_number") or ""
        self.chip_label.text = status_label(status)
        self.chip_label.text_color = rgba(status_color(status))

        origin = wb.get("origin") or wb.get("origin_city") or ""
        destination = wb.get("destination") or wb.get("destination_city") or ""
        self.route_label.text = f"{origin} \u2192 {destination}" if (origin or destination) else ""

        created = wb.get("created_at") or wb.get("date") or wb.get("delivery_date") or ""
        self.date_label.text = self._format_date(created)
        fee = wb.get("fee") or wb.get("price") or wb.get("amount") or ""
        if fee:
            try:
                # Format as currency if numeric
                f = float(str(fee).replace(",", "").replace("\u20a6", "").strip())
                self.fee_label.text = f"\u20a6{f:,.2f}"
            except Exception:
                self.fee_label.text = str(fee)
        else:
            self.fee_label.text = ""

    def _format_date(self, value):
        if not value:
            return ""
        text = str(value)
        if "T" in text:
            text = text.split("T")[0]
        return text
