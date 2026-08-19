import pytest

from src.config import load_config


def test_load_config_supports_legacy_url_key(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """price_range:
  min: 50000
  max: 150000

targets:
  - name: Office
    address: Tokyo Station, Tokyo, Japan
    arrival_time: "09:00"
    arrival_day: Monday

websites:
  - name: TokyoMonthly
    url: https://tokyomonthly.com/properties/
    is_active: true
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.price_range.min == 50000
    assert config.price_range.max == 150000
    assert config.targets[0].name == "Office"
    assert config.websites[0].base_url == "https://tokyomonthly.com/properties/"
    assert config.websites[0].is_active is True


def test_load_config_defaults_distance_settings(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """price_range:
  min: 50000
  max: 150000

targets:
  - name: Office
    address: Tokyo Station, Tokyo, Japan

websites:
  - name: TokyoMonthly
    base_url: https://tokyomonthly.com/properties/
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.distance.use_google_maps_bike_calculation is True
    assert config.distance.geocoding.provider == "google"
    assert config.distance.geocoding.nominatim.min_delay_seconds == 1.0
    assert config.distance.geocoding.nominatim.max_requests_per_run == 25


def test_load_config_supports_distance_provider_switches(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """price_range:
  min: 50000
  max: 150000

distance:
  use_google_maps_bike_calculation: false
  geocoding:
    provider: nominatim
    nominatim:
      base_url: https://example.org/nominatim
      user_agent: apt-finder-test
      email: user@example.com
      min_delay_seconds: 1.5
      max_requests_per_run: 10

targets:
  - name: Office
    address: Tokyo Station, Tokyo, Japan

websites:
  - name: TokyoMonthly
    base_url: https://tokyomonthly.com/properties/
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.distance.use_google_maps_bike_calculation is False
    assert config.distance.geocoding.provider == "nominatim"
    assert config.distance.geocoding.nominatim.base_url == "https://example.org/nominatim"
    assert config.distance.geocoding.nominatim.user_agent == "apt-finder-test"
    assert config.distance.geocoding.nominatim.email == "user@example.com"
    assert config.distance.geocoding.nominatim.min_delay_seconds == 1.5
    assert config.distance.geocoding.nominatim.max_requests_per_run == 10


def test_load_config_supports_jageocoder_provider(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """price_range:
  min: 50000
  max: 150000

distance:
  use_google_maps_bike_calculation: false
  geocoding:
    provider: jageocoder
    jageocoder:
      server_url: https://jageocoder.example.com/jsonrpc
      min_delay_seconds: 1.0

targets:
  - name: Office
    address: Tokyo Station, Tokyo, Japan

websites:
  - name: TokyoMonthly
    base_url: https://tokyomonthly.com/properties/
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.distance.geocoding.provider == "jageocoder"
    assert config.distance.geocoding.jageocoder.server_url == "https://jageocoder.example.com/jsonrpc"
    assert config.distance.geocoding.jageocoder.min_delay_seconds == 1.0


def test_load_config_jageocoder_defaults(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """price_range:
  min: 50000
  max: 150000

distance:
  geocoding:
    provider: jageocoder

targets:
  - name: Office
    address: Tokyo Station, Tokyo, Japan

websites:
  - name: TokyoMonthly
    base_url: https://tokyomonthly.com/properties/
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.distance.geocoding.jageocoder.server_url is None
    assert config.distance.geocoding.jageocoder.min_delay_seconds == 0.5


def test_load_config_rejects_invalid_jageocoder_min_delay(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """price_range:
  min: 50000
  max: 150000

distance:
  geocoding:
    provider: jageocoder
    jageocoder:
      min_delay_seconds: -1

targets:
  - name: Office
    address: Tokyo Station, Tokyo, Japan

websites:
  - name: TokyoMonthly
    base_url: https://tokyomonthly.com/properties/
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="min_delay_seconds"):
        load_config(config_file)
