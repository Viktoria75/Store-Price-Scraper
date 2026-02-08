"""Additional tests for HTTP scraper to increase coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from price_tracker.scraper.http_scraper import HttpScraper
from price_tracker.scraper.base import ScraperError


class TestHttpScraperAdvanced:
    """Extended tests for HttpScraper."""

    def test_scraper_init_custom_timeout(self):
        scraper = HttpScraper(timeout=60)
        assert scraper.timeout == 60

    @pytest.mark.asyncio
    async def test_fetch_page_success(self, sample_html):
        scraper = HttpScraper()
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=sample_html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession') as mock_session_cls:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_cls.return_value = mock_session
            
            html = await scraper.fetch_page("https://example.com")
            assert "Test Product" in html

    @pytest.mark.asyncio
    async def test_fetch_page_http_error(self):
        scraper = HttpScraper()
        
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession') as mock_session_cls:
            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_cls.return_value = mock_session
            
            with pytest.raises(ScraperError) as exc:
                await scraper.fetch_page("https://example.com")
            assert "404" in str(exc.value)

    @pytest.mark.asyncio
    async def test_fetch_page_connection_error(self):
        scraper = HttpScraper()
        
        with patch('aiohttp.ClientSession') as mock_session_cls:
            mock_session = MagicMock()
            mock_session.get = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_cls.return_value = mock_session
            
            with pytest.raises(ScraperError):
                await scraper.fetch_page("https://example.com")

    def test_extract_element_text_css(self, sample_html):
        scraper = HttpScraper()
        text = scraper.extract_element_text(sample_html, ".price", "css")
        assert text == "99.99 лв."

    def test_extract_element_text_xpath(self, sample_html):
        scraper = HttpScraper()
        text = scraper.extract_element_text(sample_html, "//span[@class='price']", "xpath")
        assert text == "99.99 лв."

    def test_extract_element_text_by_id(self, sample_html):
        scraper = HttpScraper()
        text = scraper.extract_element_text(sample_html, "#alt-price", "css")
        assert text == "€89.99"

    def test_extract_element_text_not_found(self, sample_html):
        scraper = HttpScraper()
        text = scraper.extract_element_text(sample_html, ".nonexistent", "css")
        assert text is None

    def test_extract_element_text_xpath_not_found(self, sample_html):
        scraper = HttpScraper()
        text = scraper.extract_element_text(sample_html, "//div[@class='nonexistent']", "xpath")
        assert text is None

    @pytest.mark.asyncio
    async def test_get_price_success(self, sample_html):
        scraper = HttpScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_html
            price = await scraper.get_price("https://example.com", ".price", "css")
        
        assert price == 99.99

    @pytest.mark.asyncio
    async def test_get_price_selector_not_found(self, sample_html):
        scraper = HttpScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_html
            price = await scraper.get_price("https://example.com", ".nonexistent", "css")
        
        assert price is None

    @pytest.mark.asyncio
    async def test_get_price_fetch_error(self):
        scraper = HttpScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ScraperError("Failed")
            price = await scraper.get_price("https://example.com", ".price", "css")
        
        assert price is None

    @pytest.mark.asyncio
    async def test_get_page_title(self, sample_html):
        scraper = HttpScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_html
            title = await scraper.get_page_title("https://example.com")
        
        assert title == "Test Product Page"

    @pytest.mark.asyncio
    async def test_get_page_title_no_title(self):
        scraper = HttpScraper()
        html = "<html><body>No title</body></html>"
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = html
            title = await scraper.get_page_title("https://example.com")
        
        assert title is None

    @pytest.mark.asyncio
    async def test_get_page_title_error(self):
        scraper = HttpScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ScraperError("Failed")
            title = await scraper.get_page_title("https://example.com")
        
        assert title is None

    @pytest.mark.asyncio
    async def test_test_selector_success(self, sample_html):
        scraper = HttpScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_html
            success, text, price = await scraper.test_selector(
                "https://example.com", ".price", "css"
            )
        
        assert success is True
        assert text == "99.99 лв."
        assert price == 99.99

    @pytest.mark.asyncio
    async def test_test_selector_not_found(self, sample_html):
        scraper = HttpScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_html
            success, text, price = await scraper.test_selector(
                "https://example.com", ".nonexistent", "css"
            )
        
        assert success is False
        assert text is None
        assert price is None

    @pytest.mark.asyncio
    async def test_test_selector_error(self):
        scraper = HttpScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ScraperError("Failed")
            success, text, price = await scraper.test_selector(
                "https://example.com", ".price", "css"
            )
        
        assert success is False

    @pytest.mark.asyncio
    async def test_extract_element_text_exception(self):
        """Test extract_element_text catching exception."""
        scraper = HttpScraper()
        # Invalid xpath should raise etree.XPathEvalError, caught by extract_element_text
        text = scraper.extract_element_text(
            "<html></html>", "INVALID[XPATH///", "xpath"
        )
        assert text is None

    def test_extract_with_xpath_string_result(self):
        """Test xpath that returns a string directly."""
        scraper = HttpScraper()
        html = '<html><body><div id="price">100.00</div></body></html>'
        # XPath 'string(...)' function returns a string, not an element
        # But lxml .xpath() returns it as a distinct type that creates a list of strings
        text = scraper.extract_element_text(
            html, "string(//div[@id='price'])", "xpath"
        )
        assert text == "100.00"

    def test_extract_with_xpath_text_content(self):
        """Test xpath getting text content."""
        scraper = HttpScraper()
        html = '<html><body><div id="wrapper"><span>Part1</span> <span>Part2</span></div></body></html>'
        # This returns the div element, which has text_content() containing all children text
        text = scraper.extract_element_text(
            html, "//div[@id='wrapper']", "xpath"
        )
        assert text is not None
        assert "Part1" in text
        assert "Part2" in text

