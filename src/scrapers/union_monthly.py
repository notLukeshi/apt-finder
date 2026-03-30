import re
import logging
from typing import Iterator, Optional

from bs4 import BeautifulSoup

from src.models import Apartment, Address
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry

logger = logging.getLogger(__name__)


@ScraperRegistry.register("UnionMonthly")
class UnionMonthlyScraper(BaseScraper):
    """Scraper for unionmonthly.jp"""

    name = "UnionMonthly"
    base_url = "https://www.unionmonthly.jp/tokyo/room/"

    def get_page_url(self, page: int) -> str:
        return f"{self.base_url}?p={page}"

    def scrape_page(self, soup: BeautifulSoup) -> Iterator[Apartment]:
        """Parse listing page and yield apartments."""
        items = soup.select("div.list_item")

        for item in items:
            try:
                apt = self._parse_listing(item)
                if apt:
                    yield apt
            except Exception as e:
                logger.warning(f"Failed to parse listing: {e}")

    def _parse_listing(self, item) -> Optional[Apartment]:
        """Parse a single listing item."""
        # Get external ID from data attribute
        external_id = item.get("data-troom_id")

        # Get name
        name_elem = item.select_one("h2.gArticle_name")
        if not name_elem:
            return None
        name = name_elem.get_text(strip=True)

        # Get URL
        detail_link = item.select_one("a.u-btn01")
        url = None
        if detail_link:
            href = detail_link.get("href", "")
            if href.startswith("/"):
                url = f"https://www.unionmonthly.jp{href}"
            else:
                url = href

        # Get price
        price = self._extract_price(item)
        if not price:
            return None

        # Get address - UnionMonthly has it directly in the listing
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
        """Extract monthly price from listing."""
        price_elem = item.select_one("p.gArticle_price b")
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_text = re.sub(r"[^\d]", "", price_text)
            if price_text:
                return float(price_text)
        return None

    def _extract_address(self, item) -> Optional[str]:
        """Extract address from listing."""
        # Address is in the info list with marker icon
        info_items = item.select("ul.gArticle_infoList li")
        for li in info_items:
            icon = li.select_one("i.icon-marker")
            if icon:
                # Get text content, excluding icon
                text = li.get_text(strip=True)
                return text

        # Fallback: check hidden form field
        form = item.select_one("form[id^='form_contact']")
        if form:
            addr_input = form.select_one("input[name='room_address']")
            if addr_input:
                return addr_input.get("value")

        return None

    def _extract_image(self, item) -> Optional[str]:
        """Extract preview image URL from listing."""
        # UnionMonthly uses slick slider with images
        img_elem = item.select_one("div.gArticle_image img")
        if img_elem:
            # Try data-original-src first (original image URL), then src
            img_url = img_elem.get("data-original-src") or img_elem.get("src")
            if img_url:
                # Handle relative URLs
                if img_url.startswith("/"):
                    return f"https://www.unionmonthly.jp{img_url}"
                return img_url
        return None

    def get_address(self, apt_url: str) -> Optional[str]:
        """Not needed for UnionMonthly - address is on listing page."""
        return None
