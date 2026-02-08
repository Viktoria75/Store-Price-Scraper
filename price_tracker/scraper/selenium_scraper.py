"""Selenium scraper - uses a real browser for JS-heavy sites."""

from typing import Optional
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager

from price_tracker.scraper.base import BaseScraper, ScraperError


class SeleniumScraper(BaseScraper):
    """Uses Chrome to render pages - slower but handles JavaScript."""

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        page_load_wait: int = 5,
    ):
        self.headless = headless
        self.timeout = timeout
        self.page_load_wait = page_load_wait
        self._driver: Optional[webdriver.Chrome] = None

    def _create_driver(self) -> webdriver.Chrome:
        """Set up Chrome with settings to avoid bot detection."""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless=new")
        
        # Stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Make it look like a normal browser
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        # Bulgarian language for local sites
        options.add_argument("--lang=bg-BG,bg")
        options.add_argument("--accept-lang=bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7")
        
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(self.timeout)
        
        # Hide the fact that we're using Selenium
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['bg-BG', 'bg', 'en-US', 'en']});
                window.chrome = {runtime: {}};
            """
        })
        
        return driver

    def _get_driver(self) -> webdriver.Chrome:
        """Get existing driver or create new one."""
        if self._driver is None:
            self._driver = self._create_driver()
        return self._driver

    def close(self) -> None:
        """Shut down the browser."""
        if self._driver:
            try:
                self._driver.quit()
            except WebDriverException:
                pass
            self._driver = None

    def __del__(self) -> None:
        self.close()

    async def fetch_page(self, url: str) -> str:
        """Load page in browser and return HTML (runs in background thread)."""
        return await asyncio.to_thread(self._fetch_page_sync, url)

    def _fetch_page_sync(self, url: str) -> str:
        """Actually load the page - called from thread."""
        import time
        try:
            driver = self._get_driver()
            driver.get(url)
            WebDriverWait(driver, self.page_load_wait).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)  # Let JS finish loading
            return driver.page_source
        except TimeoutException as e:
            raise ScraperError(
                f"Page load timeout after {self.timeout}s", url=url, cause=e
            ) from e
        except WebDriverException as e:
            raise ScraperError(f"Browser error: {str(e)}", url=url, cause=e) from e

    def extract_element_text(
        self, html: str, selector: str, selector_type: str
    ) -> Optional[str]:
        """Find element on the live page and get its text."""
        try:
            driver = self._get_driver()
            if selector_type == "xpath":
                element = driver.find_element(By.XPATH, selector)
            else:
                element = driver.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip() if element else None
        except (NoSuchElementException, WebDriverException):
            return None

    async def get_page_title(self, url: str) -> Optional[str]:
        """Load page and return its title."""
        try:
            await self.fetch_page(url)
            return self._get_driver().title
        except ScraperError:
            return None

    async def test_selector(
        self, url: str, selector: str, selector_type: str = "css"
    ) -> tuple[bool, Optional[str], Optional[float]]:
        """Try selector and return (worked, text, price)."""
        try:
            await self.fetch_page(url)
            text = self.extract_element_text("", selector, selector_type)
            if text:
                price = self.parse_price(text)
                return True, text, price
            return False, None, None
        except ScraperError:
            return False, None, None

    async def get_price_with_wait(
        self,
        url: str,
        selector: str,
        selector_type: str = "css",
        wait_time: int = 10,
    ) -> Optional[float]:
        """Load page, wait for price element to appear, then extract it."""
        return await asyncio.to_thread(
            self._get_price_with_wait_sync, url, selector, selector_type, wait_time
        )

    def _get_price_with_wait_sync(
        self, url: str, selector: str, selector_type: str, wait_time: int
    ) -> Optional[float]:
        """Wait for element then get price - called from thread."""
        try:
            driver = self._get_driver()
            driver.get(url)

            by = By.XPATH if selector_type == "xpath" else By.CSS_SELECTOR
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((by, selector))
            )

            element = driver.find_element(by, selector)
            if element:
                return self.parse_price(element.text)
            return None
        except (TimeoutException, NoSuchElementException, WebDriverException):
            return None
