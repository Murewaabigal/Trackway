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
from kivymd.uix.menu import MDDropdownMenu

from app.core.theme import PRIMARY, DARK, MUTED, BACKGROUND, CARD_BG, SUCCESS, ERROR
from app.core import session
from app.views.base_screen import BaseScreen


class RiderWalletScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._data = {"balance": "0.00", "total_earned": "0.00", "total_credit": "0.00", "total_withdrawn": "0.00", "transaction_count": 0, "total_pages": 0, "current_page": 1}
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

        self._build_balance_banner()
        self._build_stats_row()
        self._build_history()
        # 8dp spacer + existing 12dp content spacing = 20dp visual gap between history card and footer (isolated)
        try:
            self._content.add_widget(MDBoxLayout(size_hint_y=None, height="8dp", md_bg_color=[0,0,0,0]))
        except Exception:
            pass
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

    # ---------- Section 1: Available Balance banner ----------
    def _build_balance_banner(self):
        self._banner = MDCard(orientation="vertical", padding="14dp", spacing="6dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        top = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="20dp")
        top.add_widget(MDIcon(icon="calendar-month-outline", theme_text_color="Custom", text_color=rgba("#c8e6c9"), font_size="12sp", size_hint_x=None, width="16dp"))
        top.add_widget(MDLabel(text="AVAILABLE BALANCE", font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=rgba("#c8e6c9"), halign="left", size_hint_x=1, bold=True))
        self._banner.add_widget(top)
        self._balance_label = MDLabel(text="₦0.00", font_style="H5", bold=True, theme_text_color="Custom", text_color="white", size_hint_y=None, height="32dp")
        self._banner.add_widget(self._balance_label)
        sub = MDBoxLayout(orientation="horizontal", spacing="4dp", size_hint_x=1, size_hint_y=None, height="18dp")
        sub.add_widget(MDIcon(icon="trending-up", theme_text_color="Custom", text_color=rgba("#a8d5a8"), font_size="12sp", size_hint_x=None, width="16dp"))
        self._banner_earned = MDLabel(text="Total Earned: ₦0.00", font_style="Caption", font_size="11sp", theme_text_color="Custom", text_color=rgba("#e8f0e3"), halign="left", size_hint_x=1)
        sub.add_widget(self._banner_earned)
        self._banner.add_widget(sub)
        btn_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", padding=["0dp","6dp","0dp","0dp"])
        btn_row.add_widget(MDLabel(text=""))
        self._withdraw_btn = MDFlatButton(text="↑ Request Withdrawal", theme_text_color="Custom", text_color="white", line_color="white", line_width=1, font_size="12sp", size_hint_x=None, width="160dp", size_hint_y=None, height="36dp", on_release=lambda x: self._on_withdraw())
        try:
            self._withdraw_btn.md_bg_color = [1,1,1,0.15]
        except Exception:
            pass
        btn_row.add_widget(self._withdraw_btn)
        self._banner.add_widget(btn_row)
        self._content.add_widget(self._banner)

    def _on_withdraw(self, *args):
        self._open_withdraw_modal()

    # ---------- Withdrawal Modal ----------
    def _ensure_withdraw_modal(self):
        if hasattr(self, "_withdraw_modal") and self._withdraw_modal:
            return
        from kivy.uix.modalview import ModalView
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.spinner import MDSpinner
        # overlay
        modal = ModalView(size_hint=(1, 1), background_color=[0,0,0,0.5], auto_dismiss=True)
        # card
        card = MDCard(orientation="vertical", padding="14dp", spacing="10dp", size_hint=(None, None), size=("340dp","520dp"), pos_hint={"center_x":0.5,"center_y":0.5}, md_bg_color=rgba(CARD_BG), radius=[14], elevation=6)
        # header
        head = MDBoxLayout(orientation="horizontal", size_hint_x=1, size_hint_y=None, height="28dp", spacing="6dp")
        head.add_widget(MDLabel(text="↑ Request Withdrawal", font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1, halign="left"))
        close_btn = MDFlatButton(text="×", theme_text_color="Custom", text_color=rgba(MUTED), font_size="20sp", size_hint_x=None, width="32dp", size_hint_y=None, height="28dp", on_release=lambda x: self._close_withdraw_modal())
        head.add_widget(close_btn)
        card.add_widget(head)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba("#e0e0e0")))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4), size_hint_x=1, size_hint_y=None, height="380dp")
        body = MDBoxLayout(orientation="vertical", spacing="10dp", adaptive_height=True, size_hint_y=None, padding=["0dp","4dp","0dp","4dp"])
        body.bind(minimum_height=body.setter("height"))
        # Available Balance readonly
        bal_row = MDBoxLayout(orientation="vertical", spacing="2dp", adaptive_height=True)
        bal_row.add_widget(MDLabel(text="Available Balance", font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color=MUTED, halign="left", adaptive_height=True))
        self._wd_balance = MDLabel(text=f"₦{self._data.get('balance','0.00')}", font_style="H6", bold=True, theme_text_color="Custom", text_color=rgba(SUCCESS), halign="left", size_hint_y=None, height="28dp")
        bal_row.add_widget(self._wd_balance)
        body.add_widget(bal_row)
        # Amount
        self._wd_amount = MDTextField(hint_text="Amount to Withdraw", helper_text="Minimum withdrawal is ₦5,000", helper_text_mode="on_focus", input_filter="float", mode="rectangle")
        self._wd_amount.bind(text=lambda inst, val: self._on_withdraw_field_change())
        body.add_widget(self._wd_amount)
        self._wd_amount_error = MDLabel(text="", font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp", halign="left")
        body.add_widget(self._wd_amount_error)
        # Bank dropdown trigger field (read-only)
        self._wd_bank_field = MDTextField(hint_text="-- Select Bank --", mode="rectangle", readonly=True)
        # make clickable to open menu
        self._wd_bank_field.bind(on_touch_down=self._on_bank_field_touch)
        body.add_widget(self._wd_bank_field)
        self._wd_bank_error = MDLabel(text="", font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        body.add_widget(self._wd_bank_error)
        # Account Number
        self._wd_account_number = MDTextField(hint_text="Enter 10-digit account number", helper_text="10 digits", helper_text_mode="on_focus", input_filter="int", mode="rectangle")
        self._wd_account_number.bind(text=lambda inst, val: self._on_account_number_change(val))
        body.add_widget(self._wd_account_number)
        self._wd_accnum_error = MDLabel(text="", font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="0dp")
        body.add_widget(self._wd_accnum_error)
        # Account Name (readonly, auto-filled)
        self._wd_account_name = MDTextField(hint_text="Account name will appear automatically", mode="rectangle", disabled=True)
        body.add_widget(self._wd_account_name)
        # resolving spinner row
        spin_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="20dp", spacing="6dp", adaptive_height=True)
        self._wd_resolve_spinner = MDSpinner(size_hint=(None,None), size=("16dp","16dp"), active=False, color=rgba(PRIMARY))
        self._wd_resolve_label = MDLabel(text="", font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=MUTED, halign="left")
        spin_row.add_widget(self._wd_resolve_spinner)
        spin_row.add_widget(self._wd_resolve_label)
        body.add_widget(spin_row)
        scroll.add_widget(body)
        card.add_widget(scroll)
        self._wd_general_error = MDLabel(text="", font_style="Caption", font_size="10sp", theme_text_color="Custom", text_color=rgba(ERROR), halign="center", size_hint_y=None, height="0dp")
        card.add_widget(self._wd_general_error)
        # footer
        foot = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_x=1, size_hint_y=None, height="36dp")
        cancel = MDFlatButton(text="Cancel", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=1, on_release=lambda x: self._close_withdraw_modal())
        foot.add_widget(cancel)
        self._wd_submit = MDRaisedButton(text="↑ Request Withdrawal", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=1, disabled=True, on_release=lambda x: self._do_withdraw())
        foot.add_widget(self._wd_submit)
        card.add_widget(foot)
        modal.add_widget(card)
        self._withdraw_modal = modal
        self._wd_banks = []
        self._wd_bank_menu = None
        self._wd_selected_bank_code = ""
        self._wd_selected_bank_name = ""
        self._wd_resolve_clock = None
        self._wd_account_verified = False

    def _open_withdraw_modal(self, *args):
        try:
            self._ensure_withdraw_modal()
            # refresh balance display
            try:
                self._wd_balance.text = f"₦{self._data.get('balance','0.00')}"
            except Exception:
                pass
            # reset fields
            try:
                self._wd_amount.text = ""
                self._wd_amount_error.text = ""
                self._wd_amount_error.height = "0dp"
                self._wd_bank_field.text = ""
                self._wd_bank_error.text = ""
                self._wd_bank_error.height = "0dp"
                self._wd_account_number.text = ""
                self._wd_accnum_error.text = ""
                self._wd_accnum_error.height = "0dp"
                self._wd_account_name.text = ""
                self._wd_resolve_label.text = ""
                self._wd_resolve_spinner.active = False
                self._wd_general_error.text = ""
                self._wd_general_error.height = "0dp"
                self._wd_selected_bank_code = ""
                self._wd_selected_bank_name = ""
                self._wd_account_verified = False
                self._wd_submit.disabled = True
            except Exception:
                pass
            self._withdraw_modal.open()
            # load banks if needed
            if not getattr(self, "_wd_banks", None):
                self._load_banks()
            self._validate_withdraw()
        except Exception as e:
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text=f"Could not open withdrawal: {e}").open()
            except Exception:
                pass

    def _close_withdraw_modal(self, *args):
        try:
            if hasattr(self, "_withdraw_modal") and self._withdraw_modal:
                self._withdraw_modal.dismiss()
        except Exception:
            pass
        try:
            if self._wd_resolve_clock:
                self._wd_resolve_clock.cancel()
        except Exception:
            pass

    def _load_banks(self):
        import threading
        def do():
            try:
                from app.services.rider_service import get_rider_banks
                r = get_rider_banks()
                banks = r.get("data") if r.get("ok") else []
                Clock.schedule_once(lambda dt: self._on_banks_loaded(banks), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._on_banks_loaded([], error=str(e)), 0)
        threading.Thread(target=do, daemon=True).start()
        try:
            self._wd_resolve_spinner.active = True
            self._wd_resolve_label.text = "Loading banks..."
        except Exception:
            pass

    def _on_banks_loaded(self, banks, error=None):
        try:
            self._wd_resolve_spinner.active = False
            self._wd_resolve_label.text = ""
        except Exception:
            pass
        if banks is None:
            banks = []
        self._wd_banks = banks if isinstance(banks, list) else []
        if error and not self._wd_banks:
            self._wd_bank_error.text = "Could not load banks. Tap Bank to retry."
            self._wd_bank_error.height = "16dp"
        # build menu next time field touched

    def _on_bank_field_touch(self, instance, touch):
        if not instance.collide_point(*touch.pos):
            return False
        # open bank menu
        try:
            self._show_bank_menu()
        except Exception:
            pass
        return True

    def _show_bank_menu(self, *args):
        if not getattr(self, "_wd_banks", None):
            self._load_banks()
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text="Loading banks...").open()
            except Exception:
                pass
            return
        from kivymd.uix.menu import MDDropdownMenu
        items = []
        for b in self._wd_banks:
            code = b.get("bank_code","")
            name = b.get("bank_name","")
            # capture in lambda
            items.append({"text": name, "on_release": lambda x, c=code, n=name: self._on_bank_selected(c, n)})
        if not items:
            items = [{"text": "No banks found", "on_release": lambda x: None}]
        try:
            if hasattr(self, "_wd_bank_menu") and self._wd_bank_menu:
                self._wd_bank_menu.dismiss()
        except Exception:
            pass
        self._wd_bank_menu = MDDropdownMenu(caller=self._wd_bank_field, items=items, width_mult=4, max_height="400dp")
        self._wd_bank_menu.open()

    def _on_bank_selected(self, code, name):
        try:
            if self._wd_bank_menu:
                self._wd_bank_menu.dismiss()
        except Exception:
            pass
        self._wd_selected_bank_code = code
        self._wd_selected_bank_name = name
        self._wd_bank_field.text = name
        self._wd_bank_error.text = ""
        self._wd_bank_error.height = "0dp"
        # if account number already 10 digits, trigger resolve
        if len(self._wd_account_number.text.strip()) == 10:
            self._trigger_resolve()
        self._validate_withdraw()

    def _on_account_number_change(self, val):
        # limit to 10 digits visually
        if len(val) > 10:
            self._wd_account_number.text = val[:10]
            return
        self._wd_accnum_error.text = ""
        self._wd_accnum_error.height = "0dp"
        self._wd_account_name.text = ""
        self._wd_account_verified = False
        self._wd_resolve_label.text = ""
        if len(val.strip()) == 10 and self._wd_selected_bank_code:
            self._trigger_resolve()
        else:
            if self._wd_resolve_clock:
                try:
                    self._wd_resolve_clock.cancel()
                except Exception:
                    pass
        self._validate_withdraw()

    def _on_withdraw_field_change(self, *args):
        # validate amount on change
        self._wd_amount_error.text = ""
        self._wd_amount_error.height = "0dp"
        self._wd_general_error.text = ""
        self._wd_general_error.height = "0dp"
        self._validate_withdraw()

    def _trigger_resolve(self):
        try:
            if self._wd_resolve_clock:
                self._wd_resolve_clock.cancel()
        except Exception:
            pass
        self._wd_resolve_clock = Clock.schedule_once(lambda dt: self._do_resolve(), 0.5)

    def _do_resolve(self, *args):
        code = self._wd_selected_bank_code
        acc = self._wd_account_number.text.strip()
        if not code or len(acc) != 10:
            return
        self._wd_resolve_spinner.active = True
        self._wd_resolve_label.text = "Verifying account..."
        self._wd_account_verified = False
        import threading
        def do():
            result = {"ok": False, "error": "Failed"}
            try:
                from app.services.rider_service import resolve_rider_account
                result = resolve_rider_account(acc, code)
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            Clock.schedule_once(lambda dt: self._on_resolve_done(result), 0)
        threading.Thread(target=do, daemon=True).start()

    def _on_resolve_done(self, result):
        self._wd_resolve_spinner.active = False
        if result.get("ok"):
            name = ""
            d = result.get("data") or {}
            if isinstance(d, dict):
                name = d.get("account_name") or ""
            if name:
                self._wd_account_name.text = name
                self._wd_account_verified = True
                self._wd_resolve_label.text = "✓ Verified"
                self._wd_resolve_label.text_color = rgba(SUCCESS)
            else:
                self._wd_resolve_label.text = "Could not verify"
                self._wd_resolve_label.text_color = rgba(ERROR)
                self._wd_account_verified = False
        else:
            err = result.get("error") or "Could not verify account"
            self._wd_resolve_label.text = err
            try:
                self._wd_resolve_label.text_color = rgba(ERROR)
            except Exception:
                pass
            self._wd_account_verified = False
        self._validate_withdraw()

    def _validate_withdraw(self):
        try:
            amount_raw = self._wd_amount.text.strip() if hasattr(self, "_wd_amount") else ""
            bank_code = getattr(self, "_wd_selected_bank_code", "")
            acc = self._wd_account_number.text.strip() if hasattr(self, "_wd_account_number") else ""
            verified = getattr(self, "_wd_account_verified", False)
            # reset amount error unless needed
            has_error = False
            if amount_raw:
                try:
                    amt = float(amount_raw)
                    bal = float(str(self._data.get("balance","0.00")).replace(",",""))
                    if amt < 5000:
                        self._wd_amount_error.text = "Minimum withdrawal is ₦5,000"
                        self._wd_amount_error.height = "16dp"
                        has_error = True
                    elif amt > bal:
                        self._wd_amount_error.text = f"Exceeds available balance ₦{self._data.get('balance','0.00')}"
                        self._wd_amount_error.height = "16dp"
                        has_error = True
                    else:
                        self._wd_amount_error.text = ""
                        self._wd_amount_error.height = "0dp"
                except Exception:
                    self._wd_amount_error.text = "Enter a valid amount"
                    self._wd_amount_error.height = "16dp"
                    has_error = True
            else:
                # empty is not error yet, just disable submit
                self._wd_amount_error.text = ""
                self._wd_amount_error.height = "0dp"
            if acc and len(acc) != 10:
                # let helper show, not error until 10 needed for resolve
                pass
            enable = False
            if amount_raw and bank_code and len(acc) == 10 and verified and not has_error:
                try:
                    amt = float(amount_raw)
                    if amt >= 5000:
                        enable = True
                except Exception:
                    enable = False
            self._wd_submit.disabled = not enable
        except Exception:
            try:
                self._wd_submit.disabled = True
            except Exception:
                pass

    def _do_withdraw(self, *args):
        # final validation before submit
        self._validate_withdraw()
        if self._wd_submit.disabled:
            return
        self._wd_submit.disabled = True
        self._wd_general_error.text = ""
        self._wd_general_error.height = "0dp"
        amount = self._wd_amount.text.strip()
        bank_code = self._wd_selected_bank_code
        acc = self._wd_account_number.text.strip()
        name = self._wd_account_name.text.strip()
        self._wd_resolve_spinner.active = True
        self._wd_resolve_label.text = "Submitting..."
        import threading
        def do():
            result = {"ok": False, "error": "Failed"}
            try:
                from app.services.rider_service import request_rider_withdrawal
                result = request_rider_withdrawal(amount, bank_code, acc, name)
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            Clock.schedule_once(lambda dt: self._on_withdraw_done(result), 0)
        threading.Thread(target=do, daemon=True).start()

    def _on_withdraw_done(self, result):
        self._wd_resolve_spinner.active = False
        self._wd_resolve_label.text = ""
        self._wd_submit.disabled = False
        if result.get("ok"):
            msg = ""
            if isinstance(result.get("data"), dict):
                msg = result["data"].get("message") or result.get("data").get("msg") or ""
            msg = msg or result.get("error") or "Withdrawal requested"
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text=msg or "Withdrawal requested successfully").open()
            except Exception:
                pass
            self._close_withdraw_modal()
            # refresh wallet
            Clock.schedule_once(lambda dt: self._load_wallet(), 0.5)
        else:
            err = result.get("error") or "Withdrawal failed"
            self._wd_general_error.text = err
            self._wd_general_error.height = "24dp"
            self._wd_general_error.text_color = rgba(ERROR)
            self._validate_withdraw()

    # ---------- Section 2: Stats row ----------
    def _build_stats_row(self):
        self._stats_grid = GridLayout(cols=3, spacing="10dp", size_hint_y=None)
        self._stats_grid.bind(minimum_height=self._stats_grid.setter("height"))
        self._content.add_widget(self._stats_grid)
        self._render_stats()

    def _render_stats(self):
        try:
            self._stats_grid.clear_widgets()
        except Exception:
            pass
        d = self._data or {}
        items = [
            ("Total Earned", "₦" + str(d.get("total_earned", "0.00")), SUCCESS),
            ("Total Withdrawn", "₦" + str(d.get("total_withdrawn", "0.00")), ERROR),
            ("Transactions", str(d.get("transaction_count", 0)), "#1976D2"),
        ]
        for label, value, color in items:
            card = MDCard(orientation="vertical", padding="8dp", spacing="2dp", size_hint_y=None, height="72dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
            val_lbl = MDLabel(text=value, font_style="Subtitle1", font_size="13sp", bold=True, theme_text_color="Custom", text_color=rgba(color), halign="center", valign="middle", max_lines=1, shorten=True, adaptive_height=True, text_size=(dp(106 - 16), None))
            lbl = MDLabel(text=label.upper(), font_style="Caption", font_size="7sp", theme_text_color="Custom", text_color=MUTED, halign="center", valign="middle", max_lines=1, shorten=True, shorten_from="right", adaptive_height=True, text_size=(dp(106 - 16), None))
            try:
                card.bind(width=lambda inst, w, vl=val_lbl, ll=lbl: (setattr(vl, "text_size", (w - dp(16), None)), setattr(ll, "text_size", (w - dp(16), None))))
            except Exception:
                pass
            card.add_widget(val_lbl)
            card.add_widget(lbl)
            self._stats_grid.add_widget(card)

    # ---------- Section 3: Transaction History ----------
    def _build_history(self):
        card = MDCard(orientation="vertical", padding="12dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
        head = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="22dp")
        head.add_widget(MDIcon(icon="history", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="18dp", font_size="14sp"))
        head.add_widget(MDLabel(text="Transaction History", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, size_hint_x=1))
        card.add_widget(head)
        card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba("#e0e0e0")))
        self._history_box = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, padding=["0dp","8dp","0dp","4dp"])
        card.add_widget(self._history_box)
        self._history_card = card
        self._content.add_widget(card)
        self._render_history()

    def _render_history(self):
        try:
            self._history_box.clear_widgets()
        except Exception:
            pass
        d = self._data or {}
        count = int(d.get("transaction_count", 0) or 0)
        if count == 0:
            empty = MDBoxLayout(orientation="vertical", spacing="8dp", padding=["0dp","16dp","0dp","16dp"], adaptive_height=True)
            empty.add_widget(MDIcon(icon="receipt-text-outline", halign="center", theme_text_color="Custom", text_color=rgba("#d5e8d0"), font_size="36sp", size_hint_y=None, height="36dp"))
            empty.add_widget(MDLabel(text="No Transactions Yet", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK, halign="center", adaptive_height=True))
            empty.add_widget(MDLabel(text="Complete deliveries to start earning and see your transactions here.", font_style="Caption", theme_text_color="Custom", text_color=MUTED, halign="center", adaptive_height=True))
            btn_wrap = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_y=None, height="36dp", padding=["0dp","8dp","0dp","0dp"])
            btn_wrap.add_widget(MDLabel(text=""))
            btn = MDRaisedButton(text="View Deliveries", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", size_hint_x=None, width="140dp", on_release=lambda x: self._go_deliveries())
            btn_wrap.add_widget(btn)
            btn_wrap.add_widget(MDLabel(text=""))
            empty.add_widget(btn_wrap)
            self._history_box.add_widget(empty)
        else:
            # Future populated state — transactions_html parsing not yet captured; show placeholder list
            self._history_box.add_widget(MDLabel(text=f"{count} transaction(s)", font_style="Body2", theme_text_color="Custom", text_color=MUTED, halign="center", adaptive_height=True))
            # TODO: render per-transaction rows once funded account sample captured

    def _go_deliveries(self, *args):
        # Consistent with dashboard View All stub per Q10
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="All deliveries — coming soon").open()
        except Exception:
            pass
        if self.manager:
            try:
                self.manager.current = "rider_home"
            except Exception:
                pass

    def _build_footer(self):
        footer = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="56dp", md_bg_color=rgba(DARK), radius=[0], elevation=0)
        footer.add_widget(MDLabel(text="© 2026 Trackway Logistics. Trackway Smart Logistics. All rights reserved.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        footer.add_widget(MDLabel(text="Delivering Excellence, One Parcel at a Time.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        self._content.add_widget(footer)

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
        try:
            name = session.get_customer_name() or ""
            self.top_name_label.text = name
            if hasattr(self, "_avatar_card"):
                self._avatar_card.children[0].text = (name.strip()[0].upper() if name else "A")
        except Exception:
            pass
        self._load_wallet()

    def _load_wallet(self):
        if self._loading:
            return
        self._loading = True
        import threading
        def do():
            data = {}
            err = None
            try:
                from app.services.rider_service import get_rider_wallet_json
                r = get_rider_wallet_json(page=1, limit=20)
                if r.get("ok"):
                    data = r.get("data") or {}
                else:
                    err = r.get("error")
            except Exception as e:
                err = str(e)
            Clock.schedule_once(lambda dt: self._apply_wallet(data, err), 0)
        threading.Thread(target=do, daemon=True).start()

    def _apply_wallet(self, data, err):
        self._loading = False
        if data and isinstance(data, dict):
            # accept even if all zeros — still valid empty state
            self._data.update({k: v for k, v in data.items() if v is not None})
            self._render_all()
        if err and "Session expired" in str(err):
            try:
                session.clear_session()
            except Exception:
                pass
            if self.manager:
                self.manager.current = "rider_login"

    def _render_all(self):
        try:
            bal = str(self._data.get("balance", "0.00"))
            earned = str(self._data.get("total_earned", "0.00"))
            self._balance_label.text = f"₦{bal}"
            self._banner_earned.text = f"Total Earned: ₦{earned}"
        except Exception:
            pass
        self._render_stats()
        self._render_history()

    def rebuild_ui(self):
        try:
            self._render_all()
        except Exception:
            pass
