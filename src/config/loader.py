from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import yaml


@dataclass
class PriceRange:
    min: int
    max: int


@dataclass
class TargetConfig:
    name: str
    address: str
    arrival_time: Optional[str] = None
    arrival_day: Optional[str] = None


@dataclass
class WebsiteConfig:
    name: str
    base_url: str
    is_active: bool = True


@dataclass
class NominatimConfig:
    base_url: str = "https://nominatim.openstreetmap.org"
    user_agent: str = "APT-Finder/1.0"
    email: Optional[str] = None
    min_delay_seconds: float = 1.0
    max_requests_per_run: Optional[int] = 25


@dataclass
class GeocodingConfig:
    provider: str = "google"
    nominatim: NominatimConfig = field(default_factory=NominatimConfig)


@dataclass
class DistanceConfig:
    use_google_maps_bike_calculation: bool = True
    geocoding: GeocodingConfig = field(default_factory=GeocodingConfig)


@dataclass
class Config:
    price_range: PriceRange
    targets: list[TargetConfig]
    websites: list[WebsiteConfig]
    distance: DistanceConfig = field(default_factory=DistanceConfig)


def load_config(path: Path | str = "config.yaml") -> Config:
    """Load configuration from YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {config_path}")

    raw_targets = data.get("targets", [])
    raw_websites = data.get("websites", [])

    if raw_targets is None:
        raw_targets = []
    if raw_websites is None:
        raw_websites = []

    if not isinstance(raw_targets, list):
        raise ValueError(f"'targets' must be a list in {config_path}")
    if not isinstance(raw_websites, list):
        raise ValueError(f"'websites' must be a list in {config_path}")

    return Config(
        price_range=_load_price_range(data.get("price_range"), config_path),
        targets=[_load_target_config(target, config_path) for target in raw_targets],
        websites=[_load_website_config(website, config_path) for website in raw_websites],
        distance=_load_distance_config(data.get("distance"), config_path),
    )


def _load_price_range(raw: Any, config_path: Path) -> PriceRange:
    if not isinstance(raw, dict):
        raise ValueError(f"Missing or invalid 'price_range' section in {config_path}")

    try:
        price_range = PriceRange(min=int(raw["min"]), max=int(raw["max"]))
    except KeyError as exc:
        raise ValueError(f"Missing price range field {exc.args[0]!r} in {config_path}") from exc

    if price_range.min < 0 or price_range.max < 0:
        raise ValueError(f"Price range values must be non-negative in {config_path}")
    if price_range.min > price_range.max:
        raise ValueError(f"Price range min cannot be greater than max in {config_path}")
    return price_range


def _load_target_config(raw: Any, config_path: Path) -> TargetConfig:
    if not isinstance(raw, dict):
        raise ValueError(f"Each target entry must be a mapping in {config_path}")

    try:
        name = str(raw["name"])
        address = str(raw["address"])
    except KeyError as exc:
        raise ValueError(f"Missing target field {exc.args[0]!r} in {config_path}") from exc

    arrival_time = raw.get("arrival_time")
    arrival_day = raw.get("arrival_day")
    return TargetConfig(name=name, address=address, arrival_time=arrival_time, arrival_day=arrival_day)


def _load_website_config(raw: Any, config_path: Path) -> WebsiteConfig:
    if not isinstance(raw, dict):
        raise ValueError(f"Each website entry must be a mapping in {config_path}")

    try:
        name = str(raw["name"])
    except KeyError as exc:
        raise ValueError(f"Missing website field {exc.args[0]!r} in {config_path}") from exc

    base_url = raw.get("base_url") or raw.get("url")
    if not base_url:
        raise ValueError(f"Website entry {name!r} must define 'base_url' or legacy 'url' in {config_path}")

    is_active = raw.get("is_active", True)
    return WebsiteConfig(name=name, base_url=str(base_url), is_active=bool(is_active))


def _load_distance_config(raw: Any, config_path: Path) -> DistanceConfig:
    if raw is None:
        return DistanceConfig()
    if not isinstance(raw, dict):
        raise ValueError(f"'distance' must be a mapping in {config_path}")

    use_google_bike = raw.get(
        "use_google_maps_bike_calculation",
        raw.get("google_maps_bike_calculation", True),
    )
    geocoding = _load_geocoding_config(raw.get("geocoding"), config_path)
    return DistanceConfig(
        use_google_maps_bike_calculation=bool(use_google_bike),
        geocoding=geocoding,
    )


def _load_geocoding_config(raw: Any, config_path: Path) -> GeocodingConfig:
    if raw is None:
        return GeocodingConfig()
    if not isinstance(raw, dict):
        raise ValueError(f"'distance.geocoding' must be a mapping in {config_path}")

    provider = str(raw.get("provider", "google")).strip().lower()
    if provider not in {"google", "nominatim"}:
        raise ValueError(
            f"'distance.geocoding.provider' must be either 'google' or 'nominatim' in {config_path}"
        )

    raw_nominatim = raw.get("nominatim", {})
    if raw_nominatim is None:
        raw_nominatim = {}
    if not isinstance(raw_nominatim, dict):
        raise ValueError(f"'distance.geocoding.nominatim' must be a mapping in {config_path}")

    return GeocodingConfig(
        provider=provider,
        nominatim=_load_nominatim_config(raw_nominatim, config_path),
    )


def _load_nominatim_config(raw: Any, config_path: Path) -> NominatimConfig:
    if not isinstance(raw, dict):
        raise ValueError(f"'distance.geocoding.nominatim' must be a mapping in {config_path}")

    base_url = str(raw.get("base_url", "https://nominatim.openstreetmap.org")).strip()
    if not base_url:
        base_url = "https://nominatim.openstreetmap.org"
    user_agent = str(raw.get("user_agent", "APT-Finder/1.0")).strip() or "APT-Finder/1.0"
    email = raw.get("email")
    if email is not None:
        email = str(email).strip() or None

    try:
        min_delay_seconds = float(raw.get("min_delay_seconds", 1.0))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"'distance.geocoding.nominatim.min_delay_seconds' must be a number in {config_path}"
        ) from exc

    raw_max_requests = raw.get("max_requests_per_run", 25)
    if raw_max_requests in (None, ""):
        max_requests_per_run = None
    else:
        try:
            max_requests_per_run = int(raw_max_requests)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"'distance.geocoding.nominatim.max_requests_per_run' must be an integer in {config_path}"
            ) from exc
        if max_requests_per_run <= 0:
            raise ValueError(
                f"'distance.geocoding.nominatim.max_requests_per_run' must be positive in {config_path}"
            )

    if min_delay_seconds <= 0:
        raise ValueError(
            f"'distance.geocoding.nominatim.min_delay_seconds' must be greater than zero in {config_path}"
        )

    return NominatimConfig(
        base_url=base_url,
        user_agent=user_agent,
        email=email,
        min_delay_seconds=min_delay_seconds,
        max_requests_per_run=max_requests_per_run,
    )
