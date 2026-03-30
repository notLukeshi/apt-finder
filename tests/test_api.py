from fastapi.testclient import TestClient

from src.api.app import app
from src.api import routes
from src.database import Repository
from src.models import Address, Apartment, Distance, Target, Website


def test_api_smoke(tmp_path, monkeypatch):
    repo = Repository(tmp_path / "apartments.db")
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

    monkeypatch.setattr(routes, "get_repo", lambda: repo)

    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200

    stats = client.get("/api/stats").json()
    assert stats["total_apartments"] == 1
    assert stats["best_commute"] == 25

    apartments = client.get("/api/apartments").json()
    assert apartments["total"] == 1
    assert apartments["apartments"][0]["name"] == "Test Apartment"

    apartment = client.get(f"/api/apartments/{apartment_id}").json()
    assert apartment["id"] == apartment_id
    assert apartment["distances"][0]["time_minutes"] == 25
