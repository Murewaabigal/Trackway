from kivy.utils import rgba
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon

from app.core.theme import PRIMARY, MUTED, CARD_BG, BACKGROUND


class StatusTimeline(MDBoxLayout):
    def __init__(self, timeline=None, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=["16dp", "8dp"],
            spacing="0dp",
            size_hint_x=1,
            adaptive_height=True,
            **kwargs,
        )
        self._steps = []
        if timeline:
            self.set_timeline(timeline)

    def set_timeline(self, timeline):
        self.clear_widgets()
        self._steps = timeline
        for i, step in enumerate(timeline):
            is_last = i == len(timeline) - 1
            completed = step.get("completed", False)
            active = not completed and not is_last
            self._add_step(step, completed, active, is_last)

    def _add_step(self, step, completed, active, is_last):
        row = MDBoxLayout(
            orientation="horizontal",
            size_hint_x=1,
            adaptive_height=True,
            spacing="12dp",
        )

        icon_col = MDBoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width="32dp",
            adaptive_height=True,
        )

        if completed:
            icon_name = "check-circle"
            icon_color = PRIMARY
        elif active:
            icon_name = "circle-slice8"
            icon_color = PRIMARY
        else:
            icon_name = "circle-outline"
            icon_color = MUTED

        icon = MDIcon(
            icon=icon_name,
            theme_text_color="Custom",
            text_color=rgba(icon_color),
            halign="center",
            size_hint_y=None,
            height="24dp",
        )
        icon_col.add_widget(icon)

        if not is_last:
            line = MDLabel(
                text="|",
                font_style="Caption",
                halign="center",
                theme_text_color="Custom",
                text_color=rgba(MUTED),
                size_hint_y=None,
                height="20dp",
            )
            icon_col.add_widget(line)

        text_col = MDBoxLayout(
            orientation="vertical",
            size_hint_x=1,
            adaptive_height=True,
            padding=[0, "2dp"],
        )

        label_text = step.get("label", step.get("status", ""))
        label = MDLabel(
            text=label_text,
            font_style="Body2",
            theme_text_color="Custom",
            text_color=rgba(PRIMARY if completed or active else MUTED),
            size_hint_y=None,
            height="24dp",
        )

        timestamp = step.get("timestamp", "")
        time_label = MDLabel(
            text=timestamp,
            font_style="Caption",
            theme_text_color="Custom",
            text_color=rgba(MUTED),
            size_hint_y=None,
            height="18dp",
        )

        text_col.add_widget(label)
        text_col.add_widget(time_label)

        row.add_widget(icon_col)
        row.add_widget(text_col)
        self.add_widget(row)
