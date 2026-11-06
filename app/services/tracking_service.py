from app.core.api_client import api_get


def track_waybill(waybill_number):
    result = api_get(
        "track_details",
        params={"waybill_number": waybill_number},
    )
    return result


def get_rider_location(waybill_number):
    result = api_get(
        "track_rider_location",
        params={"waybill_number": waybill_number},
    )
    return result
