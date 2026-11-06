from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDFlatButton, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.screen import MDScreen
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.list import MDList

from app.i18n.translator import tr
from app.core.theme import PRIMARY, DARK, MUTED, BACKGROUND, CARD_BG, ERROR
from app.views.base_screen import BaseScreen


def _notif_icon_for_type(type_str):
    t = (type_str or "info").strip().lower()
    mapping = {
        "info": ("information", "#1976d2", "#e3f2fd"),
        "success": ("check-circle", "#388e3c", "#e8f5e9"),
        "warning": ("alert", "#f57c00", "#fff8e1"),
        "danger": ("alert-circle", "#d32f2f", "#ffebee"),
    }
    if t in mapping:
        return mapping[t]
    if t in ("error", "failed", "cancelled"):
        return mapping["danger"]
    if t in ("completed", "done"):
        return mapping["success"]
    if t in ("pending", "in_progress"):
        return mapping["warning"]
    return mapping["info"]


class RiderNotificationScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = rgba(BACKGROUND)
        self._items = []
        self._page = 1
        self._has_more = False
        self._loading = False
        self._unread_count = 0
        self._total_count = 0

        outer = MDBoxLayout(orientation="vertical", spacing="0dp")
        outer.add_widget(self._build_top_nav())
        outer.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba("#e0e0e0")))
        outer.add_widget(self._build_header())
        outer.add_widget(self._build_list())
        outer.add_widget(self._build_footer())
        self.add_widget(outer)
        self._outer = outer

    # ---------- Top nav: white 48dp, van TRACKWAY + 3 right elements ----------
    def _build_top_nav(self):
        nav = MDCard(
            orientation="horizontal",
            padding="6dp",
            spacing="6dp",
            size_hint_x=1,
            size_hint_y=None,
            height="48dp",
            md_bg_color=rgba(CARD_BG),
            radius=[0],
            elevation=1,
        )
        # Left: van icon + TRACKWAY column
        left = MDBoxLayout(orientation="horizontal", spacing="6dp", size_hint_x=1, size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        van_card = MDCard(size_hint=(None, None), size=("28dp", "28dp"), md_bg_color=rgba(CARD_BG), radius=[6], elevation=0)
        van_card.add_widget(MDIcon(icon="truck-delivery", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="18sp", halign="center"))
        left.add_widget(van_card)
        logo_col = MDBoxLayout(orientation="vertical", spacing="0dp", size_hint_x=1, size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        # Use markup to make WAY green while TRACKWAY base is black
        logo_title = MDLabel(
            text="[color=12171a]TRACK[/color][color=567f30]WAY[/color]",
            markup=True,
            font_style="Subtitle2",
            bold=True,
            halign="left",
            size_hint_y=None,
            height="18dp",
        )
        logo_sub = MDLabel(text="SMART LOGISTICS", font_style="Caption", font_size="9sp", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_y=None, height="10dp", halign="left")
        logo_col.add_widget(logo_title)
        logo_col.add_widget(logo_sub)
        left.add_widget(logo_col)
        nav.add_widget(left)

        # Right: globe/language, back arrow, avatar with chevron — three elements
        right = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_x=None, width="148dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        # globe/language light gray circular with dropdown arrow beside it
        lang_wrap = MDBoxLayout(orientation="horizontal", spacing="2dp", size_hint_x=None, width="52dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        lang_btn = MDCard(size_hint=(None, None), size=("32dp", "32dp"), md_bg_color=rgba("#f0f0f0"), radius=[16], elevation=0, ripple_behavior=True)
        lang_btn.add_widget(MDIcon(icon="earth", theme_text_color="Custom", text_color=rgba(MUTED), font_size="16sp", halign="center"))
        lang_wrap.add_widget(lang_btn)
        lang_wrap.add_widget(MDIcon(icon="chevron-down", theme_text_color="Custom", text_color=rgba(MUTED), font_size="12sp", size_hint=(None, None), size=("16dp", "16dp"), pos_hint={"center_y": 0.5}))
        right.add_widget(lang_wrap)
        # Back arrow circular outlined white gray border
        back_btn = MDCard(size_hint=(None, None), size=("32dp", "32dp"), md_bg_color=rgba(CARD_BG), radius=[16], elevation=0, line_color=rgba("#e0e0e0"), line_width=1, ripple_behavior=True)
        back_btn.add_widget(MDIcon(icon="arrow-left", theme_text_color="Custom", text_color=rgba(MUTED), font_size="18sp", halign="center"))
        back_btn.bind(on_release=lambda x: self._go_back())
        # need to make ripple work
        try:
            back_btn.bind(on_release=lambda *a: self._go_back())
        except Exception:
            pass
        right.add_widget(back_btn)
        self._top_back_btn = back_btn
        # Avatar green circular A + chevron
        avatar_wrap = MDBoxLayout(orientation="horizontal", spacing="2dp", size_hint_x=None, width="56dp", size_hint_y=None, height="32dp", pos_hint={"center_y": 0.5})
        avatar = MDCard(size_hint=(None, None), size=("28dp", "28dp"), md_bg_color=rgba(PRIMARY), radius=[14], elevation=0)
        avatar.add_widget(MDLabel(text="A", halign="center", theme_text_color="Custom", text_color=rgba("#ffffff"), bold=True))
        avatar_wrap.add_widget(avatar)
        avatar_wrap.add_widget(MDIcon(icon="chevron-down", theme_text_color="Custom", text_color=rgba(MUTED), font_size="14sp", size_hint_x=None, width="16dp", pos_hint={"center_y": 0.5}))
        right.add_widget(avatar_wrap)
        nav.add_widget(right)
        self._top_nav = nav
        # store ref for language picker later if needed
        self._lang_btn = lang_btn
        return nav

    # ---------- Header: bell + Notifications + Total ----------
    def _build_header(self):
        header = MDBoxLayout(orientation="vertical", size_hint_x=1, size_hint_y=None, adaptive_height=True, md_bg_color=rgba(CARD_BG), padding=["12dp", "12dp", "12dp", "8dp"], spacing="4dp")
        row1 = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_x=1)
        row1.add_widget(MDIcon(icon="bell", theme_text_color="Custom", text_color=rgba(DARK), font_size="20sp", size_hint=(None, None), size=("24dp", "24dp"), pos_hint={"center_y": 0.5}))
        self._header_title = MDLabel(text=tr("notifications"), font_style="H6", bold=True, theme_text_color="Custom", text_color=rgba(DARK), size_hint_x=1, halign="left")
        row1.add_widget(self._header_title)
        header.add_widget(row1)
        row2 = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_x=1)
        row2.add_widget(MDIcon(icon="bell-outline", theme_text_color="Custom", text_color=rgba(MUTED), font_size="14sp", size_hint=(None, None), size=("18dp", "18dp"), pos_hint={"center_y": 0.5}))
        self._total_label = MDLabel(text=tr("total_notifications").format(count=0) if "{" in tr("total_notifications") else "Total: 0", font_style="Caption", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_x=1, halign="left")
        row2.add_widget(self._total_label)
        header.add_widget(row2)
        return header

    # ---------- List ----------
    def _build_list(self):
        container = MDBoxLayout(orientation="vertical", size_hint_x=1, size_hint_y=1, md_bg_color=rgba(BACKGROUND), padding=["0dp", "8dp", "0dp", "0dp"])
        self._list_scroll = ScrollView()
        self._list_content = MDList(spacing="10dp", padding=["12dp", "8dp", "12dp", "16dp"], adaptive_height=True)
        self._list_scroll.add_widget(self._list_content)
        container.add_widget(self._list_scroll)
        self._spinner = MDSpinner(size_hint=(None, None), size=(32, 32), active=False, color=rgba(PRIMARY), pos_hint={"center_x": 0.5})
        container.add_widget(self._spinner)
        return container

    # ---------- Footer: DARK near-black ----------
    def _build_footer(self):
        footer = MDCard(orientation="vertical", padding="12dp", spacing="4dp", size_hint_x=1, size_hint_y=None, height="56dp", md_bg_color=rgba(DARK), radius=[0], elevation=0)
        footer.add_widget(MDLabel(text="© 2026 Trackway Logistics. Trackway Smart Logistics. All rights reserved.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        footer.add_widget(MDLabel(text="Delivering Excellence, One Parcel at a Time.", font_style="Caption", halign="center", theme_text_color="Custom", text_color=rgba("#e8f0e3"), font_size="11sp", adaptive_height=True))
        return footer

    def _go_back(self, *args):
        if self.manager:
            # rider back goes to rider_home
            try:
                self.manager.current = "rider_home"
            except Exception:
                pass

    def on_pre_enter(self, *args):
        from app.core import session
        if not session.is_logged_in() or session.get_role() != "rider":
            if self.manager:
                try:
                    self.manager.current = "rider_login"
                except Exception:
                    pass
            return
        super().on_pre_enter(*args)

    def on_enter(self, *args):
        from app.core import session
        if not session.is_logged_in() or session.get_role() != "rider":
            if self.manager:
                try:
                    self.manager.current = "rider_login"
                except Exception:
                    pass
            return
        self._refresh()

    def _refresh(self, *args):
        if self._loading:
            return
        self._page = 1
        self._items = []
        self._list_content.clear_widgets()
        self._load_page()

    def _load_page(self):
        if self._loading:
            return
        self._loading = True
        self._spinner.active = True
        result = {"ok": False, "data": {}, "error": None}
        try:
            from app.services.rider_service import get_rider_notifications
            result = get_rider_notifications(page=self._page)
        except Exception as e:
            result = {"ok": False, "error": str(e), "data": {}}
        # fallback to customer service if rider returns 404/not found (dev)
        if not result.get("ok") and result.get("error") and ("404" in str(result["error"]) or "Not Found" in str(result["error"])):
            try:
                from app.services.customer_service import get_notifications as _get_c
                result = _get_c(page=self._page)
            except Exception:
                pass
        self._spinner.active = False
        self._loading = False
        if result.get("ok"):
            d = result.get("data") or {}
            # normalize: rider_service returns _unwrap raw, customer returns {items, unread_count, total}
            items = d.get("items") or d.get("notifications") or d.get("data") or []
            if isinstance(items, dict):
                items = items.get("items") or items.get("data") or []
            if not isinstance(items, list):
                items = []
            self._items.extend(items)
            self._unread_count = d.get("unread_count", 0)
            self._total_count = d.get("total", len(self._items))
            if self._total_count == 0 and items:
                self._total_count = len(self._items)
            # if result ok but no items, treat as true empty — do not inject demo
            if not self._total_count and not items and not self._items:
                self._total_count = 0
            self._has_more = d.get("has_more", False)
            try:
                self._page = int(d.get("page", self._page))
            except Exception:
                pass
            if items:
                self._render_items(items)
            elif not self._items:
                # real empty: show No notifications yet + Total: 0, nothing else
                self._show_empty()
            self._update_total_label()
            self._update_home_badge()
        else:
            # API failure: show proper error state, not fake data
            err = result.get("error") or "Unable to load notifications, please try again"
            self._show_error(err)

    def _render_items(self, items):
        if not items and not self._items:
            self._show_empty()
            return
        for notif in items:
            self._list_content.add_widget(self._create_notification_card(notif))

    def _create_notification_card(self, notif):
        notif_id = notif.get("id")
        title = notif.get("title") or notif.get("subject") or ""
        message = notif.get("message") or notif.get("body") or ""
        # plain/neutral for read - no accent/dot per screenshot
        is_read = notif.get("is_read", True)
        time_ago = notif.get("time_ago") or notif.get("timestamp") or notif.get("created_at") or ""

        card = MDCard(
            orientation="horizontal",
            padding="0dp",
            spacing="0dp",
            size_hint_x=1,
            size_hint_y=None,
            adaptive_height=True,
            md_bg_color=rgba(CARD_BG),
            radius=[12],
            elevation=1,
        )
        try:
            card.line_color = rgba(0, 0, 0, 0)
            card.line_width = 1
        except Exception:
            pass
        # accent hidden for rider View All per screenshot (plain/neutral)
        accent = MDBoxLayout(size_hint=(None, 1), width="4dp", size_hint_y=1, md_bg_color=rgba(0, 0, 0, 0), radius=[12, 0, 0, 12])
        card.add_widget(accent)
        inner = MDBoxLayout(orientation="vertical", padding="14dp", spacing="10dp", adaptive_height=True, size_hint_x=1, size_hint_y=None)
        card.add_widget(inner)

        title_row_container = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_x=1)
        icon_anchor = AnchorLayout(anchor_x="center", anchor_y="top", size_hint=(None, None), size=("32dp", "32dp"), padding=(0, dp(2), 0, 0))
        notif_type = notif.get("type") or notif.get("category") or "info"
        _icon, _text_color, _bg_color = _notif_icon_for_type(notif_type)
        icon_box = MDCard(size_hint=(None, None), size=("32dp", "32dp"), md_bg_color=rgba(_bg_color), radius=[16], elevation=0)
        icon_box.add_widget(MDIcon(icon=_icon, theme_text_color="Custom", text_color=rgba(_text_color), halign="center", valign="middle", font_size="18sp"))
        icon_anchor.add_widget(icon_box)
        title_row_container.add_widget(icon_anchor)
        title_anchor = AnchorLayout(anchor_x="left", anchor_y="top", size_hint_x=1, size_hint_y=None, height="32dp", padding=(0, dp(2), 0, 0))
        title_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_x=1, size_hint_y=None, pos_hint={"center_y": 0.5})
        title_lbl = MDLabel(text=title, font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color=rgba(DARK), adaptive_height=True, size_hint_x=1, halign="left", shorten=True, shorten_from="right")
        title_row.add_widget(title_lbl)
        # no dot / no Mark read per Rider View All spec (plain)
        title_anchor.add_widget(title_row)
        title_row_container.add_widget(title_anchor)
        inner.add_widget(title_row_container)

        body_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_x=1, size_hint_y=None)
        spacer = Widget(size_hint=(None, None), size=("32dp", "1dp"), opacity=0)
        body_row.add_widget(spacer)
        body_lbl = MDLabel(text=message, font_style="Body2", theme_text_color="Custom", text_color=rgba(MUTED), adaptive_height=True, size_hint_x=1, halign="left")
        body_row.add_widget(body_lbl)
        inner.add_widget(body_row)

        timestamp_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_x=1, size_hint_y=None)
        timestamp_row.add_widget(MDIcon(icon="clock-outline", theme_text_color="Custom", text_color=rgba(MUTED), font_size="12sp", size_hint=(None, None), size=("16dp", "16dp"), pos_hint={"center_y": 0.5}))
        ts_lbl = MDLabel(text=time_ago, font_style="Caption", theme_text_color="Custom", text_color=rgba(MUTED), adaptive_height=True, size_hint_x=1, halign="left", font_size="10sp")
        timestamp_row.add_widget(ts_lbl)
        inner.add_widget(timestamp_row)

        # wrap
        def _upd(*a):
            try:
                avail = card.width - dp(68) if card.width and card.width > dp(68) else dp(240)
                body_lbl.text_size = (avail, None)
                title_lbl.text_size = (avail, None)
                try:
                    body_lbl.texture_update()
                    title_lbl.texture_update()
                except Exception:
                    pass
            except Exception:
                pass
        try:
            card.bind(width=_upd)
            inner.bind(width=_upd)
            Clock.schedule_once(_upd, 0)
            Clock.schedule_once(_upd, 0.05)
        except Exception:
            pass

        card.notif_id = notif_id
        card.is_read = True
        return card

    def _update_total_label(self):
        try:
            count = self._total_count if self._total_count is not None else len(self._items)
            tmpl = tr("total_notifications")
            if "{" in tmpl:
                self._total_label.text = tmpl.format(count=count)
            else:
                self._total_label.text = f"Total: {count}"
        except Exception:
            try:
                self._total_label.text = f"Total: {len(self._items)}"
            except Exception:
                pass

    def _update_home_badge(self):
        if self.manager:
            try:
                home = self.manager.get_screen("rider_home")
                if hasattr(home, "bell_count_label"):
                    home.bell_count_label.text = str(self._unread_count) if self._unread_count > 0 else ""
            except Exception:
                pass

    def _show_empty(self):
        self._list_content.clear_widgets()
        empty = MDLabel(text=tr("no_notifications"), font_style="Body2", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_y=None, height="80dp")
        self._list_content.add_widget(empty)

    def _show_error(self, msg):
        self._list_content.clear_widgets()
        err_text = msg or "Unable to load notifications, please try again"
        # normalize HTML 404 to user-friendly error
        if "404" in str(err_text) or "Not Found" in str(err_text):
            err_text = "Unable to load notifications, please try again"
        box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="8dp", padding="12dp")
        box.add_widget(MDLabel(text=err_text, font_style="Body2", halign="center", theme_text_color="Custom", text_color=rgba(ERROR), size_hint_y=None, height="80dp"))
        btn = MDFlatButton(text=tr("retry"), theme_text_color="Custom", text_color=rgba(PRIMARY), on_release=self._refresh)
        box.add_widget(btn)
        self._list_content.add_widget(box)

    def rebuild_ui(self):
        try:
            self._header_title.text = tr("notifications")
            self._update_total_label()
        except Exception:
            pass
