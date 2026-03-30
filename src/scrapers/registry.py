from typing import Type, Optional

from src.scrapers.base import BaseScraper


class ScraperRegistry:
    """Registry for website scrapers."""

    _scrapers: dict[str, Type[BaseScraper]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a scraper class."""
        def decorator(scraper_cls: Type[BaseScraper]):
            cls._scrapers[name.lower()] = scraper_cls
            return scraper_cls
        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseScraper]]:
        """Get scraper class by name."""
        return cls._scrapers.get(name.lower())

    @classmethod
    def get_all(cls) -> dict[str, Type[BaseScraper]]:
        """Get all registered scrapers."""
        return cls._scrapers.copy()
