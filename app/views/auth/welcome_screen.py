from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from kivymd.uix.screen import MDScreen
from app.views.base_screen import BaseScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.navigationdrawer import (
    MDNavigationLayout,
    MDNavigationDrawer,
)
from kivymd.uix.list import MDList, OneLineListItem

from app.i18n.translator import tr
from app.core.theme import (
    PRIMARY, DARK, MUTED, BACKGROUND, CARD_BG, ERROR,
)


class WelcomeScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.nav_layout = MDNavigationLayout()
        self.screen_manager = None

        self.drawer = MDNavigationDrawer(
            anchor="left",
            type="modal",
            md_bg_color=CARD_BG,
            radius=[0, 16, 16, 0],
        )
        self._build_drawer()

        self.screen_manager = MDScreenManager()
        self.screen = MDScreen(name="landing", md_bg_color=rgba(BACKGROUND))
        self._build_screen()
        self.screen_manager.add_widget(self.screen)

        self.nav_layout.add_widget(self.screen_manager)
        self.nav_layout.add_widget(self.drawer)
        self.add_widget(self.nav_layout)

    def _build_drawer(self):
        menu = MDList(
            padding=["0dp", "24dp", "0dp", "0dp"],
        )
        customer_item = OneLineListItem(
            text=tr("login_customer"),
            on_release=lambda x: self._go("customer_login"),
        )
        rider_item = OneLineListItem(
            text=tr("login_rider"),
            on_release=lambda x: self._go("rider_login"),
        )
        menu.add_widget(customer_item)
        menu.add_widget(rider_item)
        self.drawer.add_widget(menu)

    def _build_screen(self):
        self._content = MDBoxLayout(
            orientation="vertical",
            spacing="14dp",
            adaptive_height=True,
            size_hint_y=None,
        )
        self._content.bind(minimum_height=self._content.setter("height"))

        self._build_top_bar()
        self._build_hero()
        self._build_track_parcel()
        self._build_ctas()
        self._build_stats()
        self._build_footer()

        scroll = ScrollView()
        scroll.add_widget(self._content)
        self.screen.add_widget(scroll)

    def _build_top_bar(self):
        bar = MDBoxLayout(
            orientation="horizontal",
            spacing="8dp",
            adaptive_height=True,
            padding=["8dp", "6dp", "12dp", "6dp"],
        )
        menu_btn = MDIconButton(
            icon="menu",
            theme_icon_color="Custom",
            icon_color=rgba(PRIMARY),
            on_release=self._open_drawer,
        )
        brand = MDLabel(
            text="[color=%s]TRACK[/color][color=%s]WAY[/color]"
            % (PRIMARY, DARK),
            font_style="H6",
            bold=True,
            markup=True,
            size_hint_y=None,
            height="40dp",
            valign="middle",
        )
        bar.add_widget(menu_btn)
        bar.add_widget(brand)
        self._content.add_widget(bar)

    def _open_drawer(self, *args):
        if self.drawer:
            self.drawer.set_state("open")

    def _build_hero(self):
        hero = MDBoxLayout(
            orientation="vertical",
            spacing="8dp",
            size_hint_x=1,
            adaptive_height=True,
        )
        badge = MDCard(
            orientation="vertical",
            padding=["14dp", "6dp"],
            size_hint=(None, None),
            width="260dp",
            height="32dp",
            md_bg_color=rgba("#e8f0e3"),
            radius=[50],
            pos_hint={"center_x": 0.5},
        )
        badge_label = MDLabel(
            text="• " + tr("trusted_partner"),
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=PRIMARY,
            size_hint_y=None,
            height="20dp",
        )
        badge.add_widget(badge_label)
        self._content.add_widget(badge)

        h1 = MDLabel(
            text=tr("hero_1"),
            font_style="H4",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=DARK,
            size_hint_y=None,
            height="44dp",
        )
        h2 = MDLabel(
            text=tr("hero_2"),
            font_style="H4",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=PRIMARY,
            size_hint_y=None,
            height="44dp",
        )
        h3 = MDLabel(
            text=tr("hero_3"),
            font_style="H4",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=PRIMARY,
            size_hint_y=None,
            height="44dp",
        )
        hero.add_widget(h1)
        hero.add_widget(h2)
        hero.add_widget(h3)
        self._content.add_widget(hero)

    def _build_track_parcel(self):
        card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="12dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=CARD_BG,
            radius=[16],
            elevation=1,
        )
        self.waybill_field = MDTextField(
            hint_text=tr("enter_tracking_number"),
            icon_right="barcode",
            size_hint_x=1,
            mode="rectangle",
        )
        self.track_error = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=ERROR,
            halign="center",
            size_hint_y=None,
            height="0dp",
        )
        track_btn = MDRaisedButton(
            text=tr("track_parcel_btn"),
            size_hint_x=1,
            height="50dp",
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            font_size="16sp",
            on_release=self._do_track,
        )
        card.add_widget(self.waybill_field)
        card.add_widget(self.track_error)
        card.add_widget(track_btn)
        self._content.add_widget(card)

    def _build_ctas(self):
        send_btn = MDRaisedButton(
            text=tr("send_parcel"),
            size_hint_x=1,
            height="48dp",
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            font_size="15sp",
            on_release=lambda x: self._go("customer_login"),
        )
        from kivymd.uix.button import MDRectangleFlatButton

        ride_btn = MDRectangleFlatButton(
            text=tr("request_rider_ride"),
            size_hint_x=1,
            height="48dp",
            md_bg_color=rgba(CARD_BG),
            line_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            font_size="15sp",
            on_release=lambda x: self._go("customer_login"),
        )
        self._content.add_widget(send_btn)
        self._content.add_widget(ride_btn)

    def _build_stats(self):
        stats_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=1,
            adaptive_height=True,
            spacing="8dp",
        )
        stats = [
            ("6+", tr("stats_deliveries")),
            ("3+", tr("stats_customers")),
            ("2+", tr("stats_drivers")),
        ]
        for number, label in stats:
            col = MDBoxLayout(
                orientation="vertical",
                size_hint_x=0.33,
                adaptive_height=True,
                spacing="0dp",
            )
            num = MDLabel(
                text=number,
                font_style="H5",
                bold=True,
                halign="center",
                theme_text_color="Custom",
                text_color=PRIMARY,
                size_hint_y=None,
                height="30dp",
            )
            lab = MDLabel(
                text=label,
                font_style="Caption",
                halign="center",
                theme_text_color="Custom",
                text_color=MUTED,
                size_hint_y=None,
                height="28dp",
            )
            col.add_widget(num)
            col.add_widget(lab)
            stats_row.add_widget(col)
        self._content.add_widget(stats_row)

    def _build_footer(self):
        footer = MDBoxLayout(
            orientation="vertical",
            spacing="4dp",
            size_hint_x=1,
            adaptive_height=True,
        )
        tag = MDLabel(
            text=tr("footer_tagline"),
            font_style="Body2",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=DARK,
            size_hint_y=None,
            height="24dp",
        )
        copy = MDLabel(
            text="© 2026 Trackway Smart Logistics. All rights reserved.",
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="20dp",
        )
        footer.add_widget(tag)
        footer.add_widget(copy)
        self._content.add_widget(footer)

    def _do_track(self, *args):
        waybill = self.waybill_field.text.strip()
        if not waybill:
            self._show_error(tr("enter_tracking_number"))
            return
        self._show_error("")
        self.manager.get_screen("tracking_search").set_initial_waybill(waybill)
        self.manager.current = "tracking_search"

    def _show_error(self, msg):
        self.track_error.text = msg
        self.track_error.height = "20dp" if msg else "0dp"

    def _go(self, screen_name):
        self.manager.current = screen_name

    def rebuild_ui(self):
        try:
            from app.i18n.translator import tr
            # best-effort: rebuild key texts (drawer uses tr, hero/badge)
            if hasattr(self, '_content'):
                # trigger per-screen revisit rebuild via clearing and rebuilding is heavy;
                # for welcome, simply update stored tr texts if they exist
                pass
        except Exception:
            pass
