WAYBILL_STATUSES = [
    "pending_pickup",
    "picked_up",
    "in_transit",
    "arrived_destination_city",
    "out_for_delivery",
    "delivered",
    "failed",
    "cancelled",
]

STATUS_LABELS = {
    "pending_pickup":           "Pending Pickup",
    "picked_up":                "Picked Up",
    "in_transit":               "In Transit",
    "arrived_destination_city": "Arrived at Destination",
    "out_for_delivery":         "Out for Delivery",
    "delivered":                "Delivered",
    "failed":                   "Failed",
    "cancelled":                "Cancelled",
}

STATUS_TRANSITIONS = {
    "pending_pickup": {
        "customer": ["cancelled"],
        "rider":    ["picked_up"],
    },
    "picked_up": {
        "rider": ["in_transit"],
    },
    "in_transit": {
        "rider": ["arrived_destination_city"],
    },
    "arrived_destination_city": {
        "rider":    ["out_for_delivery"],
        "driver":   ["receive_from_driver"],
    },
    "out_for_delivery": {
        "rider": ["delivered"],
    },
    "delivered": {},
    "failed": {},
    "cancelled": {},
}

ROLES = ("customer", "rider", "driver")

DELIVERY_METHODS = {
    "instant":    "Instant",
    "same_day":   "Same Day",
    "next_day":   "Next Day",
    "express":    "Express",
    "standard":   "Standard",
}

PAYMENT_METHODS = {
    "cash":           "Cash on Delivery",
    "card":           "Debit Card",
    "wallet":         "Wallet",
    "bank_transfer":  "Bank Transfer",
}

COMPLAINT_TYPES = {
    "delay":        "Delayed Delivery",
    "lost_parcel":  "Lost Parcel",
    "damaged":      "Damaged Parcel",
    "wrong_item":   "Wrong Item",
    "rider_conduct":"Rider Conduct",
    "other":        "Other",
}
