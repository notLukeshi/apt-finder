"""
OpenTripPlanner (OTP) Client for Japan public transit routing.
Uses OTP 2.x GraphQL API for routing queries.
"""
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from zoneinfo import ZoneInfo

# Japan Standard Time
JST = ZoneInfo("Asia/Tokyo")

# After this many consecutive failures for a (target, mode) pair,
# the mode is skipped for the remainder of that target's run.
SKIP_MODE_FAILURE_THRESHOLD = 20

logger = logging.getLogger(__name__)


@dataclass
class OTPRouteResult:
    """Result from an OTP routing query."""
    duration_minutes: int
    distance_km: Optional[float] = None
    transfers: int = 0
    walk_distance_m: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class OTPClient:
    """Client for OpenTripPlanner 2.x GraphQL API."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self.graphql_endpoint = f"{self.base_url}/otp/gtfs/v1"
        self._available = None
        # Persistent session for HTTP keep-alive connection reuse.
        self._session = requests.Session()
        # Per-target consecutive failure counters for adaptive mode skipping.
        # Key: (target_lat, target_lon, mode_string), Value: failure count.
        self._failure_counts: dict[tuple[float, float, str], int] = {}

    def is_available(self) -> bool:
        """Check if OTP server is running and ready."""
        if self._available is not None:
            return self._available

        try:
            test_query = '{ __typename }'
            response = self._session.post(
                self.graphql_endpoint,
                json={"query": test_query},
                timeout=5,
            )
            self._available = response.status_code == 200
            if self._available:
                logger.info("OTP server is available (GraphQL API)")
            return self._available
        except requests.RequestException:
            logger.warning("OTP server is not available")
            self._available = False
            return False

    def reset_availability_cache(self):
        """Reset the availability cache to force a new check."""
        self._available = None

    def _should_skip_mode(self, target_lat: float, target_lon: float, mode: str) -> bool:
        """Check if a mode has failed too many times for this target and should be skipped."""
        key = (round(target_lat, 4), round(target_lon, 4), mode)
        return self._failure_counts.get(key, 0) >= SKIP_MODE_FAILURE_THRESHOLD

    def _record_failure(self, target_lat: float, target_lon: float, mode: str) -> None:
        """Record a consecutive failure for a (target, mode) pair."""
        key = (round(target_lat, 4), round(target_lon, 4), mode)
        self._failure_counts[key] = self._failure_counts.get(key, 0) + 1

    def _record_success(self, target_lat: float, target_lon: float, mode: str) -> None:
        """Reset failure counter on success."""
        key = (round(target_lat, 4), round(target_lon, 4), mode)
        self._failure_counts.pop(key, None)

    def _build_batched_query(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        modes_list: list[list[str]],
        date_time: datetime,
        arrive_by: bool,
    ) -> str:
        """Build a single GraphQL query with multiple plan requests using aliases.

        Each entry in modes_list becomes a separate aliased plan field,
        allowing OTP to compute all routes in a single HTTP round-trip.
        """
        date_str = date_time.strftime('%Y-%m-%d')
        time_str = date_time.strftime('%H:%M')
        arrive_str = str(arrive_by).lower()

        plan_fields = []
        for alias, modes in modes_list:
            modes_str = ", ".join(f"{{mode: {m}}}" for m in modes)
            plan_fields.append(f"""
            {alias}: plan(
                from: {{lat: {from_lat}, lon: {from_lon}}}
                to: {{lat: {to_lat}, lon: {to_lon}}}
                date: "{date_str}"
                time: "{time_str}"
                arriveBy: {arrive_str}
                transportModes: [{modes_str}]
                numItineraries: 1
            ) {{
                itineraries {{
                    duration
                    startTime
                    endTime
                    walkDistance
                    legs {{
                        mode
                        distance
                        duration
                        transitLeg
                    }}
                }}
            }}""")

        return f"""
        {{
          {" ".join(plan_fields)}
        }}
        """

    def _parse_itinerary(self, itinerary: dict) -> OTPRouteResult:
        """Parse a single OTP itinerary dict into OTPRouteResult."""
        duration_seconds = itinerary.get("duration", 0)
        duration_minutes = duration_seconds // 60

        legs = itinerary.get("legs", [])
        total_distance_m = sum(leg.get("distance", 0) for leg in legs)
        transit_legs = [leg for leg in legs if leg.get("transitLeg", False)]
        transfers = max(0, len(transit_legs) - 1)
        walk_distance_m = itinerary.get("walkDistance", 0)

        return OTPRouteResult(
            duration_minutes=duration_minutes,
            distance_km=total_distance_m / 1000 if total_distance_m else None,
            transfers=transfers,
            walk_distance_m=walk_distance_m,
            start_time=itinerary.get("startTime"),
            end_time=itinerary.get("endTime"),
        )

    def _extract_plan_result(self, data: dict, alias: str) -> Optional[OTPRouteResult]:
        """Extract and parse a single plan result from a batched GraphQL response."""
        plan = data.get("data", {}).get(alias)
        if not plan:
            return None
        itineraries = plan.get("itineraries", [])
        if not itineraries:
            return None
        return self._parse_itinerary(itineraries[0])

    def get_routes_batch(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        arrive_by: Optional[datetime] = None,
    ) -> dict[str, Optional[OTPRouteResult]]:
        """Get all three route types in a single GraphQL request.

        Returns a dict with keys 'walk_transit', 'bike_transit', 'bike_only'.
        Modes that have been skipped due to repeated failures are omitted.
        """
        if not self.is_available():
            return {"walk_transit": None, "bike_transit": None, "bike_only": None}

        # Determine query time
        if arrive_by:
            query_time = arrive_by
            is_arrive_by = True
        else:
            now_jst = datetime.now(JST)
            days_until_monday = (7 - now_jst.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            query_time = now_jst.replace(hour=9, minute=0, second=0, microsecond=0)
            query_time += timedelta(days=days_until_monday)
            is_arrive_by = True

        # Build the list of modes to query, skipping failed ones
        all_modes = [
            ("walk_transit", ["WALK", "TRANSIT"]),
            ("bike_transit", ["BICYCLE", "TRANSIT"]),
            ("bike_only", ["BICYCLE"]),
        ]

        modes_to_query = []
        skipped = []
        for alias, modes in all_modes:
            mode_str = ",".join(modes)
            if self._should_skip_mode(to_lat, to_lon, mode_str):
                skipped.append(alias)
            else:
                modes_to_query.append((alias, modes))

        if not modes_to_query:
            logger.warning("All modes skipped due to repeated failures")
            return {alias: None for alias, _ in all_modes}

        try:
            query = self._build_batched_query(
                from_lat, from_lon, to_lat, to_lon,
                modes_to_query, query_time, is_arrive_by,
            )

            response = self._session.post(
                self.graphql_endpoint,
                json={"query": query},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                error_msgs = [e.get("message", "Unknown") for e in data["errors"]]
                logger.warning(f"OTP GraphQL errors: {error_msgs}")
                # Record failures for all queried modes
                for alias, modes in modes_to_query:
                    self._record_failure(to_lat, to_lon, ",".join(modes))
                return {alias: None for alias, _ in all_modes}

            results = {}
            for alias, modes in modes_to_query:
                mode_str = ",".join(modes)
                result = self._extract_plan_result(data, alias)
                if result:
                    self._record_success(to_lat, to_lon, mode_str)
                else:
                    self._record_failure(to_lat, to_lon, mode_str)
                    logger.warning(f"No itineraries found for {mode_str}")
                results[alias] = result

            # Fill in skipped modes as None
            for alias in skipped:
                results[alias] = None

            # Ensure all keys are present
            for alias, _ in all_modes:
                results.setdefault(alias, None)

            return results

        except requests.Timeout:
            logger.error("OTP batched request timed out")
            for alias, modes in modes_to_query:
                self._record_failure(to_lat, to_lon, ",".join(modes))
            return {alias: None for alias, _ in all_modes}
        except requests.RequestException as e:
            logger.error(f"OTP batched request failed: {e}")
            for alias, modes in modes_to_query:
                self._record_failure(to_lat, to_lon, ",".join(modes))
            return {alias: None for alias, _ in all_modes}
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse OTP batched response: {e}")
            return {alias: None for alias, _ in all_modes}

    # Legacy single-route methods (kept for backward compatibility)
    def get_route(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        mode: str,
        arrive_by: Optional[datetime] = None,
        depart_at: Optional[datetime] = None,
    ) -> Optional[OTPRouteResult]:
        """Get a single route from OTP using GraphQL API (legacy, unbatched)."""
        if not self.is_available():
            return None

        modes = [m.strip() for m in mode.split(",")]

        if arrive_by:
            query_time = arrive_by
            is_arrive_by = True
        elif depart_at:
            query_time = depart_at
            is_arrive_by = False
        else:
            now_jst = datetime.now(JST)
            days_until_monday = (7 - now_jst.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            query_time = now_jst.replace(hour=9, minute=0, second=0, microsecond=0)
            query_time += timedelta(days=days_until_monday)
            is_arrive_by = True

        try:
            query = self._build_batched_query(
                from_lat, from_lon, to_lat, to_lon,
                [("plan", modes)], query_time, is_arrive_by,
            )
            response = self._session.post(
                self.graphql_endpoint,
                json={"query": query},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                error_msgs = [e.get("message", "Unknown") for e in data["errors"]]
                logger.warning(f"OTP GraphQL error for {mode}: {error_msgs}")
                return None

            return self._extract_plan_result(data, "plan")
        except requests.Timeout:
            logger.error(f"OTP request timed out for {mode}")
            return None
        except requests.RequestException as e:
            logger.error(f"OTP request failed for {mode}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse OTP response for {mode}: {e}")
            return None

    def get_walk_transit_route(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        arrive_by: Optional[datetime] = None,
    ) -> Optional[OTPRouteResult]:
        """Get a WALK + TRANSIT route (walk to station, take train)."""
        return self.get_route(
            from_lat, from_lon, to_lat, to_lon,
            mode="WALK,TRANSIT",
            arrive_by=arrive_by,
        )

    def get_bike_transit_route(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        arrive_by: Optional[datetime] = None,
    ) -> Optional[OTPRouteResult]:
        """Get a BICYCLE + TRANSIT route (bike to station, take train)."""
        return self.get_route(
            from_lat, from_lon, to_lat, to_lon,
            mode="BICYCLE,TRANSIT",
            arrive_by=arrive_by,
        )

    def get_bike_only_route(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
    ) -> Optional[OTPRouteResult]:
        """Get a BICYCLE only route (direct cycling)."""
        return self.get_route(
            from_lat, from_lon, to_lat, to_lon,
            mode="BICYCLE",
        )
