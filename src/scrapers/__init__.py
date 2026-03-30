from .base import BaseScraper
from .registry import ScraperRegistry
from .tokyo_monthly import TokyoMonthlyScraper
from .union_monthly import UnionMonthlyScraper
from .weekly_monthly import WeeklyMonthlyScraper
from .good_monthly import GoodMonthlyScraper
from .shintoshin import ShintoshinScraper

__all__ = ["BaseScraper", "ScraperRegistry", "TokyoMonthlyScraper", "UnionMonthlyScraper", "WeeklyMonthlyScraper", "GoodMonthlyScraper", "ShintoshinScraper"]
