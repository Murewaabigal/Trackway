<?php
// api/v1/customer/request-ride.php — CSRF-free mirror of WEB/customer/request-ride.php
// Mobile: dropoff_* + fare + estimated_duration, JWT Bearer auth, JSON {status,data} like api/v1/customer/request-delivery.php
// Deploy: copy to server as api/v1/customer/request-ride.php (alongside api/v1/customer/request-delivery.php)
// After deploy, mobile app/core/config.py request_ride -> BASE_URL/api/v1/customer/request-ride.php (Bearer) will return JSON, not 302→HTML.

header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With, X-Authorization, X-Auth-Token, X-API-Key, X-Token");
header("Access-Control-Allow-Credentials: true");
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(200); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(["status" => "error", "message" => "Method not allowed"]);
    exit;
}

// --- 1. JWT extraction — same as api/v1/customer/request-delivery.php you confirmed ---
function getBearerToken() {
    $headers = null;
    if (isset($_SERVER['HTTP_AUTHORIZATION'])) $headers = trim($_SERVER['HTTP_AUTHORIZATION']);
    elseif (isset($_SERVER['HTTP_X_AUTHORIZATION'])) $headers = trim($_SERVER['HTTP_X_AUTHORIZATION']);
    elseif (isset($_SERVER['HTTP_X_AUTH_TOKEN'])) $headers = trim($_SERVER['HTTP_X_AUTH_TOKEN']);
    elseif (isset($_SERVER['HTTP_X_API_KEY'])) $headers = trim($_SERVER['HTTP_X_API_KEY']);
    elseif (isset($_SERVER['HTTP_X_TOKEN'])) $headers = trim($_SERVER['HTTP_X_TOKEN']);
    elseif (function_exists('apache_request_headers')) {
        $ah = apache_request_headers();
        foreach (['Authorization','X-Authorization','X-Auth-Token','X-API-Key','X-Token'] as $k) {
            if (isset($ah[$k])) { $headers = trim($ah[$k]); break; }
            if (isset($ah[strtolower($k)])) { $headers = trim($ah[strtolower($k)]); break; }
        }
    }
    if (!empty($headers)) {
        if (preg_match('/Bearer\s+(.*)$/i', $headers, $m)) return trim($m[1]);
        return $headers; // allow raw token if client sent without Bearer prefix
    }
    return null;
}

require_once __DIR__ . '/../../../config.php'; // adjust to your api/v1 path if needed — same as request-delivery.php
require_once __DIR__ . '/../../core/JwtHandler.php'; // same as request-delivery.php — adjust path

$token = getBearerToken();
if (empty($token)) {
    http_response_code(401);
    echo json_encode(["status" => "error", "message" => "Invalid or expired token"]);
    exit;
}
try {
    $jwt = new JwtHandler();
    $payload = $jwt->verifyToken($token);
} catch (Exception $e) {
    http_response_code(401);
    echo json_encode(["status" => "error", "message" => "Invalid or expired token"]);
    exit;
}
$customer_id = $payload['customer_id'] ?? $payload['user_id'] ?? 0;
if (!$customer_id) {
    http_response_code(401);
    echo json_encode(["status" => "error", "message" => "Invalid or expired token"]);
    exit;
}

// --- 2. Customer lookup — same as delivery ---
// $pdo is expected from config.php; adjust variable name to match your delivery file ($conn/$db)
$stmt = $pdo->prepare("SELECT * FROM customers WHERE id = ? LIMIT 1");
$stmt->execute([$customer_id]);
$customer = $stmt->fetch(PDO::FETCH_ASSOC);
if (!$customer) {
    http_response_code(404);
    echo json_encode(["status" => "error", "message" => "Customer not found"]);
    exit;
}

// --- 3. Input — accept both JSON body and form-data (like delivery) ---
$input = [];
$contentType = $_SERVER['CONTENT_TYPE'] ?? $_SERVER['HTTP_CONTENT_TYPE'] ?? '';
if (stripos($contentType, 'application/json') !== false) {
    $raw = file_get_contents('php://input');
    $json = json_decode($raw, true);
    if (is_array($json)) $input = $json;
}
if (empty($input)) $input = $_POST; // form-data fallback — mobile app/core/api_client uses x-www-form-urlencoded by default

// --- 4. Field validation — ride uses dropoff_* + fare + estimated_duration (per WEB/customer/request-ride.php $_POST you read) ---
$required = [
    'pickup_address','pickup_city','pickup_lat','pickup_lng',
    'dropoff_address','dropoff_city','dropoff_lat','dropoff_lng',
    'distance_km','estimated_duration','fare'
];
$errors = [];
foreach ($required as $f) {
    if (!isset($input[$f]) || trim((string)$input[$f]) === '') $errors[] = "$f is required";
}
// optional: special_instructions allowed empty
if (!empty($errors)) {
    http_response_code(400);
    echo json_encode(["status" => "error", "message" => implode(", ", $errors)]);
    exit;
}
// numeric sanity (like delivery) — keeps 400 shape consistent
if (!is_numeric($input['pickup_lat']) || !is_numeric($input['pickup_lng']) || !is_numeric($input['dropoff_lat']) || !is_numeric($input['dropoff_lng']) || !is_numeric($input['distance_km']) || !is_numeric($input['estimated_duration']) || !is_numeric($input['fare'])) {
    http_response_code(400);
    echo json_encode(["status" => "error", "message" => "Invalid numeric fields"]);
    exit;
}

// --- 5. Business logic — COPY from WEB/customer/request-ride.php AFTER its verifyCSRFToken() line, up to its redirect/$error_message ---
// Example: keep everything that inserts ride, calculates fee server-side, creates paystack transaction, etc.
// Remove any `if ($error_message) { header("Location: login.php"); }` / HTML redirect — replace with JSON error above.
// The WEB file's core after CSRF is DB insert + paystack; reuse verbatim, just ensure it populates $authorization_url, $reference, $waybill_number etc.
// For template, placeholder insert — replace with your actual WEB ride logic:
try {
    // PLACEHOLDER — replace with copied WEB/customer/request-ride.php body (minus CSRF):
    // e.g. $stmt = $pdo->prepare("INSERT INTO rides (customer_id, pickup_address, ...) VALUES (...)");
    //      $stmt->execute([...]);
    //      $ride_id = $pdo->lastInsertId();
    //      // paystack initialize via PAYSTACK_SECRET_KEY — same as delivery
    //      // $paystack = paystack_initialize($customer['email'], $input['fare']*100, $reference);
    // For now, return success without DB side-effects so mobile routing can be verified immediately.
    // TODO: paste real WEB ride insert + paystack code here.
    $reference = "TRK-RIDE-" . strtoupper(bin2hex(random_bytes(4)));
    $waybill_number = $reference;
    $authorization_url = "https://checkout.paystack.com/" . $reference; // replace with real paystack response

    http_response_code(200);
    echo json_encode([
        "status" => "success",
        "message" => "Ride requested",
        "data" => [
            "ride_id" => $waybill_number,
            "waybill_number" => $waybill_number,
            "reference" => $reference,
            "authorization_url" => $authorization_url,
            "fare" => (string)$input['fare'],
            "distance_km" => (string)$input['distance_km'],
            "estimated_duration" => (string)$input['estimated_duration']
        ]
    ]);
    exit;
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(["status" => "error", "message" => "Server error: " . $e->getMessage()]);
    exit;
}
