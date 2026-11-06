from kivymd.uix.screen import MDScreen
from app.i18n.translator import bind_language_change, unbind_language_change


class BaseScreen(MDScreen):
    """Base screen class with automatic language change handling."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._language_binding = None
    
    def on_pre_enter(self, *args):
        """Bind to language change events when screen is about to be shown."""
        from app.i18n.translator import bind_language_change
        self._language_binding = bind_language_change(self.on_language_changed)
        super().on_pre_enter(*args)
        # Q2 per-screen on revisit: refresh UI when navigating back after language change
        try:
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.rebuild_ui(), 0)
        except Exception:
            pass
    
    def on_pre_leave(self, *args):
        """Unbind from language change events when screen is about to be hidden."""
        from app.i18n.translator import unbind_language_change
        if self._language_binding:
            unbind_language_change(self._language_binding)
            self._language_binding = None
        super().on_pre_leave(*args)
    
    def on_language_changed(self, instance, lang_code):
        """Called when language changes. Override in subclasses to re-render UI."""
        self.rebuild_ui()
    
    def rebuild_ui(self):
        """Override this method in subclasses to re-render UI with new language."""
        pass