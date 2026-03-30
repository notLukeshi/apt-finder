from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Website:
    name: str
    base_url: str
    is_active: bool = True
    id: Optional[int] = None


@dataclass
class Address:
    address_text: str
    apartment_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    id: Optional[int] = None


@dataclass
class Apartment:
    name: str
    price: float
    website_id: int
    external_id: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    address: Optional[Address] = None
    id: Optional[int] = None


@dataclass
class Target:
    name: str
    address: str
    arrival_time: Optional[str] = None
    arrival_day: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    id: Optional[int] = None


@dataclass
class Distance:
    apartment_id: int
    target_id: int
    time_minutes: int
    distance_km: Optional[float] = None
    time_transit_walk_minutes: Optional[int] = None   # WALK + TRANSIT
    time_transit_bike_minutes: Optional[int] = None   # BICYCLE + TRANSIT
    time_bike_minutes: Optional[int] = None           # BICYCLE only
    selected_mode: Optional[str] = None  # 'transit_walk', 'transit_bike', or 'bike'
    id: Optional[int] = None


@dataclass
class DistanceSummary:
    target_id: int
    target_name: str
    distance_km: Optional[float]
    time_minutes: int
    time_transit_walk_minutes: Optional[int] = None
    time_transit_bike_minutes: Optional[int] = None
    time_bike_minutes: Optional[int] = None
    selected_mode: Optional[str] = None
