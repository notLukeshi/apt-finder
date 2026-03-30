from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Optional

from src.models import Apartment, Address, Target, Distance, DistanceSummary, Website


SCHEMA_PATH = Path(__file__).with_name("schema.sql")
LEGACY_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema.sql"


def _load_schema_sql() -> str:
    for candidate in (SCHEMA_PATH, LEGACY_SCHEMA_PATH):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH} or {LEGACY_SCHEMA_PATH}")


class Repository:
    def __init__(self, db_path: Path | str = "apartments.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with schema."""
        with self._connection() as conn:
            conn.executescript(_load_schema_sql())

    @contextmanager
    def _connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # Website operations
    def upsert_website(self, website: Website) -> int:
        """Insert or update website, return id."""
        with self._connection() as conn:
            cursor = conn.execute(
                """INSERT INTO websites (name, base_url, is_active)
                   VALUES (?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                     base_url = excluded.base_url,
                     is_active = excluded.is_active
                   RETURNING id""",
                (website.name, website.base_url, website.is_active),
            )
            return cursor.fetchone()[0]

    def get_website_by_name(self, name: str) -> Optional[Website]:
        """Get website by name."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM websites WHERE name = ?", (name,)
            ).fetchone()
            if row:
                return Website(
                    id=row["id"],
                    name=row["name"],
                    base_url=row["base_url"],
                    is_active=bool(row["is_active"]),
                )
        return None

    def get_website_by_id(self, website_id: int) -> Optional[Website]:
        """Get website by id."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM websites WHERE id = ?", (website_id,)).fetchone()
            if row:
                return Website(
                    id=row["id"],
                    name=row["name"],
                    base_url=row["base_url"],
                    is_active=bool(row["is_active"]),
                )
        return None

    # Target operations
    def upsert_target(self, target: Target) -> int:
        """Insert or update target, return id."""
        with self._connection() as conn:
            cursor = conn.execute(
                """INSERT INTO targets (name, address, arrival_time, arrival_day, latitude, longitude)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name, address) DO UPDATE SET
                     arrival_time = excluded.arrival_time,
                     arrival_day = excluded.arrival_day
                   RETURNING id""",
                (target.name, target.address, target.arrival_time, target.arrival_day,
                 target.latitude, target.longitude),
            )
            return cursor.fetchone()[0]

    def get_all_targets(self) -> list[Target]:
        """Get all targets."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM targets").fetchall()
            return [
                Target(
                    id=row["id"],
                    name=row["name"],
                    address=row["address"],
                    arrival_time=row["arrival_time"],
                    arrival_day=row["arrival_day"],
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                )
                for row in rows
            ]

    def get_target_by_id(self, target_id: int) -> Optional[Target]:
        """Get target by id."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM targets WHERE id = ?", (target_id,)).fetchone()
            if row:
                return Target(
                    id=row["id"],
                    name=row["name"],
                    address=row["address"],
                    arrival_time=row["arrival_time"],
                    arrival_day=row["arrival_day"],
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                )
        return None

    # Apartment operations
    def upsert_apartment(self, apt: Apartment) -> int:
        """Insert or update apartment, return id."""
        with self._connection() as conn:
            cursor = conn.execute(
                """INSERT INTO apartments (external_id, name, price, website_id, url, image_url)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(external_id, website_id) DO UPDATE SET
                     name = excluded.name,
                     price = excluded.price,
                     url = excluded.url,
                     image_url = excluded.image_url,
                     last_updated = CURRENT_TIMESTAMP
                   RETURNING id""",
                (apt.external_id, apt.name, apt.price, apt.website_id, apt.url, apt.image_url),
            )
            apt_id = cursor.fetchone()[0]

            if apt.address:
                self._upsert_address(conn, apt_id, apt.address)

            return apt_id

    def _upsert_address(self, conn, apartment_id: int, address: Address) -> None:
        """Insert or update address for apartment."""
        conn.execute(
            """INSERT INTO addresses (apartment_id, address_text, latitude, longitude)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(apartment_id) DO UPDATE SET
                 address_text = excluded.address_text,
                 latitude = excluded.latitude,
                 longitude = excluded.longitude""",
            (apartment_id, address.address_text, address.latitude, address.longitude),
        )

    def get_apartments_in_price_range(self, min_price: float, max_price: float) -> list[Apartment]:
        """Get apartments within price range."""
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT a.id, a.external_id, a.name, a.price, a.website_id, a.url, a.image_url,
                          addr.address_text, addr.latitude, addr.longitude
                   FROM apartments a
                   LEFT JOIN addresses addr ON a.id = addr.apartment_id
                   WHERE a.price >= ? AND a.price <= ?""",
                (min_price, max_price),
            ).fetchall()
            return [self._row_to_apartment(row) for row in rows]

    def get_apartments_in_price_range_for_websites(
        self,
        min_price: float,
        max_price: float,
        website_ids: Optional[list[int]] = None,
    ) -> list[Apartment]:
        """Get apartments within price range and optional website filter."""
        if website_ids is not None and len(website_ids) == 0:
            return []

        query = (
            """SELECT a.id, a.external_id, a.name, a.price, a.website_id, a.url, a.image_url,
                      addr.address_text, addr.latitude, addr.longitude
               FROM apartments a
               LEFT JOIN addresses addr ON a.id = addr.apartment_id
               WHERE a.price >= ? AND a.price <= ?"""
        )
        params: list[object] = [min_price, max_price]

        if website_ids is not None:
            placeholders = ",".join("?" for _ in website_ids)
            query += f" AND a.website_id IN ({placeholders})"
            params.extend(website_ids)

        with self._connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_apartment(row) for row in rows]

    def get_apartment_by_id(self, apartment_id: int) -> Optional[Apartment]:
        """Get a single apartment by id."""
        with self._connection() as conn:
            row = conn.execute(
                """SELECT a.id, a.external_id, a.name, a.price, a.website_id, a.url, a.image_url,
                          addr.address_text, addr.latitude, addr.longitude
                   FROM apartments a
                   LEFT JOIN addresses addr ON a.id = addr.apartment_id
                   WHERE a.id = ?""",
                (apartment_id,),
            ).fetchone()
            return self._row_to_apartment(row) if row else None

    def get_apartments_without_distance(self, target_id: int) -> list[Apartment]:
        """Get apartments that don't have distance calculated for a target."""
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT a.id, a.external_id, a.name, a.price, a.website_id, a.url, a.image_url,
                          addr.address_text, addr.latitude, addr.longitude
                   FROM apartments a
                   LEFT JOIN addresses addr ON a.id = addr.apartment_id
                   WHERE a.id NOT IN (
                     SELECT apartment_id FROM distances WHERE target_id = ?
                   )
                   AND addr.address_text IS NOT NULL""",
                (target_id,),
            ).fetchall()
            return [self._row_to_apartment(row) for row in rows]

    def get_apartments_with_incomplete_distance(self, target_id: int) -> list[Apartment]:
        """Get apartments that have incomplete distance data (missing some time values)."""
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT a.id, a.external_id, a.name, a.price, a.website_id, a.url, a.image_url,
                          addr.address_text, addr.latitude, addr.longitude
                   FROM apartments a
                   LEFT JOIN addresses addr ON a.id = addr.apartment_id
                   LEFT JOIN distances d ON a.id = d.apartment_id AND d.target_id = ?
                   WHERE addr.address_text IS NOT NULL
                   AND (d.id IS NULL 
                        OR d.time_transit_walk_minutes IS NULL
                        OR d.time_transit_bike_minutes IS NULL
                        OR d.time_bike_minutes IS NULL)""",
                (target_id,),
            ).fetchall()
            return [self._row_to_apartment(row) for row in rows]

    def get_all_apartments_for_distance_recalc(self, target_id: int) -> list[Apartment]:
        """Get all apartments with addresses for distance recalculation."""
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT a.id, a.external_id, a.name, a.price, a.website_id, a.url, a.image_url,
                          addr.address_text, addr.latitude, addr.longitude
                   FROM apartments a
                   LEFT JOIN addresses addr ON a.id = addr.apartment_id
                   WHERE addr.address_text IS NOT NULL""",
            ).fetchall()
            return [self._row_to_apartment(row) for row in rows]

    def _row_to_apartment(self, row) -> Apartment:
        """Convert database row to Apartment object."""
        address = None
        if row["address_text"]:
            address = Address(
                address_text=row["address_text"],
                latitude=row["latitude"],
                longitude=row["longitude"],
            )
        return Apartment(
            id=row["id"],
            external_id=row["external_id"],
            name=row["name"],
            price=row["price"],
            website_id=row["website_id"],
            url=row["url"],
            image_url=row["image_url"] if "image_url" in row.keys() else None,
            address=address,
        )

    # Distance operations
    def save_distance(self, distance: Distance) -> int:
        """Save distance calculation."""
        with self._connection() as conn:
            cursor = conn.execute(
                """INSERT INTO distances 
                   (apartment_id, target_id, distance_km, time_minutes, 
                    time_transit_walk_minutes, time_transit_bike_minutes, 
                    time_bike_minutes, selected_mode)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(apartment_id, target_id) DO UPDATE SET
                     distance_km = excluded.distance_km,
                     time_minutes = excluded.time_minutes,
                     time_transit_walk_minutes = excluded.time_transit_walk_minutes,
                     time_transit_bike_minutes = excluded.time_transit_bike_minutes,
                     time_bike_minutes = excluded.time_bike_minutes,
                     selected_mode = excluded.selected_mode,
                     calculated_at = CURRENT_TIMESTAMP
                   RETURNING id""",
                (distance.apartment_id, distance.target_id, distance.distance_km,
                 distance.time_minutes, distance.time_transit_walk_minutes,
                 distance.time_transit_bike_minutes, distance.time_bike_minutes, 
                 distance.selected_mode),
            )
            return cursor.fetchone()[0]

    def update_address_coordinates(self, apartment_id: int, lat: float, lng: float) -> None:
        """Update latitude/longitude for an apartment's address."""
        with self._connection() as conn:
            conn.execute(
                """UPDATE addresses 
                   SET latitude = ?, longitude = ?, geocoded_at = CURRENT_TIMESTAMP
                   WHERE apartment_id = ?""",
                (lat, lng, apartment_id),
            )

    def update_target_coordinates(self, target_id: int, lat: float, lng: float) -> None:
        """Update latitude/longitude for a target."""
        with self._connection() as conn:
            conn.execute(
                """UPDATE targets SET latitude = ?, longitude = ? WHERE id = ?""",
                (lat, lng, target_id),
            )

    def get_apartments_without_coordinates(self) -> list[Apartment]:
        """Get apartments that don't have geocoded coordinates."""
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT a.id, a.external_id, a.name, a.price, a.website_id, a.url, a.image_url,
                          addr.address_text, addr.latitude, addr.longitude
                   FROM apartments a
                   LEFT JOIN addresses addr ON a.id = addr.apartment_id
                   WHERE addr.address_text IS NOT NULL 
                   AND (addr.latitude IS NULL OR addr.longitude IS NULL)""",
            ).fetchall()
            return [self._row_to_apartment(row) for row in rows]

    def get_all_websites(self) -> list[Website]:
        """Get all websites."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM websites").fetchall()
            return [
                Website(
                    id=row["id"],
                    name=row["name"],
                    base_url=row["base_url"],
                    is_active=bool(row["is_active"]),
                )
                for row in rows
            ]

    def get_distances_for_apartment(
        self,
        apartment_id: int,
        target_id: Optional[int] = None,
    ) -> list[DistanceSummary]:
        """Get commute distances for an apartment."""
        query = (
            """SELECT d.target_id, t.name as target_name, d.distance_km, d.time_minutes,
                      d.time_transit_walk_minutes, d.time_transit_bike_minutes,
                      d.time_bike_minutes, d.selected_mode
               FROM distances d
               JOIN targets t ON d.target_id = t.id
               WHERE d.apartment_id = ?"""
        )
        params: list[object] = [apartment_id]

        if target_id is not None:
            query += " AND d.target_id = ?"
            params.append(target_id)

        query += " ORDER BY d.time_minutes ASC, t.name ASC"

        with self._connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                DistanceSummary(
                    target_id=row["target_id"],
                    target_name=row["target_name"],
                    distance_km=row["distance_km"],
                    time_minutes=row["time_minutes"],
                    time_transit_walk_minutes=row["time_transit_walk_minutes"],
                    time_transit_bike_minutes=row["time_transit_bike_minutes"],
                    time_bike_minutes=row["time_bike_minutes"],
                    selected_mode=row["selected_mode"],
                )
                for row in rows
            ]

    def get_total_apartments(self) -> int:
        """Get total apartment count."""
        with self._connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM apartments").fetchone()
            return int(row[0] if row else 0)

    def get_average_apartment_price(self) -> float:
        """Get average apartment price."""
        with self._connection() as conn:
            row = conn.execute("SELECT AVG(price) FROM apartments").fetchone()
            return float(row[0] or 0.0)

    def get_best_commute_minutes(self) -> Optional[int]:
        """Get the shortest commute time currently stored."""
        with self._connection() as conn:
            row = conn.execute("SELECT MIN(time_minutes) FROM distances").fetchone()
            if not row or row[0] is None:
                return None
            return int(row[0])
