from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFlatButton, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.screen import MDScreen
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.list import MDList
from kivymd.uix.label import MDIcon


class PlainTextLink(ButtonBehavior, MDLabel):
    """Plain-text link: no background, no border, no elevation — looks like a link."""
    pass

from app.i18n.translator import tr
from app.core.theme import (
    PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, DARK, MUTED, BACKGROUND, CARD_BG, ERROR, SUCCESS,
)
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


class NotificationScreen(BaseScreen):
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

        self._build_header(outer)
        self._build_stats_row(outer)
        self._build_list(outer)

        self.add_widget(outer)

    def _build_header(self, outer):
        header = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=1,
            size_hint_y=None,
            height="56dp",
            padding=["12dp", "8dp", "12dp", "8dp"],
            spacing="8dp",
        )

        back_btn = MDIconButton(
            icon="chevron-left",
            theme_icon_color="Custom",
            icon_color=rgba(DARK),
            icon_size="24sp",
            size_hint=(None, None),
            size=("48dp", "48dp"),
            pos_hint={"center_y": 0.5},
            on_release=self._go_back,
        )
        header.add_widget(back_btn)

        title = MDLabel(
            text=tr("notifications"),
            font_style="H6",
            bold=True,
            halign="left",
            theme_text_color="Custom",
            text_color=rgba(DARK),
            size_hint_x=1,
            size_hint_y=None,
            height="32dp",
            pos_hint={"center_y": 0.5},
        )
        header.add_widget(title)

        self._mark_all_btn = PlainTextLink(
            text=tr("mark_all_read"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            font_size="14sp",
            halign="right",
            valign="middle",
            size_hint=(None, None),
            size=("140dp", "32dp"),
            pos_hint={"center_y": 0.5},
            on_press=self._mark_all_read,
        )
        self._mark_all_btn.opacity = 0
        self._mark_all_btn.disabled = True
        header.add_widget(self._mark_all_btn)

        outer.add_widget(header)

    def _build_stats_row(self, outer):
        stats_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=1,
            size_hint_y=None,
            height="36dp",
            padding=["12dp", "0dp", "12dp", "8dp"],
            spacing="8dp",
        )

        self._total_pill = MDLabel(
            text=tr("total_notifications").format(count=0),
            font_style="Caption",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=rgba(MUTED),
            size_hint_x=0.5,
            size_hint_y=None,
            height="28dp",
        )
        total_card = MDCard(
            orientation="vertical",
            padding=["8dp", "2dp", "8dp", "2dp"],
            radius=[14],
            elevation=0,
            md_bg_color=rgba(CARD_BG),
            size_hint_x=0.5,
            size_hint_y=None,
            height="32dp",
        )
        total_card.add_widget(self._total_pill)
        stats_row.add_widget(total_card)

        self._unread_pill = MDLabel(
            text=tr("unread_notifications").format(count=0),
            font_style="Caption",
            bold=True,
            halign="center",
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            size_hint_x=0.5,
            size_hint_y=None,
            height="28dp",
        )
        unread_card = MDCard(
            orientation="vertical",
            padding=["8dp", "2dp", "8dp", "2dp"],
            radius=[14],
            elevation=0,
            md_bg_color=rgba("#e8f0e3"),
            size_hint_x=0.5,
            size_hint_y=None,
            height="32dp",
        )
        unread_card.add_widget(self._unread_pill)
        stats_row.add_widget(unread_card)

        outer.add_widget(stats_row)

    def _build_list(self, outer):
        list_container = MDBoxLayout(orientation="vertical", size_hint_x=1, size_hint_y=1)

        refresh_btn = MDFlatButton(
            text=tr("retry"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            font_size="12sp",
            size_hint=(None, None),
            height="32dp",
            width="100dp",
            pos_hint={"center_x": 0.5},
            on_release=self._refresh,
        )
        refresh_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=1,
            size_hint_y=None,
            height="40dp",
            padding=["0dp", "8dp", "0dp", "0dp"],
        )
        refresh_row.add_widget(MDBoxLayout())  # spacer
        refresh_row.add_widget(refresh_btn)
        refresh_row.add_widget(MDBoxLayout())  # spacer
        list_container.add_widget(refresh_row)

        self._list_scroll = ScrollView()
        self._list_content = MDList(
            spacing="10dp",
            padding=["12dp", "8dp", "12dp", "16dp"],
            adaptive_height=True,
        )
        self._list_scroll.add_widget(self._list_content)
        list_container.add_widget(self._list_scroll)

        self._spinner = MDSpinner(
            size_hint=(None, None), size=(32, 32),
            active=False, color=rgba(PRIMARY),
            pos_hint={"center_x": 0.5},
        )
        list_container.add_widget(self._spinner)

        outer.add_widget(list_container)

    def _go_back(self, *args):
        if self.manager:
            self.manager.current = "customer_home"

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

        from app.services.customer_service import get_notifications
        result = get_notifications(page=self._page)

        self._spinner.active = False
        self._loading = False

        if result["ok"]:
            data = result["data"]
            page_items = data["items"]
            self._items.extend(page_items)
            self._unread_count = data["unread_count"]
            self._total_count = data["total"]
            self._has_more = data["has_more"]
            self._page = data["page"]
            self._render_items(page_items)
            self._update_stats_badges()
            self._update_mark_all_visibility()
            self._update_home_badge()
        else:
            self._show_error(result["error"])

    def _render_items(self, items):
        if not items and not self._items:
            self._show_empty()
            return

        for notif in items:
            self._list_content.add_widget(self._create_notification_card(notif))

    def _create_notification_card(self, notif):
        notif_id = notif.get("id")
        title = notif.get("title") or ""
        message = notif.get("message") or ""
        is_read = notif.get("is_read", True)
        time_ago = notif.get("time_ago") or notif.get("created_at") or ""

        # card with edge-to-edge green accent bar (web parity) + top-aligned icon
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
        accent = MDBoxLayout(
            size_hint=(None, 1),
            width="4dp",
            size_hint_y=1,
            md_bg_color=rgba(PRIMARY) if not is_read else rgba(0, 0, 0, 0),
            radius=[12, 0, 0, 12],
        )
        card.add_widget(accent)
        inner = MDBoxLayout(
            orientation="vertical",
            padding="14dp",
            spacing="10dp",
            adaptive_height=True,
            size_hint_x=1,
            size_hint_y=None,
        )
        card.add_widget(inner)

        # Option C: structural split — icon measured only against title, body is separate row with spacer.
        # Title row (icon + title only) — height does NOT include body, so icon stays pinned to title.
        title_row_container = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_x=1)

        icon_anchor = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            size_hint=(None, None),
            size=("32dp", "32dp"),
            padding=(0, dp(2), 0, 0),
        )
        notif_type = notif.get("type") or notif.get("category") or "info"
        _icon, _text_color, _bg_color = _notif_icon_for_type(notif_type)
        icon_box = MDCard(
            size_hint=(None, None),
            size=("32dp", "32dp"),
            md_bg_color=rgba(_bg_color),
            radius=[16],
            elevation=0,
        )
        icon_box.add_widget(MDIcon(
            icon=_icon,
            theme_text_color="Custom",
            text_color=rgba(_text_color),
            halign="center",
            valign="middle",
            font_size="18sp",
        ))
        icon_anchor.add_widget(icon_box)
        title_row_container.add_widget(icon_anchor)

        title_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_x=1)

        if not is_read:
            unread_dot = MDLabel(
                text="\u2022",
                font_style="Caption",
                bold=True,
                theme_text_color="Custom",
                text_color=rgba(PRIMARY),
                size_hint=(None, None),
                size=("16dp", "16dp"),
                halign="center",
                valign="middle",
            )
            title_row.add_widget(unread_dot)

        title_label = MDLabel(
            text=title,
            font_style="Subtitle1",
            bold=not is_read,
            theme_text_color="Custom",
            text_color=rgba(DARK),
            adaptive_height=True,
            size_hint_x=1,
        )
        title_row.add_widget(title_label)

        if not is_read:
            mark_read_btn = MDFlatButton(
                text=tr("mark_read"),
                theme_text_color="Custom",
                text_color=rgba(PRIMARY),
                font_size="12sp",
                size_hint=(None, None),
                height="24dp",
                pos_hint={"center_y": 0.5},
                on_release=lambda x, nid=notif_id: self._mark_single_read(nid),
            )
            title_row.add_widget(mark_read_btn)

        title_row_container.add_widget(title_row)
        inner.add_widget(title_row_container)

        # Body row — spacer preserves original indent (32dp icon + 8dp spacing) so body stays under title.
        body_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_x=1)
        spacer = Widget(size_hint=(None, None), size=("32dp", "1dp"), opacity=0)
        body_row.add_widget(spacer)
        body_label = MDLabel(
            text=message,
            font_style="Body2",
            theme_text_color="Custom",
            text_color=rgba(MUTED),
            adaptive_height=True,
            size_hint_x=1,
        )
        body_row.add_widget(body_label)
        inner.add_widget(body_row)

        timestamp_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp")
        timestamp_row.add_widget(MDIcon(
            icon="clock-outline",
            theme_text_color="Custom",
            text_color=rgba(MUTED),
            font_size="12sp",
            size_hint=(None, None),
            size=("16dp", "16dp"),
            pos_hint={"center_y": 0.5},
        ))
        timestamp_label = MDLabel(
            text=time_ago,
            font_style="Caption",
            theme_text_color="Custom",
            text_color=rgba(MUTED),
            adaptive_height=True,
            halign="left",
            font_size="10sp",
        )
        timestamp_row.add_widget(timestamp_label)
        inner.add_widget(timestamp_row)

        card.notif_id = notif_id
        card.is_read = is_read
        card.bind(on_release=lambda x: self._on_card_tap(notif))

        return card

    def _on_card_tap(self, notif):
        link = notif.get("link")
        if link:
            pass

    def _mark_single_read(self, notif_id):
        from app.services.customer_service import mark_notification_read
        result = mark_notification_read(notif_id)
        if result["ok"]:
            self._unread_count = max(0, self._unread_count - 1)
            self._update_stats_badges()
            self._update_mark_all_visibility()
            self._update_home_badge()
            self._refresh_list_after_mark_read(notif_id)
        else:
            self._show_error(result["error"] or "Failed to mark as read")

    def _mark_all_read(self, *args):
        from app.services.customer_service import mark_all_notifications_read
        result = mark_all_notifications_read()
        if result["ok"]:
            self._unread_count = 0
            self._update_stats_badges()
            self._update_mark_all_visibility()
            self._update_home_badge()
            self._refresh_list_after_mark_all_read()
            try:
                from kivymd.uix.snackbar import Snackbar
                msg = tr("all_notifications_marked_read") if tr("all_notifications_marked_read") != "all_notifications_marked_read" else "All notifications marked as read"
                Snackbar(text=msg, duration=2).open()
            except Exception:
                pass
        else:
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text=str(result.get("error") or "Failed to mark all as read"), duration=2.5).open()
            except Exception:
                pass
            self._show_error(result["error"] or "Failed to mark all as read")

    def _refresh_list_after_mark_read(self, notif_id):
        # Option-C aware single mark
        def _traverse(widget, fn):
            try:
                fn(widget)
            except Exception:
                pass
            for ch in list(getattr(widget, "children", [])):
                _traverse(ch, fn)

        for child in list(self._list_content.children):
            if getattr(child, "notif_id", None) != notif_id:
                continue
            child.is_read = True
            try:
                child.md_bg_color = rgba("#fafafa")
                child.line_color = rgba(0, 0, 0, 0)
            except Exception:
                pass

            def _clear_accent(w):
                try:
                    if isinstance(w, MDBoxLayout) and (w.width == dp(4) or str(getattr(w, "width", "")) == "4dp" or w.width in (4, 4.0)):
                        w.md_bg_color = rgba(0, 0, 0, 0)
                except Exception:
                    pass

            def _hide(w):
                try:
                    if isinstance(w, MDLabel) and w.text == "\u2022":
                        w.text = ""
                        w.opacity = 0
                    if isinstance(w, MDFlatButton) and w.text == tr("mark_read"):
                        w.opacity = 0
                        w.disabled = True
                    from kivymd.uix.card import MDCard as _MDCard
                    if isinstance(w, _MDCard) and (w.size[0] == dp(8) or w.width == dp(8)):
                        w.opacity = 0
                        w.disabled = True
                        try:
                            w.md_bg_color = rgba(0, 0, 0, 0)
                        except Exception:
                            pass
                except Exception:
                    pass

            _traverse(child, _clear_accent)
            _traverse(child, _hide)
            break

    def _refresh_list_after_mark_all_read(self):
        # Option-C aware: card is horizontal [accent 4dp, inner vertical[title_row_container[icon_anchor, title_anchor[title_row[dot+label+btn]]], body_row, timestamp_row]]
        # Recursively hide dot/btn and clear accent for all pages (server marks all)
        def _traverse(widget, fn):
            try:
                fn(widget)
            except Exception:
                pass
            for ch in list(getattr(widget, "children", [])):
                _traverse(ch, fn)

        for child in list(self._list_content.children):
            if not hasattr(child, "is_read") or child.is_read:
                continue
            child.is_read = True
            try:
                child.md_bg_color = rgba("#fafafa")
            except Exception:
                pass
            try:
                child.line_color = rgba(0, 0, 0, 0)
            except Exception:
                pass

            def _clear_accent(w):
                try:
                    if isinstance(w, MDBoxLayout):
                        # accent is width 4dp (int, str, or dp)
                        try:
                            is_accent = w.width == dp(4) or str(getattr(w, "width", "")) == "4dp" or w.width in (4, 4.0)
                        except Exception:
                            is_accent = False
                        # also check size_hint None width flag
                        if is_accent or (getattr(w, "width", None) == dp(4) and w.size_hint_x is not None and w.size_hint[0] is None):
                            w.md_bg_color = rgba(0, 0, 0, 0)
                except Exception:
                    pass

            def _hide_dot_btn(w):
                try:
                    if isinstance(w, MDLabel) and w.text == "\u2022":
                        w.text = ""
                        w.opacity = 0
                    if isinstance(w, MDFlatButton) and w.text == tr("mark_read"):
                        w.opacity = 0
                        w.disabled = True
                    # also MDCard dot 8dp
                    from kivymd.uix.card import MDCard as _MDCard
                    if isinstance(w, _MDCard):
                        try:
                            if w.size[0] == dp(8) or w.width == dp(8):
                                w.opacity = 0
                                w.disabled = True
                                w.md_bg_color = rgba(0, 0, 0, 0)
                        except Exception:
                            pass
                except Exception:
                    pass

            _traverse(child, _clear_accent)
            _traverse(child, _hide_dot_btn)

    def _update_stats_badges(self):
        self._total_pill.text = tr("total_notifications").format(count=self._total_count)
        self._unread_pill.text = tr("unread_notifications").format(count=self._unread_count)

    def _update_mark_all_visibility(self):
        if self._unread_count > 0:
            self._mark_all_btn.opacity = 1
            self._mark_all_btn.disabled = False
        else:
            self._mark_all_btn.opacity = 0
            self._mark_all_btn.disabled = True

    def _update_home_badge(self):
        if self.manager:
            try:
                home = self.manager.get_screen("customer_home")
                if hasattr(home, "bell_count_label"):
                    home.bell_count_label.text = str(self._unread_count) if self._unread_count > 0 else ""
            except Exception:
                pass

    def _show_empty(self):
        self._list_content.clear_widgets()
        empty = MDLabel(
            text=tr("no_notifications"),
            font_style="Body2",
            halign="center",
            theme_text_color="Custom",
            text_color=rgba(MUTED),
            size_hint_y=None,
            height="80dp",
        )
        self._list_content.add_widget(empty)

    def _show_error(self, error_msg):
        self._list_content.clear_widgets()
        error = MDLabel(
            text=error_msg or tr("error"),
            font_style="Body2",
            halign="center",
            theme_text_color="Custom",
            text_color=rgba(ERROR),
            size_hint_y=None,
            height="80dp",
        )
        retry_btn = MDFlatButton(
            text=tr("retry"),
            theme_text_color="Custom",
            text_color=rgba(PRIMARY),
            on_release=self._refresh,
        )
        box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing="8dp", padding="12dp")
        box.add_widget(error)
        box.add_widget(retry_btn)
        self._list_content.add_widget(box)

    def rebuild_ui(self):
        try:
            from app.i18n.translator import tr
            # header title + mark all read button
            if hasattr(self, '_header_label'):
                self._header_label.text = tr("notifications")
            if hasattr(self, '_mark_all_btn'):
                self._mark_all_btn.text = tr("mark_all_read")
            # re-apply list rendering if data exists
            if hasattr(self, '_render_list'):
                try:
                    self._render_list()
                except Exception:
                    pass
        except Exception:
            pass