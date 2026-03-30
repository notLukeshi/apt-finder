import re
import logging
from typing import Iterator, Optional

from bs4 import BeautifulSoup

from src.models import Apartment, Address
from src.scrapers.base import BaseScraper
from src.scrapers.registry import ScraperRegistry

logger = logging.getLogger(__name__)


@ScraperRegistry.register("GoodMonthly")
class GoodMonthlyScraper(BaseScraper):
    """Scraper for good-monthly.com using POST requests."""

    name = "GoodMonthly"
    base_url = "https://www.good-monthly.com/tokyo/search/list_pref.html"

    def get_page_url(self, page: int) -> str:
        # Not used for POST-based scraper, but required by base class
        return self.base_url

    def _build_payload(self, page: int) -> str:
        """Build the POST payload for a specific page."""
        return (
            f"disp_count_upper=30&sort=1&disp_count_upper=30&priod_time_to_short=S"
            f"&web_yachin_int_ss_to=&web_yachin_int_s_month_from=1"
            f"&web_yachin_int_s_month_to=150000&web_nyukyo_ninzu=&walk="
            f"&good_web_hirosa_from=&good_web_hirosa_to=&chiku_ym="
            f"&this_page_no={page}&cmd=SELECT_PAGE&disp_count=30&hidden_sort=1"
            f"&random_number=726&hidden_priod_time_to_short=S"
            f"&hidden_web_yachin_int_ss_from=&hidden_web_yachin_int_ss_to="
            f"&hidden_web_yachin_int_s_month_from=1&hidden_web_yachin_int_s_month_to=150000"
            f"&hidden_web_nyukyo_ninzu=&hidden_new_web_bed_type1=&hidden_new_web_bed_type2="
            f"&hidden_new_web_bed_type3=&hidden_new_web_bed_type4=&hidden_walk="
            f"&hidden_good_web_madori_1R=&hidden_good_web_madori_1K=&hidden_good_web_madori_1DK="
            f"&hidden_good_web_madori_1LDK=&hidden_good_web_madori_1SLDK=&hidden_good_web_madori_2K="
            f"&hidden_good_web_madori_2DK=&hidden_good_web_madori_2LDK=&hidden_good_web_madori_2SLDK="
            f"&hidden_good_web_hirosa_from=&hidden_good_web_hirosa_to=&hidden_chiku_ym="
            f"&hidden_jyouken_campaign=&hidden_jyouken_guest_house=&hidden_jyouken1="
            f"&hidden_setsubi_autoLock=&hidden_setsubi_air_conditioner=&hidden_setsubi_tv="
            f"&hidden_setsubi_microwave_oven=&hidden_setsubi_icebox=&hidden_setsubi_closet="
            f"&hidden_setsubi_bath_toilet_separate=&hidden_setsubi_washroom_separate="
            f"&hidden_setsubi_flooring=&hidden_setsubi_washing_machine=&hidden_setsubi_vacuum_cleaner="
            f"&hidden_setsubi_delivery_to_home_box=&hidden_jyouken10=&hidden_hoshounin_flag="
            f"&hidden_web_pay3=&hidden_jyouken16=&hidden_setsubi_ih_cooking_heater="
            f"&hidden_setsubi_gas_conlo=&hidden_setsubi_addition_heat=&hidden_setsubi_bathroom_dryer="
            f"&hidden_setsubi_wash_toilet=&hidden_setsubi_elevator=&hidden_jyouken4="
            f"&hidden_jyouken6=&hidden_jyouken17=&hidden_jyouken8=&hidden_telework="
        )

    def fetch_post(self, page: int) -> BeautifulSoup:
        """Fetch page using POST request."""
        import time
        logger.debug(f"Fetching page {page} via POST")
        time.sleep(self.delay)
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = self._build_payload(page)
        
        response = self.session.post(self.base_url, headers=headers, data=payload, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def scrape_all(self, start_page: Optional[int] = None, end_page: Optional[int] = None) -> Iterator[Apartment]:
        """Override scrape_all to use POST requests."""
        page = start_page or 1
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        if end_page:
            logger.info(f"Scraping pages {page} to {end_page}")
        else:
            logger.info(f"Scraping all pages starting from {page}")
        
        while True:
            logger.info(f"Scraping page {page}")

            try:
                soup = self.fetch_post(page)
                apartments = list(self.scrape_page(soup))
                consecutive_errors = 0

                if not apartments:
                    logger.info(f"No more apartments found on page {page}. Stopping.")
                    break

                for apt in apartments:
                    yield apt

                page += 1
                
                if end_page and page > end_page:
                    logger.info(f"Reached end page {end_page}. Stopping.")
                    break

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Page {page}: Error - {e}. Error #{consecutive_errors}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}). Stopping scraper.")
                    break
                page += 1

    def scrape_page(self, soup: BeautifulSoup) -> Iterator[Apartment]:
        """Parse listing page and yield apartments."""
        items = soup.select("section.default")

        for item in items:
            try:
                apt = self._parse_listing(item)
                if apt:
                    yield apt
            except Exception as e:
                logger.warning(f"Failed to parse listing: {e}")

    def _parse_listing(self, item) -> Optional[Apartment]:
        """Parse a single listing item."""
        # Get name from h3 > a
        name_elem = item.select_one("div.titArea h3 a")
        if not name_elem:
            return None
        name = name_elem.get_text(strip=True)

        # Extract external ID from checkbox or URL
        external_id = None
        checkbox = item.select_one("input[name='bukken_no_list[]']")
        if checkbox:
            external_id = checkbox.get("value")
        else:
            href = name_elem.get("href", "")
            match = re.search(r"bukken_no=(\d+)", href)
            if match:
                external_id = match.group(1)

        # Get URL
        href = name_elem.get("href", "")
        if href.startswith("/"):
            url = f"https://www.good-monthly.com{href}"
        else:
            url = href if href else None

        # Get price - ショート (short-term) daily rate × 30 for monthly estimate
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
        """Extract monthly price from listing."""
        # Look for the monthly price in the table (賃料 column, /月 value)
        price_cells = item.select("div.priceArea table td")
        for cell in price_cells:
            text = cell.get_text()
            # Look for monthly price pattern like "49,500円/月"
            match = re.search(r"([\d,]+)円/月", text)
            if match:
                price_text = match.group(1).replace(",", "")
                return float(price_text)
        return None

    def _extract_address(self, item) -> Optional[str]:
        """Extract address from listing."""
        # Address is in dl > dt "所在地" > dd
        for dl in item.select("div.detailTxt dl"):
            dt = dl.select_one("dt")
            if dt and "所在地" in dt.get_text():
                dd = dl.select_one("dd")
                if dd:
                    return dd.get_text(strip=True)
        return None

    def _extract_image(self, item) -> Optional[str]:
        """Extract preview image URL from listing."""
        img_elem = item.select_one("ul.detailPhoto li img")
        if img_elem:
            src = img_elem.get("src")
            if src:
                if src.startswith("/"):
                    return f"https://www.good-monthly.com{src}"
                return src
        return None

    def get_address(self, apt_url: str) -> Optional[str]:
        """Not needed for GoodMonthly - address is on listing page."""
        return None
