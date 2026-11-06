from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivy.uix.widget import Widget
from kivy.utils import rgba

from app.i18n.translator import tr
from app.core.theme import PRIMARY, MUTED, DARK


class HomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", padding="20dp", spacing="16dp")
        layout.add_widget(Widget())
        layout.add_widget(
            MDLabel(
                text=tr("home"),
                halign="center",
                font_style="H5",
                bold=True,
            )
        )
        layout.add_widget(Widget())
        self.add_widget(layout)


class DeliveriesScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", padding="20dp", spacing="16dp")
        layout.add_widget(Widget())
        layout.add_widget(
            MDLabel(
                text=tr("deliveries"),
                halign="center",
                font_style="H5",
                bold=True,
            )
        )
        layout.add_widget(Widget())
        self.add_widget(layout)


class TrackScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", padding="20dp", spacing="16dp")
        layout.add_widget(Widget())
        layout.add_widget(
            MDLabel(
                text=tr("track"),
                halign="center",
                font_style="H5",
                bold=True,
            )
        )
        track_btn = MDRaisedButton(
            text=tr("track_parcel_btn"),
            size_hint_x=1,
            height="48dp",
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            font_size="16sp",
            on_release=self._go_track,
        )
        layout.add_widget(track_btn)
        layout.add_widget(Widget())
        self.add_widget(layout)

    def _go_track(self, *args):
        if self.manager and hasattr(self.manager, "parent"):
            root = self.manager.parent
            while root is not None and not hasattr(root, "current"):
                root = root.parent
            if root is not None and "tracking_search" in [
                s.name for s in root.screens
            ]:
                root.current = "tracking_search"


class ProfileScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", padding="20dp", spacing="16dp")
        layout.add_widget(Widget())
        layout.add_widget(
            MDLabel(
                text=tr("profile"),
                halign="center",
                font_style="H5",
                bold=True,
            )
        )
        layout.add_widget(Widget())
        self.add_widget(layout)


class NavShell(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.screen_manager = MDScreenManager()
        self.screen_manager.add_widget(HomeScreen(name="home"))
        self.screen_manager.add_widget(DeliveriesScreen(name="deliveries"))
        self.screen_manager.add_widget(TrackScreen(name="track"))
        self.screen_manager.add_widget(ProfileScreen(name="profile"))

        self.bottom_nav = MDBottomNavigation()

        home_item = MDBottomNavigationItem(
            name="home_tab", text=tr("home"), icon="home-outline"
        )
        home_item.bind(on_release=lambda x: self._switch("home"))

        deliveries_item = MDBottomNavigationItem(
            name="deliveries_tab", text=tr("deliveries"), icon="truck-outline"
        )
        deliveries_item.bind(on_release=lambda x: self._switch("deliveries"))

        track_item = MDBottomNavigationItem(
            name="track_tab", text=tr("track"), icon="crosshairs-outline"
        )
        track_item.bind(on_release=lambda x: self._switch("track"))

        profile_item = MDBottomNavigationItem(
            name="profile_tab", text=tr("profile"), icon="account-outline"
        )
        profile_item.bind(on_release=lambda x: self._switch("profile"))

        self.bottom_nav.add_widget(home_item)
        self.bottom_nav.add_widget(deliveries_item)
        self.bottom_nav.add_widget(track_item)
        self.bottom_nav.add_widget(profile_item)

        self.add_widget(self.screen_manager)
        self.add_widget(self.bottom_nav)

        self.bottom_nav.switch_tab("home_tab")

        self.bottom_nav.panel_color = "white"
        self.bottom_nav.text_color_active = PRIMARY
        self.bottom_nav.text_color_normal = MUTED

    def _switch(self, name):
        self.screen_manager.current = name
