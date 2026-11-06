import re
from datetime import datetime

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu

from app.core.theme import PRIMARY, PRIMARY_DARK, DARK, MUTED, BACKGROUND, CARD_BG, SUCCESS, ERROR
from app.core import session
from app.i18n.translator import tr
from app.views.base_screen import BaseScreen

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email(v):
    return bool(v and EMAIL_RE.match(v.strip()))


def _format_date(val):
    if not val or val == "-":
        return "-"
    raw = str(val).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d %b %Y", "%b %d, %Y", "%d %B %Y"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%d %b %Y")
        except Exception:
            continue
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return raw


class RiderProfileScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._data = {}
        self._profile_menu = None
        self._loading = False

        self._outer = MDBoxLayout(orientation="vertical", spacing="0dp")
        self._scroll = ScrollView(do_scroll_x=False, bar_width=dp(4), size_hint_y=1, effect_cls="DampedScrollEffect")
        try:
            self._scroll.effect_y.allow_overscroll = False
            self._scroll.effect_x.allow_overscroll = False
        except Exception:
            pass
        self._content = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp", adaptive_height=True, size_hint_y=None)
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        self._outer.add_widget(self._build_top_nav())
        self._outer.add_widget(self._scroll)
        self.add_widget(self._outer)

        self._build_banner()
        self._build_personal_info()
        self._build_change_password()
        self._build_vehicle_info()
        self._build_metrics()
        self._build_account_status()
        self._build_footer()

        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

    # ---------- Top nav ----------
    def _build_top_nav(self):
        nav = MDCard(orientation="horizontal", padding="6dp", spacing="6dp", size_hint_x=1, size_hint_y=None, height="48dp", md_bg_color=rgba(CARD_BG), radius=[0], elevation=2)
        logo_box = MDBoxLayout(orientation="vertical", size_hint_x=1, size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5}, spacing="0dp")
        _track = MDLabel(text="TRACKWAY", font_style="Subtitle2", bold=True, font_size="12sp", theme_text_color="Custom", text_color=DARK, size_hint_y=None, height="16dp", halign="left", shorten=True, shorten_from="right", max_lines=1)
        _smart = MDLabel(text="SMART LOGISTICS", font_style="Caption", font_size="6.5sp", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="9dp", halign="left", shorten=False, max_lines=1)
        logo_box.add_widget(_track)
        logo_box.add_widget(_smart)
        try:
            logo_box.bind(width=lambda inst, w, lbl=_smart: setattr(lbl, "text_size", (w - dp(4), None)))
            _smart.text_size = (logo_box.width - dp(4), None) if logo_box.width else (dp(90), None)
        except Exception:
            pass
        right = MDBoxLayout(orientation="horizontal", size_hint_x=None, width="250dp", spacing="6dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        try:
            from app.views.shared.language_picker import LanguagePicker
            lp = LanguagePicker(compact=True)
            lp.size_hint_x = None
            lp.width = "36dp"
            right.add_widget(lp)
        except Exception:
            right.add_widget(MDLabel(text="EN", font_style="Caption", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=None, width="32dp", halign="center"))
        dash_btn = MDFlatButton(text="← Dashboard", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="12sp", size_hint_x=None, width="90dp", on_release=lambda x: self._go_dashboard())
        right.add_widget(dash_btn)
        avatar = MDCard(size_hint=(None,None), size=("28dp","28dp"), md_bg_color=rgba(PRIMARY), radius=[14], elevation=0, ripple_behavior=True, pos_hint={"center_y": 0.5})
        avatar.add_widget(MDLabel(text="A", halign="center", theme_text_color="Custom", text_color="white", bold=True))
        right.add_widget(avatar)
        self._avatar_card = avatar
        name_card = MDCard(size_hint=(None,None), size=("90dp","32dp"), md_bg_color=[0,0,0,0], radius=[6], elevation=0, ripple_behavior=True, pos_hint={"center_y": 0.5})
        self.top_name_label = MDLabel(text="", font_style="Caption", bold=True, theme_text_color="Custom", text_color=DARK, halign="left")
        name_card.add_widget(self.top_name_label)
        right.add_widget(name_card)
        self._name_card = name_card
        avatar.bind(on_release=lambda x: self._open_profile_menu())
        name_card.bind(on_release=lambda x: self._open_profile_menu())
        nav.add_widget(logo_box)
        nav.add_widget(right)
        self._top_nav = nav
        return nav

    def _create_profile_menu(self):
        if hasattr(self, "_profile_menu") and self._profile_menu:
            return
        items = [
            {"text": "My Profile", "leading_icon": "account-outline", "on_release": lambda: self._menu_navigate("rider_profile")},
            {"text": "My Wallet", "leading_icon": "wallet-outline", "on_release": lambda: self._menu_navigate("rider_wallet")},
            {"text": "Earnings", "leading_icon": "cash", "on_release": lambda: self._menu_navigate("rider_earnings")},
            {"text": "Support", "leading_icon": "headset", "on_release": lambda: self._menu_navigate("rider_support")},
            {"text": "Notifications", "leading_icon": "bell-outline", "on_release": lambda: self._menu_navigate("rider_notifications")},
            {"viewclass": "MDSeparator", "height": dp(1)},
            {"text": "Logout", "leading_icon": "logout", "text_color": rgba(ERROR), "leading_icon_color": rgba(ERROR), "on_release": lambda: self._menu_logout()},
        ]
        caller = getattr(self, "_avatar_card", self._top_nav)
        self._profile_menu = MDDropdownMenu(caller=caller, items=items, width_mult=4, max_height="320dp", border_margin=dp(8))

    def _open_profile_menu(self, *args):
        try:
            self._create_profile_menu()
            self._profile_menu.caller = getattr(self, "_avatar_card", self._top_nav)
            self._profile_menu.open()
        except Exception:
            pass

    def _menu_navigate(self, route):
        try:
            if self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", route) if self.manager else None, 0.15)

    def _menu_coming_soon(self, label):
        try:
            if self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text=f"{label} — coming soon").open()
        except Exception:
            pass

    def _menu_logout(self):
        try:
            if self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        def do(dt):
            try:
                from app.services.auth_service import logout
                logout()
            except Exception:
                try:
                    session.clear_session()
                except Exception:
                    pass
            if self.manager:
                self.manager.current = "welcome"
        Clock.schedule_once(do, 0.2)

    def _go_dashboard(self, *args):
        if self.manager:
            self.manager.current = "rider_home"

    def _on_window_width(self, instance, width):
        try:
            hide = width < 360
            if hasattr(self, "top_name_label"):
                self.top_name_label.opacity = 0 if hide else 1
        except Exception:
            pass

    # ---------- Section 1 Banner ----------
    def _build_banner(self):
        self._banner = MDCard(orientation="vertical", padding="16dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=1)
        # large circular avatar centered
        avatar_wrap = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, size_hint_x=1)
        self._banner_avatar = MDCard(size_hint=(None,None), size=("72dp","72dp"), md_bg_color=rgba(PRIMARY_DARK), radius=[36], elevation=0, pos_hint={"center_x": 0.5})
        self._banner_initial = MDLabel(text="A", halign="center", valign="middle", theme_text_color="Custom", text_color="white", bold=True, font_style="H4")
        self._banner_avatar.add_widget(self._banner_initial)
        avatar_wrap.add_widget(self._banner_avatar)
        self._banner_name = MDLabel(text="", font_style="H6", bold=True, theme_text_color="Custom", text_color="white", halign="center", adaptive_height=True)
        avatar_wrap.add_widget(self._banner_name)
        # pill
        pill_wrap = MDBoxLayout(orientation="horizontal", adaptive_height=True, size_hint_x=1, size_hint_y=None, height="22dp", spacing="4dp")
        pill_wrap.add_widget(MDLabel(text=""))
        self._banner_pill_card = MDCard(size_hint=(None,None), size=("160dp","22dp"), md_bg_color=rgba("#e8f0e3"), radius=[11], elevation=0, pos_hint={"center_x": 0.5})
        self._banner_pill = MDLabel(text="", halign="center", font_style="Caption", font_size="11sp", bold=True, theme_text_color="Custom", text_color=rgba(PRIMARY_DARK))
        self._banner_pill_card.add_widget(self._banner_pill)
        pill_wrap.add_widget(self._banner_pill_card)
        pill_wrap.add_widget(MDLabel(text=""))
        avatar_wrap.add_widget(pill_wrap)
        # two info rows side by side: Rider ID and Joined
        info_row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_x=1, padding=["0dp","6dp","0dp","0dp"])
        self._banner_rider_id = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), halign="center", adaptive_height=True, size_hint_x=1, font_size="11sp")
        self._banner_joined = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), halign="center", adaptive_height=True, size_hint_x=1, font_size="11sp")
        info_row.add_widget(self._banner_rider_id)
        info_row.add_widget(self._banner_joined)
        avatar_wrap.add_widget(info_row)
        self._banner.add_widget(avatar_wrap)
        self._content.add_widget(self._banner)

    # ---------- Section 2 Personal Information ----------
    def _build_personal_info(self):
        card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="account-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Personal Information", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        card.add_widget(header)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="2dp", md_bg_color=rgba(PRIMARY)))
        grid = GridLayout(cols=2, spacing="12dp", size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        self._pi_name = MDTextField(hint_text="Full Name", mode="rectangle")
        self._pi_username = MDTextField(hint_text="Username", mode="rectangle", disabled=True, helper_text="Cannot be changed", helper_text_mode="on_focus")
        self._pi_phone = MDTextField(hint_text="Phone Number", mode="rectangle")
        self._pi_email = MDTextField(hint_text="Email Address", helper_text="Used for notifications and password recovery", helper_text_mode="on_focus", mode="rectangle")
        grid.add_widget(self._pi_name)
        grid.add_widget(self._pi_username)
        grid.add_widget(self._pi_phone)
        grid.add_widget(self._pi_email)
        card.add_widget(grid)
        btn_wrap = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_y=None, height="36dp", padding=["0dp","4dp","0dp","0dp"])
        btn_wrap.add_widget(MDLabel(text=""))
        self._pi_save_btn = MDRaisedButton(text="Save Changes", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="140dp", on_release=lambda x: self._save_personal_info())
        btn_wrap.add_widget(self._pi_save_btn)
        card.add_widget(btn_wrap)
        self._pi_status = MDLabel(text="", font_style="Caption", halign="center", theme_text_color="Custom", text_color=SUCCESS, size_hint_y=None, height="0dp")
        card.add_widget(self._pi_status)
        self._personal_card = card
        self._content.add_widget(card)

    def _save_personal_info(self, *args):
        full_name = self._pi_name.text.strip()
        phone = self._pi_phone.text.strip()
        email = self._pi_email.text.strip()
        if not full_name or not phone:
            self._show_pi_error("Full Name and Phone are required")
            return
        if email and not _is_valid_email(email):
            self._show_pi_error("Please provide a valid email")
            return
        self._pi_save_btn.disabled = True
        self._pi_status.text = "Saving..."
        self._pi_status.text_color = rgba(MUTED)
        self._pi_status.height = "20dp"
        import threading
        def do():
            result = {"ok": False, "error": "Failed"}
            try:
                from app.services.rider_service import update_rider_profile
                result = update_rider_profile({"full_name": full_name, "phone": phone, "email": email})
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            Clock.schedule_once(lambda dt: self._on_pi_saved(result, full_name, phone, email), 0)
        threading.Thread(target=do, daemon=True).start()

    def _on_pi_saved(self, result, full_name, phone, email):
        self._pi_save_btn.disabled = False
        if result.get("ok"):
            msg = result.get("data", {}).get("message") if isinstance(result.get("data"), dict) else None
            display = msg or result.get("error") or "Profile updated"
            # success may be in error field if alert-success parsed as ok True with message in data
            if "updated" in str(display).lower() or "success" in str(display).lower() or result.get("ok"):
                self._pi_status.text = "Profile updated"
                self._pi_status.text_color = rgba(SUCCESS)
                self._pi_status.height = "20dp"
                Clock.schedule_once(lambda dt: setattr(self._pi_status, "height", 0), 2.5)
                self._data.update({"full_name": full_name, "phone": phone, "email": email})
                self._render_banner()
                try:
                    # update session name
                    session.save_tokens(session.get_access_token(), session.get_refresh_token(), session.get_role(), full_name)
                    self.top_name_label.text = full_name
                except Exception:
                    pass
                try:
                    from kivymd.uix.snackbar import Snackbar
                    Snackbar(text="Profile updated").open()
                except Exception:
                    pass
            else:
                self._show_pi_error(display)
        else:
            err = result.get("error") or "Update failed"
            self._show_pi_error(err)

    def _show_pi_error(self, msg):
        self._pi_status.text = msg
        self._pi_status.text_color = rgba(ERROR)
        self._pi_status.height = "24dp"

    # ---------- Section 3 Change Password ----------
    def _build_change_password(self):
        card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="lock-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Change Password", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        card.add_widget(header)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="2dp", md_bg_color=rgba(PRIMARY)))
        grid = GridLayout(cols=3, spacing="12dp", size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        # Use size_hint_y None to align
        self._cp_current = MDTextField(hint_text="Current Password", password=True, mode="rectangle")
        self._cp_new = MDTextField(hint_text="New Password", password=True, helper_text="Minimum 6 characters", helper_text_mode="on_focus", mode="rectangle")
        self._cp_confirm = MDTextField(hint_text="Confirm New Password", password=True, mode="rectangle")
        # simpler: on mobile 3 cols may be narrow, but keep as per web spec; on < 500dp fallback to 1 col via _on_window_width
        grid.add_widget(self._cp_current)
        grid.add_widget(self._cp_new)
        grid.add_widget(self._cp_confirm)
        card.add_widget(grid)
        self._cp_grid = grid
        row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="36dp", padding=["0dp","4dp","0dp","0dp"])
        self._cp_btn = MDRaisedButton(text="Change Password", md_bg_color=rgba(PRIMARY_DARK), theme_text_color="Custom", text_color="white", on_release=lambda x: self._do_change_password())
        row.add_widget(self._cp_btn)
        row.add_widget(MDLabel(text=""))
        card.add_widget(row)
        self._cp_status = MDLabel(text="", font_style="Caption", halign="center", theme_text_color="Custom", text_color=ERROR, size_hint_y=None, height="0dp")
        card.add_widget(self._cp_status)
        self._content.add_widget(card)

    def _do_change_password(self, *args):
        cur = self._cp_current.text.strip()
        new = self._cp_new.text.strip()
        conf = self._cp_confirm.text.strip()
        if not cur or not new or not conf:
            self._cp_status.text = "Please fill all password fields"
            self._cp_status.height = "20dp"
            self._cp_status.text_color = rgba(ERROR)
            return
        if len(new) < 6:
            self._cp_status.text = "Minimum 6 characters"
            self._cp_status.height = "20dp"
            self._cp_status.text_color = rgba(ERROR)
            return
        if new == cur:
            self._cp_status.text = "New password must be different from current"
            self._cp_status.height = "20dp"
            self._cp_status.text_color = rgba(ERROR)
            return
        if new != conf:
            self._cp_status.text = "Passwords do not match"
            self._cp_status.height = "20dp"
            self._cp_status.text_color = rgba(ERROR)
            return
        self._cp_btn.disabled = True
        self._cp_status.text = "Updating..."
        self._cp_status.text_color = rgba(MUTED)
        self._cp_status.height = "20dp"
        import threading
        def do():
            result = {"ok": False, "error": "Failed"}
            try:
                from app.services.rider_service import change_rider_password
                result = change_rider_password({"current_password": cur, "new_password": new, "confirm_password": conf})
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            Clock.schedule_once(lambda dt: self._on_cp_done(result), 0)
        threading.Thread(target=do, daemon=True).start()

    def _on_cp_done(self, result):
        self._cp_btn.disabled = False
        if result.get("ok"):
            # success message may be in data.message
            msg = ""
            if isinstance(result.get("data"), dict):
                msg = result["data"].get("message") or ""
            display = msg or result.get("error") or "Password changed successfully"
            # check if actually success text
            if "incorrect" in display.lower() or "error" in display.lower() or "failed" in display.lower():
                self._cp_status.text = display
                self._cp_status.text_color = rgba(ERROR)
                self._cp_status.height = "24dp"
                return
            self._cp_status.text = ""
            self._cp_status.height = "0dp"
            self._cp_current.text = ""; self._cp_new.text = ""; self._cp_confirm.text = ""
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text="Password changed successfully").open()
            except Exception:
                pass
        else:
            err = result.get("error") or "Password change failed"
            self._cp_status.text = err
            self._cp_status.text_color = rgba(ERROR)
            self._cp_status.height = "24dp"

    # ---------- Section 4 Vehicle Information ----------
    def _build_vehicle_info(self):
        card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="motorbike", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Vehicle Information", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        card.add_widget(header)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="2dp", md_bg_color=rgba(PRIMARY)))
        self._vehicle_grid = GridLayout(cols=2, spacing="8dp", size_hint_y=None)
        self._vehicle_grid.bind(minimum_height=self._vehicle_grid.setter("height"))
        card.add_widget(self._vehicle_grid)
        self._vehicle_card = card
        self._content.add_widget(card)
        self._render_vehicle()

    def _render_vehicle(self):
        try:
            self._vehicle_grid.clear_widgets()
        except Exception:
            pass
        v = (self._data.get("vehicle") or {}) if isinstance(self._data, dict) else {}
        items = [
            ("Vehicle Type", v.get("vehicle_type") or "N/A"),
            ("Bike Ownership", v.get("bike_ownership") or "N/A"),
            ("Bike Model", v.get("bike_model") or "N/A"),
            ("Plate Number", v.get("plate_number") or "N/A"),
        ]
        for title, value in items:
            c = MDCard(orientation="vertical", padding="10dp", spacing="4dp", size_hint_y=None, height="64dp", md_bg_color=rgba(CARD_BG), radius=[10], elevation=0, line_color=rgba("#e0e0e0"), line_width=1)
            c.add_widget(MDLabel(text=title, font_style="Caption", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, font_size="11sp"))
            c.add_widget(MDLabel(text=str(value), font_style="Body2", bold=True, theme_text_color="Custom", text_color=DARK, adaptive_height=True))
            self._vehicle_grid.add_widget(c)

    # ---------- Section 5 Performance Metrics ----------
    def _build_metrics(self):
        card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="chart-line", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Performance Metrics", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        card.add_widget(header)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="2dp", md_bg_color=rgba(PRIMARY)))
        # 3 large blocks
        self._metrics_top = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="80dp")
        card.add_widget(self._metrics_top)
        # 4 smaller
        self._metrics_bottom = GridLayout(cols=4, spacing="8dp", size_hint_y=None)
        self._metrics_bottom.bind(minimum_height=self._metrics_bottom.setter("height"))
        card.add_widget(self._metrics_bottom)
        self._metrics_card = card
        self._content.add_widget(card)
        self._render_metrics()

    def _render_metrics(self):
        try:
            self._metrics_top.clear_widgets()
            self._metrics_bottom.clear_widgets()
        except Exception:
            pass
        m = (self._data.get("metrics") or {}) if isinstance(self._data, dict) else {}
        # top 3
        top_items = [
            ("Total Deliveries", str(m.get("total_deliveries", 0)), DARK, None),
            ("Completed", str(m.get("completed", 0)), SUCCESS, None),
            ("Rating", str(m.get("rating", "0.0")), DARK, "star"),
        ]
        for label, value, color, icon in top_items:
            c = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="80dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=0, line_color=rgba("#e0e0e0"), line_width=1)
            row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="4dp")
            val_lbl = MDLabel(text=value, font_style="H6", bold=True, theme_text_color="Custom", text_color=rgba(color) if isinstance(color, str) else color, halign="center", adaptive_height=True)
            row.add_widget(val_lbl)
            if icon:
                row.add_widget(MDIcon(icon=icon, theme_text_color="Custom", text_color=rgba("#FFB300"), font_size="18sp", size_hint_x=None, width="20dp"))
            lab = MDLabel(text=label, font_style="Caption", theme_text_color="Custom", text_color=MUTED, halign="center", adaptive_height=True, font_size="11sp")
            c.add_widget(row)
            c.add_widget(lab)
            self._metrics_top.add_widget(c)
        # bottom 4
        bottom_items = [
            ("Active", str(m.get("active", 0)), DARK),
            ("Failed", str(m.get("failed", 0)), ERROR),
            ("Cancelled", str(m.get("cancelled", 0)), DARK),
            ("Total Earnings", str(m.get("total_earnings", "0.00")), SUCCESS),
        ]
        for label, value, color in bottom_items:
            c = MDCard(orientation="vertical", padding="10dp", spacing="4dp", size_hint_y=None, height="64dp", md_bg_color=rgba(CARD_BG), radius=[10], elevation=0, line_color=rgba("#e0e0e0"), line_width=1)
            # earnings needs ₦ prefix if not present
            disp = value
            if label == "Total Earnings" and "₦" not in str(value):
                disp = f"₦{value}"
            val_color = color
            c.add_widget(MDLabel(text=disp, font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color=rgba(val_color) if isinstance(val_color, str) else val_color, halign="center", adaptive_height=True))
            c.add_widget(MDLabel(text=label, font_style="Caption", theme_text_color="Custom", text_color=MUTED, halign="center", adaptive_height=True, font_size="10sp"))
            self._metrics_bottom.add_widget(c)

    # ---------- Section 6 Account Status ----------
    def _build_account_status(self):
        card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="shield-check-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Account Status", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        card.add_widget(header)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="2dp", md_bg_color=rgba(PRIMARY)))
        self._account_grid = GridLayout(cols=2, spacing="8dp", size_hint_y=None)
        self._account_grid.bind(minimum_height=self._account_grid.setter("height"))
        card.add_widget(self._account_grid)
        self._account_card = card
        self._content.add_widget(card)
        self._render_account()

    def _render_account(self):
        try:
            self._account_grid.clear_widgets()
        except Exception:
            pass
        a = (self._data.get("account") or {}) if isinstance(self._data, dict) else {}
        items = [
            ("Account Status", a.get("account_status") or "Active"),
            ("Verification Status", a.get("verification_status") or "Verified"),
            ("Last Login", a.get("last_login") or "-"),
            ("Member Since", a.get("member_since") or "-"),
        ]
        for title, value in items:
            c = MDCard(orientation="vertical", padding="10dp", spacing="4dp", size_hint_y=None, height="70dp", md_bg_color=rgba(CARD_BG), radius=[10], elevation=0, line_color=rgba("#e0e0e0"), line_width=1)
            c.add_widget(MDLabel(text=title, font_style="Caption", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, font_size="11sp"))
            val = str(value)
            if title == "Account Status":
                is_active = "active" in val.lower()
                txt = "● Active" if is_active else val
                col = SUCCESS if is_active else MUTED
                c.add_widget(MDLabel(text=txt, font_style="Body2", bold=True, theme_text_color="Custom", text_color=rgba(col), adaptive_height=True))
            elif title == "Verification Status":
                is_v = "verif" in val.lower()
                txt = "✓ Verified" if is_v else val
                col = SUCCESS if is_v else MUTED
                c.add_widget(MDLabel(text=txt, font_style="Body2", bold=True, theme_text_color="Custom", text_color=rgba(col), adaptive_height=True))
            else:
                c.add_widget(MDLabel(text=val, font_style="Body2", bold=True, theme_text_color="Custom", text_color=DARK, adaptive_height=True, font_size="12sp"))
            self._account_grid.add_widget(c)

    def _build_footer(self):
        footer = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="56dp", md_bg_color=rgba(DARK), radius=[0], elevation=0)
        footer.add_widget(MDLabel(text="© 2026 Trackway Logistics. Trackway Smart Logistics. All rights reserved.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        footer.add_widget(MDLabel(text="Delivering Excellence, One Parcel at a Time.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        self._content.add_widget(footer)

    # ---------- Helpers ----------
    def _render_banner(self):
        d = self._data or {}
        name = d.get("full_name") or ""
        self._banner_name.text = name or "Rider"
        initial = (name.strip()[0].upper() if name else "A")
        self._banner_initial.text = initial
        try:
            self._avatar_card.children[0].text = initial
        except Exception:
            pass
        try:
            self.top_name_label.text = name
        except Exception:
            pass
        pill = d.get("vehicle_pill") or "Rider"
        if pill and "🏍" not in pill:
            pill = f"🏍 {pill}"
        self._banner_pill.text = pill
        rid = d.get("rider_id") or ""
        self._banner_rider_id.text = f"Rider ID: {rid}" if rid else ""
        joined = d.get("joined") or d.get("account", {}).get("member_since") or ""
        self._banner_joined.text = f"Joined {joined}" if joined else ""

    def _render_all(self):
        self._render_banner()
        try:
            self._pi_name.text = self._data.get("full_name") or ""
            self._pi_username.text = self._data.get("username") or ""
            self._pi_phone.text = self._data.get("phone") or ""
            self._pi_email.text = self._data.get("email") or ""
        except Exception:
            pass
        self._render_vehicle()
        self._render_metrics()
        self._render_account()

    # ---------- Lifecycle ----------
    def on_pre_enter(self, *args):
        from app.core import session as _sess
        if not _sess.is_logged_in() or _sess.get_role() != "rider":
            if self.manager:
                self.manager.current = "rider_login"
            return
        super().on_pre_enter(*args)

    def on_enter(self, *args):
        from app.core import session as _sess
        if not _sess.is_logged_in() or _sess.get_role() != "rider":
            if self.manager:
                self.manager.current = "rider_login"
            return
        self._load_profile()

    def _load_profile(self):
        if self._loading:
            return
        self._loading = True
        import threading
        def do():
            data = {}
            err = None
            try:
                from app.services.rider_service import get_rider_profile
                r = get_rider_profile()
                if r.get("ok"):
                    data = r.get("data") or {}
                else:
                    err = r.get("error")
                    # keep raw_html if available for debug
                    if isinstance(r.get("data"), dict) and r["data"].get("raw_html"):
                        data = {"raw_html": r["data"]["raw_html"]}
            except Exception as e:
                err = str(e)
            Clock.schedule_once(lambda dt: self._apply_profile(data, err), 0)
        threading.Thread(target=do, daemon=True).start()

    def _apply_profile(self, data, err):
        self._loading = False
        if data and isinstance(data, dict) and (data.get("full_name") or data.get("rider_id") or data.get("phone")):
            self._data = data
            self._render_all()
        else:
            # fallback: try to show session name at least
            try:
                name = session.get_customer_name() or ""
                if name:
                    self._data.setdefault("full_name", name)
                    self._render_banner()
            except Exception:
                pass
            if err and "Session expired" in str(err):
                try:
                    session.clear_session()
                except Exception:
                    pass
                if self.manager:
                    self.manager.current = "rider_login"
        try:
            self._on_window_width(Window, Window.width if hasattr(Window, "width") else 360)
        except Exception:
            pass

    def rebuild_ui(self):
        try:
            self._render_all()
        except Exception:
            pass
