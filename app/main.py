from kivy.config import Config

# Force true mobile viewport for accurate sizing (360x740 mdpi primary)
Config.set("graphics", "width", "360")
Config.set("graphics", "height", "740")
Config.set("graphics", "resizable", "0")

from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager

from app.core.theme import apply_theme
from app.core import session
from app.i18n.translator import init_translator


class TrackwayApp(MDApp):
    def build(self):
        self.title = "Trackway"
        apply_theme(self)
        try:
            from app.core.session import get_language
            init_translator(get_language())
        except Exception:
            init_translator()

        sm = MDScreenManager()

        from app.views.auth.welcome_screen import WelcomeScreen
        from app.views.auth.customer_login_screen import CustomerLoginScreen
        from app.views.auth.customer_register_screen import CustomerRegisterScreen
        from app.views.auth.rider_login_screen import RiderLoginScreen
        from app.views.auth.forgot_password_screen import ForgotPasswordScreen
        from app.views.customer.customer_home_screen import CustomerHomeScreen
        from app.views.customer.customer_deliveries_screen import CustomerDeliveriesScreen
        from app.views.customer.customer_history_screen import CustomerHistoryScreen
        from app.views.customer.waybill_detail_screen import WaybillDetailScreen
        from app.views.customer.profile_screen import ProfileScreen
        from app.views.customer.notification_screen import NotificationScreen
        from app.views.customer.refer_earn_screen import ReferEarnScreen
        from app.views.customer.support_screen import SupportScreen
        from app.views.customer.request_delivery_screen import RequestDeliveryScreen
        from app.views.customer.request_ride_screen import RequestRideScreen
        from app.views.rider.rider_home_screen import RiderHomeScreen
        from app.views.rider.rider_notification_screen import RiderNotificationScreen
        from app.views.rider.rider_profile_screen import RiderProfileScreen
        from app.views.rider.rider_wallet_screen import RiderWalletScreen
        from app.views.rider.rider_earnings_screen import RiderEarningsScreen
        from app.views.rider.rider_support_screen import RiderSupportScreen
        from app.views.rider.rider_deliveries_screen import RiderDeliveriesScreen
        from app.views.shared.nav_shell import NavShell
        from app.views.shared.tracking_screen import TrackingSearchScreen
        from app.views.shared.tracking_result_screen import TrackingResultScreen

        sm.add_widget(WelcomeScreen(name="welcome"))
        sm.add_widget(CustomerLoginScreen(name="customer_login"))
        sm.add_widget(CustomerRegisterScreen(name="customer_register"))
        sm.add_widget(RiderLoginScreen(name="rider_login"))
        sm.add_widget(ForgotPasswordScreen(name="forgot_password"))
        sm.add_widget(CustomerHomeScreen(name="customer_home"))
        sm.add_widget(CustomerDeliveriesScreen(name="customer_deliveries"))
        sm.add_widget(CustomerHistoryScreen(name="customer_history"))
        sm.add_widget(WaybillDetailScreen(name="waybill_detail"))
        sm.add_widget(ProfileScreen(name="profile"))
        sm.add_widget(NotificationScreen(name="notifications"))
        sm.add_widget(ReferEarnScreen(name="refer_earn"))
        sm.add_widget(SupportScreen(name="support"))
        sm.add_widget(RequestDeliveryScreen(name="request_delivery"))
        sm.add_widget(RequestRideScreen(name="request_ride"))
        sm.add_widget(RiderHomeScreen(name="rider_home"))
        sm.add_widget(RiderNotificationScreen(name="rider_notifications"))
        sm.add_widget(RiderProfileScreen(name="rider_profile"))
        sm.add_widget(RiderWalletScreen(name="rider_wallet"))
        sm.add_widget(RiderEarningsScreen(name="rider_earnings"))
        sm.add_widget(RiderSupportScreen(name="rider_support"))
        sm.add_widget(RiderDeliveriesScreen(name="rider_deliveries"))
        sm.add_widget(TrackingSearchScreen(name="tracking_search"))
        sm.add_widget(TrackingResultScreen(name="tracking_result"))
        from kivymd.uix.screen import MDScreen as _Screen
        nav_screen = _Screen(name="nav_shell")
        nav_screen.add_widget(NavShell())
        sm.add_widget(nav_screen)

        return sm

    def on_start(self):
        # Restore persisted PHPSESSID for get-notifications.php so bell works without re-login
        try:
            from app.core.api_client import _restore_phpsessid
            _restore_phpsessid()
        except Exception:
            pass
        sess = session.load_session()
        if sess:
            role = sess.get("role")
            if role == "customer":
                self.root.current = "customer_home"
            elif role == "rider":
                self.root.current = "rider_home"
            else:
                self.root.current = "welcome"
        else:
            self.root.current = "welcome"


if __name__ == "__main__":
    TrackwayApp().run()
