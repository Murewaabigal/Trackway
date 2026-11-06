from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton

from app.core.theme import PRIMARY, PRIMARY_DARK, DARK, MUTED, BACKGROUND, CARD_BG, SUCCESS, ERROR
from app.core import session
from app.i18n.translator import tr
from app.views.base_screen import BaseScreen


class ReferEarnScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._stats = {}
        self._referrals = []
        self._pagination = {}
        self._current_page = 1
        self._has_next = False
        self._reward_amount = 500

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

        self._build_hero()
        self._build_stats()
        self._build_how_it_works()
        self._build_referrals_section()
        self._build_info_callout()
        self._build_footer()

        try:
            Window.bind(width=self._on_window_width)
        except Exception:
            pass

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
        self.top_name_label = MDLabel(text="", font_style="Caption", bold=True, theme_text_color="Custom", text_color=DARK, halign="left", valign="middle")
        name_card.add_widget(self.top_name_label)
        right_cluster.add_widget(name_card)
        self._name_card = name_card

        # Reuse profile dropdown from customer_home if available, else direct
        avatar.bind(on_release=lambda x: self._open_profile_menu())
        name_card.bind(on_release=lambda x: self._open_profile_menu())

        nav.add_widget(logo)
        nav.add_widget(right_cluster)
        self._top_nav = nav
        return nav

    def _open_profile_menu(self, *args):
        # Delegate to customer_home's menu if exists, else go to profile
        try:
            # Try to reuse existing menu from customer_home
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, 'root'):
                # Find customer_home screen to reuse its menu
                try:
                    home = app.root.get_screen("customer_home")
                    if hasattr(home, "_open_profile_menu"):
                        home._open_profile_menu()
                        return
                except Exception:
                    pass
        except Exception:
            pass
        # Fallback to profile
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
            spacing="12dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba(PRIMARY),
            radius=[14],
            elevation=1,
        )
        self._hero_title = MDLabel(
            text="🎉 Invite Friends, Earn Rewards!",
            font_style="H6",
            bold=True,
            theme_text_color="Custom",
            text_color="white",
            adaptive_height=True,
            halign="center",
        )
        self._hero_sub = MDLabel(
            text="Share your referral code with friends. When they sign up and send a parcel, you both get rewarded!",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=rgba("#e8f0e3"),
            adaptive_height=True,
            halign="center",
        )
        self._hero_card.add_widget(self._hero_title)
        self._hero_card.add_widget(self._hero_sub)

        # Inset card inside banner
        self._inset_card = MDCard(
            orientation="vertical",
            padding="12dp",
            spacing="8dp",
            size_hint_x=1,
            adaptive_height=True,
            md_bg_color=rgba("#e8f0e3"),
            radius=[12],
            elevation=0,
        )
        self._inset_label = MDLabel(
            text="Your Referral Code:",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=MUTED,
            adaptive_height=True,
            halign="center",
        )
        self._code_label = MDLabel(
            text="REF------",
            font_style="H5",
            bold=True,
            theme_text_color="Custom",
            text_color=DARK,
            adaptive_height=True,
            halign="center",
        )
        btn_row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="36dp", pos_hint={"center_x": 0.5}, size_hint_x=None, width="180dp")
        self._copy_btn = MDRaisedButton(
            text="Copy",
            md_bg_color=rgba(PRIMARY),
            theme_text_color="Custom",
            text_color="white",
            size_hint_x=None,
            width="80dp",
            on_release=lambda x: self._copy_code(),
        )
        self._share_btn = MDRaisedButton(
            text="Share",
            md_bg_color=rgba(PRIMARY_DARK),
            theme_text_color="Custom",
            text_color="white",
            size_hint_x=None,
            width="80dp",
            on_release=lambda x: self._share_code(),
        )
        btn_row.add_widget(self._copy_btn)
        btn_row.add_widget(self._share_btn)
        self._inset_card.add_widget(self._inset_label)
        self._inset_card.add_widget(self._code_label)
        self._inset_card.add_widget(btn_row)
        self._hero_card.add_widget(self._inset_card)

        self._reward_label = MDLabel(
            text="🎁 You earn ₦500.00 for each friend who ships their first parcel!",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=rgba("#e8f0e3"),
            adaptive_height=True,
            halign="center",
        )
        self._hero_card.add_widget(self._reward_label)
        self._content.add_widget(self._hero_card)

    def _copy_code(self):
        code = getattr(self, "_stats", {}).get("referral_code") or "REF------"
        try:
            Clipboard.copy(code)
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="Copied").open()
        except Exception:
            pass

    def _share_code(self):
        # Ship Snackbar + visible code for now, no plyer native sheet yet per spec
        url = getattr(self, "_stats", {}).get("share_url") or f"https://www.trackwaylogistics.ng/customer/register.php?ref={getattr(self, '_stats', {}).get('referral_code','')}"
        try:
            Clipboard.copy(url)
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="Copied share link").open()
        except Exception:
            pass

    # ---------- Stats row 4 cards (spec 3) ----------
    def _build_stats(self):
        self._stats_container = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="8dp")
        self._content.add_widget(self._stats_container)
        self._render_stats()

    def _render_stats(self):
        self._stats_container.clear_widgets()
        s = getattr(self, "_stats", {}) or {}
        items = [
            ("Total Referrals", s.get("total_referrals", 0), "account-group", PRIMARY),
            ("Completed", s.get("completed_referrals", s.get("completed", 0)), "check-circle-outline", SUCCESS),
            ("Pending", s.get("pending_referrals", s.get("pending", 0)), "progress-clock", MUTED),
            ("Referral Balance", f"₦{float(str(s.get('referral_balance', 0)).replace(',', '').replace('₦','') or 0):,.2f}", "wallet-outline", PRIMARY),
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
            val_label = MDLabel(text=str(value), font_style="H6", bold=True, halign="left", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=1, adaptive_height=True)
            icon_w = MDIcon(icon=icon, theme_text_color="Custom", text_color=rgba(color), halign="right", size_hint_x=None, width="28dp", font_size="20sp")
            top_row.add_widget(val_label)
            top_row.add_widget(icon_w)
            lab = MDLabel(text=label, font_style="Caption", halign="left", theme_text_color="Custom", text_color=MUTED, adaptive_height=True)
            card.add_widget(top_row)
            card.add_widget(lab)
            grid.add_widget(card)
        self._stats_container.add_widget(grid)

    # ---------- How It Works (spec 4) ----------
    def _build_how_it_works(self):
        card = MDCard(orientation="vertical", padding="16dp", spacing="12dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="24dp")
        header.add_widget(MDIcon(icon="information-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="How It Works", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        card.add_widget(header)

        steps_row = MDBoxLayout(orientation="horizontal", spacing="8dp", adaptive_height=True, size_hint_y=None, height="100dp")
        steps = [
            ("1", "Share Your Code", "Share your unique referral code with friends and family"),
            ("2", "Friend Signs Up", "They use your referral code when creating their account"),
            ("3", "They Ship a Parcel", "Your friend completes their first delivery with Trackway"),
            ("4", "You Earn Rewards!", "Reward credited to your referral balance"),
        ]
        for num, title, desc in steps:
            col = MDBoxLayout(orientation="vertical", spacing="6dp", adaptive_height=True, size_hint_x=1)
            circle = MDCard(size_hint=(None, None), size=("32dp", "32dp"), md_bg_color=rgba(PRIMARY), radius=[16], elevation=0, pos_hint={"center_x": 0.5})
            circle.add_widget(MDLabel(text=num, halign="center", valign="middle", theme_text_color="Custom", text_color="white", bold=True))
            col.add_widget(circle)
            col.add_widget(MDLabel(text=title, font_style="Caption", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True, text_size=(None, None)))
            col.add_widget(MDLabel(text=desc, font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True, text_size=(None, None), font_size="10sp"))
            steps_row.add_widget(col)
        card.add_widget(steps_row)
        self._content.add_widget(card)

    # ---------- Your Referrals section (spec 5) ----------
    def _build_referrals_section(self):
        header = MDBoxLayout(orientation="horizontal", spacing="6dp", adaptive_height=True, size_hint_y=None, height="24dp", padding=["4dp", "0dp"])
        header.add_widget(MDIcon(icon="account-group", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        header.add_widget(MDLabel(text="Your Referrals", font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=DARK))
        self._content.add_widget(header)

        self._referrals_container = MDBoxLayout(orientation="vertical", spacing="8dp", adaptive_height=True, size_hint_y=None)
        self._referrals_container.bind(minimum_height=self._referrals_container.setter("height"))
        self._content.add_widget(self._referrals_container)
        self._render_referrals()

    def _render_referrals(self):
        self._referrals_container.clear_widgets()
        items = getattr(self, "_referrals", []) or []
        if not items:
            empty = MDCard(orientation="vertical", padding="16dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[14], elevation=1)
            empty.add_widget(MDIcon(icon="account-group-outline", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), font_size="48sp", size_hint_y=None, height="48dp"))
            empty.add_widget(MDLabel(text="No referrals yet", font_style="Subtitle2", bold=True, halign="center", theme_text_color="Custom", text_color=DARK, adaptive_height=True))
            empty.add_widget(MDLabel(text="Share your referral code to start earning rewards!", font_style="Caption", halign="center", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            btn = MDRaisedButton(text="Share Now", md_bg_color=rgba(PRIMARY), theme_text_color="Custom", text_color="white", pos_hint={"center_x": 0.5}, on_release=lambda x: self._share_code())
            empty.add_widget(btn)
            self._referrals_container.add_widget(empty)
            return
        for r in items:
            name = r.get("name") or r.get("full_name") or r.get("phone") or "Friend"
            date = r.get("created_at") or r.get("date") or ""
            status = (r.get("status") or "pending").lower()
            reward = r.get("reward") or r.get("reward_amount") or self._reward_amount
            is_completed = status in ("completed", "success", "done")
            card = MDCard(orientation="horizontal", padding="12dp", spacing="8dp", size_hint_x=1, size_hint_y=None, height="64dp", md_bg_color=rgba(CARD_BG), radius=[12], elevation=1)
            avatar = MDCard(size_hint=(None, None), size=("36dp", "36dp"), md_bg_color=rgba(MUTED if not is_completed else SUCCESS), radius=[18], elevation=0)
            avatar.add_widget(MDLabel(text=name[0].upper() if name else "F", halign="center", theme_text_color="Custom", text_color="white", bold=True))
            card.add_widget(avatar)
            col = MDBoxLayout(orientation="vertical", spacing="2dp", size_hint_x=1, adaptive_height=True)
            col.add_widget(MDLabel(text=name, font_style="Body2", bold=True, theme_text_color="Custom", text_color=DARK, adaptive_height=True))
            col.add_widget(MDLabel(text=date, font_style="Caption", theme_text_color="Custom", text_color=MUTED, adaptive_height=True))
            card.add_widget(col)
            # Status pill
            chip_color = SUCCESS if is_completed else MUTED
            chip = MDCard(size_hint=(None, None), size=("80dp", "24dp"), md_bg_color=rgba(CARD_BG), line_color=rgba(chip_color), radius=[12], elevation=0)
            chip.add_widget(MDLabel(text=status.capitalize(), halign="center", font_style="Caption", theme_text_color="Custom", text_color=rgba(chip_color), font_size="11sp"))
            card.add_widget(chip)
            try:
                reward_str = f"₦{float(str(reward).replace(',', '')):,.0f}"
            except Exception:
                reward_str = f"₦{reward}"
            card.add_widget(MDLabel(text=reward_str, font_style="Caption", bold=True, halign="right", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="60dp"))
            self._referrals_container.add_widget(card)
        # Pagination button if has_next
        if getattr(self, "_has_next", False):
            more = MDFlatButton(text="Load More", theme_text_color="Custom", text_color=rgba(PRIMARY), pos_hint={"center_x": 0.5}, on_release=lambda x: self._load_next_page())
            self._referrals_container.add_widget(more)

    def _load_next_page(self):
        self._current_page += 1
        self._load_referrals()

    # ---------- Info callout (spec 6) ----------
    def _build_info_callout(self):
        card = MDCard(orientation="horizontal", padding="12dp", spacing="8dp", size_hint_x=1, adaptive_height=True, md_bg_color=rgba("#f6f6f8"), radius=[12], elevation=0)
        card.add_widget(MDIcon(icon="information-outline", theme_text_color="Custom", text_color=rgba(PRIMARY), size_hint_x=None, width="24dp"))
        card.add_widget(MDLabel(
            text="How to use your referral balance: Your referral credits can be applied to your next delivery. The system will automatically apply your available balance to reduce your delivery cost.",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=MUTED,
            adaptive_height=True,
        ))
        self._content.add_widget(card)

    # ---------- Footer (spec 7) ----------
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
        self._load_referral_data()

    def _load_referral_data(self):
        # Stats
        try:
            from app.services.customer_service import get_referral_stats
            result = get_referral_stats()
            if result.get("ok"):
                d = result.get("data", {}) or {}
                self._stats = d
                self._reward_amount = d.get("reward_amount", 500)
                # Update hero
                code = d.get("referral_code") or "REF------"
                self._code_label.text = code
                try:
                    amt = float(str(self._reward_amount).replace(",", ""))
                    self._reward_label.text = f"🎁 You earn ₦{amt:,.2f} for each friend who ships their first parcel!"
                except Exception:
                    self._reward_label.text = f"🎁 You earn ₦{self._reward_amount} for each friend who ships their first parcel!"
                # Update name
                try:
                    name = session.get_customer_name() or ""
                    self.top_name_label.text = name
                    if hasattr(self, "_avatar_card"):
                        initial = (name.strip()[0].upper() if name else "A")
                        self._avatar_card.children[0].text = initial
                except Exception:
                    pass
                self._render_stats()
            elif result.get("error") and "Session expired" in str(result.get("error")):
                from app.core import session
                session.clear_session()
                if self.manager:
                    self.manager.current = "customer_login"
                return
        except Exception:
            pass
        # List
        self._current_page = 1
        self._load_referrals()

    def _load_referrals(self):
        try:
            from app.services.customer_service import get_referrals
            result = get_referrals(page=self._current_page)
            if result.get("ok"):
                data = result.get("data", {}) or {}
                referrals = data.get("referrals", []) or []
                pagination = data.get("pagination", {}) or {}
                if self._current_page == 1:
                    self._referrals = referrals
                else:
                    self._referrals.extend(referrals)
                self._pagination = pagination
                self._has_next = pagination.get("has_next", False) if isinstance(pagination, dict) else data.get("has_next", False)
                self._render_referrals()
            elif result.get("error") and "Session expired" in str(result.get("error")):
                from app.core import session
                session.clear_session()
                if self.manager:
                    self.manager.current = "customer_login"
                return
        except Exception:
            pass

    def rebuild_ui(self):
        try:
            from app.i18n.translator import tr
            if hasattr(self, '_title_label'):
                self._title_label.text = tr("refer_and_earn")
            # re-render referral code/balance areas
            if hasattr(self, '_render'):
                try:
                    self._render()
                except Exception:
                    pass
        except Exception:
            pass
