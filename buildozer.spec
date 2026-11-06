[app]

title = Trackway
package.name = trackway
package.domain = ng
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 0.1.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,requests

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_FINE_LOCATION
android.api = 34
android.minapi = 24
android.archs = arm64-v8a

# Buildozer fixes from Phase 0
warn_on_root = 0
p4a.branch = v2024.01.21

# Icon and splash
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/splash.png

# Log
log_level = 2
