import os

base = r'C:\Users\FAITH MUREWA\Desktop\All_My_Projects\Trackway\app\views\customer'
files = ['customer_home_screen.py', 'customer_deliveries_screen.py', 'customer_history_screen.py', 'waybill_detail_screen.py', 'profile_screen.py']

old = '''def on_pre_enter(self, *args):
        from app.core import session
        if not session.is_logged_in() or session.get_role() != "customer":
            if self.manager:
                self.manager.current = "customer_login"'''

new = '''def on_pre_enter(self, *args):
        from app.core import session
        if not session.is_logged_in() or session.get_role() != "customer":
            if self.manager:
                self.manager.current = "customer_login"
            return
        super().on_pre_enter(*args)'''

for f in files:
    path = os.path.join(base, f)
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    if old in content:
        content = content.replace(old, new)
        with open(path, 'w', encoding='utf-8') as file:
            file.write(content)
        print('Fixed ' + f)
    else:
        print('Pattern not found in ' + f)