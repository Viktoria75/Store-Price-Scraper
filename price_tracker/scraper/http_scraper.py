"""HTTP scraper using aiohttp and BeautifulSoup."""

from typing import Optional
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from lxml import etree

from price_tracker.scraper.base import BaseScraper, ScraperError


class HttpScraper(BaseScraper):
    """Scraper that uses plain HTTP requests - fast but doesn't handle JS."""

    DEFAULT_HEADERS: dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(
        self,
        timeout: int = 30,
        headers: Optional[dict[str, str]] = None,
    ):
        self.timeout = timeout
        self.headers = headers or self.DEFAULT_HEADERS.copy()

    async def fetch_page(self, url: str, retries: int = 3) -> str:
        """Download HTML from URL with automatic retry on failure."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        last_error = None
        
        for attempt in range(retries):
            try:
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector,
                    headers=self.headers,
                ) as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise ScraperError(
                                f"HTTP {response.status}: Failed to fetch page",
                                url=url,
                            )
                        return await response.text()
            except aiohttp.ClientError as e:
                last_error = e
                if attempt < retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise ScraperError(f"Network error: {str(e)}", url=url, cause=e) from e
            except asyncio.TimeoutError as e:
                last_error = e
                if attempt < retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise ScraperError(
                    f"Request timeout after {self.timeout}s", url=url, cause=e
                ) from e
        
        raise ScraperError(f"Failed after {retries} attempts", url=url, cause=last_error)

    def extract_element_text(
        self, html: str, selector: str, selector_type: str
    ) -> Optional[str]:
        """Find element by selector and return its text."""
        try:
            if selector_type == "xpath":
                return self._extract_with_xpath(html, selector)
            return self._extract_with_css(html, selector)
        except Exception:
            return None

    def _extract_with_css(self, html: str, selector: str) -> Optional[str]:
        """Use BeautifulSoup to find element by CSS selector."""
        soup = BeautifulSoup(html, "lxml")
        element = soup.select_one(selector)
        if element:
            return element.get_text(strip=True)
        return None

    def _extract_with_xpath(self, html: str, xpath: str) -> Optional[str]:
        """Use lxml to find element by XPath."""
        tree = etree.HTML(html)
        if tree is None:
            return None
        elements = tree.xpath(xpath)
        if elements:
            if isinstance(elements[0], str):
                return elements[0].strip()
            if hasattr(elements[0], "text") and elements[0].text:
                return elements[0].text.strip()
            if hasattr(elements[0], "text_content"):
                return elements[0].text_content().strip()
        return None

    async def test_selector(
        self, url: str, selector: str, selector_type: str = "css"
    ) -> tuple[bool, Optional[str], Optional[float]]:
        """Try selector on a page and return (success, raw_text, parsed_price)."""
        try:
            html = await self.fetch_page(url)
            text = self.extract_element_text(html, selector, selector_type)
            if text:
                price = self.parse_price(text)
                return True, text, price
            return False, None, None
        except ScraperError:
            return False, None, None

    async def get_page_title(self, url: str) -> Optional[str]:
        """Fetch page and return the <title> tag content."""
        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("title")
            if title_tag:
                return title_tag.get_text(strip=True)
            return None
        except ScraperError:
            return None
