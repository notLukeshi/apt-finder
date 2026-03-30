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
    
    def is_available(self) -> bool:
        """Check if OTP server is running and ready."""
        if self._available is not None:
            return self._available
        
        try:
            # Test GraphQL endpoint with a simple query
            test_query = '{ __typename }'
            response = requests.post(
                self.graphql_endpoint,
                json={"query": test_query},
                timeout=5
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
    
    def _build_graphql_query(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        modes: list,
        date_time: datetime,
        arrive_by: bool = False,
    ) -> dict:
        """Build GraphQL query for OTP 2.x routing."""
        # Format modes for GraphQL
        transport_modes = []
        for mode in modes:
            if mode == "WALK":
                transport_modes.append('{mode: WALK}')
            elif mode == "BICYCLE":
                transport_modes.append('{mode: BICYCLE}')
            elif mode == "TRANSIT":
                transport_modes.append('{mode: TRANSIT}')
        
        modes_str = ", ".join(transport_modes)
        
        query = f'''
        {{
          plan(
            from: {{lat: {from_lat}, lon: {from_lon}}}
            to: {{lat: {to_lat}, lon: {to_lon}}}
            date: "{date_time.strftime('%Y-%m-%d')}"
            time: "{date_time.strftime('%H:%M')}"
            arriveBy: {str(arrive_by).lower()}
            transportModes: [{modes_str}]
            numItineraries: 3
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
          }}
        }}
        '''
        return {"query": query}
    
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
        """
        Get a route from OTP using GraphQL API.
        
        Args:
            from_lat, from_lon: Origin coordinates
            to_lat, to_lon: Destination coordinates
            mode: Mode string, e.g., "WALK,TRANSIT", "BICYCLE,TRANSIT", "BICYCLE"
            arrive_by: Desired arrival time (for reverse routing)
            depart_at: Desired departure time
            
        Returns:
            OTPRouteResult or None if routing failed
        """
        if not self.is_available():
            return None
        
        # Parse mode string into list
        modes = [m.strip() for m in mode.split(",")]
        
        # Determine date/time in Japan timezone (JST)
        if arrive_by:
            query_time = arrive_by
            is_arrive_by = True
        elif depart_at:
            query_time = depart_at
            is_arrive_by = False
        else:
            # Default: next Monday at 9:00 AM JST (arrive by)
            now_jst = datetime.now(JST)
            days_until_monday = (7 - now_jst.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            query_time = now_jst.replace(hour=9, minute=0, second=0, microsecond=0)
            query_time += timedelta(days=days_until_monday)
            is_arrive_by = True
            logger.debug(f"Using JST time: {query_time.strftime('%Y-%m-%d %H:%M')} JST")
        
        try:
            logger.debug(f"OTP GraphQL request: {mode} from ({from_lat:.4f},{from_lon:.4f}) to ({to_lat:.4f},{to_lon:.4f})")
            
            query_body = self._build_graphql_query(
                from_lat, from_lon, to_lat, to_lon,
                modes, query_time, is_arrive_by
            )
            
            response = requests.post(
                self.graphql_endpoint,
                json=query_body,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Check for GraphQL errors
            if "errors" in data:
                error_msgs = [e.get("message", "Unknown") for e in data["errors"]]
                logger.warning(f"OTP GraphQL error for {mode}: {error_msgs}")
                return None
            
            plan = data.get("data", {}).get("plan")
            if not plan:
                logger.warning(f"No plan in OTP response for {mode}")
                return None
            
            itineraries = plan.get("itineraries", [])
            if not itineraries:
                logger.warning(f"No itineraries found for {mode}")
                return None
            
            # Get the best (first) itinerary
            itinerary = itineraries[0]
            
            duration_seconds = itinerary.get("duration", 0)
            duration_minutes = duration_seconds // 60
            
            # Calculate total distance from legs
            legs = itinerary.get("legs", [])
            total_distance_m = sum(leg.get("distance", 0) for leg in legs)
            
            # Count transfers (number of transit legs - 1, minimum 0)
            transit_legs = [leg for leg in legs if leg.get("transitLeg", False)]
            transfers = max(0, len(transit_legs) - 1)
            
            # Get walk distance
            walk_distance_m = itinerary.get("walkDistance", 0)
            
            result = OTPRouteResult(
                duration_minutes=duration_minutes,
                distance_km=total_distance_m / 1000 if total_distance_m else None,
                transfers=transfers,
                walk_distance_m=walk_distance_m,
                start_time=itinerary.get("startTime"),
                end_time=itinerary.get("endTime"),
            )
            
            logger.debug(f"OTP result for {mode}: {duration_minutes} min, {transfers} transfers")
            return result
            
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
