import re
import logging
from typing import Iterator, Optional

from bs4 import BeautifulSoup

from src.models import Apartment, Address
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry

logger = logging.getLogger(__name__)


@ScraperRegistry.register("Shintoshin")
class ShintoshinScraper(BaseScraper):
    """Scraper for monthly-shintoshin.com."""

    name = "Shintoshin"
    base_url = "https://www.monthly-shintoshin.com/search/list.html"

    def __init__(self, website_id: int):
        super().__init__(website_id)
        # All results are on one page with location codes in URL
        self.search_url = (
            "https://www.monthly-shintoshin.com/search/list.html?"
            "jyuusyo_cd_list[]=13121&jyuusyo_cd_list[]=13118&jyuusyo_cd_list[]=13119&"
            "jyuusyo_cd_list[]=13123&jyuusyo_cd_list[]=13111&jyuusyo_cd_list[]=13117&"
            "jyuusyo_cd_list[]=13108&jyuusyo_cd_list[]=13109&jyuusyo_cd_list[]=13113&"
            "jyuusyo_cd_list[]=13104&jyuusyo_cd_list[]=13115&jyuusyo_cd_list[]=13107&"
            "jyuusyo_cd_list[]=13112&jyuusyo_cd_list[]=13106&jyuusyo_cd_list[]=13224&"
            "jyuusyo_cd_list[]=13101&jyuusyo_cd_list[]=13116&jyuusyo_cd_list[]=13114&"
            "jyuusyo_cd_list[]=13120&jyuusyo_cd_list[]=13206&jyuusyo_cd_list[]=13105&"
            "jyuusyo_cd_list[]=13203&jyuusyo_cd_list[]=13110"
        )

    def get_page_url(self, page: int) -> str:
        """Get URL for a specific page number."""
        # All results are on one page
        return self.search_url

    def scrape_all(self, start_page: Optional[int] = None, end_page: Optional[int] = None) -> Iterator[Apartment]:
        """Override to scrape single page with all results."""
        logger.info(f"Scraping Shintoshin (single page with all results)")

        try:
            soup = self.fetch(self.search_url)
            apartments = list(self.scrape_page(soup))

            if not apartments:
                logger.info("No apartments found on Shintoshin.")
                return

            for apt in apartments:
                yield apt

        except Exception as e:
            logger.error(f"Error scraping Shintoshin: {e}")

    def scrape_page(self, soup: BeautifulSoup) -> Iterator[Apartment]:
        """Parse listing page and yield apartments."""
        items = soup.select("div.box")

        for item in items:
            try:
                apt = self._parse_listing(item)
                if apt:
                    yield apt
            except Exception as e:
                logger.warning(f"Failed to parse listing: {e}")

    def _parse_listing(self, item) -> Optional[Apartment]:
        """Parse a single listing item."""
        # Get name from .tit p a
        name_elem = item.select_one("div.tit p a")
        if not name_elem:
            return None
        name = name_elem.get_text(strip=True)

        # Extract external ID from URL
        external_id = None
        href = name_elem.get("href", "")
        match = re.search(r"bukken_no=(\d+)", href)
        if match:
            external_id = match.group(1)

        # Get URL
        if href.startswith("/"):
            url = f"https://www.monthly-shintoshin.com{href}"
        else:
            url = href if href else None

        # Get price - detect format and calculate monthly
        price = self._extract_price(item)
        if not price:
            return None

        # Get address
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
        """Extract monthly price from listing.

        Two formats supported:
        1. Daily rate (table.type02): Take ミドル (middle) rate and multiply by 30
        2. Monthly rate (table.type03): Take 賃料 directly
        """
        # Check for daily rate format (table.type02)
        daily_table = item.select_one("table.type02")
        if daily_table:
            return self._extract_daily_price(daily_table)

        # Check for monthly rate format (table.type03)
        monthly_table = item.select_one("table.type03")
        if monthly_table:
            return self._extract_monthly_price(monthly_table)

        return None

    def _extract_daily_price(self, table) -> Optional[float]:
        """Extract price from daily rate table (type02).

        Table structure:
        - Header row with: スーパーショート, ショート, ミドル, ロング
        - Data row with: 賃料, daily rates for each category

        We take the ミドル (middle) rate and multiply by 30.
        """
        rows = table.select("tr")
        if len(rows) < 2:
            return None

        header_row = rows[0]
        data_row = rows[1]

        # Find index of ミドル column
        headers = header_row.select("th")
        middle_index = None
        for i, th in enumerate(headers):
            if "ミドル" in th.get_text():
                middle_index = i
                break

        if middle_index is None:
            return None

        # Get price cells from data row (skip first th which is 賃料 label)
        price_cells = data_row.select("td")
        if len(price_cells) < middle_index:
            return None

        # Get the ミドル price cell
        middle_cell = price_cells[middle_index - 1]  # -1 because first th is label, not a price cell
        text = middle_cell.get_text(strip=True)

        # Extract daily rate - format like "１９００円/日・２１００円/日" or "2400円/日"
        # Take the first number found
        match = re.search(r"[\d,]+", text.replace("０", "0").replace("１", "1").replace("２", "2")
                                                  .replace("３", "3").replace("４", "4").replace("５", "5")
                                                  .replace("６", "6").replace("７", "7").replace("８", "8")
                                                  .replace("９", "9"))
        if match:
            daily_rate = float(match.group().replace(",", ""))
            return daily_rate * 30

        return None

    def _extract_monthly_price(self, table) -> Optional[float]:
        """Extract price from monthly rate table (type03).

        Table structure:
        - Header row with: 賃料, 管理費, クリーニング代
        - Data row with: monthly prices

        We take the 賃料 (rent) value directly.
        """
        rows = table.select("tr")
        if len(rows) < 2:
            return None

        data_row = rows[1]
        price_cells = data_row.select("td")
        if not price_cells:
            return None

        # First cell is 賃料
        rent_text = price_cells[0].get_text(strip=True)

        # Extract monthly rate - format like "４００００円/月"
        match = re.search(r"[\d,]+", rent_text.replace("０", "0").replace("１", "1").replace("２", "2")
                                                     .replace("３", "3").replace("４", "4").replace("５", "5")
                                                     .replace("６", "6").replace("７", "7").replace("８", "8")
                                                     .replace("９", "9"))
        if match:
            return float(match.group().replace(",", ""))

        return None

    def _extract_address(self, item) -> Optional[str]:
        """Extract address from listing."""
        # Address is in table.type01, row with th "所在地"
        table = item.select_one("table.type01")
        if not table:
            return None

        for row in table.select("tr"):
            th = row.select_one("th")
            if th and "所在地" in th.get_text():
                td = row.select_one("td")
                if td:
                    return td.get_text(strip=True)
        return None

    def _extract_image(self, item) -> Optional[str]:
        """Extract preview image URL from listing."""
        img_elem = item.select_one("div.photo div img")
        if img_elem:
            src = img_elem.get("src")
            if src:
                if src.startswith("/"):
                    return f"https://www.monthly-shintoshin.com{src}"
                return src
        return None

    def get_address(self, apt_url: str) -> Optional[str]:
        """Not needed for Shintoshin - address is on listing page."""
        return None
