"""Tests for background checker."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from price_tracker.scheduler.background_checker import BackgroundChecker, PriceUpdate
from price_tracker.models.product import Product
from price_tracker.storage.json_storage import JsonStorage


class TestPriceUpdate:
    """Test PriceUpdate dataclass."""

    def test_create_successful_update(self):
        product = Product(name="Test", url="https://example.com", selector=".price")
        update = PriceUpdate(
            product=product,
            old_price=100.0,
            new_price=80.0,
            success=True,
        )
        assert update.success is True
        assert update.old_price == 100.0
        assert update.new_price == 80.0
        assert update.error is None

    def test_create_failed_update(self):
        product = Product(name="Test", url="https://example.com", selector=".price")
        update = PriceUpdate(
            product=product,
            old_price=100.0,
            new_price=0,
            success=False,
            error="Could not extract price",
        )
        assert update.success is False
        assert update.error == "Could not extract price"


class TestBackgroundChecker:
    """Test BackgroundChecker class."""

    def test_init(self, storage):
        checker = BackgroundChecker(storage, interval_minutes=30)
        assert checker.interval_minutes == 30
        assert checker.use_selenium_fallback is True
        assert checker.is_running() is False

    def test_start_stop(self, storage):
        checker = BackgroundChecker(storage, interval_minutes=60)
        
        checker.start()
        assert checker.is_running() is True
        
        checker.stop()
        assert checker.is_running() is False

    def test_start_twice(self, storage):
        checker = BackgroundChecker(storage, interval_minutes=60)
        checker.start()
        checker.start()  # Should not fail
        assert checker.is_running() is True
        checker.stop()

    def test_stop_when_not_running(self, storage):
        checker = BackgroundChecker(storage, interval_minutes=60)
        checker.stop()  # Should not fail
        assert checker.is_running() is False

    def test_set_interval(self, storage):
        checker = BackgroundChecker(storage, interval_minutes=60)
        checker.set_interval(30)
        assert checker.interval_minutes == 30

    def test_set_interval_while_running(self, storage):
        checker = BackgroundChecker(storage, interval_minutes=60)
        checker.start()
        checker.set_interval(30)
        assert checker.interval_minutes == 30
        checker.stop()

    def test_set_callbacks(self, storage):
        checker = BackgroundChecker(storage)
        
        update_callback = MagicMock()
        complete_callback = MagicMock()
        
        checker.set_on_price_update(update_callback)
        checker.set_on_check_complete(complete_callback)
        
        assert checker._on_price_update == update_callback
        assert checker._on_check_complete == complete_callback

    def test_get_next_run_time_not_running(self, storage):
        checker = BackgroundChecker(storage)
        assert checker.get_next_run_time() is None

    def test_get_next_run_time_running(self, storage):
        checker = BackgroundChecker(storage, interval_minutes=60)
        checker.start()
        next_run = checker.get_next_run_time()
        assert next_run is not None
        checker.stop()

    @pytest.mark.asyncio
    async def test_check_all_products_empty(self, storage):
        checker = BackgroundChecker(storage)
        updates = await checker.check_all_products()
        assert updates == []

    @pytest.mark.asyncio
    async def test_check_all_products_with_callback(self, storage, sample_product):
        storage.add_product(sample_product)
        checker = BackgroundChecker(storage, use_selenium_fallback=False)
        
        complete_callback = MagicMock()
        checker.set_on_check_complete(complete_callback)
        
        with patch.object(checker._http_scraper, 'get_price', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = 99.99
            await checker.check_all_products()
        
        complete_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_single_product_success(self, storage, sample_product):
        storage.add_product(sample_product)
        checker = BackgroundChecker(storage, use_selenium_fallback=False)
        
        with patch.object(checker._http_scraper, 'get_price', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = 79.99
            update = await checker.check_single_product(sample_product)
        
        assert update.success is True
        assert update.new_price == 79.99

    @pytest.mark.asyncio
    async def test_check_single_product_failure(self, storage, sample_product):
        storage.add_product(sample_product)
        checker = BackgroundChecker(storage, use_selenium_fallback=False)
        
        with patch.object(checker._http_scraper, 'get_price', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            update = await checker.check_single_product(sample_product)
        
        assert update.success is False
        assert update.error == "Could not extract price"

    @pytest.mark.asyncio
    async def test_check_product_with_selenium(self, storage):
        product = Product(
            name="Selenium Test",
            url="https://example.com",
            selector=".price",
            use_selenium=True,
        )
        storage.add_product(product)
        checker = BackgroundChecker(storage)
        
        with patch('price_tracker.scheduler.background_checker.SeleniumScraper') as mock_cls:
            mock_scraper = MagicMock()
            mock_scraper.get_price = AsyncMock(return_value=59.99)
            mock_cls.return_value = mock_scraper
            
            update = await checker.check_single_product(product)
        
        assert update.success is True
        assert update.new_price == 59.99

    @pytest.mark.asyncio
    async def test_check_product_selenium_fallback(self, storage, sample_product):
        storage.add_product(sample_product)
        checker = BackgroundChecker(storage, use_selenium_fallback=True)
        
        with patch.object(checker._http_scraper, 'get_price', new_callable=AsyncMock) as mock_http:
            mock_http.return_value = None
            
            with patch('price_tracker.scheduler.background_checker.SeleniumScraper') as mock_cls:
                mock_scraper = MagicMock()
                mock_scraper.get_price = AsyncMock(return_value=49.99)
                mock_cls.return_value = mock_scraper
                
                update = await checker.check_single_product(sample_product)
        
        assert update.success is True
        assert update.new_price == 49.99

    @pytest.mark.asyncio
    async def test_check_product_exception(self, storage, sample_product):
        storage.add_product(sample_product)
        checker = BackgroundChecker(storage, use_selenium_fallback=False)
        
        with patch.object(checker._http_scraper, 'get_price', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Network error")
            update = await checker.check_single_product(sample_product)
        
        assert update.success is False
        assert "Network error" in update.error

    @pytest.mark.asyncio
    async def test_check_product_updates_storage(self, storage, sample_product):
        storage.add_product(sample_product)
        checker = BackgroundChecker(storage, use_selenium_fallback=False)
        
        with patch.object(checker._http_scraper, 'get_price', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = 75.00
            await checker.check_single_product(sample_product)
        
        updated = storage.get_product(sample_product.id)
        assert updated.current_price == 75.00
        assert updated.last_checked is not None

    @pytest.mark.asyncio
    async def test_check_product_calls_update_callback(self, storage, sample_product):
        storage.add_product(sample_product)
        checker = BackgroundChecker(storage, use_selenium_fallback=False)
        
        update_callback = MagicMock()
        checker.set_on_price_update(update_callback)
        
        with patch.object(checker._http_scraper, 'get_price', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = 75.00
            await checker.check_single_product(sample_product)
        
        update_callback.assert_called_once()

    def test_stop_cleans_up_selenium(self, storage):
        checker = BackgroundChecker(storage)
        mock_selenium = MagicMock()
        checker._selenium_scraper = mock_selenium
        
        checker.stop()
        
        mock_selenium.close.assert_called_once()
        assert checker._selenium_scraper is None
