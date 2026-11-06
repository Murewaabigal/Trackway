import os

PRIMARY = "#567f30"
PRIMARY_DARK = "#3d5f23"
PRIMARY_LIGHT = "#7ba84a"
DARK = "#12171a"
GRAY = "#21282e"
BACKGROUND = "#f6f6f8"
CARD_BG = "#ffffff"
MUTED = "#859393"
ERROR = "#d32f2f"
SUCCESS = "#388e3c"
WHITE = "#ffffff"
TEAL = "#00897B"
BLUE = "#1976D2"

CARD_RADIUS = 24
PILL_RADIUS = 50

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets"
)
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

FONT_FILES = {
    "regular":  os.path.join(FONTS_DIR, "Inter-Regular.ttf"),
    "semibold": os.path.join(FONTS_DIR, "Inter-SemiBold.ttf"),
    "bold":     os.path.join(FONTS_DIR, "Inter-Bold.ttf"),
}

FONT_NAMES = {
    "regular":  "Inter",
    "semibold": "Inter-SemiBold",
    "bold":     "Inter-Bold",
}


def register_fonts():
    from kivy.core.text import LabelBase
    for key, path in FONT_FILES.items():
        if os.path.exists(path):
            LabelBase.register(
                name=FONT_NAMES[key],
                fn_regular=path,
            )


def apply_theme(app):
    app.theme_cls.primary_palette = "Green"
    app.theme_cls.primary_hue = "500"
    app.theme_cls.theme_style = "Light"
    register_fonts()
