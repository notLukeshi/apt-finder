#!/usr/bin/env python3
"""
Apartment Scraper - Main Entry Point

Scrapes Japanese housing websites and calculates commute distances.
"""
import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.config import load_config
from src.database import Repository
from src.distance import DistanceCalculator
from src.filters import PriceFilter
from src.models import Website, Target
from src.scrapers import ScraperRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_database(config, repo: Repository) -> dict[str, int]:
    """Setup websites and targets in database, return website IDs."""
    website_ids = {}

    for web_cfg in config.websites:
        if web_cfg.is_active:
            website = Website(
                name=web_cfg.name,
                base_url=web_cfg.base_url,
                is_active=web_cfg.is_active,
            )
            website_ids[web_cfg.name] = repo.upsert_website(website)
            logger.info(f"Registered website: {web_cfg.name}")

    for target_cfg in config.targets:
        target = Target(
            name=target_cfg.name,
            address=target_cfg.address,
            arrival_time=target_cfg.arrival_time,
            arrival_day=target_cfg.arrival_day,
        )
        repo.upsert_target(target)
        logger.info(f"Registered target: {target_cfg.name}")

    return website_ids


def scrape_apartments(
    config,
    repo: Repository,
    website_ids: dict[str, int],
    website_filter: str | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
):
    """Scrape apartments from all active websites."""
    price_filter = PriceFilter(config.price_range.min, config.price_range.max)

    for web_cfg in config.websites:
        if not web_cfg.is_active:
            continue
        if website_filter and web_cfg.name.lower() != website_filter.lower():
            continue

        scraper_cls = ScraperRegistry.get(web_cfg.name)
        if not scraper_cls:
            logger.warning(f"No scraper found for: {web_cfg.name}")
            continue

        website_id = website_ids[web_cfg.name]
        scraper = scraper_cls(website_id)
        logger.info(f"Starting scrape: {web_cfg.name}")

        count = 0
        for apt in scraper.scrape_all(start_page=start_page, end_page=end_page):
            if not price_filter.is_in_range(apt.price):
                logger.debug(f"Skipping {apt.name}: price {apt.price} out of range")
                continue

            apt_id = repo.upsert_apartment(apt)
            count += 1
            logger.info(f"Saved: {apt.name} (¥{apt.price:,.0f})")

        logger.info(f"Scraped {count} apartments from {web_cfg.name}")


def geocode_addresses(repo: Repository, calculator: DistanceCalculator):
    """Geocode all apartment addresses that don't have coordinates."""
    # Geocode targets first so any limited provider budget is spent on the shared commute anchors.
    targets = repo.get_all_targets()
    for target in targets:
        if not target.id or (target.latitude and target.longitude):
            continue
        if not calculator.can_geocode():
            logger.warning("Geocoding budget exhausted before all targets were processed")
            return
        coords = calculator.geocode(target.address)
        if coords:
            repo.update_target_coordinates(target.id, coords[0], coords[1])
            logger.info(f"Geocoded target: {target.name} -> ({coords[0]:.4f}, {coords[1]:.4f})")

    apartments = repo.get_apartments_without_coordinates()
    logger.info(f"Geocoding {len(apartments)} apartments without coordinates")

    for apt in apartments:
        if not apt.address or not apt.id:
            continue
        if not calculator.can_geocode():
            logger.warning("Geocoding budget exhausted while processing apartments")
            break

        coords = calculator.geocode(apt.address.address_text)
        if coords:
            repo.update_address_coordinates(apt.id, coords[0], coords[1])
            logger.info(f"Geocoded: {apt.name[:40]}... -> ({coords[0]:.4f}, {coords[1]:.4f})")


def calculate_distances(
    repo: Repository,
    calculator: DistanceCalculator,
    incomplete_only: bool = False,
    workers: int = 1,
):
    """Calculate distances for all apartments to all targets.

    Args:
        incomplete_only: If True, only calculate for apartments with incomplete distance data
        workers: Number of parallel workers for distance calculation (1 = sequential)
    """
    targets = repo.get_all_targets()

    for target in targets:
        if not target.id:
            continue

        if incomplete_only:
            apartments = repo.get_apartments_with_incomplete_distance(target.id)
            logger.info(f"Calculating distances to {target.name} for {len(apartments)} apartments with incomplete data")
        else:
            apartments = repo.get_apartments_without_distance(target.id)
            logger.info(f"Calculating distances to {target.name} for {len(apartments)} apartments")

        apartments = [apt for apt in apartments if apt.address]
        if not apartments:
            continue

        if workers <= 1:
            _calculate_distances_sequential(repo, calculator, apartments, target)
        else:
            _calculate_distances_parallel(repo, calculator, apartments, target, workers)


def _calculate_distances_sequential(repo, calculator, apartments, target):
    """Sequential distance calculation."""
    for apt in apartments:
        _process_single_distance(repo, calculator, apt, target)


def _calculate_distances_parallel(repo, calculator, apartments, target, workers):
    """Parallel distance calculation using ThreadPoolExecutor."""
    completed = 0
    total = len(apartments)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_process_single_distance, repo, calculator, apt, target): apt
            for apt in apartments
        }
        for future in as_completed(futures):
            apt = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error calculating distance for {apt.name[:30]}...: {e}")
            completed += 1
            if completed % 50 == 0 or completed == total:
                logger.info(f"Progress: {completed}/{total} apartments processed for {target.name}")


def _process_single_distance(repo, calculator, apt, target):
    """Process distance calculation for a single apartment-target pair."""
    distance = calculator.calculate(apt, target)
    if distance:
        repo.save_distance(distance)
        # Also update coordinates if they were geocoded during calculation
        if apt.id and apt.address:
            coords = calculator._get_coords_for_address(apt.address)
            if coords and not apt.address.latitude:
                repo.update_address_coordinates(apt.id, coords[0], coords[1])

        logger.info(
            f"Distance: {apt.name} -> {target.name}: "
            f"{distance.time_minutes}min ({distance.selected_mode})"
        )


def main():
    parser = argparse.ArgumentParser(description="Apartment Scraper")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--db", default="apartments.db", help="Database file path")
    parser.add_argument("--scrape-only", action="store_true", help="Only scrape, skip distances")
    parser.add_argument("--calculate-only", action="store_true", help="Only calculate distances (for incomplete data)")
    parser.add_argument("--recalculate-all", action="store_true", help="Recalculate distances for all apartments")
    parser.add_argument("--geocode-only", action="store_true", help="Only geocode addresses")
    parser.add_argument("--website", help="Scrape only this website")
    parser.add_argument("--start-page", type=int, help="Start scraping from this page (default: 1)")
    parser.add_argument("--end-page", type=int, help="Stop scraping at this page (default: all)")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers for distance calculation (default: 1)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(config_path)
    repo = Repository(args.db)
    website_ids = setup_database(config, repo)

    try:
        calculator = DistanceCalculator(config.distance)
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)

    if args.geocode_only:
        geocode_addresses(repo, calculator)
        logger.info("Done!")
        return

    if not args.calculate_only and not args.recalculate_all:
        scrape_apartments(
            config, repo, website_ids, args.website,
            start_page=args.start_page, end_page=args.end_page
        )

    if not args.scrape_only:
        # Geocode addresses first, then calculate distances
        geocode_addresses(repo, calculator)
        
        if args.recalculate_all:
            # Recalculate for all apartments
            targets = repo.get_all_targets()
            for target in targets:
                if not target.id:
                    continue
                apartments = repo.get_all_apartments_for_distance_recalc(target.id)
                apartments = [apt for apt in apartments if apt.address]
                logger.info(f"Recalculating distances to {target.name} for ALL {len(apartments)} apartments")

                if args.workers <= 1:
                    for apt in apartments:
                        _process_single_distance(repo, calculator, apt, target)
                else:
                    _calculate_distances_parallel(repo, calculator, apartments, target, args.workers)
        else:
            # Normal calculation (only for incomplete data when --calculate-only)
            incomplete_only = args.calculate_only
            calculate_distances(repo, calculator, incomplete_only=incomplete_only, workers=args.workers)

    logger.info("Done!")


if __name__ == "__main__":
    main()
