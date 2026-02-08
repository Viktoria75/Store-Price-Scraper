"""Tests for Selenium scraper with mocked WebDriver."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from price_tracker.scraper.selenium_scraper import SeleniumScraper
from price_tracker.scraper.base import ScraperError


class TestSeleniumScraper:
    """Test SeleniumScraper class."""

    def test_init_default(self):
        scraper = SeleniumScraper()
        assert scraper.headless is True
        assert scraper.timeout == 30
        assert scraper.page_load_wait == 5
        assert scraper._driver is None

    def test_init_custom(self):
        scraper = SeleniumScraper(headless=False, timeout=60, page_load_wait=10)
        assert scraper.headless is False
        assert scraper.timeout == 60
        assert scraper.page_load_wait == 10

    def test_close_no_driver(self):
        scraper = SeleniumScraper()
        scraper.close()  # Should not fail
        assert scraper._driver is None

    def test_close_with_driver(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        scraper._driver = mock_driver
        
        scraper.close()
        
        mock_driver.quit.assert_called_once()
        assert scraper._driver is None

    def test_close_driver_error(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_driver.quit.side_effect = WebDriverException("Error")
        scraper._driver = mock_driver
        
        scraper.close()  # Should not raise
        assert scraper._driver is None

    def test_del_calls_close(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        scraper._driver = mock_driver
        
        scraper.__del__()
        mock_driver.quit.assert_called()

    @patch('price_tracker.scraper.selenium_scraper.ChromeDriverManager')
    @patch('price_tracker.scraper.selenium_scraper.webdriver.Chrome')
    def test_create_driver(self, mock_chrome, mock_manager):
        mock_manager.return_value.install.return_value = "/path/to/chromedriver"
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        scraper = SeleniumScraper()
        driver = scraper._create_driver()
        
        assert driver == mock_driver
        mock_driver.set_page_load_timeout.assert_called_with(30)
        mock_driver.execute_cdp_cmd.assert_called()

    @patch('price_tracker.scraper.selenium_scraper.ChromeDriverManager')
    @patch('price_tracker.scraper.selenium_scraper.webdriver.Chrome')
    def test_get_driver_creates_new(self, mock_chrome, mock_manager):
        mock_manager.return_value.install.return_value = "/path/to/chromedriver"
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        scraper = SeleniumScraper()
        driver = scraper._get_driver()
        
        assert driver == mock_driver
        assert scraper._driver == mock_driver

    def test_get_driver_reuses_existing(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        scraper._driver = mock_driver
        
        driver = scraper._get_driver()
        assert driver == mock_driver

    def test_fetch_page_sync_success(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>Content</body></html>"
        scraper._driver = mock_driver
        
        with patch.object(scraper, '_get_driver', return_value=mock_driver):
            html = scraper._fetch_page_sync("https://example.com")
        
        assert "Content" in html
        mock_driver.get.assert_called_with("https://example.com")

    def test_fetch_page_sync_timeout(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_driver.get.side_effect = TimeoutException("Timeout")
        scraper._driver = mock_driver
        
        with patch.object(scraper, '_get_driver', return_value=mock_driver):
            with pytest.raises(ScraperError) as exc:
                scraper._fetch_page_sync("https://example.com")
            assert "timeout" in str(exc.value).lower()

    def test_fetch_page_sync_webdriver_error(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_driver.get.side_effect = WebDriverException("Driver crashed")
        scraper._driver = mock_driver
        
        with patch.object(scraper, '_get_driver', return_value=mock_driver):
            with pytest.raises(ScraperError):
                scraper._fetch_page_sync("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_page_async(self):
        scraper = SeleniumScraper()
        
        with patch.object(scraper, '_fetch_page_sync', return_value="<html></html>"):
            html = await scraper.fetch_page("https://example.com")
        
        assert html == "<html></html>"

    def test_extract_element_text_css(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "  99.99  "
        mock_driver.find_element.return_value = mock_element
        scraper._driver = mock_driver
        
        with patch.object(scraper, '_get_driver', return_value=mock_driver):
            text = scraper.extract_element_text("<html></html>", ".price", "css")
        
        assert text == "99.99"

    def test_extract_element_text_xpath(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "49.99"
        mock_driver.find_element.return_value = mock_element
        scraper._driver = mock_driver
        
        with patch.object(scraper, '_get_driver', return_value=mock_driver):
            text = scraper.extract_element_text("<html></html>", "//div[@class='price']", "xpath")
        
        assert text == "49.99"

    def test_extract_element_text_not_found(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = NoSuchElementException("Not found")
        scraper._driver = mock_driver
        
        with patch.object(scraper, '_get_driver', return_value=mock_driver):
            text = scraper.extract_element_text("<html></html>", ".nonexistent", "css")
        
        assert text is None

    def test_extract_element_text_driver_error(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = WebDriverException("Error")
        scraper._driver = mock_driver
        
        with patch.object(scraper, '_get_driver', return_value=mock_driver):
            text = scraper.extract_element_text("<html></html>", ".price", "css")
        
        assert text is None

    @pytest.mark.asyncio
    async def test_get_page_title(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_driver.title = "Test Page Title"
        scraper._driver = mock_driver
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "<html></html>"
            with patch.object(scraper, '_get_driver', return_value=mock_driver):
                title = await scraper.get_page_title("https://example.com")
        
        assert title == "Test Page Title"

    @pytest.mark.asyncio
    async def test_get_page_title_error(self):
        scraper = SeleniumScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ScraperError("Failed")
            title = await scraper.get_page_title("https://example.com")
        
        assert title is None

    @pytest.mark.asyncio
    async def test_test_selector_success(self):
        scraper = SeleniumScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock):
            with patch.object(scraper, 'extract_element_text', return_value="99.99 лв."):
                with patch.object(scraper, 'parse_price', return_value=99.99):
                    success, text, price = await scraper.test_selector(
                        "https://example.com", ".price", "css"
                    )
        
        assert success is True
        assert text == "99.99 лв."
        assert price == 99.99

    @pytest.mark.asyncio
    async def test_test_selector_not_found(self):
        scraper = SeleniumScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock):
            with patch.object(scraper, 'extract_element_text', return_value=None):
                success, text, price = await scraper.test_selector(
                    "https://example.com", ".nonexistent", "css"
                )
        
        assert success is False
        assert text is None
        assert price is None

    @pytest.mark.asyncio
    async def test_test_selector_error(self):
        scraper = SeleniumScraper()
        
        with patch.object(scraper, 'fetch_page', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ScraperError("Failed")
            success, text, price = await scraper.test_selector(
                "https://example.com", ".price", "css"
            )
        
        assert success is False

    def test_get_price_with_wait_sync_success(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "99.99"
        mock_driver.find_element.return_value = mock_element
        scraper._driver = mock_driver
        
        with patch.object(scraper, '_get_driver', return_value=mock_driver):
            with patch.object(scraper, 'parse_price', return_value=99.99):
                price = scraper._get_price_with_wait_sync(
                    "https://example.com", ".price", "css", 10
                )
        
        assert price == 99.99

    def test_get_price_with_wait_sync_timeout(self):
        scraper = SeleniumScraper()
        mock_driver = MagicMock()
        mock_driver.get.side_effect = TimeoutException("Timeout")
        scraper._driver = mock_driver
        
        with patch.object(scraper, '_get_driver', return_value=mock_driver):
            price = scraper._get_price_with_wait_sync(
                "https://example.com", ".price", "css", 10
            )
        
        assert price is None

    @pytest.mark.asyncio
    async def test_get_price_with_wait_async(self):
        scraper = SeleniumScraper()
        
        with patch.object(scraper, '_get_price_with_wait_sync', return_value=79.99):
            price = await scraper.get_price_with_wait(
                "https://example.com", ".price", "css", 10
            )
        
        assert price == 79.99
