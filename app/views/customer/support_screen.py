from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.spinner import MDSpinner

from app.core.theme import PRIMARY, PRIMARY_DARK, DARK, MUTED, BACKGROUND, CARD_BG, ERROR, SUCCESS
from app.core.constants import COMPLAINT_TYPES
from app.core import session
from app.i18n.translator import tr
from app.views.base_screen import BaseScreen


def _complaint_label(key):
    # Try i18n first, then COMPLAINT_TYPES, else raw
    translated = tr(key)
    if translated != key:
        return translated
    return COMPLAINT_TYPES.get(key, key)


class SupportScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._complaint_type = ""
        self._complaint_label = ""
        self._waybill_number = ""
        self._waybill_items = []
        self._tickets = []
        self._tickets_page = 1
        self._tickets_has_more = False
        self._submitting = False
        self._loading_tickets = False
        self._profile_menu = None

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

        self._build_header()
        self._build_form_card()
        self._build_tickets_section()
        self._build_alternative_contacts()
        self._build_footer()

        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

    # ---------- Top nav (spec) ----------
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
            from app.views.shared.language_picker import LanguagePicker
            self.language_picker = LanguagePicker(compact=True)
            self.language_picker.size_hint_x = None
            self.language_picker.width = "36dp"
            right_cluster.add_widget(self.language_picker)
        except Exception:
            right_cluster.add_widget(MDLabel(text="EN", font_style="Caption", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=None, width="32dp", halign="center"))

        self._dash_btn = MDFlatButton(
            text="\u2190 Dashboard",
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            font_size="12sp",
            size_hint_x=None,
            width="90dp",
            on_release=lambda x: self._go_dashboard(),
        )
        right_cluster.add_widget(self._dash_btn)

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
        self.top_name_label = MDLabel(text="", font_style="Caption", bold=True, theme_text_color="Custom", text_color=DARK, halign="left", valign="middle")
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
            {"text": "Support", "leading_icon": "headset", "on_release": lambda: self._menu_navigate("support")},
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
            if self.manager:
                self.manager.current = "profile"

    def _menu_navigate(self, route):
        try:
            if hasattr(self, "_profile_menu") and self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", route) if self.manager else None, 0.15)

    def _menu_action_refer(self):
        try:
            if hasattr(self, "_profile_menu") and self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", "refer_earn") if self.manager else None, 0.2)

    def _menu_logout(self):
        try:
            if hasattr(self, "_profile_menu") and self._profile_menu:
                self._profile_menu.dismiss()
        except Exception:
            pass
        def do_logout(dt):
            try:
                from app.services.auth_service import logout
                logout()
            except Exception:
                try:
                    from app.core import session as sess
                    sess.clear_session()
                except Exception:
                    pass
            if self.manager:
                self.manager.current = "welcome"
        Clock.schedule_once(do_logout, 0.2)

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

    # ---------- Header (green banner – parity with Dashboard welcome) ----------
    def _build_header(self):
        self._header_card = MDCard(
            orientation="vertical",
            padding="16dp",
            spacing="6dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba(PRIMARY),
            radius=[14],
            elevation=0,
        )
        row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="28dp")
        row.add_widget(MDIcon(icon="headset", theme_text_color="Custom", text_color="white", size_hint_x=None, width="28dp", font_size="22sp", pos_hint={"center_y": 0.5}))
        self._header_title = MDLabel(text=tr("customer_support"), font_style="H6", bold=True, theme_text_color="Custom", text_color="white", adaptive_height=True, pos_hint={"center_y": 0.5})
        row.add_widget(self._header_title)
        self._header_card.add_widget(row)
        self._header_sub = MDLabel(text=tr("having_issues_subtitle"), font_style="Body2", theme_text_color="Custom", text_color=rgba("#e8f0e3"), adaptive_height=True)
        self._header_card.add_widget(self._header_sub)
        self._content.add_widget(self._header_card)

    # ---------- Form card ----------
    def _build_form_card(self):
        self._form_card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        # Title
        self._form_title = MDLabel(text=tr("report_an_issue"), font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color=DARK, adaptive_height=True)
        self._form_card.add_widget(self._form_title)

        # Complaint Type dropdown field (read-only text field acting as trigger)
        self._complaint_field = MDTextField(hint_text=tr("select_type"), text="", mode="rectangle", readonly=True, on_focus=self._on_complaint_focus)
        # Overlay icon behavior via touch – we handle MDDropdownMenu
        self._complaint_field.bind(on_touch_down=self._maybe_open_complaint_menu)
        self._form_card.add_widget(MDLabel(text=tr("complaint_type"), font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp"))
        self._form_card.add_widget(self._complaint_field)
        self._complaint_menu = None
        self._build_complaint_menu()
        self._complaint_error = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        self._form_card.add_widget(self._complaint_error)

        # Related Waybill dropdown
        self._form_card.add_widget(MDLabel(text=tr("related_waybill"), font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp"))
        self._waybill_field = MDTextField(hint_text=tr("select_waybill_placeholder"), text="", mode="rectangle", readonly=True)
        self._waybill_field.bind(on_touch_down=self._maybe_open_waybill_menu)
        self._form_card.add_widget(self._waybill_field)
        self._waybill_menu = None
        self._waybill_spinner = MDSpinner(size_hint=(None, None), size=("20dp", "20dp"), active=False, pos_hint={"center_x": 0.5})

        # Related Ride disabled placeholder
        self._form_card.add_widget(MDLabel(text=tr("related_ride"), font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp"))
        self._ride_field = MDTextField(hint_text=tr("select_ride_placeholder"), text="", mode="rectangle", disabled=True)
        self._form_card.add_widget(self._ride_field)
        self._ride_helper = MDLabel(text=tr("ride_optional_helper"), font_style="Caption", theme_text_color="Custom", text_color=MUTED, adaptive_height=True)
        self._form_card.add_widget(self._ride_helper)

        # Subject
        self._form_card.add_widget(MDLabel(text=tr("subject"), font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp"))
        self._subject_field = MDTextField(hint_text=tr("enter_subject_placeholder"), mode="rectangle", multiline=False)
        self._form_card.add_widget(self._subject_field)
        self._subject_error = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        self._form_card.add_widget(self._subject_error)

        # Message
        self._form_card.add_widget(MDLabel(text=tr("message"), font_style="Caption", theme_text_color="Custom", text_color=MUTED, size_hint_y=None, height="16dp"))
        self._message_field = MDTextField(hint_text=tr("describe_issue_placeholder"), mode="rectangle", multiline=True, size_hint_y=None, height="100dp")
        self._form_card.add_widget(self._message_field)
        self._message_error = MDLabel(text="", font_style="Caption", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        self._form_card.add_widget(self._message_error)

        # Submit row right-aligned
        btn_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, size_hint_y=None, height="44dp", spacing="8dp")
        btn_row.add_widget(MDLabel(text=""))  # spacer
        self._submit_btn = MDRaisedButton(text=tr("submit_support_request"), md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="200dp", on_release=lambda x: self._submit())
        # Add paper-plane icon via left padding trick – MDRaisedButton does not have icon param, add via text
        # Use unicode paper plane
        self._submit_btn.text = "\u2708  " + tr("submit_support_request")
        btn_row.add_widget(self._submit_btn)
        self._form_card.add_widget(btn_row)
        self._form_status = MDLabel(text="", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba(SUCCESS), size_hint_y=None, height="0dp")
        self._form_card.add_widget(self._form_status)
        self._submit_spinner = MDSpinner(size_hint=(None, None), size=("24dp", "24dp"), active=False, color=rgba(PRIMARY), pos_hint={"center_x": 0.5})
        self._form_card.add_widget(self._submit_spinner)

        self._content.add_widget(self._form_card)

    def _build_complaint_menu(self):
        items = []
        for key in COMPLAINT_TYPES.keys():
            label = _complaint_label(key)
            items.append({"text": label, "viewclass": "OneLineListItem", "on_release": lambda k=key, lbl=label: self._select_complaint(k, lbl)})
        try:
            self._complaint_menu = MDDropdownMenu(caller=self._complaint_field, items=items, width_mult=4, max_height="280dp")
        except Exception:
            self._complaint_menu = None

    def _maybe_open_complaint_menu(self, instance, touch):
        if instance != self._complaint_field:
            return False
        if instance.collide_point(*touch.pos):
            try:
                if self._complaint_menu:
                    self._complaint_menu.caller = self._complaint_field
                    self._complaint_menu.open()
                    return True
            except Exception:
                pass
        return False

    def _on_complaint_focus(self, instance, value):
        if value:
            try:
                if self._complaint_menu:
                    self._complaint_menu.caller = self._complaint_field
                    self._complaint_menu.open()
            except Exception:
                pass

    def _select_complaint(self, key, label):
        self._complaint_type = key
        self._complaint_label = label
        self._complaint_field.text = label
        self._complaint_error.text = ""
        self._complaint_error.height = "0dp"
        try:
            if self._complaint_menu:
                self._complaint_menu.dismiss()
        except Exception:
            pass

    # Waybill menu
    def _build_waybill_menu(self):
        waybills = getattr(self, "_waybill_items", []) or []
        items = []
        # First item: clear selection (optional)
        items.append({"text": tr("select_waybill_placeholder"), "viewclass": "OneLineListItem", "on_release": lambda: self._select_waybill("", "")})
        for wb in waybills[:30]:
            num = wb.get("waybill_number") or wb.get("waybill") or str(wb.get("id") or "")
            origin = wb.get("origin") or wb.get("origin_city") or ""
            dest = wb.get("destination") or wb.get("destination_city") or ""
            label = f"{num}  {origin}->{dest}" if num else str(wb)
            # Truncate long labels
            if len(label) > 48:
                label = label[:47] + "\u2026"
            items.append({"text": label, "viewclass": "OneLineListItem", "on_release": lambda n=num: self._select_waybill(n, n)})
        try:
            if self._waybill_menu:
                try:
                    self._waybill_menu.dismiss()
                except Exception:
                    pass
            self._waybill_menu = MDDropdownMenu(caller=self._waybill_field, items=items, width_mult=4, max_height="280dp")
        except Exception:
            self._waybill_menu = None

    def _maybe_open_waybill_menu(self, instance, touch):
        if instance != self._waybill_field:
            return False
        if instance.collide_point(*touch.pos):
            try:
                if not self._waybill_items:
                    # Still allow opening to show placeholder
                    pass
                if self._waybill_menu:
                    self._waybill_menu.caller = self._waybill_field
                    self._waybill_menu.open()
                else:
                    self._build_waybill_menu()
                    if self._waybill_menu:
                        self._waybill_menu.open()
                return True
            except Exception:
                pass
        return False

    def _select_waybill(self, number, label):
        self._waybill_number = number
        self._waybill_field.text = label
        try:
            if self._waybill_menu:
                self._waybill_menu.dismiss()
        except Exception:
            pass

    def _submit(self, *args):
        if self._submitting:
            return
        # Validate
        has_error = False
        if not self._complaint_type:
            self._complaint_error.text = tr("validation_complaint_type")
            self._complaint_error.height = "18dp"
            has_error = True
        else:
            self._complaint_error.text = ""
            self._complaint_error.height = "0dp"
        subj = self._subject_field.text.strip()
        if len(subj) < 3:
            self._subject_error.text = tr("validation_subject")
            self._subject_error.height = "18dp"
            has_error = True
        else:
            self._subject_error.text = ""
            self._subject_error.height = "0dp"
        msg = self._message_field.text.strip()
        if len(msg) < 10:
            self._message_error.text = tr("validation_message")
            self._message_error.height = "18dp"
            has_error = True
        else:
            self._message_error.text = ""
            self._message_error.height = "0dp"
        if has_error:
            return
        # Submit
        self._submitting = True
        self._submit_btn.disabled = True
        self._submit_spinner.active = True
        self._form_status.text = ""
        self._form_status.height = "0dp"
        payload = {
            "complaint_type": self._complaint_type,
            "subject": subj,
            "message": msg,
        }
        if self._waybill_number:
            payload["waybill_number"] = self._waybill_number
            payload["waybill"] = self._waybill_number
        # Ride disabled – not sent
        try:
            from app.services.customer_service import submit_complaint
            result = submit_complaint(payload)
            self._submit_spinner.active = False
            self._submitting = False
            self._submit_btn.disabled = False
            if result.get("ok"):
                self._form_status.text = tr("complaint_submitted")
                self._form_status.text_color = rgba(SUCCESS)
                self._form_status.height = "22dp"
                try:
                    from kivymd.uix.snackbar import Snackbar
                    Snackbar(text=tr("complaint_submitted")).open()
                except Exception:
                    pass
                # Clear form except waybill? clear all
                self._complaint_type = ""
                self._complaint_label = ""
                self._complaint_field.text = ""
                self._waybill_number = ""
                self._waybill_field.text = ""
                self._subject_field.text = ""
                self._message_field.text = ""
                Clock.schedule_once(lambda dt: self._reset_form_status(), 3)
                # Refresh tickets
                self._tickets_page = 1
                self._tickets = []
                self._load_tickets()
            else:
                err = result.get("error") or tr("complaint_failed")
                if "Session expired" in str(err):
                    from app.core import session as sess
                    sess.clear_session()
                    if self.manager:
                        self.manager.current = "customer_login"
                    return
                self._form_status.text = err
                self._form_status.text_color = rgba(ERROR)
                self._form_status.height = "28dp"
                try:
                    from kivymd.uix.snackbar import Snackbar
                    Snackbar(text=err).open()
                except Exception:
                    pass
        except Exception as e:
            self._submit_spinner.active = False
            self._submitting = False
            self._submit_btn.disabled = False
            self._form_status.text = str(e) or tr("complaint_failed")
            self._form_status.text_color = rgba(ERROR)
            self._form_status.height = "28dp"

    def _reset_form_status(self):
        try:
            self._form_status.text = ""
            self._form_status.height = "0dp"
        except Exception:
            pass

    # ---------- Tickets section ----------
    def _build_tickets_section(self):
        self._tickets_card = MDCard(orientation="vertical", padding="16dp", spacing="10dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        header = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="ticket-confirmation-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text=tr("support_tickets"), font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color=DARK))
        self._tickets_card.add_widget(header)
        self._tickets_container = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, size_hint_y=None)
        self._tickets_container.bind(minimum_height=self._tickets_container.setter("height"))
        self._tickets_card.add_widget(self._tickets_container)
        self._tickets_spinner = MDSpinner(size_hint=(None, None), size=("24dp", "24dp"), active=False, color=rgba(PRIMARY), pos_hint={"center_x": 0.5})
        self._tickets_card.add_widget(self._tickets_spinner)
        self._content.add_widget(self._tickets_card)
        self._render_tickets()

    def _render_tickets(self):
        self._tickets_container.clear_widgets()
        items = getattr(self, "_tickets", []) or []
        if not items:
            empty = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, padding=["12dp", "16dp", "12dp", "16dp"])
            empty.add_widget(MDIcon(icon="ticket-confirmation-outline", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), font_size="48sp", size_hint_y=None, height="48dp"))
            empty.add_widget(MDLabel(text=tr("no_support_tickets"), font_style="Subtitle2", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True))
            empty.add_widget(MDLabel(text=tr("no_support_tickets_subtext"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            self._tickets_container.add_widget(empty)
            return
        for t in items:
            card = self._create_ticket_card(t)
            self._tickets_container.add_widget(card)
        if getattr(self, "_tickets_has_more", False):
            more = MDFlatButton(text=tr("load_more"), theme_text_color="Custom", text_color=rgba(PRIMARY), pos_hint={"center_x": 0.5}, on_release=lambda x: self._load_next_tickets())
            self._tickets_container.add_widget(more)

    def _create_ticket_card(self, t):
        subject = t.get("subject") or t.get("title") or ""
        msg = t.get("message") or t.get("description") or ""
        status = (t.get("status") or "open").lower()
        date = t.get("created_at") or t.get("date") or t.get("createdAt") or ""
        waybill = t.get("waybill_number") or t.get("waybill") or ""
        complaint_type = t.get("complaint_type") or t.get("type") or ""
        if "T" in str(date):
            date = str(date).split("T")[0]
        # Status color mapping
        if status in ("resolved", "closed", "completed", "done"):
            chip_color = SUCCESS
        elif status in ("pending", "open", "in_progress"):
            chip_color = PRIMARY
        else:
            chip_color = MUTED
        card = MDCard(orientation="vertical", padding="12dp", spacing="6dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=0, line_color=rgba(chip_color), line_width=0.6)
        top_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp")
        subj_label = MDLabel(text=subject or _complaint_label(complaint_type) or tr("support_tickets"), font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1, adaptive_height=True)
        top_row.add_widget(subj_label)
        chip = MDCard(size_hint=(None, None), size=("80dp", "22dp"), md_bg_color=rgba(CARD_BG), line_color=rgba(chip_color), radius=[12], elevation=0)
        chip.add_widget(MDLabel(text=status.capitalize(), halign="center", font_style="Caption", theme_text_color="Custom", text_color=rgba(chip_color), font_size="11sp"))
        top_row.add_widget(chip)
        card.add_widget(top_row)
        if waybill:
            card.add_widget(MDLabel(text=f"{tr('waybill_number')}: {waybill}", font_style="Caption", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
        if complaint_type:
            card.add_widget(MDLabel(text=_complaint_label(complaint_type), font_style="Caption", theme_text_color="Custom", text_color=rgba(PRIMARY), adaptive_height=True))
        if msg:
            preview = msg[:120] + ("..." if len(msg) > 120 else "")
            card.add_widget(MDLabel(text=preview, font_style="Body2", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
        if date:
            card.add_widget(MDLabel(text=str(date), font_style="Caption", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, halign="right"))
        return card

    def _load_next_tickets(self):
        if self._tickets_has_more and not self._loading_tickets:
            self._tickets_page += 1
            self._load_tickets()

    def _load_tickets(self):
        if self._loading_tickets:
            return
        self._loading_tickets = True
        self._tickets_spinner.active = True
        try:
            from app.services.customer_service import get_support_tickets
            result = get_support_tickets(page=self._tickets_page)
            self._tickets_spinner.active = False
            self._loading_tickets = False
            if result.get("ok"):
                data = result.get("data", {}) or {}
                page_items = data.get("items", []) or []
                if self._tickets_page == 1:
                    self._tickets = page_items
                else:
                    self._tickets.extend(page_items)
                self._tickets_has_more = data.get("has_more", False)
                self._render_tickets()
            else:
                err = result.get("error") or ""
                if "Session expired" in str(err):
                    from app.core import session as sess
                    sess.clear_session()
                    if self.manager:
                        self.manager.current = "customer_login"
                    return
                # On error, keep empty state but show snackbar
                if self._tickets_page == 1:
                    self._tickets = []
                    self._render_tickets()
                # Optionally show error snackbar only if not empty auth error
                if err and "No" not in err:
                    try:
                        from kivymd.uix.snackbar import Snackbar
                        Snackbar(text=err).open()
                    except Exception:
                        pass
        except Exception:
            self._tickets_spinner.active = False
            self._loading_tickets = False
            if self._tickets_page == 1:
                self._tickets = []
                self._render_tickets()

    # ---------- Alternative contacts ----------
    def _build_alternative_contacts(self):
        # Green banner card – increase spacing/padding to prevent subtitle/card overlap
        banner = MDCard(orientation="vertical", padding="16dp", spacing="12dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        self._banner_title = MDLabel(
            text="\U0001f4de " + tr("alternative_contact_methods"),
            font_style="Subtitle1",
            bold=True,
            theme_text_color="Custom",
            text_color="white",
            adaptive_height=True,
            halign="center",
        )
        banner.add_widget(self._banner_title)
        self._banner_label = MDLabel(text=tr("cant_reach_online"), font_style="Caption", theme_text_color="Custom", text_color=rgba("#e8f0e3"), adaptive_height=True, halign="center")
        banner.add_widget(self._banner_label)
        # Spacer between subtitle and card row – mirrors pre-title spacing
        spacer = MDBoxLayout(size_hint_y=None, height="4dp")
        banner.add_widget(spacer)
        # 3 cards horizontal – 12dp gaps, taller cards with 12dp padding to avoid text wrap/bleed
        row = MDBoxLayout(orientation="horizontal", spacing="12dp", adaptive_height=True, size_hint_y=None, height="122dp", padding=["0dp", "4dp", "0dp", "0dp"])
        # Phone
        phone_card = MDCard(orientation="vertical", padding="12dp", spacing="6dp", size_hint_x=1, size_hint_y=None, height="114dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, ripple_behavior=True)
        phone_card.bind(on_release=lambda x: self._stub_contact("phone"))
        phone_card.add_widget(MDIcon(icon="phone", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="22sp", size_hint_y=None, height="24dp"))
        phone_card.add_widget(MDLabel(text=tr("phone_support"), font_style="Caption", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True))
        phone_card.add_widget(MDLabel(text=tr("support_phone"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), adaptive_height=True, text_size=(None, None), shorten=False))
        phone_card.add_widget(MDLabel(text=tr("phone_hours"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, font_size="10sp", adaptive_height=True))
        row.add_widget(phone_card)
        # Email
        email_card = MDCard(orientation="vertical", padding="12dp", spacing="6dp", size_hint_x=1, size_hint_y=None, height="114dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, ripple_behavior=True)
        email_card.bind(on_release=lambda x: self._stub_contact("email"))
        email_card.add_widget(MDIcon(icon="email-outline", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="22sp", size_hint_y=None, height="24dp"))
        email_card.add_widget(MDLabel(text=tr("email_support"), font_style="Caption", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True))
        email_card.add_widget(MDLabel(text=tr("support_email"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="9sp", adaptive_height=True, text_size=(None, None), shorten=False))
        email_card.add_widget(MDLabel(text=tr("email_hours"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, font_size="10sp", adaptive_height=True))
        row.add_widget(email_card)
        # WhatsApp
        wa_card = MDCard(orientation="vertical", padding="12dp", spacing="6dp", size_hint_x=1, size_hint_y=None, height="114dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1, ripple_behavior=True)
        wa_card.bind(on_release=lambda x: self._stub_contact("whatsapp"))
        wa_card.add_widget(MDIcon(icon="whatsapp", halign="center", theme_text_color="Custom", text_color=rgba(SUCCESS), font_size="22sp", size_hint_y=None, height="24dp"))
        wa_card.add_widget(MDLabel(text=tr("whatsapp_support"), font_style="Caption", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True))
        wa_card.add_widget(MDLabel(text=tr("support_phone"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba(PRIMARY), adaptive_height=True, text_size=(None, None), shorten=False))
        wa_card.add_widget(MDLabel(text=tr("whatsapp_hours"), font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, font_size="10sp", adaptive_height=True))
        row.add_widget(wa_card)
        banner.add_widget(row)
        self._content.add_widget(banner)

    def _stub_contact(self, kind):
        try:
            from kivymd.uix.snackbar import Snackbar
            if kind == "phone":
                Snackbar(text=f"{tr('phone_support')}: {tr('support_phone')}").open()
            elif kind == "email":
                Snackbar(text=f"{tr('email_support')}: {tr('support_email')}").open()
            else:
                Snackbar(text=f"{tr('whatsapp_support')}: {tr('support_phone')}").open()
        except Exception:
            pass

    # ---------- Footer ----------
    def _build_footer(self):
        # Reuse exact refer_earn footer string
        footer = MDBoxLayout(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="56dp", md_bg_color=rgba(DARK))
        # Use MDCard black full-width to match spec footer
        card = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="56dp", md_bg_color=rgba(DARK), radius=[0], elevation=0)
        card.add_widget(MDLabel(text="\u00a9 2026 Trackway Logistics. Trackway Smart Logistics. All rights reserved.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        card.add_widget(MDLabel(text="Delivering Excellence, One Parcel at a Time.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        self._footer_card = card
        self._content.add_widget(card)

    # ---------- Lifecycle ----------
    def on_pre_enter(self, *args):
        from app.core import session as sess
        if not sess.is_logged_in() or sess.get_role() != "customer":
            if self.manager:
                self.manager.current = "customer_login"
            return
        super().on_pre_enter(*args)

    def on_enter(self, *args):
        from app.core import session as sess
        if not sess.is_logged_in() or sess.get_role() != "customer":
            if self.manager:
                self.manager.current = "customer_login"
            return
        # Update name
        try:
            name = sess.get_customer_name() or ""
            self.top_name_label.text = name
            if hasattr(self, "_avatar_card"):
                initial = (name.strip()[0].upper() if name else "A")
                self._avatar_card.children[0].text = initial
        except Exception:
            pass
        self._load_waybills()
        self._tickets_page = 1
        self._load_tickets()
        try:
            self._on_window_width(Window, Window.width if hasattr(Window, "width") else 400)
        except Exception:
            pass

    def _load_waybills(self):
        try:
            from app.services.customer_service import get_deliveries
            result = get_deliveries(page=1)
            if result.get("ok"):
                self._waybill_items = result["data"]["items"] or []
                self._build_waybill_menu()
            else:
                self._waybill_items = []
                self._build_waybill_menu()
        except Exception:
            self._waybill_items = []
            self._build_waybill_menu()

    def rebuild_ui(self):
        # Re-translate static labels on language change
        try:
            self._header_title.text = tr("customer_support")
            self._header_sub.text = tr("having_issues_subtitle")
            self._form_title.text = tr("report_an_issue")
            # Rebuild complaint menu labels
            self._build_complaint_menu()
            if self._complaint_type:
                self._complaint_field.text = _complaint_label(self._complaint_type)
            else:
                self._complaint_field.hint_text = tr("select_type")
            self._waybill_field.hint_text = tr("select_waybill_placeholder")
            self._ride_field.hint_text = tr("select_ride_placeholder")
            self._ride_helper.text = tr("ride_optional_helper")
            self._subject_field.hint_text = tr("enter_subject_placeholder")
            self._message_field.hint_text = tr("describe_issue_placeholder")
            self._submit_btn.text = "\u2708  " + tr("submit_support_request")
            if hasattr(self, "_banner_title"):
                self._banner_title.text = "\U0001f4de " + tr("alternative_contact_methods")
            self._banner_label.text = tr("cant_reach_online")
            self._render_tickets()
        except Exception:
            pass
