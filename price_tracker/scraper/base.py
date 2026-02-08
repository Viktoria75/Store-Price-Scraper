"""Base scraper for extracting prices from web pages."""

from abc import ABC, abstractmethod
from typing import Optional
import re


class BaseScraper(ABC):
    """Base class that all scrapers inherit from."""

    # Regex patterns to find prices in different formats
    PRICE_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"([\d\s,.]+)\s*(?:лв\.?|лева|BGN)", re.IGNORECASE),  # Bulgarian lev
        re.compile(r"€\s*([\d\s,.]+)", re.IGNORECASE),  # Euro prefix
        re.compile(r"([\d\s,.]+)\s*€", re.IGNORECASE),  # Euro suffix
        re.compile(r"([\d\s,.]+)\s*EUR", re.IGNORECASE),
        re.compile(r"\$\s*([\d\s,.]+)", re.IGNORECASE),  # USD prefix
        re.compile(r"([\d\s,.]+)\s*(?:USD|\$)", re.IGNORECASE),  # USD suffix
        re.compile(r"([\d,.]+)"),  # Just numbers as fallback
    ]

    @abstractmethod
    async def fetch_page(self, url: str) -> str:
        """Download the HTML from a URL."""

    @abstractmethod
    def extract_element_text(
        self, html: str, selector: str, selector_type: str
    ) -> Optional[str]:
        """Find an element and return its text content."""

    def parse_price(self, text: str) -> Optional[float]:
        """Try to extract a number from text like '99.99 лв' or '$49.99'."""
        if not text:
            return None

        cleaned = text.strip()

        for pattern in self.PRICE_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                price_str = match.group(1).replace(" ", "")

                # Figure out if comma is decimal or thousands separator
                import re as regex
                if regex.match(r"^\d{1,3}(,\d{3})+(\.\d+)?$", price_str):
                    # US format: 1,234.56
                    price_str = price_str.replace(",", "")
                else:
                    # European format: 1.234,56
                    price_str = price_str.replace(",", ".")

                # Handle multiple dots like 1.234.56
                parts = price_str.split(".")
                if len(parts) > 2:
                    price_str = "".join(parts[:-1]) + "." + parts[-1]

                try:
                    return float(price_str)
                except ValueError:
                    continue

        return None

    async def get_price(
        self, url: str, selector: str, selector_type: str = "css"
    ) -> Optional[float]:
        """Fetch a page and extract the price using the given selector."""
        try:
            html = await self.fetch_page(url)
            text = self.extract_element_text(html, selector, selector_type)
            if text:
                return self.parse_price(text)
            return None
        except Exception:
            return None


class ScraperError(Exception):
    """Raised when scraping fails."""

    def __init__(self, message: str, url: str = "", cause: Optional[Exception] = None):
        super().__init__(message)
        self.url = url
        self.cause = cause
