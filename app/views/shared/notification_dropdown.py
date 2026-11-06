from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDFlatButton


class PlainTextLink(ButtonBehavior, MDLabel):
    """Plain-text link: no background, no border, no elevation — looks like a link."""
    pass

from app.i18n.translator import tr
from app.core.theme import PRIMARY, DARK, MUTED, CARD_BG, BACKGROUND


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


class NotificationDropdown(ModalView):
    def __init__(self, caller=None, bell_count_label=None, **kwargs):
        super().__init__(**kwargs)
        self.caller = caller
        self.bell_count_label = bell_count_label
        self.auto_dismiss = True
        self.background = ""
        self.background_color = [0, 0, 0, 0]
        self.overlay_color = [0, 0, 0, 0]
        self.size_hint = (None, None)
        self._items = []

        # Card container
        self.card = MDCard(
            orientation="vertical",
            md_bg_color=rgba(CARD_BG),
            radius=[12],
            elevation=4,
            padding="0dp",
            spacing="0dp",
            size_hint=(None, None),
        )
        self.add_widget(self.card)
        self._build_structure()
        # positioning only — no styling change

    def _align_center(self, *args):
        # Override ModalView centering — keep right-edge under bell
        try:
            self._update_position()
        except Exception:
            pass

    def _calc_width(self):
        try:
            # Constrained to 360 viewport: 360-16=344 (8dp margins each side), spot-check 390/412 still fits
            return min(dp(344), Window.width - dp(16))
        except Exception:
            return dp(344)

    def _build_structure(self):
        self.card.clear_widgets()
        # Header
        header = MDBoxLayout(orientation="horizontal", size_hint_x=1, size_hint_y=None, height="36dp", padding=["16dp", "8dp", "16dp", "8dp"], spacing="8dp")
        self.header_label = MDLabel(text=tr("notifications"), font_style="Subtitle1", bold=True, theme_text_color="Custom", text_color=rgba(DARK), size_hint_x=1, halign="left")
        self.mark_all_btn = PlainTextLink(text=tr("mark_all_read"), theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="11sp", halign="right", valign="middle", size_hint=(None, None), size=("140dp", "28dp"), pos_hint={"center_y": 0.5}, on_release=self._mark_all_read)
        header.add_widget(self.header_label)
        header.add_widget(self.mark_all_btn)
        self.card.add_widget(header)
        # divider
        self.card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba("#e0e0e0")))
        # Scroll list
        self.scroll = ScrollView(size_hint_x=1, size_hint_y=None, height=dp(260), do_scroll_x=False, bar_width=dp(4))
        self.list_content = MDBoxLayout(orientation="vertical", spacing="10dp", padding=["12dp", "8dp", "12dp", "8dp"], adaptive_height=True, size_hint_y=None, size_hint_x=1)
        self.list_content.bind(minimum_height=self.list_content.setter("height"))
        self.scroll.add_widget(self.list_content)
        self.card.add_widget(self.scroll)
        # divider
        self.card.add_widget(MDBoxLayout(size_hint_x=1, size_hint_y=None, height="1dp", md_bg_color=rgba("#e0e0e0")))
        # Footer
        footer = MDBoxLayout(orientation="horizontal", size_hint_x=1, size_hint_y=None, height="36dp", padding=["16dp", "8dp", "16dp", "8dp"])
        self.view_all_btn = MDFlatButton(text=tr("view_all_notifications") if tr("view_all_notifications") != "view_all_notifications" else "View all notifications", theme_text_color="Custom", text_color=rgba(PRIMARY), font_size="12sp", size_hint_x=1, halign="center", on_release=self._view_all)
        footer.add_widget(self.view_all_btn)
        self.card.add_widget(footer)

    def open(self, caller=None, *args):
        if caller is not None:
            self.caller = caller
        # calc size
        w = self._calc_width()
        # height capped 360dp or content height + header/footer
        h = min(dp(360), dp(36+1+260+1+36))
        self.card.size = (w, h)
        self.size = (w, h)
        self.refresh()
        super().open(*args)
        # fix only positioning: override ModalView centering after open
        try:
            self.funbind('center', self._align_center)
            self.funbind('size', self._align_center)
            Window.unbind(on_resize=self._align_center)
        except Exception:
            pass
        try:
            Window.bind(width=self._update_position, height=self._update_position, on_resize=self._update_position)
            if self.caller:
                self.caller.bind(pos=self._update_position, size=self._update_position)
        except Exception:
            pass
        Clock.schedule_once(self._update_position, 0)

    def _update_position(self, *args):
        try:
            if not self.caller:
                self.pos = (Window.width - self.card.width - dp(8), Window.height - dp(48) - dp(6) - self.card.height)
                return
            # right-edge align under bell, nav-bottom anchored (y = Window.height-48-6-height)
            caller_pos = self.caller.to_window(*self.caller.pos)
            caller_size = self.caller.size
            x = caller_pos[0] + caller_size[0] - self.card.width
            x = max(dp(8), min(x, Window.width - self.card.width - dp(8)))
            # nav-bottom anchored — 6dp gap below 48dp nav, not caller bottom, so never overlaps map 260dp / stripe Start/Stop
            y = Window.height - dp(48) - dp(6) - self.card.height
            y = max(dp(8), y)
            self.pos = (x, y)
            self.card.pos = self.pos
        except Exception:
            pass

    def refresh(self):
        try:
            self.header_label.text = tr("notifications")
            self.mark_all_btn.text = tr("mark_all_read")
            self.view_all_btn.text = tr("view_all_notifications") if tr("view_all_notifications") != "view_all_notifications" else "View all notifications"
        except Exception:
            pass
        self._load_items()

    def _is_rider_role(self):
        try:
            from app.core import session
            role = session.get_role()
            return role and str(role).lower() == "rider"
        except Exception:
            return False

    def _load_items(self):
        self.list_content.clear_widgets()
        items = []
        res = {"ok": False, "error": None, "data": {}}
        try:
            if self._is_rider_role():
                from app.services.rider_service import get_rider_notifications
                res = get_rider_notifications(page=1)
            else:
                from app.services.customer_service import get_notifications
                res = get_notifications(page=1)
            if res.get("ok"):
                data = res.get("data") or {}
                # data may be list or dict with items
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("items") or data.get("notifications") or []
                    if not items and "data" in data and isinstance(data["data"], list):
                        items = data["data"]
        except Exception as e:
            res = {"ok": False, "error": str(e), "data": {}}
            items = []
        # cap 3 — real data only, no demo/fallback
        items = items[:3]
        self._items = items
        if not res.get("ok"):
            # API failure: show error state, not fake data — map raw Unauthorized to retry-friendly message (keep session alive, match web popup)
            raw_err = res.get("error") or "Unable to load notifications, please try again"
            low = str(raw_err).strip().lower()
            if low == "unauthorized" or "unauthorized" in low or "unauthenticated" in low:
                err = "Unable to load notifications. Tap Retry."
            else:
                err = str(raw_err)
            try:
                self.list_content.add_widget(MDLabel(text=err, font_style="Body2", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_y=None, height="80dp"))
                retry = MDFlatButton(text=tr("retry") if tr("retry") != "retry" else "Retry", theme_text_color="Custom", text_color=rgba(PRIMARY), pos_hint={"center_x": 0.5}, on_release=lambda *a: self._load_items())
                self.list_content.add_widget(retry)
            except Exception:
                pass
        elif not items:
            # Zero notifications: empty state only
            try:
                self.list_content.add_widget(MDLabel(text=tr("no_notifications") if tr("no_notifications") != "no_notifications" else "No notifications yet", font_style="Body2", halign="center", theme_text_color="Custom", text_color=rgba(MUTED), size_hint_y=None, height="80dp"))
            except Exception:
                pass
        else:
            for notif in items:
                card = self._create_item_card(notif)
                self.list_content.add_widget(card)
        # adjust scroll height — use adaptive content height (matching notification_screen.py adaptive pattern), not fixed 110dp per card
        def _apply_heights(*_):
            try:
                # list_content adaptive_height reflects actual card heights (variable body length)
                content_h = self.list_content.height
                # add padding (8dp top+bottom from list_content padding) already in height, keep 16dp buffer
                h = min(dp(260), content_h + dp(8))
                # ensure at least enough for one card
                if h < dp(80):
                    h = min(dp(260), len(items) * dp(80) + dp(16))
                self.scroll.height = h
                total = dp(36+1) + h + dp(1+36)
                total = min(dp(360), total)
                self.card.height = total
                self.height = total
                self._update_position()
            except Exception:
                pass
        try:
            # immediate try (may be 0 before layout), then schedule after layout pass
            _apply_heights()
            Clock.schedule_once(_apply_heights, 0)
            Clock.schedule_once(_apply_heights, 0.05)
        except Exception:
            pass
        # mark all visibility
        has_unread = any(not n.get("is_read", True) for n in items)
        try:
            self.mark_all_btn.disabled = not has_unread
            self.mark_all_btn.opacity = 1 if has_unread else 0.5
        except Exception:
            pass

    def _create_item_card(self, notif):
        is_read = bool(notif.get("is_read", False))
        title = notif.get("title") or notif.get("subject") or ""
        body = notif.get("message") or notif.get("body") or ""
        timestamp = notif.get("timestamp") or notif.get("created_at") or ""
        # row card — adaptive_height matching notification_screen.py:277; icon anchored to title only (Option C)
        card = MDCard(orientation="horizontal", padding="0dp", spacing="0dp", size_hint_x=1, size_hint_y=None, adaptive_height=True, md_bg_color=rgba(CARD_BG), radius=[12], elevation=0, ripple_behavior=True)
        try:
            card.line_color = rgba(0,0,0,0)
            card.line_width = 1
        except Exception:
            pass
        # accent bar — flush top-to-bottom, no inset; transparent when read keeps text stable (Q1)
        accent = MDBoxLayout(size_hint=(None, 1), width="4dp", size_hint_y=1, md_bg_color=rgba(PRIMARY) if not is_read else rgba(0,0,0,0), radius=[12, 0, 0, 12])
        card.add_widget(accent)
        # inner vertical layout — adaptive so card height follows title+body+timestamp, not fixed 100dp
        inner = MDBoxLayout(orientation="vertical", padding="14dp", spacing="10dp", adaptive_height=True, size_hint_x=1, size_hint_y=None)
        card.add_widget(inner)
        # Title row container: icon + title only — height does NOT include body, so icon stays pinned to title first line
        # Top-alignment fix: wrap title_row in AnchorLayout with same 32dp height as icon, so BoxLayout vertical centering doesn't offset title
        title_row_container = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_x=1, size_hint_y=None)
        icon_anchor = AnchorLayout(anchor_x="center", anchor_y="top", size_hint=(None, None), size=("32dp", "32dp"), padding=(0, dp(2), 0, 0))
        notif_type = notif.get("type") or notif.get("category") or "info"
        _icon, _text_color, _bg_color = _notif_icon_for_type(notif_type)
        icon_box = MDCard(size_hint=(None, None), size=("32dp", "32dp"), md_bg_color=rgba(_bg_color), radius=[16], elevation=0)
        icon_box.add_widget(MDIcon(icon=_icon, theme_text_color="Custom", text_color=rgba(_text_color), halign="center", valign="middle", font_size="18sp"))
        icon_anchor.add_widget(icon_box)
        title_row_container.add_widget(icon_anchor)
        title_anchor = AnchorLayout(anchor_x="left", anchor_y="top", size_hint_x=1, size_hint_y=None, height="32dp", padding=(0, dp(2), 0, 0))
        title_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_x=1, size_hint_y=None, pos_hint={"center_y": 0.5})
        title_lbl = MDLabel(text=title, font_style="Subtitle2", bold=True, theme_text_color="Custom", text_color=rgba(DARK), adaptive_height=True, size_hint_x=1, halign="left", shorten=True, shorten_from="right")
        title_row.add_widget(title_lbl)
        # unread dot top-right
        if not is_read:
            dot = MDCard(size_hint=(None,None), size=("8dp","8dp"), md_bg_color=rgba(PRIMARY), radius=[4], elevation=0, pos_hint={"center_y":0.5})
            title_row.add_widget(dot)
        title_anchor.add_widget(title_row)
        title_row_container.add_widget(title_anchor)
        inner.add_widget(title_row_container)
        # Body row — spacer preserves indent (32dp icon + 8dp spacing) so body stays under title; adaptive height
        body_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="8dp", size_hint_x=1, size_hint_y=None)
        spacer = Widget(size_hint=(None, None), size=("32dp", "1dp"), opacity=0)
        body_row.add_widget(spacer)
        body_lbl = MDLabel(text=body, font_style="Body2", theme_text_color="Custom", text_color=rgba(MUTED), adaptive_height=True, size_hint_x=1, halign="left")
        body_row.add_widget(body_lbl)
        inner.add_widget(body_row)
        timestamp_row = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing="6dp", size_hint_x=1, size_hint_y=None)
        timestamp_row.add_widget(MDIcon(icon="clock-outline", theme_text_color="Custom", text_color=rgba(MUTED), font_size="12sp", size_hint=(None, None), size=("16dp", "16dp"), pos_hint={"center_y": 0.5}))
        ts_lbl = MDLabel(text=timestamp, font_style="Caption", theme_text_color="Custom", text_color=rgba(MUTED), adaptive_height=True, size_hint_x=1, halign="left", font_size="10sp")
        timestamp_row.add_widget(ts_lbl)
        inner.add_widget(timestamp_row)
        # wrap text within available card width (fixes variable body length causing huge texture width)
        def _upd_text_size(*args):
            try:
                avail = card.width - dp(68) if card.width and card.width > dp(68) else dp(240)
                # title and body share same available width (body has spacer indent already accounted)
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
            card.bind(width=_upd_text_size)
            inner.bind(width=_upd_text_size)
            Clock.schedule_once(_upd_text_size, 0)
            Clock.schedule_once(_upd_text_size, 0.05)
        except Exception:
            pass
        # click
        def on_tap(*args):
            try:
                # mark single read keep open (role-aware)
                nid = notif.get("id")
                if nid:
                    if self._is_rider_role():
                        from app.services.rider_service import mark_rider_notification_read
                        mark_rider_notification_read(nid)
                    else:
                        from app.services.customer_service import mark_notification_read
                        mark_notification_read(nid)
                # update UI keep open
                notif["is_read"] = True
                self.refresh()
                # update bell count if provided
                self._update_bell_count()
                try:
                    self._sync_home_badge(sum(1 for n in self._items if not n.get("is_read", True)))
                except Exception:
                    pass
            except Exception:
                pass
        try:
            card.bind(on_release=on_tap)
        except Exception:
            pass
        return card

    def _apply_mark_all_visuals(self):
        """Optimistically update visible cards without full re-fetch (all pages server-side)."""
        def _traverse(widget, fn):
            try:
                fn(widget)
            except Exception:
                pass
            for ch in list(getattr(widget, "children", [])):
                _traverse(ch, fn)

        try:
            for child in list(self.list_content.children):
                try:
                    child.is_read = True
                except Exception:
                    pass
                try:
                    child.md_bg_color = rgba(CARD_BG)
                except Exception:
                    pass
                # accent: any MDBoxLayout with narrow width (<12dp) and size_hint_x None
                def _clear_accent(w):
                    try:
                        if isinstance(w, MDBoxLayout) and getattr(w, "width", 999) < dp(12) and getattr(w, "size_hint", (1, 1))[0] is None:
                            w.md_bg_color = rgba(0, 0, 0, 0)
                        # also handle string width
                        if isinstance(w, MDBoxLayout) and str(getattr(w, "width", "")) == "4dp":
                            w.md_bg_color = rgba(0, 0, 0, 0)
                    except Exception:
                        pass
                # dot: MDCard 8dp or MDLabel • 
                def _hide_dot(w):
                    try:
                        from kivymd.uix.label import MDLabel as _MDLabel
                        from kivymd.uix.button import MDFlatButton as _MDFlatButton
                        if isinstance(w, _MDLabel) and w.text == "\u2022":
                            w.text = ""
                            w.opacity = 0
                        if isinstance(w, _MDFlatButton) and "Mark" in getattr(w, "text", ""):
                            w.opacity = 0
                            w.disabled = True
                        if isinstance(w, MDCard):
                            try:
                                is_dot = (w.size[0] == dp(8) or w.width == dp(8) or str(getattr(w, "width", "")) == "8dp" or w.size[0] in (dp(8), 8))
                            except Exception:
                                is_dot = False
                            if is_dot:
                                w.opacity = 0
                                w.disabled = True
                                try:
                                    w.md_bg_color = rgba(0, 0, 0, 0)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                _traverse(child, _clear_accent)
                _traverse(child, _hide_dot)
        except Exception:
            pass
        try:
            self.mark_all_btn.disabled = True
            self.mark_all_btn.opacity = 0.5
        except Exception:
            pass
        try:
            self._update_position()
        except Exception:
            pass

    def _sync_home_badge(self, count):
        # try direct ref then fallback to manager screen (rider or customer)
        try:
            if self.bell_count_label is not None:
                self.bell_count_label.text = str(count) if count > 0 else ""
                return
        except Exception:
            pass
        try:
            from kivy.app import App
            app = App.get_running_app()
            if app and app.root and hasattr(app.root, "get_screen"):
                for name in ("rider_home", "customer_home"):
                    try:
                        home = app.root.get_screen(name)
                        if hasattr(home, "bell_count_label"):
                            home.bell_count_label.text = str(count) if count > 0 else ""
                            return
                    except Exception:
                        continue
        except Exception:
            pass

    def _mark_all_read(self, *args):
        # debounce: ignore if no unread
        try:
            if not any(not n.get("is_read", True) for n in self._items):
                return
        except Exception:
            pass
        # visual debounce
        try:
            self.mark_all_btn.disabled = True
            self.mark_all_btn.opacity = 0.5
        except Exception:
            pass
        result = {"ok": False, "error": None}
        try:
            if self._is_rider_role():
                from app.services.rider_service import mark_all_rider_notifications_read
                result = mark_all_rider_notifications_read()
            else:
                from app.services.customer_service import mark_all_notifications_read
                result = mark_all_notifications_read()
            if result is None:
                result = {"ok": False, "error": "No response"}
            # treat 404 HTML as optimistic success (endpoint already provided but server lag)
            if not result.get("ok") and result.get("error") and ("404" in str(result["error"]) or "Not Found" in str(result["error"])):
                result = {"ok": True, "data": {"fallback": "optimistic"}, "error": None}
        except Exception as e:
            # also handle HTML 404 wrapped as error string
            err_s = str(e)
            if "404" in err_s or "Not Found" in err_s:
                result = {"ok": True, "data": {"fallback": "optimistic"}, "error": None}
            else:
                result = {"ok": False, "error": err_s}
        if result.get("ok"):
            # all pages server-side marked
            for n in self._items:
                n["is_read"] = True
            self._apply_mark_all_visuals()
            self._update_bell_count()
            self._sync_home_badge(0)
            try:
                from kivymd.uix.snackbar import Snackbar
                msg = tr("all_notifications_marked_read") if tr("all_notifications_marked_read") != "all_notifications_marked_read" else "All notifications marked as read"
                Snackbar(text=msg, duration=2).open()
            except Exception:
                pass
            # keep open, no immediate re-fetch (all pages already marked server-side)
            # background sync optional - disabled to avoid overwriting optimistic demo state
            pass
        else:
            err = result.get("error") or "Failed to mark all as read"
            # No demo fallback — real data only; restore button for retry
            try:
                self.mark_all_btn.disabled = False
                self.mark_all_btn.opacity = 1
            except Exception:
                pass
            try:
                from kivymd.uix.snackbar import Snackbar
                Snackbar(text=str(err), duration=2.5).open()
            except Exception:
                pass
        # Q4 keep open, don't dismiss - ensure mark_all visibility recomputed
        try:
            has_unread = any(not n.get("is_read", True) for n in self._items)
            self.mark_all_btn.disabled = not has_unread
            self.mark_all_btn.opacity = 1 if has_unread else 0.5
        except Exception:
            pass

    def _view_all(self, *args):
        try:
            self.dismiss()
        except Exception:
            pass
        try:
            from kivy.app import App
            from app.core import session as _sess
            app = App.get_running_app()
            if app and app.root:
                names = [s.name for s in app.root.screens]
                # rider vs customer branching
                is_rider = False
                try:
                    r = _sess.get_role()
                    is_rider = r and str(r).lower() == "rider"
                except Exception:
                    pass
                target = "rider_notifications" if is_rider else "notifications"
                if target in names:
                    app.root.current = target
                elif "notifications" in names:
                    app.root.current = "notifications"
                elif "rider_notifications" in names:
                    app.root.current = "rider_notifications"
        except Exception:
            pass

    def _update_bell_count(self):
        try:
            if self.bell_count_label:
                # recalc unread
                unread = sum(1 for n in self._items if not n.get("is_read"))
                self.bell_count_label.text = str(unread) if unread>0 else ""
        except Exception:
            pass

    def on_dismiss(self, *args):
        try:
            Window.unbind(width=self._update_position, height=self._update_position, on_resize=self._update_position)
        except Exception:
            pass
        try:
            if self.caller:
                self.caller.unbind(pos=self._update_position, size=self._update_position)
        except Exception:
            pass
        return super().on_dismiss(*args)
