"""Generate 360x740 screenshots: 1-line vs 2-line body, verify icon anchored to title."""
import os
os.environ.setdefault('KIVY_NO_ARGS', '1')
# Force 360x740 before any Kivy import
from kivy.config import Config
Config.set("graphics", "width", "360")
Config.set("graphics", "height", "740")
Config.set("graphics", "resizable", "0")
Config.set("graphics", "fullscreen", "0")
Config.set("kivy", "exit_on_escape", "0")

from pathlib import Path
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import rgba
from kivymd.app import MDApp

# Need to init translations minimally
try:
    from app.i18n.translator import init_translator
    init_translator("en")
except Exception as e:
    print("translator init failed", e)

from app.views.customer.notification_screen import NotificationScreen

def make_card(screen, title, body, is_read=False):
    notif = {"id": "test", "title": title, "message": body, "is_read": is_read, "time_ago": "11 Aug 2026"}
    return screen._create_notification_card(notif)

class ShotApp(MDApp):
    def build(self):
        Window.size = (360, 740)
        root = BoxLayout(orientation="vertical", padding="12dp", spacing="12dp")
        screen = NotificationScreen()
        # Don't add screen directly, just extract cards
        self.screen = screen

        # Create two cards with same title but different body lengths
        card1 = make_card(screen, "Rider Application Approved!", "Short body one line.", is_read=False)
        card2 = make_card(screen, "Rider Application Approved!", "Congratulations! Your rider application has been approved. You can now log in to the rider app.", is_read=False)

        # Wrap each in container with label for screenshot
        from kivymd.uix.label import MDLabel
        from kivymd.uix.boxlayout import MDBoxLayout

        container = MDBoxLayout(orientation="vertical", spacing="16dp", padding=["8dp","24dp","8dp","24dp"], adaptive_height=True, size_hint_y=None)
        container.height = dp(400)
        container.md_bg_color = rgba("#f5f5f5")

        # Top label
        header = MDLabel(text="360x740 verification: 1-line vs 2-line body", halign="center", font_style="Caption", size_hint_y=None, height="24dp")
        container.add_widget(header)

        lbl1 = MDLabel(text="1-line body:", font_style="Caption", size_hint_y=None, height="16dp")
        container.add_widget(lbl1)
        container.add_widget(card1)

        lbl2 = MDLabel(text="2-line body (mobile wraps):", font_style="Caption", size_hint_y=None, height="16dp")
        container.add_widget(lbl2)
        container.add_widget(card2)

        root.add_widget(container)
        self.container = container
        self.card1 = card1
        self.card2 = card2
        return root

    def on_start(self):
        from kivy.clock import Clock
        Clock.schedule_once(self.do_capture, 0.5)
        Clock.schedule_once(self.do_measure, 0.6)

    def do_measure(self, dt):
        # Measure icon Y vs title Y for both cards
        def find_icon_and_title(card):
            # card -> accent, inner
            # inner is vertical MDBoxLayout with children: timestamp, body_row, title_row_container (reverse order because added)
            inner = None
            for c in card.children:
                from kivymd.uix.boxlayout import MDBoxLayout
                if isinstance(c, MDBoxLayout) and c.orientation == "vertical":
                    inner = c
                    break
            if not inner:
                return None, None
            # inner children are in reverse add order: last added first in children list
            # inner.addWidget order: title_row_container, body_row, timestamp_row
            # so children[0]=timestamp, [1]=body_row, [2]=title_row_container
            title_container = None
            body_row = None
            for child in inner.children:
                # body_row has a Widget spacer with opacity 0
                has_spacer = any(child.__class__.__name__ == "Widget" or getattr(child, "opacity", 1)==0 for child in getattr(child, "children", []))
                # title container has AnchorLayout
                from kivy.uix.anchorlayout import AnchorLayout
                has_anchor = any(isinstance(x, AnchorLayout) for x in getattr(child, "children", []))
                if has_anchor:
                    title_container = child
                # fallback: check spacing and children count
            # simpler: title_container is the one with spacing 8dp and containing AnchorLayout
            # body_row contains spacer Widget 32dp
            # We'll just search by containing AnchorLayout vs Widget spacer
            title_container = None
            body_row = None
            for ch in inner.children:
                children = list(ch.children)
                has_anchor = any(c.__class__.__name__ == "AnchorLayout" for c in children)
                if has_anchor:
                    title_container = ch
                # body_row has Widget
                has_widget = any(c.__class__.__name__ == "Widget" for c in children)
                if has_widget and not has_anchor:
                    body_row = ch
            # Find icon y and title y
            icon_y = None
            title_y = None
            if title_container:
                for c in title_container.children:
                    if c.__class__.__name__ == "AnchorLayout":
                        # icon_anchor pos
                        icon_y = c.y + c.height - 32  # approximate top
                        # inside anchor, icon_box y?
                        try:
                            # AnchorLayout centers? But we use pos inside
                            if c.children:
                                ib = c.children[0]
                                icon_y = ib.to_window(0, ib.y)[1] if hasattr(ib, 'to_window') else ib.y
                        except:
                            pass
                    else:
                        # title_row
                        # title_label inside
                        for sub in c.children:
                            # title_row children may include dot, label, btn
                            for maybe in getattr(sub, 'children', []):
                                if hasattr(maybe, 'text') and maybe.text == "Rider Application Approved!":
                                    title_y = maybe.y
                            if hasattr(c, 'text') and "Rider" in getattr(c, 'text', ''):
                                title_y = c.y
            return icon_y, title_y

        # More direct: to_window comparison after layout
        try:
            # Get icon_box and body_label
            def extract(card):
                inner = [c for c in card.children if hasattr(c, 'orientation') and c.orientation=='vertical'][0]
                # title_container is last in children (added first)
                title_container = inner.children[-1]
                body_row = inner.children[-2]
                # icon_anchor is first child of title_container (due to add order, children reversed)
                # title_container.add_widget(icon_anchor) then add title_row -> children[0]=title_row, [1]=icon_anchor
                icon_anchor = title_container.children[1] if len(title_container.children)>1 else title_container.children[0]
                icon_box = icon_anchor.children[0] if icon_anchor.children else None
                # title_label inside title_row
                title_row = title_container.children[0]
                title_label = None
                for ch in title_row.children:
                    if hasattr(ch, 'text') and "Rider Application Approved!" in ch.text:
                        title_label = ch
                    # also check nested
                    for sub in getattr(ch, 'children', []):
                        if hasattr(sub, 'text') and "Rider" in sub.text:
                            title_label = sub
                # body_label inside body_row
                body_label = None
                for ch in body_row.children:
                    if hasattr(ch, 'text') and ("Short" in ch.text or "Congratulations" in ch.text):
                        body_label = ch
                return icon_box, title_label, body_label, title_container, body_row

            ib1, tl1, bl1, tc1, br1 = extract(self.card1)
            ib2, tl2, bl2, tc2, br2 = extract(self.card2)
            print(f"CARD1 window pos icon={ib1.to_window(ib1.x, ib1.y) if ib1 else None} title={tl1.to_window(tl1.x, tl1.y) if tl1 else None} body_lines={bl1.height if bl1 else None} tc_height={tc1.height if tc1 else None}")
            print(f"CARD2 window pos icon={ib2.to_window(ib2.x, ib2.y) if ib2 else None} title={tl2.to_window(tl2.x, tl2.y) if tl2 else None} body_lines={bl2.height if bl2 else None} tc_height={tc2.height if tc2 else None}")
            if ib1 and tl1 and ib2 and tl2:
                # Check that icon top is aligned to title top (within 4dp)
                w1_icon_top = ib1.to_window(ib1.x, ib1.y+ib1.height)[1]
                w1_title_top = tl1.to_window(tl1.x, tl1.y+tl1.height)[1]
                w2_icon_top = ib2.to_window(ib2.x, ib2.y+ib2.height)[1]
                w2_title_top = tl2.to_window(tl2.x, tl2.y+tl2.height)[1]
                print(f"CARD1 icon_top={w1_icon_top:.1f} title_top={w1_title_top:.1f} delta={(w1_icon_top-w1_title_top):.1f}")
                print(f"CARD2 icon_top={w2_icon_top:.1f} title_top={w2_title_top:.1f} delta={(w2_icon_top-w2_title_top):.1f}")
                # Icon should remain same offset from title regardless of body height
                delta1 = abs(w1_icon_top - w1_title_top)
                delta2 = abs(w2_icon_top - w2_title_top)
                print(f"Body height card1={bl1.height:.1f} card2={bl2.height:.1f}")
                print(f"Anchor check delta diff = {abs(delta1-delta2):.1f} should be < 3dp")
                if abs(delta1 - delta2) < dp(3):
                    print("PASS: icon anchored to title, not body")
                else:
                    print("FAIL: icon drift with body")
                # Also check title_container height stable
                print(f"title_container heights: c1={tc1.height:.1f} c2={tc2.height:.1f} diff={abs(tc1.height-tc2.height):.1f} should be small")
        except Exception as e:
            import traceback
            traceback.print_exc()

    def do_capture(self, dt):
        # Ensure window size
        Window.size = (360, 740)
        out = Path("screenshot_360x740.png")
        try:
            Window.screenshot(str(out))
            print(f"screenshot saved to {out.resolve()}")
        except Exception as e:
            print("screenshot failed", e)
            # try export_to_png
            try:
                self.root.export_to_png(str(out))
                print("export_to_png saved")
            except Exception as e2:
                print("export failed", e2)
        # also save via container export
        try:
            c_out = Path("screenshot_container.png")
            self.container.export_to_png(str(c_out))
            print(f"container png {c_out.resolve()}")
        except Exception as e:
            print("container export fail", e)
        # stop after short delay
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.stop(), 0.8)

if __name__ == "__main__":
    ShotApp().run()
