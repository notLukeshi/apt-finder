import re
import logging
from typing import Iterator, Optional

from bs4 import BeautifulSoup

from src.models import Apartment, Address
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry

logger = logging.getLogger(__name__)


@ScraperRegistry.register("WeeklyMonthly")
class WeeklyMonthlyScraper(BaseScraper):
    """Scraper for weeklyandmonthly.com"""

    name = "WeeklyMonthly"
    base_url = "https://weeklyandmonthly.com/srch/pref_13/"

    def get_page_url(self, page: int) -> str:
        return f"{self.base_url}?limit=30&sort=2&page={page}"

    def scrape_page(self, soup: BeautifulSoup) -> Iterator[Apartment]:
        """Parse listing page and yield apartments."""
        items = soup.select("li.roomitemlist__item")

        for item in items:
            try:
                apt = self._parse_listing(item)
                if apt:
                    yield apt
            except Exception as e:
                logger.warning(f"Failed to parse listing: {e}")

    def _parse_listing(self, item) -> Optional[Apartment]:
        """Parse a single listing item."""
        # Get name from h3.item__head-name > a
        name_elem = item.select_one("h3.item__head-name a.item-inner")
        if not name_elem:
            return None
        name = name_elem.get_text(strip=True)

        # Extract external ID from URL (id=XXXXXX)
        href = name_elem.get("href", "")
        external_id = None
        match = re.search(r"id=(\d+)", href)
        if match:
            external_id = match.group(1)

        # Get URL
        url = href if href else None

        # Get price - first plan's price (ロングプラン is cheapest)
        price = self._extract_price(item)
        if not price:
            return None

        # Get address from table
        address_text = self._extract_address(item)

        # Extract preview image URL
        image_url = self._extract_image(item)

        apt = Apartment(
            name=name,
            price=price,
            website_id=self.website_id,
            external_id=external_id,
            url=url,
            image_url=image_url,
        )

        if address_text:
            apt.address = Address(address_text=address_text)

        return apt

    def _extract_price(self, item) -> Optional[float]:
        """Extract monthly price from listing (first/cheapest plan)."""
        # Get all price cells and take the first one (ロングプラン - cheapest)
        price_elem = item.select_one("td.r-price__num__total-month-amount strong")
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_text = re.sub(r"[^\d]", "", price_text)
            if price_text:
                return float(price_text)
        return None

    def _extract_address(self, item) -> Optional[str]:
        """Extract address from listing table."""
        # Address is in table.item__text-details > td.address-data
        addr_elem = item.select_one("td.address-data")
        if addr_elem:
            return addr_elem.get_text(strip=True)
        return None

    def _extract_image(self, item) -> Optional[str]:
        """Extract preview image URL from listing."""
        img_elem = item.select_one("div.item__img img")
        if img_elem:
            return img_elem.get("src") or img_elem.get("data-src")
        return None

    def get_address(self, apt_url: str) -> Optional[str]:
        """Not needed for WeeklyMonthly - address is on listing page."""
        return None
