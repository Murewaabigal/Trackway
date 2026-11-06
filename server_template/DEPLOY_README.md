# Deploy: new api/v1/customer/request-ride.php

**Source:** `server_template/api/v1/customer/request-ride.php` in this repo (template)

**Target on server:** `api/v1/customer/request-ride.php` (sibling to `api/v1/customer/request-delivery.php`)

**Steps:**
1. Copy template to server path: `api/v1/customer/request-ride.php`
2. Fix `require_once` paths at top to match your `request-delivery.php` (JwtHandler, config/pdo). Template uses `__DIR__/../../core/JwtHandler.php` — adjust if different.
3. Replace placeholder business-logic block (marked `PLACEHOLDER — replace with copied WEB/customer/request-ride.php body`) with actual `WEB/customer/request-ride.php` contents *after* its `verifyCSRFToken()` line, removing any `header("Location: login.php")` / `$error_message` HTML redirects. Keep `dropoff_* + fare + estimated_duration` field names as-is.
4. Test:
```
curl.exe -i -X POST "https://trackwaylogistics.ng/api/v1/customer/request-ride.php" -H "Authorization: Bearer <REAL_TOKEN_AFTER_FRESH_LOGIN>" --data-urlencode "pickup_address=Ikeja, Lagos" --data-urlencode "pickup_city=Lagos" --data-urlencode "pickup_lat=6.6018" --data-urlencode "pickup_lng=3.3515" --data-urlencode "dropoff_address=Abuja, FCT" --data-urlencode "dropoff_city=Abuja" --data-urlencode "dropoff_lat=9.0765" --data-urlencode "dropoff_lng=7.3986" --data-urlencode "distance_km=178.13" --data-urlencode "estimated_duration=208" --data-urlencode "fare=500"
# expect 200 {"status":"success",...} not 404/302
```
5. Mobile already fixed: `app/core/config.py:26 WEB_ENDPOINTS={"register_customer"}` and `app/services/customer_service.py:277 request_ride -> request_ride` endpoint. No further mobile deploy needed after this server file is live.
