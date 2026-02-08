"""Background checker - periodically checks all product prices."""

from datetime import datetime
from typing import Optional, Callable, Awaitable
import asyncio
from dataclasses import dataclass

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from price_tracker.models.product import Product
from price_tracker.models.price_record import PriceRecord
from price_tracker.scraper.http_scraper import HttpScraper
from price_tracker.scraper.selenium_scraper import SeleniumScraper
from price_tracker.storage.json_storage import JsonStorage


@dataclass
class PriceUpdate:
    """Result of checking a product's price."""

    product: Product
    old_price: Optional[float]
    new_price: float
    success: bool
    error: Optional[str] = None


class BackgroundChecker:
    """Runs price checks on a schedule in the background."""

    def __init__(
        self,
        storage: JsonStorage,
        interval_minutes: int = 60,
        use_selenium_fallback: bool = True,
    ):
        self.storage = storage
        self.interval_minutes = interval_minutes
        self.use_selenium_fallback = use_selenium_fallback

        self._scheduler: Optional[BackgroundScheduler] = None
        self._http_scraper = HttpScraper()
        self._selenium_scraper: Optional[SeleniumScraper] = None

        self._on_price_update: Optional[Callable[[PriceUpdate], None]] = None
        self._on_check_complete: Optional[Callable[[int, int], None]] = None
        self._is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_on_price_update(self, callback: Callable[[PriceUpdate], None]) -> None:
        """Called when a product price is updated."""
        self._on_price_update = callback

    def set_on_check_complete(self, callback: Callable[[int, int], None]) -> None:
        """Called when all products checked - receives (success, total) counts."""
        self._on_check_complete = callback

    def start(self) -> None:
        """Start the timer."""
        if self._is_running:
            return

        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(
            self._run_check,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id="price_check",
            name="Price Check",
            replace_existing=True,
        )
        self._scheduler.start()
        self._is_running = True

    def stop(self) -> None:
        """Stop the timer and clean up."""
        if self._scheduler and self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            self._scheduler = None

        if self._selenium_scraper:
            self._selenium_scraper.close()
            self._selenium_scraper = None

    def is_running(self) -> bool:
        return self._is_running

    def set_interval(self, minutes: int) -> None:
        """Change how often we check prices."""
        self.interval_minutes = minutes
        if self._is_running and self._scheduler:
            self._scheduler.reschedule_job(
                "price_check",
                trigger=IntervalTrigger(minutes=minutes),
            )

    def _run_check(self) -> None:
        """Called by scheduler - sets up async and runs the check."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._check_all_products())
        finally:
            loop.close()

    async def check_all_products(self) -> list[PriceUpdate]:
        """Manually trigger a check of all products."""
        return await self._check_all_products()

    async def check_single_product(self, product: Product) -> PriceUpdate:
        """Check one specific product."""
        return await self._check_product(product)

    async def _check_all_products(self) -> list[PriceUpdate]:
        """Go through all products and check their prices."""
        products = self.storage.get_all_products()
        updates: list[PriceUpdate] = []
        success_count = 0

        for product in products:
            update = await self._check_product(product)
            updates.append(update)
            if update.success:
                success_count += 1

        if self._on_check_complete:
            self._on_check_complete(success_count, len(products))

        return updates

    async def _check_product(self, product: Product) -> PriceUpdate:
        """Fetch current price for a product and save it."""
        old_price = product.current_price

        try:
            if product.use_selenium:
                new_price = await self._fetch_with_selenium(product)
            else:
                new_price = await self._http_scraper.get_price(
                    product.url, product.selector, product.selector_type
                )
                # Try Selenium if HTTP didn't work
                if new_price is None and self.use_selenium_fallback:
                    new_price = await self._fetch_with_selenium(product)

            if new_price is None:
                return PriceUpdate(
                    product=product,
                    old_price=old_price,
                    new_price=0,
                    success=False,
                    error="Could not extract price",
                )

            # Save the new price
            product.previous_price = old_price
            product.current_price = new_price
            product.last_checked = datetime.now()
            self.storage.update_product(product)

            # Add to history
            record = PriceRecord(product_id=product.id, price=new_price)
            self.storage.add_price_record(record)

            update = PriceUpdate(
                product=product,
                old_price=old_price,
                new_price=new_price,
                success=True,
            )

            if self._on_price_update:
                self._on_price_update(update)

            return update

        except Exception as e:
            return PriceUpdate(
                product=product,
                old_price=old_price,
                new_price=0,
                success=False,
                error=str(e),
            )

    async def _fetch_with_selenium(self, product: Product) -> Optional[float]:
        """Use browser to get price (for JS-heavy sites)."""
        if self._selenium_scraper is None:
            self._selenium_scraper = SeleniumScraper()

        return await self._selenium_scraper.get_price(
            product.url, product.selector, product.selector_type
        )

    def get_next_run_time(self) -> Optional[datetime]:
        """When is the next check scheduled?"""
        if self._scheduler and self._is_running:
            job = self._scheduler.get_job("price_check")
            if job:
                return job.next_run_time
        return None
