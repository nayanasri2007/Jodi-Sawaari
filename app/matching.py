from math import radians, sin, cos, asin, sqrt

PICKUP_RADIUS_KM = 1.0
DROP_RADIUS_KM = 2.0


def haversine_km(lat1, lng1, lat2, lng2):
    """Distance in km between two map points."""
    r = 6371  # earth radius in km
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * asin(sqrt(a))


def gender_allowed(preference, gender):
    """Does this preference accept a person of this gender?"""
    if preference == "women_only":
        return gender == "female"
    if preference == "men_only":
        return gender == "male"
    return True  # "mixed" accepts anyone


def is_match(a, a_gender, b, b_gender):
    """True if ride request a and ride request b can share a ride."""
    # 1. Both people must accept each other's gender
    if not gender_allowed(a.preference, b_gender):
        return False
    if not gender_allowed(b.preference, a_gender):
        return False

    # 2. Pickup points close together
    if haversine_km(a.pickup_lat, a.pickup_lng, b.pickup_lat, b.pickup_lng) > PICKUP_RADIUS_KM:
        return False

    # 3. Drop points close together
    if haversine_km(a.drop_lat, a.drop_lng, b.drop_lat, b.drop_lng) > DROP_RADIUS_KM:
        return False

    # 4. Departure times overlap
    gap_minutes = abs((a.depart_time - b.depart_time).total_seconds()) / 60
    if gap_minutes > a.flexibility_minutes + b.flexibility_minutes:
        return False

    return True