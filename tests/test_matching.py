from datetime import datetime
from types import SimpleNamespace

from app.matching import haversine_km, is_match


def make_request(preference="mixed", hour=9, minute=0,
                 pickup=(17.4400, 78.3489), drop=(17.4947, 78.3996)):
    return SimpleNamespace(
        pickup_lat=pickup[0], pickup_lng=pickup[1],
        drop_lat=drop[0], drop_lng=drop[1],
        depart_time=datetime(2026, 10, 28, hour, minute),
        flexibility_minutes=15,
        preference=preference,
    )


def test_distance_same_point_is_zero():
    assert haversine_km(17.44, 78.34, 17.44, 78.34) == 0


def test_two_women_women_only_match():
    a = make_request("women_only")
    b = make_request("women_only")
    assert is_match(a, "female", b, "female")


def test_man_does_not_match_women_only():
    a = make_request("women_only")
    b = make_request("mixed")
    assert not is_match(a, "female", b, "male")


def test_two_men_men_only_match():
    a = make_request("men_only")
    b = make_request("men_only")
    assert is_match(a, "male", b, "male")


def test_mixed_matches_anyone():
    a = make_request("mixed")
    b = make_request("mixed")
    assert is_match(a, "female", b, "male")


def test_far_pickup_does_not_match():
    a = make_request("mixed")
    b = make_request("mixed", pickup=(17.5500, 78.3489))  # about 12 km away
    assert not is_match(a, "female", b, "female")


def test_time_too_far_apart_does_not_match():
    a = make_request("mixed", hour=9)
    b = make_request("mixed", hour=11)
    assert not is_match(a, "female", b, "female")