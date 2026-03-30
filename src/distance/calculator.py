import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

import googlemaps
import requests
from dotenv import load_dotenv

from src.config.loader import DistanceConfig
from src.models import Apartment, Target, Distance, Address
from src.distance.otp_client import OTPClient

load_dotenv()
logger = logging.getLogger(__name__)


class DistanceCalculator:
    """
    Distance calculator using:
    - Google Maps API for optional geocoding and bicycle routing
    - Nominatim for API-free geocoding
    - OpenTripPlanner (OTP) for public transit routing
    
    Calculates three route types:
    - WALK + TRANSIT: Walk to station, take train (OTP)
    - BICYCLE + TRANSIT: Bike to station, take train (OTP)
    - BICYCLE: Either Google Maps + OTP average or OTP-only, depending on config
    """
    
    def __init__(
        self,
        distance_config: DistanceConfig | None = None,
        otp_url: str = "http://localhost:8080",
    ):
        self.distance_config = distance_config or DistanceConfig()
        self.use_google_maps_bike_calculation = self.distance_config.use_google_maps_bike_calculation
        self.geocoding_provider = self.distance_config.geocoding.provider.lower().strip()
        self.nominatim_config = self.distance_config.geocoding.nominatim
        self._google_maps_client: googlemaps.Client | None = None
        self._google_maps_api_key: Optional[str] = None
        self._nominatim_session = requests.Session()
        self._nominatim_session.headers.update({"User-Agent": self.nominatim_config.user_agent})
        self._nominatim_requests_made = 0
        self._nominatim_last_request_at = 0.0

        if self.geocoding_provider not in {"google", "nominatim"}:
            raise ValueError(
                f"Unsupported geocoding provider: {self.geocoding_provider!r}. Use 'google' or 'nominatim'."
            )

        if self.geocoding_provider == "google" or self.use_google_maps_bike_calculation:
            api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            if not api_key:
                raise ValueError(
                    "GOOGLE_MAPS_API_KEY environment variable not set, but Google Maps features are enabled"
                )
            self._google_maps_api_key = api_key

        # Initialize OTP client
        self.otp_client = OTPClient(otp_url)
        
        if not self.otp_client.is_available():
            logger.warning(
                "OTP server not available at %s. "
                "Start OTP server with: cd otp-routing && .\\start_otp.ps1",
                otp_url
            )

    def is_available(self) -> bool:
        """Check if OTP routing service is available."""
        return self.otp_client.is_available()

    @property
    def geocoding_requests_remaining(self) -> Optional[int]:
        """Return remaining Nominatim geocoding requests for this run, if limited."""
        if self.geocoding_provider != "nominatim":
            return None
        if self.nominatim_config.max_requests_per_run is None:
            return None
        return max(0, self.nominatim_config.max_requests_per_run - self._nominatim_requests_made)

    def can_geocode(self) -> bool:
        """Return True if geocoding requests are still allowed for the configured provider."""
        remaining = self.geocoding_requests_remaining
        return remaining is None or remaining > 0

    def _get_google_maps_client(self) -> googlemaps.Client:
        if self._google_maps_client is None:
            if not self._google_maps_api_key:
                raise ValueError(
                    "GOOGLE_MAPS_API_KEY environment variable not set, but Google Maps features are enabled"
                )
            self._google_maps_client = googlemaps.Client(key=self._google_maps_api_key)
        return self._google_maps_client

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to coordinates using the configured provider.
        
        Args:
            address: Address string to geocode
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        if not address:
            return None
        
        try:
            if self.geocoding_provider == "nominatim":
                return self._geocode_with_nominatim(address)
            return self._geocode_with_google(address)
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
            return None

    def _geocode_with_google(self, address: str) -> Optional[Tuple[float, float]]:
        client = self._get_google_maps_client()
        results = client.geocode(address, region="jp")
        if results:
            location = results[0]["geometry"]["location"]
            lat, lng = location["lat"], location["lng"]
            logger.info(f"Geocoded with Google Maps: {address[:40]}... -> ({lat:.4f}, {lng:.4f})")
            return (lat, lng)
        logger.warning(f"No geocoding results for: {address[:50]}...")
        return None

    def _geocode_with_nominatim(self, address: str) -> Optional[Tuple[float, float]]:
        if not self.can_geocode():
            logger.warning(
                "Nominatim geocoding limit reached (%s requests max). Skipping: %s",
                self.nominatim_config.max_requests_per_run,
                address[:50],
            )
            return None

        self._respect_nominatim_rate_limit()
        self._nominatim_requests_made += 1

        params = {
            "q": address,
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "jp",
            "addressdetails": 1,
        }
        if self.nominatim_config.email:
            params["email"] = self.nominatim_config.email

        response = self._nominatim_session.get(
            f"{self.nominatim_config.base_url.rstrip('/')}/search",
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        results = response.json()

        if results:
            result = results[0]
            lat = float(result["lat"])
            lng = float(result["lon"])
            logger.info(f"Geocoded with Nominatim: {address[:40]}... -> ({lat:.4f}, {lng:.4f})")
            return (lat, lng)

        logger.warning(f"No geocoding results for: {address[:50]}...")
        return None

    def _respect_nominatim_rate_limit(self) -> None:
        if self.geocoding_provider != "nominatim":
            return

        min_delay = self.nominatim_config.min_delay_seconds
        elapsed = time.monotonic() - self._nominatim_last_request_at
        if self._nominatim_last_request_at > 0 and elapsed < min_delay:
            time.sleep(min_delay - elapsed)
        self._nominatim_last_request_at = time.monotonic()

    def _get_google_bike_time(
        self, from_lat: float, from_lon: float, to_lat: float, to_lon: float
    ) -> Optional[int]:
        """Get bicycle travel time from Google Maps API."""
        try:
            result = self._get_google_maps_client().directions(
                origin=(from_lat, from_lon),
                destination=(to_lat, to_lon),
                mode="bicycling",
            )
            if result and result[0].get("legs"):
                duration_sec = result[0]["legs"][0]["duration"]["value"]
                return int(duration_sec / 60)
            return None
        except Exception as e:
            logger.error(f"Google Maps bike route failed: {e}")
            return None

    def calculate(self, apartment: Apartment, target: Target) -> Optional[Distance]:
        """
        Calculate distance between apartment and target.
        
        Uses:
        - OTP for WALK+TRANSIT and BICYCLE+TRANSIT routes
        - Google Maps + OTP average for BICYCLE-only route when enabled
        - OTP-only bicycle routing when Google Maps bike calculation is disabled
        
        Returns Distance with three route options:
        - time_transit_walk_minutes: WALK + TRANSIT (OTP)
        - time_transit_bike_minutes: BICYCLE + TRANSIT (OTP)
        - time_bike_minutes: BICYCLE only (average or OTP-only depending on config)
        """
        if not apartment.address or not apartment.id or not target.id:
            logger.warning("Missing apartment address or IDs")
            return None

        # Get coordinates
        origin_coords = self._get_coords_for_address(apartment.address)
        target_coords = self._get_coords_for_target(target)
        
        if not origin_coords:
            logger.warning(f"No coordinates for apartment: {apartment.name[:30]}...")
            return None
        if not target_coords:
            logger.warning(f"No coordinates for target: {target.name}")
            return None
        
        from_lat, from_lon = origin_coords
        to_lat, to_lon = target_coords

        # Calculate arrival time for transit based on target settings
        arrival_time = self._get_arrival_datetime(target)
        logger.debug(f"Using arrival_time: {arrival_time}")

        logger.debug(
            f"Calculating routes from ({from_lat:.4f},{from_lon:.4f}) "
            f"to ({to_lat:.4f},{to_lon:.4f})"
        )

        # Initialize results
        walk_transit_min = None
        bike_transit_min = None
        bike_only_min = None
        distance_km = None

        # Get OTP routes if available
        if self.otp_client.is_available():
            # 1. WALK + TRANSIT (walk to station, take train)
            walk_transit_result = self.otp_client.get_walk_transit_route(
                from_lat, from_lon, to_lat, to_lon, arrive_by=arrival_time
            )
            walk_transit_min = walk_transit_result.duration_minutes if walk_transit_result else None
            
            # 2. BICYCLE + TRANSIT (bike to station, take train)
            bike_transit_result = self.otp_client.get_bike_transit_route(
                from_lat, from_lon, to_lat, to_lon, arrive_by=arrival_time
            )
            bike_transit_min = bike_transit_result.duration_minutes if bike_transit_result else None
            
            # 3. OTP BICYCLE only
            otp_bike_result = self.otp_client.get_bike_only_route(
                from_lat, from_lon, to_lat, to_lon
            )
            otp_bike_min = otp_bike_result.duration_minutes if otp_bike_result else None
            
            # Get distance from OTP bike route
            if otp_bike_result and otp_bike_result.distance_km:
                distance_km = otp_bike_result.distance_km
        else:
            logger.warning("OTP server not available, transit routes will be unavailable")
            otp_bike_min = None

        # 4. BICYCLE-only route
        google_bike_min = None
        if self.use_google_maps_bike_calculation:
            google_bike_min = self._get_google_bike_time(from_lat, from_lon, to_lat, to_lon)
        else:
            logger.debug("Google Maps bike calculation disabled; using OTP bike route only")

        # Average bike times from Google Maps and OTP when enabled
        if self.use_google_maps_bike_calculation and google_bike_min is not None and otp_bike_min is not None:
            bike_only_min = int((google_bike_min + otp_bike_min) / 2)
            logger.info(
                f"Bike time averaged: Google={google_bike_min}min, OTP={otp_bike_min}min -> {bike_only_min}min"
            )
        elif google_bike_min is not None and self.use_google_maps_bike_calculation:
            bike_only_min = google_bike_min
            logger.info(f"Using Google Maps bike time only: {bike_only_min}min")
        elif otp_bike_min is not None:
            bike_only_min = otp_bike_min
            logger.info(f"Using OTP bike time only: {bike_only_min}min")

        # Log results
        logger.info(
            f"Route results: Walk+Transit={walk_transit_min}min, "
            f"Bike+Transit={bike_transit_min}min, Bike={bike_only_min}min"
        )

        # Determine minimum time and best mode
        times = [
            (walk_transit_min, "transit_walk"),
            (bike_transit_min, "transit_bike"),
            (bike_only_min, "bike"),
        ]
        valid_times = [(t, m) for t, m in times if t is not None]
        
        if not valid_times:
            logger.warning("No valid routes found")
            return None
        
        min_time, selected_mode = min(valid_times, key=lambda x: x[0])

        return Distance(
            apartment_id=apartment.id,
            target_id=target.id,
            distance_km=distance_km,
            time_minutes=min_time,
            time_transit_walk_minutes=walk_transit_min,
            time_transit_bike_minutes=bike_transit_min,
            time_bike_minutes=bike_only_min,
            selected_mode=selected_mode,
        )

    def _get_coords_for_address(self, address: Address) -> Optional[Tuple[float, float]]:
        """Get coordinates for an address."""
        if address.latitude and address.longitude:
            return (address.latitude, address.longitude)
        logger.warning(f"Address missing coordinates: {address.address_text[:50]}...")
        return None
    
    def _get_coords_for_target(self, target: Target) -> Optional[Tuple[float, float]]:
        """Get coordinates for a target."""
        if target.latitude and target.longitude:
            return (target.latitude, target.longitude)
        logger.warning(f"Target missing coordinates: {target.address[:50]}...")
        return None

    def _get_arrival_datetime(self, target: Target) -> Optional[datetime]:
        """Get next occurrence of target arrival time in Japan timezone.
        
        Uses the target's arrival_time and arrival_day settings.
        Always calculates in Japan timezone for accurate transit results.
        """
        if not target.arrival_time or not target.arrival_day:
            return None

        day_map = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
            "Friday": 4, "Saturday": 5, "Sunday": 6,
        }

        # Use Japan timezone for calculations
        jst = ZoneInfo("Asia/Tokyo")
        now_jst = datetime.now(jst)
        
        target_day = day_map.get(target.arrival_day, 0)
        days_ahead = target_day - now_jst.weekday()
        if days_ahead <= 0:
            days_ahead += 7

        hour, minute = map(int, target.arrival_time.split(":")[:2])
        arrival = now_jst.replace(hour=hour, minute=minute, second=0, microsecond=0)
        arrival += timedelta(days=days_ahead)

        logger.debug(f"Calculated arrival time: {arrival} (JST)")
        return arrival
