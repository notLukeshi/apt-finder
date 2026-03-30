from src.database import Repository
from src.models import Address, Apartment, Distance, Target, Website


def test_repository_round_trip(repo: Repository):
    website_id = repo.upsert_website(Website(name="TokyoMonthly", base_url="https://example.com"))
    target_id = repo.upsert_target(
        Target(
            name="Office",
            address="Tokyo Station, Tokyo, Japan",
            arrival_time="09:00",
            arrival_day="Monday",
            latitude=35.681236,
            longitude=139.767125,
        )
    )

    apartment_id = repo.upsert_apartment(
        Apartment(
            name="Test Apartment",
            price=90000,
            website_id=website_id,
            external_id="apt-001",
            url="https://example.com/apartment/1",
            image_url="https://example.com/image.jpg",
            address=Address(address_text="Tokyo, Japan", latitude=35.68, longitude=139.77),
        )
    )

    repo.save_distance(
        Distance(
            apartment_id=apartment_id,
            target_id=target_id,
            time_minutes=25,
            distance_km=3.2,
            selected_mode="bike",
        )
    )

    apartment = repo.get_apartment_by_id(apartment_id)
    assert apartment is not None
    assert apartment.name == "Test Apartment"

    website = repo.get_website_by_id(website_id)
    assert website is not None
    assert website.name == "TokyoMonthly"

    target = repo.get_target_by_id(target_id)
    assert target is not None
    assert target.name == "Office"

    filtered = repo.get_apartments_in_price_range_for_websites(0, 100000, [website_id])
    assert len(filtered) == 1

    distances = repo.get_distances_for_apartment(apartment_id)
    assert len(distances) == 1
    assert distances[0].time_minutes == 25
    assert repo.get_total_apartments() == 1
    assert repo.get_average_apartment_price() == 90000.0
    assert repo.get_best_commute_minutes() == 25
