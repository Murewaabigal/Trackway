from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog

from app.i18n.translator import tr
from app.core.theme import PRIMARY, DARK, MUTED, BACKGROUND, CARD_BG, ERROR
from app.core.constants import STATUS_LABELS, DELIVERY_METHODS, PAYMENT_METHODS
from app.views.shared.status_timeline import StatusTimeline
from app.views.shared.waybill_card import status_color


def _format_value(v):
    if v is None:
        return "-"
    return str(v)

from app.views.base_screen import BaseScreen

class WaybillDetailScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._waybill = {}
        self._dialog = None

        outer = MDBoxLayout(orientation="vertical", padding="12dp", spacing="8dp")

        header = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp")
        back_btn = MDFlatButton(
            text="< " + tr("back"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            on_release=self._go_back,
        )
        self.title_label = MDLabel(
            text=tr("waybill_detail"),
            font_style="H6",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=DARK,
            size_hint_x=1,
            adaptive_height=True,
        )
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        header.add_widget(MDFlatButton(text=""))
        outer.add_widget(header)

        self._scroll = ScrollView()
        self._content = MDBoxLayout(
            orientation="vertical",
            spacing="12dp",
            adaptive_height=True,
            size_hint_y=None,
            padding=["2dp", "4dp"],
        )
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)
        outer.add_widget(self._scroll)

        self.add_widget(outer)

    def set_waybill(self, waybill):
        self._waybill = waybill or {}
        self._render()

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
        # If waybill was set before entering, ensure render
        if self._waybill:
            self._render()

    def _render(self):
        self._content.clear_widgets()
        wb = self._waybill or {}
        status = wb.get("status") or ""

        # Header card: waybill number + status chip
        header_card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="8dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba(CARD_BG),
            radius=[14],
            elevation=1,
        )
        top_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp")
        number_label = MDLabel(
            text=wb.get("waybill_number") or wb.get("waybill") or "",
            font_style="H6",
            bold=True,
            theme_text_color="Custom",
            text_color=DARK,
            size_hint_x=0.65,
            adaptive_height=True,
        )
        chip_label = MDLabel(
            text=tr(status) if tr(status) != status else STATUS_LABELS.get(status, status),
            font_style="Caption",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=rgba(status_color(status)),
            size_hint_x=0.35,
            adaptive_height=True,
        )
        top_row.add_widget(number_label)
        top_row.add_widget(chip_label)
        header_card.add_widget(top_row)

        route = ""
        origin = wb.get("origin") or wb.get("origin_city") or wb.get("sender_city") or ""
        destination = wb.get("destination") or wb.get("destination_city") or wb.get("recipient_city") or ""
        if origin or destination:
            route = f"{origin} \u2192 {destination}"
        route_label = MDLabel(
            text=route,
            font_style="Body2",
            theme_text_color="Custom",
            text_color=MUTED,
            adaptive_height=True,
        )
        date_text = wb.get("created_at") or wb.get("date") or wb.get("delivery_date") or ""
        if "T" in str(date_text):
            date_text = str(date_text).split("T")[0]
        date_label = MDLabel(
            text=str(date_text),
            font_style="Caption",
            theme_text_color="Custom",
            text_color=MUTED,
            adaptive_height=True,
        )
        header_card.add_widget(route_label)
        header_card.add_widget(date_label)
        self._content.add_widget(header_card)

        # Parcel details card
        parcel_card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="6dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba(CARD_BG),
            radius=[14],
            elevation=1,
        )
        parcel_card.add_widget(MDLabel(text=tr("parcel_details"), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, adaptive_height=True))
        details = [
            ("description", wb.get("description") or wb.get("parcel_description") or "-"),
            ("weight", wb.get("weight") or "-"),
            ("value", wb.get("declared_value") or wb.get("value") or "-"),
            ("delivery_method", DELIVERY_METHODS.get(wb.get("delivery_method") or "", wb.get("delivery_method") or "-")),
            ("payment_method", PAYMENT_METHODS.get(wb.get("payment_method") or "", wb.get("payment_method") or "-")),
            ("recipient_name", wb.get("recipient_name") or "-"),
            ("recipient_phone", wb.get("recipient_phone") or "-"),
        ]
        for key, val in details:
            row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp")
            lab = MDLabel(text=tr(key), font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_x=0.4, adaptive_height=True)
            val_lab = MDLabel(text=_format_value(val), font_style="Body2", theme_text_color="Custom", text_color=DARK, size_hint_x=0.6, adaptive_height=True)
            row.add_widget(lab)
            row.add_widget(val_lab)
            parcel_card.add_widget(row)
        self._content.add_widget(parcel_card)

        # Timeline card
        timeline_raw = wb.get("timeline") or wb.get("delivery_timeline") or wb.get("status_history") or []
        # Normalize to list of dicts with label/timestamp/completed
        timeline = []
        if isinstance(timeline_raw, list):
            for step in timeline_raw:
                if isinstance(step, dict):
                    label = step.get("label") or step.get("status") or step.get("title") or ""
                    # Translate label if it's a status key
                    if label in STATUS_LABELS:
                        label = tr(label) if tr(label) != label else STATUS_LABELS[label]
                    timeline.append({
                        "label": label,
                        "timestamp": step.get("timestamp") or step.get("created_at") or step.get("date") or "",
                        "completed": bool(step.get("completed", step.get("is_completed", False))),
                    })
                elif isinstance(step, str):
                    lab = tr(step) if tr(step) != step else STATUS_LABELS.get(step, step)
                    timeline.append({"label": lab, "timestamp": "", "completed": False})
        if not timeline and status:
            # Fallback single step from current status
            lab = tr(status) if tr(status) != status else STATUS_LABELS.get(status, status)
            timeline = [{"label": lab, "timestamp": str(date_text), "completed": True}]

        timeline_card = MDCard(
            orientation="vertical",
            padding="12dp",
            spacing="4dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba(CARD_BG),
            radius=[14],
            elevation=1,
        )
        timeline_card.add_widget(MDLabel(text=tr("delivery_timeline"), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, adaptive_height=True))
        if timeline:
            tl_widget = StatusTimeline(timeline=timeline)
            timeline_card.add_widget(tl_widget)
        else:
            timeline_card.add_widget(MDLabel(text=tr("no_timeline"), font_style="Body2", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
        self._content.add_widget(timeline_card)

        # Actions
        if status == "pending_pickup":
            actions_card = MDCard(
                orientation="vertical",
                padding="12dp",
                spacing="8dp",
                size_hint_x=1,
                adaptive_height=True,
                md_bg_color=rgba("#fff3e0"),
                radius=[14],
                elevation=0,
            )
            actions_card.add_widget(MDLabel(text=tr("actions"), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, adaptive_height=True))
            cancel_btn = MDRaisedButton(
                text=tr("cancel_delivery"),
                md_bg_color=rgba(ERROR),
                theme_text_color="Custom",
                text_color="white",
                size_hint_x=1,
                on_release=self._show_cancel_placeholder,
            )
            actions_card.add_widget(cancel_btn)
            self._content.add_widget(actions_card)

        # Contact support stub
        support_btn = MDFlatButton(
            text=tr("contact_support"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            pos_hint={"center_x": 0.5},
            on_release=self._show_support_placeholder,
        )
        self._content.add_widget(support_btn)

    def _show_cancel_placeholder(self, *args):
        if self._dialog:
            try:
                self._dialog.dismiss()
            except Exception:
                pass
        self._dialog = MDDialog(
            title=tr("cancel_delivery"),
            text=tr("cancel_placeholder_msg"),
            buttons=[
                MDFlatButton(text=tr("ok"), on_release=lambda x: self._dialog.dismiss()),
            ],
        )
        self._dialog.open()

    def _show_support_placeholder(self, *args):
        if self._dialog:
            try:
                self._dialog.dismiss()
            except Exception:
                pass
        self._dialog = MDDialog(
            title=tr("contact_support"),
            text=tr("contact_support_msg"),
            buttons=[
                MDFlatButton(text=tr("ok"), on_release=lambda x: self._dialog.dismiss()),
            ],
        )
        self._dialog.open()

    def rebuild_ui(self):
        try:
            from app.i18n.translator import tr
            if hasattr(self, 'title_label'):
                self.title_label.text = tr("waybill_detail")
            if self._waybill:
                self._render()
        except Exception:
            pass

    def _go_back(self, *args):
        if self.manager:
            # Prefer back to deliveries if available, else home
            if "customer_deliveries" in [s.name for s in self.manager.screens]:
                # Use previous screen heuristic: if we came from home vs deliveries, go home; else deliveries
                # For now go to customer_home
                self.manager.current = "customer_home"
            else:
                self.manager.current = "customer_home"
