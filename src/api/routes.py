from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from src.database import Repository
from src.api.schemas import (
    ApartmentResponse, ApartmentListResponse, AddressResponse, DistanceResponse,
    WebsiteResponse, TargetResponse, StatsResponse
)
from src.models import DistanceSummary, Website

router = APIRouter(prefix="/api")


def get_repo() -> Repository:
    return Repository("apartments.db")


def _website_to_response(website: Website) -> WebsiteResponse:
    return WebsiteResponse(
        id=website.id or 0,
        name=website.name,
        base_url=website.base_url,
        is_active=website.is_active,
    )


def _distance_to_response(distance: DistanceSummary) -> DistanceResponse:
    return DistanceResponse(
        target_id=distance.target_id,
        target_name=distance.target_name,
        distance_km=distance.distance_km,
        time_minutes=distance.time_minutes,
        time_transit_walk_minutes=distance.time_transit_walk_minutes,
        time_transit_bike_minutes=distance.time_transit_bike_minutes,
        time_bike_minutes=distance.time_bike_minutes,
        selected_mode=distance.selected_mode,
    )


def _resolve_website_ids(repo: Repository, website_filter: Optional[str]) -> Optional[list[int]]:
    if website_filter is None:
        return None

    if website_filter == "__none__":
        return []

    selected_names = {
        name.strip().lower()
        for name in website_filter.split(",")
        if name.strip()
    }
    website_ids = [
        website.id
        for website in repo.get_all_websites()
        if website.id is not None and website.name.lower() in selected_names
    ]
    return website_ids


def _build_apartment_response(
    repo: Repository,
    apartment,
    target_id: Optional[int],
    min_time: Optional[int],
    max_time: Optional[int],
) -> Optional[ApartmentResponse]:
    website = repo.get_website_by_id(apartment.website_id)
    website_name = website.name if website else "Unknown"

    distances = repo.get_distances_for_apartment(apartment.id, target_id=target_id) if apartment.id else []
    if min_time is not None:
        distances = [distance for distance in distances if distance.time_minutes >= min_time]
    if max_time is not None:
        distances = [distance for distance in distances if distance.time_minutes <= max_time]
        if not distances:
            return None

    address_resp = None
    if apartment.address:
        address_resp = AddressResponse(
            address_text=apartment.address.address_text,
            latitude=apartment.address.latitude,
            longitude=apartment.address.longitude,
        )

    return ApartmentResponse(
        id=apartment.id,
        external_id=apartment.external_id,
        name=apartment.name,
        price=apartment.price,
        website_id=apartment.website_id,
        website_name=website_name,
        url=apartment.url,
        image_url=apartment.image_url,
        address=address_resp,
        distances=[_distance_to_response(distance) for distance in distances],
    )


@router.get("/apartments", response_model=ApartmentListResponse)
def list_apartments(
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    website: Optional[str] = Query(None),
    target_id: Optional[int] = Query(None),
    min_time: Optional[int] = Query(None),
    max_time: Optional[int] = Query(None),
):
    """List apartments with optional filters."""
    repo = get_repo()

    min_p = 0 if min_price is None else min_price
    max_p = 999999999 if max_price is None else max_price
    website_ids = _resolve_website_ids(repo, website)

    apartments = repo.get_apartments_in_price_range_for_websites(min_p, max_p, website_ids)

    results = []
    for apt in apartments:
        response = _build_apartment_response(repo, apt, target_id, min_time, max_time)
        if response:
            results.append(response)

    return ApartmentListResponse(apartments=results, total=len(results))


@router.get("/apartments/{apartment_id}", response_model=ApartmentResponse)
def get_apartment(apartment_id: int):
    """Get single apartment details."""
    repo = get_repo()
    apt = repo.get_apartment_by_id(apartment_id)
    
    if not apt:
        raise HTTPException(status_code=404, detail="Apartment not found")

    response = _build_apartment_response(repo, apt, None, None, None)
    if response is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return response


@router.get("/websites", response_model=list[WebsiteResponse])
def list_websites():
    """List all scraped websites."""
    repo = get_repo()
    return [_website_to_response(website) for website in repo.get_all_websites()]


@router.get("/targets", response_model=list[TargetResponse])
def list_targets():
    """List all configured targets."""
    repo = get_repo()
    targets = repo.get_all_targets()
    return [TargetResponse(
        id=t.id,
        name=t.name,
        address=t.address,
        arrival_time=t.arrival_time,
        arrival_day=t.arrival_day,
        latitude=t.latitude,
        longitude=t.longitude,
    ) for t in targets if t.id]


@router.get("/stats", response_model=StatsResponse)
def get_stats():
    """Get dashboard statistics."""
    repo = get_repo()

    total = repo.get_total_apartments()
    avg_price = repo.get_average_apartment_price()
    best_commute = repo.get_best_commute_minutes()
    websites = repo.get_all_websites()
    
    return StatsResponse(
        total_apartments=total,
        avg_price=round(avg_price, 0),
        best_commute=best_commute,
        websites_count=len(websites),
    )
