import os

# Load local .env if present (Option A) — never commit real key; see .env.example
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_URL = "https://trackwaylogistics.ng/api/v1"
WEB_BASE_URL = "https://trackwaylogistics.ng"

# Google Places (direct, restricted Android package ng.trackway) — set via env before real users
MAPS_API_KEY = os.getenv("MAPS_API_KEY") or os.getenv("GOOGLE_PLACES_API_KEY") or ""
GOOGLE_PLACES_API_KEY = MAPS_API_KEY
PLACES_AUTOCOMPLETE_URL = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Paystack (hosted checkout — test vs live) — set via env before real users, same .env pattern
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY") or os.getenv("PAYSTACK_KEY") or ""
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY") or ""

# Endpoints that live at web root (verified via cURL: no /api/v1 prefix) – surgical
# request_delivery promoted to api/v1 Bearer (401 pattern confirmed); only register stays WEB
# rider/profile.php is HTML web page (same Referer/cookie flow as get-notifications.php rider)
# rider/wallet.php JSON variant (?ajax=1) is also WEB (not api/v1)
# customer/request-ride.php is WEB session/cookie 302 → Paystack (not api/v1 Bearer)
WEB_ENDPOINTS = {"register_customer", "rider_profile", "rider_wallet", "rider_wallet_json", "request_ride", "customer_dashboard_html"}

API_TIMEOUT = 30

ENDPOINTS = {
    # Auth: Customer
    "register_customer":    "customer/register.php",
    "login_customer":       "customer/login.php",
    "refresh_token":        "customer/refresh-token.php",
    "logout_customer":      "customer/logout.php",
    "check_referral":       "customer/check-referral.php",

    # Auth: Rider
    "login_rider":          "rider/login.php",
    "refresh_rider_token":  "rider/refresh-token.php",
    "logout_rider":         "rider/logout.php",

    # Tracking
    "track_details":         "tracking/details.php",
    "track_rider_location":  "tracking/flutter-get-rider-location.php",

    # Notifications - real endpoint (both roles, Bearer scoped)
    "get_notifications":                "https://trackwaylogistics.ng/api/get-notifications.php",
    # Customer Dashboard — dashboard_stats is api/v1 JSON, but dashboard HTML (server-rendered) is WEB with true Total Rides 10
    "customer_dashboard_html":      "customer/dashboard.php",
    "dashboard_stats":              "customer/dashboard-stats.php",
    "customer_deliveries":          "customer/deliveries.php",
    "status_counts":                "customer/status-counts.php",
    "customer_history":             "customer/history.php",
    "customer_notifications":       "https://trackwaylogistics.ng/api/get-notifications.php",
    "mark_notification_read":       "customer/mark-notification-read.php",
    "mark_all_notifications_read":  "customer/mark-all-notifications-read.php",
    # Rider Dashboard - Notifications (role-aware dropdown, list uses same get_notifications)
    "rider_notifications":                "https://trackwaylogistics.ng/api/get-notifications.php",
    "mark_rider_notification_read":       "rider/notifications/mark-read.php",
    "mark_all_rider_notifications_read":  "rider/notifications/mark-all-read.php",
    "customer_profile":             "customer/profile.php",
    "update_profile":               "customer/update-profile.php",
    "change_password":              "customer/change-password.php",
    "referral_stats":               "customer/referral/stats.php",
    "referral_list":                "customer/referral/list.php",

    # Customer: Request Delivery + Ride (ride uses dropoff_*/fare — see request_ride_screen._do_request_ride)
    "calculate_distance":       "customer/calculate-distance.php",
    "request_delivery":         "customer/request-delivery.php",
    "request_ride":             "customer/request-ride.php",
    "available_riders":         "customer/get-available-riders.php",
    "select_rider":             "customer/select-rider.php",
    "delivery_confirmed":       "customer/delivery-confirmed.php",

    # Rider
    "rider_profile":            "rider/profile.php",
    "rider_deliveries":         "rider/deliveries.php",
    "rider_delivery_details":   "rider/delivery-details.php",
    "rider_mark_pickup":        "rider/mark-pickup.php",
    "rider_update_status":      "rider/update-delivery-status.php",
    "rider_mark_delivered":     "rider/mark-delivered.php",
    "rider_handover_to_driver": "rider/handover-to-driver.php",
    "rider_receive_from_driver":"rider/receive-from-driver.php",
    "rider_acknowledge_handover":"rider/acknowledge-handover.php",
    "rider_update_location":    "rider/update-location.php",

    # Payments & Wallet
    "payment_config":       "payment/config.php",
    "retry_payment":        "retry-payment.php",
    "verify_payment":       "verify-payment.php",
    "paystack_initialize":  "paystack/initialize.php",
    "rider_earnings":       "rider/earnings.php",
    "rider_wallet":         "rider/wallet.php",
    "rider_wallet_json":    "rider/wallet.php",
    "rider_banks":          "rider/banks.php",
    "rider_resolve_account":"rider/resolve-account.php",
    "rider_withdraw":       "rider/withdraw.php",
    "rider_support_waybills":"rider/support/waybills-list.php",
    "rider_support_submit": "rider/support/submit.php",
    "rider_support_list":   "rider/support/list.php",

    # Complaints / Support
    "submit_complaint":     "customer/submit-complaint.php",
    "support_tickets":      "customer/get-complaints.php",

    # Pending Payments (customer dashboard — absolute /api/ not api/v1)
    "retry_ride_payment":   "https://trackwaylogistics.ng/api/retry-ride-payment.php",
    "cancel_ride":          "https://trackwaylogistics.ng/api/cancel-ride.php",
}
