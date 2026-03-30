import re
import logging
from typing import Iterator, Optional
from concurrent.futures import ThreadPoolExecutor  # Add this import

from bs4 import BeautifulSoup
from src.models import Apartment, Address
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry

logger = logging.getLogger(__name__)

@ScraperRegistry.register("TokyoMonthly")
class TokyoMonthlyScraper(BaseScraper):
    name = "TokyoMonthly"
    base_url = "https://tokyomonthly.com/properties/"

    def get_page_url(self, page: int) -> str:
        return f"{self.base_url}?page={page}"

    def scrape_page(self, soup: BeautifulSoup) -> Iterator[Apartment]:
        """Parse listing page and yield apartments in parallel."""
        items = soup.select("li.roomitemlist__item")
        
        # 1. Parse basic info from the list (No network calls here)
        initial_apartments = []
        for item in items:
            try:
                apt = self._parse_listing(item)
                if apt:
                    initial_apartments.append(apt)
            except Exception as e:
                logger.warning(f"Failed to parse listing: {e}")

        # 2. Use a ThreadPool to fetch detail pages (addresses) in parallel
        with ThreadPoolExecutor(max_workers=20) as executor:
            yield from executor.map(self._fetch_address_for_apt, initial_apartments)

    def _fetch_address_for_apt(self, apt: Apartment) -> Apartment:
        """Helper to fetch address for an apartment object."""
        if apt.url:
            address_text = self.get_address(apt.url)
            if address_text:
                apt.address = Address(address_text=address_text)
        return apt

    def _parse_listing(self, item) -> Optional[Apartment]:
        """Parse a single listing item (WITHOUT the address network call)."""
        name_elem = item.select_one("p.item__text-name")
        if not name_elem:
            return None
        name = name_elem.get_text(strip=True)

        fav_btn = item.select_one(".jq-toggleFavorite")
        external_id = fav_btn.get("data-room-id") if fav_btn else None

        if not external_id:
            link = item.select_one("a.item-inner")
            if link:
                href = link.get("href", "")
                match = re.search(r"id=(\d+)", href)
                if match:
                    external_id = match.group(1)

        link = item.select_one("a.item-inner")
        url = link.get("href") if link else None

        price = self._extract_price(item)
        if not price:
            return None

        # Extract preview image URL
        image_url = self._extract_image(item)

        # Return apartment without address (address will be added in parallel)
        return Apartment(
            name=name,
            price=price,
            website_id=self.website_id,
            external_id=external_id,
            url=url,
            image_url=image_url,
        )

    def _extract_price(self, item) -> Optional[float]:
        price_elem = item.select_one("td.r-price__num__total-month-amount strong")
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_text = re.sub(r"[^\d]", "", price_text)
            if price_text:
                return float(price_text)
        return None

    def _extract_image(self, item) -> Optional[str]:
        """Extract preview image URL from listing."""
        img_elem = item.select_one("div.item__img img")
        if img_elem:
            # Try src first, then data-src for lazy-loaded images
            return img_elem.get("src") or img_elem.get("data-src")
        return None

    def get_address(self, apt_url: str) -> Optional[str]:
        try:
            soup = self.fetch(apt_url)
            table = soup.select_one("table.room__outline-table")
            if table:
                for row in table.select("tr"):
                    th = row.select_one("th")
                    if th and "所在地" in th.get_text():
                        td = row.select_one("td")
                        if td:
                            return td.get_text(strip=True)
        except Exception as e:
            logger.warning(f"Failed to get address from {apt_url}: {e}")
        return None