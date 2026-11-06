from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.utils import rgba
from app.views.base_screen import BaseScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.card import MDCard

from app.i18n.translator import tr
from app.core.session import is_logged_in
from app.core.theme import PRIMARY, MUTED, ERROR, BACKGROUND, CARD_BG, DARK


class TrackingSearchScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._pending_waybill = None

        self._scroll = ScrollView()
        self._content = MDBoxLayout(
            orientation="vertical",
            padding="20dp",
            spacing="14dp",
            adaptive_height=True,
            size_hint_y=None,
        )
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)
        self.add_widget(self._scroll)

        self._build_header()
        self._build_search()
        self._build_footer()

    def _build_header(self):
        header = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=1,
            adaptive_height=True,
        )
        back_btn = MDFlatButton(
            text="< " + tr("back"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            on_release=self._go_back,
        )
        title = MDLabel(
            text=tr("track_parcel_btn"),
            font_style="H6",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=DARK,
            size_hint_y=None,
            height="44dp",
        )
        header.add_widget(back_btn)
        header.add_widget(title)
        header.add_widget(Widget())
        self._content.add_widget(header)

    def _build_search(self):
        card = MDCard(
            orientation="vertical",
            padding="20dp",
            spacing="14dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=CARD_BG,
            radius=[16],
            elevation=2,
            pos_hint={"center_x": 0.5},
        )

        heading = MDLabel(
            text="[b]" + tr("track_parcel_btn") + "[/b]",
            font_style="H5",
            markup=True,
            halign="center",
            size_hint_y=None,
            height="38dp",
        )
        sub = MDLabel(
            text=tr("enter_tracking_number"),
            font_style="Body2",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="24dp",
        )

        self.waybill_field = MDTextField(
            hint_text=tr("waybill_number"),
            icon_right="barcode",
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

        search_btn = MDRaisedButton(
            text=tr("search"),
            size_hint_x=1,
            height="48dp",
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            font_size="16sp",
            on_release=self._do_search,
        )

        card.add_widget(heading)
        card.add_widget(sub)
        card.add_widget(self.waybill_field)
        card.add_widget(self.error_label)
        card.add_widget(search_btn)

        card_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=1,
            adaptive_height=True,
        )
        card_row.add_widget(Widget())
        card_row.add_widget(card)
        card_row.add_widget(Widget())

        self._content.add_widget(card_row)

    def _build_footer(self):
        footer = MDLabel(
            text=tr("track_login_required"),
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="24dp",
        )
        self._content.add_widget(footer)

    def set_initial_waybill(self, waybill):
        self.waybill_field.text = waybill or ""

    def on_pre_enter(self, *args):
        if self._pending_waybill:
            waybill = self._pending_waybill
            self._pending_waybill = None
            self.waybill_field.text = waybill
            if not is_logged_in():
                self._show_error(tr("track_login_required"))
                return
            self._run_search(waybill)

    def _do_search(self, *args):
        waybill = self.waybill_field.text.strip()
        if not waybill:
            self._show_error(tr("enter_tracking_number"))
            return

        self._show_error("")
        if not is_logged_in():
            self._pending_waybill = waybill
            self.manager.current = "customer_login"
            return

        self._run_search(waybill)

    def _run_search(self, waybill):
        from app.services.tracking_service import track_waybill

        if not is_logged_in():
            self._pending_waybill = waybill
            self.manager.current = "customer_login"
            return

        result = track_waybill(waybill)
        if result["ok"]:
            self.manager.get_screen("tracking_result").set_data(result["data"])
            self.manager.current = "tracking_result"
        else:
            error = (result["error"] or "").lower()
            if not is_logged_in() or "token" in error or "unauthorized" in error or "401" in error:
                self._pending_waybill = waybill
                self.manager.current = "customer_login"
            else:
                self._show_error(result["error"] or tr("waybill_not_found"))

    def _show_error(self, msg):
        self.error_label.text = msg
        self.error_label.height = "20dp" if msg else "0dp"

    def _go_back(self, *args):
        self.manager.current = "welcome"
