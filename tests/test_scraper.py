"""Tests for web scrapers."""

import pytest
from price_tracker.scraper.base import BaseScraper
from price_tracker.scraper.http_scraper import HttpScraper


class TestHttpScraper:
    """Test cases for HTTP scraper."""

    def test_parse_price_bulgarian_lev(self) -> None:
        """Test parsing Bulgarian lev prices."""
        scraper = HttpScraper()

        # Various formats
        assert scraper.parse_price("99.99 лв.") == 99.99
        assert scraper.parse_price("99,99 лв") == 99.99
        assert scraper.parse_price("1 234,56 лв.") == 1234.56
        assert scraper.parse_price("100 лева") == 100.0
        assert scraper.parse_price("50.00 BGN") == 50.0

    def test_parse_price_euro(self) -> None:
        """Test parsing Euro prices."""
        scraper = HttpScraper()

        assert scraper.parse_price("€99.99") == 99.99
        assert scraper.parse_price("99,99 €") == 99.99
        assert scraper.parse_price("100.00 EUR") == 100.0

    def test_parse_price_usd(self) -> None:
        """Test parsing USD prices."""
        scraper = HttpScraper()

        assert scraper.parse_price("$99.99") == 99.99
        assert scraper.parse_price("99.99 USD") == 99.99
        assert scraper.parse_price("$1,234.56") == 1234.56

    def test_parse_price_invalid(self) -> None:
        """Test parsing invalid price strings."""
        scraper = HttpScraper()

        assert scraper.parse_price("") is None
        assert scraper.parse_price("Not a price") is None
        assert scraper.parse_price(None) is None  # type: ignore

    def test_extract_with_css(self, sample_html: str) -> None:
        """Test CSS selector extraction."""
        scraper = HttpScraper()

        # Test class selector
        result = scraper.extract_element_text(sample_html, ".price", "css")
        assert result == "99.99 лв."

        # Test ID selector
        result = scraper.extract_element_text(sample_html, "#alt-price", "css")
        assert result == "€89.99"

        # Test attribute selector
        result = scraper.extract_element_text(sample_html, "[data-price]", "css")
        assert result == "$79.99"

    def test_extract_with_xpath(self, sample_html: str) -> None:
        """Test XPath extraction."""
        scraper = HttpScraper()

        # Test XPath
        result = scraper.extract_element_text(
            sample_html,
            "//span[@class='price']",
            "xpath",
        )
        assert result == "99.99 лв."

        # Test another XPath
        result = scraper.extract_element_text(
            sample_html,
            "//div[@id='alt-price']",
            "xpath",
        )
        assert result == "€89.99"

    def test_extract_nonexistent_element(self, sample_html: str) -> None:
        """Test extraction of non-existent elements."""
        scraper = HttpScraper()

        result = scraper.extract_element_text(sample_html, ".nonexistent", "css")
        assert result is None

        result = scraper.extract_element_text(
            sample_html,
            "//div[@class='nonexistent']",
            "xpath",
        )
        assert result is None

    def test_full_price_extraction(self, sample_html: str) -> None:
        """Test full price extraction workflow."""
        scraper = HttpScraper()

        # Extract and parse
        text = scraper.extract_element_text(sample_html, ".price", "css")
        assert text is not None
        price = scraper.parse_price(text)
        assert price == 99.99


class TestBaseScraper:
    """Test cases for base scraper functionality."""

    def test_price_patterns(self) -> None:
        """Test that price patterns are properly defined."""
        patterns = BaseScraper.PRICE_PATTERNS
        assert len(patterns) > 0

        # Test Bulgarian pattern exists
        test_text = "99.99 лв."
        matched = False
        for pattern in patterns:
            if pattern.search(test_text):
                matched = True
                break
        assert matched
