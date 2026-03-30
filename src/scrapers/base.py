import time
import logging
from abc import ABC, abstractmethod
from typing import Iterator, Optional

import requests
from requests.exceptions import HTTPError, Timeout, ConnectionError
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from requests.adapters import HTTPAdapter

from src.models import Apartment

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for website scrapers."""

    name: str = "base"
    base_url: str = ""
    delay: float = 2.0 

    def __init__(self, website_id: int):
        self.website_id = website_id
        self.session = requests.Session()

        # pool_connections: number of hosts to cache
        # pool_maxsize: number of simultaneous connections to keep in the pool
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
    def fetch(self, url: str) -> BeautifulSoup:
        """Fetch and parse a URL with retry logic."""
        logger.debug(f"Fetching: {url}")
        
        # NOTE: In multi-threaded mode, every thread will sleep for 1 second.
        # This acts as a natural rate-limiter for the server.
        time.sleep(self.delay)
        
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def scrape_all(
        self, start_page: Optional[int] = None, end_page: Optional[int] = None
    ) -> Iterator[Apartment]:
        """Scrape pages and yield apartments.
        
        Args:
            start_page: First page to scrape (default: 1)
            end_page: Last page to scrape (default: None = scrape until no more results)
        """
        page = start_page or 1
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        if end_page:
            logger.info(f"Scraping pages {page} to {end_page}")
        else:
            logger.info(f"Scraping all pages starting from {page}")
        
        while True:
            url = self.get_page_url(page)
            logger.info(f"Scraping page {page}: {url}")

            try:
                soup = self.fetch(url)
                apartments = list(self.scrape_page(soup))
                consecutive_errors = 0  # Reset on success

                if not apartments:
                    logger.info(f"No more apartments found on page {page}. Stopping.")
                    break

                for apt in apartments:
                    yield apt

                page += 1
                
                # Stop if we've reached the end page
                if end_page and page > end_page:
                    logger.info(f"Reached end page {end_page}. Stopping.")
                    break

            except RetryError as e:
                consecutive_errors += 1
                original_exc = e.last_attempt.exception() if e.last_attempt else None
                original_error = original_exc if isinstance(original_exc, Exception) else e
                self._handle_error(page, original_error, consecutive_errors)
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}). Stopping scraper.")
                    break
                    
                # Incremental backoff before trying next page
                wait_time = min(60, 5 * (2 ** consecutive_errors))
                logger.info(f"Waiting {wait_time}s before trying next page...")
                time.sleep(wait_time)
                page += 1  # Skip problematic page and continue
                
            except Exception as e:
                consecutive_errors += 1
                self._handle_error(page, e, consecutive_errors)
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}). Stopping scraper.")
                    break
                page += 1
    
    def _handle_error(self, page: int, error: Exception, error_count: int) -> None:
        """Log detailed error information based on error type."""
        error_type = type(error).__name__
        
        if isinstance(error, Timeout):
            logger.error(f"Page {page}: TIMEOUT - Server took too long to respond. Error #{error_count}")
        elif isinstance(error, HTTPError):
            status_code = error.response.status_code if error.response is not None else 'unknown'
            if status_code == 429:
                logger.error(f"Page {page}: RATE LIMITED (429) - Too many requests. Error #{error_count}")
            elif status_code == 503:
                logger.error(f"Page {page}: SERVER UNAVAILABLE (503) - Server overloaded. Error #{error_count}")
            elif status_code == 500:
                logger.error(f"Page {page}: SERVER ERROR (500) - Internal server error. Error #{error_count}")
            elif status_code == 403:
                logger.error(f"Page {page}: FORBIDDEN (403) - Access denied. Error #{error_count}")
            elif status_code == 404:
                logger.error(f"Page {page}: NOT FOUND (404) - Page doesn't exist. Error #{error_count}")
            else:
                logger.error(f"Page {page}: HTTP ERROR ({status_code}) - {error}. Error #{error_count}")
        elif isinstance(error, ConnectionError):
            logger.error(f"Page {page}: CONNECTION ERROR - Network issue. Error #{error_count}")
        else:
            logger.error(f"Page {page}: {error_type} - {error}. Error #{error_count}")

    @abstractmethod
    def get_page_url(self, page: int) -> str:
        """Get URL for a specific page number."""
        pass

    @abstractmethod
    def scrape_page(self, soup: BeautifulSoup) -> Iterator[Apartment]:
        """Parse a page and yield apartment objects."""
        pass

    @abstractmethod
    def get_address(self, apt_url: str) -> Optional[str]:
        """Get address from apartment detail page (if needed)."""
        pass
