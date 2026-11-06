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
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu

from app.core.theme import PRIMARY, PRIMARY_DARK, DARK, MUTED, BACKGROUND, CARD_BG, SUCCESS, ERROR
from app.core import session
from app.i18n.translator import tr
from app.views.base_screen import BaseScreen
from app.views.shared.waybill_card import WaybillCard
from app.views.shared.language_picker import LanguagePicker

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email(v):
    return bool(v and EMAIL_RE.match(v.strip()))


def _format_created_at(val):
    if not val:
        return "-"
    raw = str(val).strip()
    # Try common formats: 2026-08-11T09:00:00Z, 2026-08-11 09:00:00, 2026-08-11
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%b %d, %Y")
        except Exception:
            continue
    try:
        # Fallback fromisoformat with Z handling
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return raw


class ProfileScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._customer = {}
        self._statistics = {}
        self._recent = []
        self._profile_menu = None

        # Outer layout: fixed top nav + scrollable content
        self._outer = MDBoxLayout(orientation="vertical")
        self._scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self._content = MDBoxLayout(
            orientation="vertical",
            padding="12dp",
            spacing="12dp",
            adaptive_height=True,
            size_hint_y=None,
        )
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)

        top_nav = self._build_top_nav()
        self._outer.add_widget(top_nav)
        self._outer.add_widget(self._scroll)
        self.add_widget(self._outer)

        # Build sections placeholders
        self._build_hero()
        self._build_stats()
        self._build_recent_deliveries()
        self._build_personal_info()
        self._build_change_password()
        self._build_account_info()
        self._build_footer()

        # Window width binding for name hide
        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

    # ---------- Top nav (spec 1) ----------
    def _build_top_nav(self):
        nav = MDCard(
            orientation="horizontal",
            padding="6dp",
            spacing="8dp",
            size_hint_x=1,
            size_hint_y=None,
            height="48dp",
            md_bg_color=rgba(CARD_BG),
            radius=[0],
            elevation=1,
        )
        logo = MDLabel(
            text="TRACKWAY / SMART LOGISTICS",
            font_style="Subtitle2",
            bold=True,
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            size_hint_x=1,
            size_hint_y=None,
            height="32dp",
            pos_hint={"center_y": 0.5},
            valign="middle",
        )
        right_cluster = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=None,
            width="230dp",
            spacing="8dp",
            size_hint_y=None,
            height="32dp",
            pos_hint={"center_y": 0.5},
        )
        try:
            self.language_picker = LanguagePicker(compact=True)
            self.language_picker.size_hint_x = None
            self.language_picker.width = "36dp"
            right_cluster.add_widget(self.language_picker)
        except Exception:
            right_cluster.add_widget(MDLabel(text="EN", font_style="Caption", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=None, width="32dp", halign="center"))

        # Dashboard back button (spec 1)
        dash_btn = MDFlatButton(
            text="← Dashboard",
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            font_size="12sp",
            size_hint_x=None,
            width="90dp",
            on_release=lambda x: self._go_dashboard(),
        )
        right_cluster.add_widget(dash_btn)

        avatar = MDCard(
            size_hint=(None, None),
            size=("28dp", "28dp"),
            md_bg_color=rgba(PRIMARY),
            radius=[14],
            elevation=0,
            ripple_behavior=True,
            pos_hint={"center_y": 0.5},
        )
        avatar.add_widget(MDLabel(text="A", halign="center", valign="middle", theme_text_color="Custom", text_color="white", bold=True))
        right_cluster.add_widget(avatar)
        self._avatar_card = avatar

        name_card = MDCard(
            size_hint=(None, None),
            size=("70dp", "32dp"),
            md_bg_color=[0, 0, 0, 0],
            radius=[6],
            elevation=0,
            ripple_behavior=True,
            pos_hint={"center_y": 0.5},
        )
        self.top_name_label = MDLabel(
            text="",
            font_style="Caption",
            bold=True,
            theme_text_color="Custom",
            text_color=DARK,
            halign="left",
            valign="middle",
        )
        name_card.add_widget(self.top_name_label)
        right_cluster.add_widget(name_card)
        self._name_card = name_card

        avatar.bind(on_release=lambda x: self._open_profile_menu())
        name_card.bind(on_release=lambda x: self._open_profile_menu())

        nav.add_widget(logo)
        nav.add_widget(right_cluster)
        self._top_nav = nav
        return nav

    def _create_profile_menu(self):
        if hasattr(self, "_profile_menu") and self._profile_menu:
            return
        items = [
            {"text": "My Profile", "leading_icon": "account-outline", "on_release": lambda: self._menu_navigate("profile")},
            {"text": "Refer & Earn", "leading_icon": "gift-outline", "on_release": lambda: self._menu_action_refer()},
            {"text": "Support", "leading_icon": "headset", "on_release": lambda: self._menu_action_support()},
            {"text": "Notifications", "leading_icon": "bell-outline", "on_release": lambda: self._menu_navigate("notifications")},
            {"text": "Full History", "leading_icon": "history", "on_release": lambda: self._menu_navigate("customer_history")},
            {"viewclass": "MDSeparator", "height": dp(1)},
            {"text": "Logout", "leading_icon": "logout", "text_color": rgba(ERROR), "leading_icon_color": rgba(ERROR), "on_release": lambda: self._menu_logout()},
        ]
        caller = getattr(self, "_avatar_card", self._top_nav)
        self._profile_menu = MDDropdownMenu(caller=caller, items=items, width_mult=4, max_height="320dp")

    def _open_profile_menu(self, *args):
        try:
            self._create_profile_menu()
            self._profile_menu.caller = getattr(self, "_avatar_card", self._top_nav)
            self._profile_menu.open()
        except Exception:
            self._go_profile()

    def _menu_navigate(self, route):
        try:
            if hasattr(self, "_profile_menu") and self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", route) if self.manager else None, 0.15)

    def _menu_action_refer(self):
        try:
            self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", "refer_earn") if self.manager else None, 0.2)

    def _menu_action_support(self):
        try:
            self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", "support") if self.manager else None, 0.2)

    def _menu_logout(self):
        try:
            self._profile_menu.dismiss()
        except Exception:
            pass

        def do_logout(dt):
            try:
                from app.services.auth_service import logout
                logout()
            except Exception:
                try:
                    from app.core import session
                    session.clear_session()
                except Exception:
                    pass
            if self.manager:
                self.manager.current = "welcome"

        Clock.schedule_once(do_logout, 0.2)

    def _go_profile(self, *args):
        if self.manager:
            self.manager.current = "profile"

    def _go_dashboard(self, *args):
        if self.manager:
            self.manager.current = "customer_home"

    def _on_window_width(self, instance, width):
        try:
            hide = width < 360
            if hasattr(self, "top_name_label"):
                self.top_name_label.opacity = 0 if hide else 1
                self.top_name_label.disabled = hide
        except Exception:
            pass

    # ---------- Hero banner (spec 2) ----------
    def _build_hero(self):
        self._hero_card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="8dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba(PRIMARY),
            radius=[14],
            elevation=1,
        )
        # Avatar row
        avatar_row = MDBoxLayout(orientation="horizontal", spacing="12dp", adaptive_height=True, size_hint_y=None, height="64dp")
        self._hero_avatar = MDCard(
            size_hint=(None, None),
            size=("64dp", "64dp"),
            md_bg_color=rgba(PRIMARY_DARK),
            radius=[32],
            elevation=0,
        )
        self._hero_initial = MDLabel(text="A", halign="center", valign="middle", theme_text_color="Custom", text_color="white", bold=True, font_style="H5")
        self._hero_avatar.add_widget(self._hero_initial)
        avatar_row.add_widget(self._hero_avatar)

        hero_text = MDBoxLayout(orientation="vertical", spacing="2dp", adaptive_height=True)
        self._hero_name = MDLabel(text="", font_style="H6", bold=True, theme_text_color="Custom", text_color="white", adaptive_height=True)
        self._hero_contact_row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="20dp")
        self._hero_phone = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), size_hint_x=None, width="110dp")
        self._hero_email = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), size_hint_x=None, width="150dp")
        self._hero_verified = MDLabel(text="Verified", font_style="Caption", bold=True, theme_text_color="Custom", text_color=rgba(SUCCESS), size_hint_x=None, width="60dp", halign="center")
        # Verified badge card
        verified_card = MDCard(size_hint=(None, None), size=("60dp", "20dp"), md_bg_color=rgba("#e8f0e3"), radius=[8], elevation=0)
        verified_card.add_widget(MDLabel(text="Verified", halign="center", font_style="Caption", theme_text_color="Custom", text_color=rgba(SUCCESS), font_size="10sp"))
        self._hero_contact_row.add_widget(self._hero_phone)
        self._hero_contact_row.add_widget(self._hero_email)
        self._hero_contact_row.add_widget(verified_card)
        self._hero_verified_card = verified_card

        self._hero_member = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), adaptive_height=True)

        hero_text.add_widget(self._hero_name)
        hero_text.add_widget(self._hero_contact_row)
        hero_text.add_widget(self._hero_member)
        avatar_row.add_widget(hero_text)

        self._hero_card.add_widget(avatar_row)
        self._content.add_widget(self._hero_card)

    # ---------- Stats row 4 cards (spec 3) ----------
    def _build_stats(self):
        self._stats_container = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="8dp")
        self._content.add_widget(self._stats_container)
        self._render_stats()

    def _render_stats(self):
        self._stats_container.clear_widgets()
        s = getattr(self, "_statistics", {}) or {}
        total_spent_raw = s.get("total_spent") or s.get("totalSpent") or s.get("total_spent_formatted") or "0.00"
        try:
            # Handle string with commas
            total_spent_val = float(str(total_spent_raw).replace(",", "").replace("₦", "").strip() or 0)
            total_spent_str = f"₦{total_spent_val:,.2f}"
        except Exception:
            total_spent_str = f"₦{total_spent_raw}"
        items = [
            ("Total Deliveries", s.get("total_deliveries", 0), "package-variant-closed", PRIMARY),
            ("Completed", s.get("completed", 0), "check-circle-outline", SUCCESS),
            ("In Progress", s.get("in_progress", 0), "progress-clock", MUTED),
            ("Total Spent", total_spent_str, "currency-ngn", PRIMARY),
        ]
        grid = GridLayout(cols=2, spacing="8dp", size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for label, value, icon, color in items:
            card = MDCard(
                orientation="vertical",
                padding="12dp",
                spacing="4dp",
                size_hint_x=1,
                size_hint_y=None,
                height="80dp",
                md_bg_color=rgba(CARD_BG),
                radius=[12],
                elevation=1,
            )
            top_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp")
            val_label = MDLabel(
                text=str(value),
                font_style="H6",
                bold=True,
                halign="left",
                theme_text_color="Custom",
                text_color=rgba(PRIMARY),
                size_hint_x=1,
                adaptive_height=True,
            )
            icon_w = MDIcon(icon=icon, theme_text_color="Custom", text_color=rgba(color), halign="right", size_hint_x=None, width="28dp", font_size="20sp")
            top_row.add_widget(val_label)
            top_row.add_widget(icon_w)
            lab = MDLabel(text=label, font_style="Caption", halign="left", theme_text_color="Custom", text_color=MUTED, adaptive_height=True)
            card.add_widget(top_row)
            card.add_widget(lab)
            grid.add_widget(card)
        self._stats_container.add_widget(grid)

    # ---------- Recent deliveries (spec 4) ----------
    def _build_recent_deliveries(self):
        self._recent_container = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, padding=["0dp", "4dp", "0dp", "0dp"])
        header = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_y=None, height="32dp")
        header.add_widget(MDIcon(icon="history", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Recent Deliveries", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1))
        view_all = MDFlatButton(text="View All", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="12sp", size_hint_x=None, width="80dp", on_release=lambda x: self._go_history())
        header.add_widget(view_all)
        self._recent_container.add_widget(header)
        self._recent_list = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, size_hint_y=None)
        self._recent_list.bind(minimum_height=self._recent_list.setter("height"))
        self._recent_container.add_widget(self._recent_list)
        self._content.add_widget(self._recent_container)

    def _render_recent(self):
        self._recent_list.clear_widgets()
        items = getattr(self, "_recent", []) or []
        if not items:
            self._recent_list.add_widget(MDLabel(text="No recent deliveries", font_style="Body2", halign="center", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="40dp"))
            return
        for wb in items[:5]:
            card = WaybillCard(waybill=wb, on_tap=self._open_detail)
            self._recent_list.add_widget(card)

    def _go_history(self, *args):
        if self.manager:
            self.manager.current = "customer_history"

    def _open_detail(self, waybill):
        try:
            detail = self.manager.get_screen("waybill_detail")
            if hasattr(detail, "set_waybill"):
                detail.set_waybill(waybill)
            self.manager.current = "waybill_detail"
        except Exception:
            pass

    # ---------- Personal Information (spec 5) ----------
    def _build_personal_info(self):
        card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="account-edit", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Personal Information", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        card.add_widget(header)

        grid = GridLayout(cols=2, spacing="12dp", size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        self._pi_name = MDTextField(hint_text="Full Name", mode="rectangle", icon_right="account-outline")
        self._pi_email = MDTextField(hint_text="Email Address", helper_text="Used for login and notifications", helper_text_mode="on_focus", mode="rectangle", icon_right="email-outline")
        self._pi_phone = MDTextField(hint_text="Phone Number", mode="rectangle", icon_right="phone-outline")
        self._pi_alt_phone = MDTextField(hint_text="Alternate Phone (Optional)", mode="rectangle", icon_right="phone-outline")

        # Add to grid (single col for simplicity on narrow, but keep 2 cols for web-like)
        grid.add_widget(self._pi_name)
        grid.add_widget(self._pi_email)
        grid.add_widget(self._pi_phone)
        grid.add_widget(self._pi_alt_phone)
        card.add_widget(grid)

        self._pi_instructions = MDTextField(
            hint_text="Delivery Instructions",
            helper_text="Gate code, landmark, preferred contact time, etc.",
            helper_text_mode="on_focus",
            mode="rectangle",
            multiline=True,
            size_hint_y=None,
            height="80dp",
        )
        card.add_widget(self._pi_instructions)

        self._pi_save_btn = MDRaisedButton(text="Save Changes", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="140dp", pos_hint={"center_x": 0.5}, on_release=lambda x: self._save_personal_info())
        card.add_widget(self._pi_save_btn)
        self._pi_status = MDLabel(text="", font_style="Caption", halign="center", theme_text_color="Custom", text_color=SUCCESS, size_hint_y=None, height="0dp")
        card.add_widget(self._pi_status)

        self._personal_card = card
        self._content.add_widget(card)

    def _save_personal_info(self, *args):
        full_name = self._pi_name.text.strip()
        email = self._pi_email.text.strip()
        phone = self._pi_phone.text.strip()
        phone_alt = self._pi_alt_phone.text.strip()
        instructions = self._pi_instructions.text.strip()
        if not full_name or not phone:
            self._show_pi_error("Full Name and Phone are required")
            return
        if email and not _is_valid_email(email):
            self._show_pi_error("Please provide a valid email")
            return
        payload = {"full_name": full_name, "email": email or None, "phone": phone, "phone_alt": phone_alt or None, "delivery_instructions": instructions or None}
        # Clean None values
        payload = {k: v for k, v in payload.items() if v is not None}
        try:
            from app.services.customer_service import update_profile
            result = update_profile(payload)
            if result.get("ok"):
                self._pi_status.text = "Profile updated"
                self._pi_status.text_color = rgba(SUCCESS)
                self._pi_status.height = "20dp"
                Clock.schedule_once(lambda dt: setattr(self._pi_status, "height", 0), 2.5)
                # Update hero
                self._customer.update({"full_name": full_name, "email": email, "phone": phone, "phone_alt": phone_alt, "delivery_instructions": instructions})
                self._render_hero()
                # Update session name
                try:
                    session.save_tokens(session.get_access_token(), session.get_refresh_token(), session.get_role(), full_name)
                except Exception:
                    pass
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text="Profile updated").open()
            else:
                self._show_pi_error(result.get("error") or "Update failed")
        except Exception as e:
            self._show_pi_error(str(e))

    def _show_pi_error(self, msg):
        self._pi_status.text = msg
        self._pi_status.text_color = rgba(ERROR)
        self._pi_status.height = "24dp"

    # ---------- Change Password (spec 6) ----------
    def _build_change_password(self):
        card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="lock-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Change Password", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        card.add_widget(header)

        self._cp_current = MDTextField(hint_text="Current Password", password=True, mode="rectangle", icon_right="lock-outline")
        self._cp_new = MDTextField(hint_text="New Password", password=True, helper_text="Minimum 6 characters", helper_text_mode="on_focus", mode="rectangle", icon_right="lock-outline")
        self._cp_confirm = MDTextField(hint_text="Confirm New Password", password=True, mode="rectangle", icon_right="lock-outline")
        # Eye toggle
        for fld in (self._cp_current, self._cp_new, self._cp_confirm):
            fld.bind(on_touch_down=self._toggle_pwd_visibility)

        card.add_widget(self._cp_current)
        card.add_widget(self._cp_new)
        card.add_widget(self._cp_confirm)

        row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="36dp")
        btn = MDRaisedButton(text="Change Password", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", on_release=lambda x: self._do_change_password())
        row.add_widget(btn)
        row.add_widget(MDLabel(text="Your account is protected. Trackway will never ask for your password via email or phone.", font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_x=1))
        card.add_widget(row)
        self._cp_status = MDLabel(text="", font_style="Caption", halign="center", theme_text_color="Custom", text_color=ERROR, size_hint_y=None, height="0dp")
        card.add_widget(self._cp_status)
        self._content.add_widget(card)

    def _toggle_pwd_visibility(self, instance, touch):
        if instance.collide_point(*touch.pos) and instance.icon_right in ("eye-outline", "eye-off-outline"):
            instance.password = not instance.password
            instance.icon_right = "eye-off-outline" if not instance.password else "eye-outline"

    def _do_change_password(self, *args):
        cur = self._cp_current.text.strip()
        new = self._cp_new.text.strip()
        conf = self._cp_confirm.text.strip()
        if not cur or not new or not conf:
            self._cp_status.text = "Please fill all password fields"
            self._cp_status.height = "20dp"
            return
        if len(new) < 6:
            self._cp_status.text = "Minimum 6 characters"
            self._cp_status.height = "20dp"
            return
        if new == cur:
            self._cp_status.text = "New password must be different from current password"
            self._cp_status.height = "20dp"
            return
        if new != conf:
            self._cp_status.text = "Passwords do not match"
            self._cp_status.height = "20dp"
            return
        try:
            from app.services.customer_service import change_password
            result = change_password({"current_password": cur, "new_password": new, "confirm_password": conf})
            if result.get("ok"):
                self._cp_status.text = ""
                self._cp_status.height = "0dp"
                self._cp_current.text = ""; self._cp_new.text = ""; self._cp_confirm.text = ""
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text="Password changed successfully").open()
            else:
                self._cp_status.text = result.get("error") or "Password change failed"
                self._cp_status.text_color = rgba(ERROR)
                self._cp_status.height = "24dp"
        except Exception as e:
            self._cp_status.text = str(e)
            self._cp_status.height = "20dp"

    # ---------- Account Information (spec 7) ----------
    def _build_account_info(self):
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="24dp", padding=["4dp", "0dp"])
        header.add_widget(MDIcon(icon="information-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Account Information", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        self._content.add_widget(header)

        self._account_grid = GridLayout(cols=2, spacing="8dp", size_hint_y=None)
        self._account_grid.bind(minimum_height=self._account_grid.setter("height"))
        self._content.add_widget(self._account_grid)
        self._render_account_info()

    def _render_account_info(self):
        self._account_grid.clear_widgets()
        c = getattr(self, "_customer", {}) or {}
        items = [
            ("Customer ID", c.get("customer_unique_id") or c.get("customer_code") or "-"),
            ("Account Status", "Active"),
            ("Member Since", _format_created_at(c.get("created_at"))),
            ("Last Login", c.get("last_login") or "-"),
        ]
        for title, value in items:
            card = MDCard(orientation="vertical", padding="10dp", spacing="4dp", size_hint_y=None, height="70dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
            card.add_widget(MDLabel(text=title, font_style="Caption", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            val_color = SUCCESS if value == "Active" else DARK
            badge = MDCard(size_hint=(None, None), size=("60dp", "20dp"), md_bg_color=rgba(SUCCESS) if value == "Active" else rgba(CARD_BG), radius=[8], elevation=0) if value == "Active" else None
            if badge:
                badge.add_widget(MDLabel(text=value, halign="center", font_style="Caption", theme_text_color="Custom", text_color="white", font_size="10sp"))
                card.add_widget(badge)
            else:
                card.add_widget(MDLabel(text=str(value), font_style="Body2", bold=True, theme_text_color="Custom", text_color=DARK))
            self._account_grid.add_widget(card)

    # ---------- Footer (spec 8) ----------
    def _build_footer(self):
        self._footer = MDLabel(
            text="© 2026 Trackway Smart Logistics. All rights reserved. Delivering Excellence, One Parcel at a Time.",
            font_style="Caption",
            halign="center",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint_y=None,
            height="40dp",
            text_size=(None, None),
        )
        self._content.add_widget(self._footer)

    # ---------- Helpers ----------
    def _render_hero(self):
        c = getattr(self, "_customer", {}) or {}
        name = c.get("full_name") or c.get("name") or ""
        phone = c.get("phone") or ""
        email = c.get("email") or ""
        verified = c.get("verified") or bool(email)
        member_since = _format_created_at(c.get("created_at"))
        self._hero_name.text = name or "Customer"
        initial = (name.strip()[0].upper() if name else "A")
        self._hero_initial.text = initial
        try:
            self._avatar_card.children[0].text = initial
        except Exception:
            pass
        self.top_name_label.text = name
        self._hero_phone.text = phone
        self._hero_email.text = email
        # Verified badge visibility
        try:
            self._hero_verified_card.opacity = 1 if verified else 0
            self._hero_verified_card.disabled = not verified
        except Exception:
            pass
        self._hero_member.text = f"Member since {member_since}" if member_since and member_since != "-" else ""

    # ---------- Lifecycle ----------
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
        self._load_profile()

    def _load_profile(self):
        try:
            from app.services.customer_service import get_profile
            result = get_profile()
            if result.get("ok"):
                data = result.get("data", {}) or {}
                self._customer = data.get("customer", {}) or {}
                self._statistics = data.get("statistics", {}) or {}
                self._recent = data.get("recent_deliveries", []) or []
                # Fallback if recent is under statistics
                if not self._recent and isinstance(self._statistics, dict):
                    self._recent = self._statistics.get("recent_deliveries", []) or []
            elif result.get("error") and "Session expired" in str(result.get("error")):
                from app.core import session
                session.clear_session()
                if self.manager:
                    self.manager.current = "customer_login"
                return
        except Exception:
            self._customer = {}
            self._statistics = {}
            self._recent = []
        # Sync personal info fields
        try:
            self._pi_name.text = self._customer.get("full_name") or self._customer.get("name") or ""
            self._pi_email.text = self._customer.get("email") or ""
            self._pi_phone.text = self._customer.get("phone") or ""
            self._pi_alt_phone.text = self._customer.get("phone_alt") or ""
            self._pi_instructions.text = self._customer.get("delivery_instructions") or ""
        except Exception:
            pass
        # Render all
        try:
            self._render_hero()
        except Exception:
            pass
        try:
            self._render_stats()
        except Exception:
            pass
        try:
            self._render_recent()
        except Exception:
            pass
        try:
            self._render_account_info()
        except Exception:
            pass
        try:
            Window.bind(width=self._on_window_width)
            self._on_window_width(Window, Window.width)
        except Exception:
            pass

    def _show_refer_stub(self, *args):
        from kivymd.uix.dialog import MDDialog
        code = self._customer.get("customer_unique_id") or self._statistics.get("referral_code") or ""
        # Try to get referral_code from customer if not in stats
        if not code:
            try:
                from app.services.customer_service import get_dashboard_stats
                r = get_dashboard_stats()
                if r.get("ok"):
                    code = r["data"].get("referral_code", "")
            except Exception:
                pass
        self._refer_dialog = MDDialog(
            title=tr("refer_and_earn"),
            text=f"{tr('refer_earn_banner')} {code}. Share with friends!",
            buttons=[MDFlatButton(text=tr("ok"), on_release=lambda x: self._refer_dialog.dismiss())],
        )
        self._refer_dialog.open()

    def _show_support_stub(self, *args):
        if self.manager:
            self.manager.current = "support"
            return
        from kivymd.uix.dialog import MDDialog
        self._support_dialog = MDDialog(
            title=tr("support"),
            text=f"{tr('need_immediate_help')}\n{tr('call_support')}: +234 800 000 0000\n{tr('email_support')}: support@trackwaylogistics.ng",
            buttons=[MDFlatButton(text=tr("ok"), on_release=lambda x: self._support_dialog.dismiss())],
        )
        self._support_dialog.open()

    def _logout(self, *args):
        try:
            from app.services.auth_service import logout
            logout()
        except Exception:
            try:
                from app.core import session
                session.clear_session()
            except Exception:
                pass
        if self.manager:
            self.manager.current = "welcome"

    def _go_back(self, *args):
        if self.manager:
            self.manager.current = "customer_home"

    def rebuild_ui(self):
        try:
            from app.i18n.translator import tr
            # header + sections use tr; re-render by clearing and rebuilding minimal header
            if hasattr(self, '_content') and hasattr(self, '_render'):
                # keep session data, just refresh texts
                for child in self.walk():
                    if isinstance(child, MDLabel) and child.text:
                        # update known keys where possible (best-effort)
                        pass
            # ensure language picker label updates
            if hasattr(self, '_lang_picker'):
                try:
                    self._lang_picker._update_label()
                except Exception:
                    pass
        except Exception:
            pass
