from dataclasses import dataclass

import src.distance.calculator as calculator_module
from src.config import DistanceConfig, GeocodingConfig, NominatimConfig
from src.distance.calculator import DistanceCalculator
from src.models import Address, Apartment, Target


@dataclass
class DummyOTPRouteResult:
    duration_minutes: int
    distance_km: float | None = None


class DummyOTPClient:
    def __init__(self, *args, **kwargs):
        self._available = True

    def is_available(self) -> bool:
        return self._available

    def get_routes_batch(self, *args, **kwargs):
        return {
            "walk_transit": DummyOTPRouteResult(duration_minutes=30, distance_km=5.0),
            "bike_transit": DummyOTPRouteResult(duration_minutes=20, distance_km=4.5),
            "bike_only": DummyOTPRouteResult(duration_minutes=18, distance_km=4.2),
        }

    def get_walk_transit_route(self, *args, **kwargs):
        return DummyOTPRouteResult(duration_minutes=30, distance_km=5.0)

    def get_bike_transit_route(self, *args, **kwargs):
        return DummyOTPRouteResult(duration_minutes=20, distance_km=4.5)

    def get_bike_only_route(self, *args, **kwargs):
        return DummyOTPRouteResult(duration_minutes=18, distance_km=4.2)


class FakeNominatimResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_nominatim_geocode_works_without_google_key(monkeypatch):
    monkeypatch.setattr(calculator_module, "OTPClient", DummyOTPClient)

    config = DistanceConfig(
        use_google_maps_bike_calculation=False,
        geocoding=GeocodingConfig(
            provider="nominatim",
            nominatim=NominatimConfig(
                user_agent="apt-finder-test",
                min_delay_seconds=0.01,
                max_requests_per_run=1,
            ),
        ),
    )
    calculator = DistanceCalculator(config)

    requests_seen = []

    def fake_get(url, params, timeout):
        requests_seen.append((url, params, timeout))
        return FakeNominatimResponse([
            {"lat": "35.681236", "lon": "139.767125"},
        ])

    monkeypatch.setattr(calculator._nominatim_session, "get", fake_get)

    coords = calculator.geocode("Tokyo Station, Tokyo, Japan")

    assert coords == (35.681236, 139.767125)
    assert calculator.geocoding_requests_remaining == 0
    assert not calculator.can_geocode()
    assert len(requests_seen) == 1


def test_otp_only_bike_mode_skips_google_maps(monkeypatch):
    monkeypatch.setattr(calculator_module, "OTPClient", DummyOTPClient)

    config = DistanceConfig(
        use_google_maps_bike_calculation=False,
        geocoding=GeocodingConfig(
            provider="nominatim",
            nominatim=NominatimConfig(user_agent="apt-finder-test"),
        ),
    )
    calculator = DistanceCalculator(config)

    def fail_google_bike_time(*args, **kwargs):
        raise AssertionError("Google bike calculation should be disabled")

    monkeypatch.setattr(calculator, "_get_google_bike_time", fail_google_bike_time)

    apartment = Apartment(
        name="Test Apartment",
        price=90000,
        website_id=1,
        address=Address(address_text="Tokyo, Japan", latitude=35.681236, longitude=139.767125),
        id=1,
    )
    target = Target(
        name="Office",
        address="Tokyo Station, Tokyo, Japan",
        latitude=35.689487,
        longitude=139.691711,
        arrival_time="09:00",
        arrival_day="Monday",
        id=1,
    )

    distance = calculator.calculate(apartment, target)

    assert distance is not None
    assert distance.time_transit_walk_minutes == 30
    assert distance.time_transit_bike_minutes == 20
    assert distance.time_bike_minutes == 18
    assert distance.selected_mode == "bike"
