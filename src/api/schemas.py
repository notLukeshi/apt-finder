from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AddressResponse(BaseModel):
    address_text: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DistanceResponse(BaseModel):
    target_id: int
    target_name: str
    distance_km: Optional[float] = None
    time_minutes: int
    time_transit_walk_minutes: Optional[int] = None   # WALK + TRANSIT
    time_transit_bike_minutes: Optional[int] = None   # BICYCLE + TRANSIT
    time_bike_minutes: Optional[int] = None           # BICYCLE only
    selected_mode: Optional[str] = None  # 'transit_walk', 'transit_bike', or 'bike'


class ApartmentResponse(BaseModel):
    id: int
    external_id: Optional[str] = None
    name: str
    price: float
    website_id: int
    website_name: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    address: Optional[AddressResponse] = None
    distances: list[DistanceResponse] = Field(default_factory=list)


class ApartmentListResponse(BaseModel):
    apartments: list[ApartmentResponse]
    total: int


class WebsiteResponse(BaseModel):
    id: int
    name: str
    base_url: str
    is_active: bool


class TargetResponse(BaseModel):
    id: int
    name: str
    address: str
    arrival_time: Optional[str] = None
    arrival_day: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class StatsResponse(BaseModel):
    total_apartments: int
    avg_price: float
    best_commute: Optional[int] = None
    websites_count: int
