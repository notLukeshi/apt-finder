from src.scrapers import ScraperRegistry


def test_known_scrapers_are_registered():
    for name in ["TokyoMonthly", "UnionMonthly", "WeeklyMonthly", "GoodMonthly", "Shintoshin"]:
        assert ScraperRegistry.get(name) is not None
