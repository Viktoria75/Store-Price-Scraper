"""Tests for data models."""

import pytest
from datetime import datetime

from price_tracker.models.product import Product
from price_tracker.models.price_record import PriceRecord


class TestProduct:
    """Test cases for Product model."""

    def test_product_creation(self) -> None:
        """Test basic product creation."""
        product = Product(
            name="Test Product",
            url="https://example.com/product",
            selector=".price",
        )

        assert product.name == "Test Product"
        assert product.url == "https://example.com/product"
        assert product.selector == ".price"
        assert product.selector_type == "css"
        assert product.id is not None
        assert product.current_price is None
        assert product.notify_on_drop is True

    def test_product_creation_with_all_fields(self) -> None:
        """Test product creation with all fields."""
        product = Product(
            name="Full Product",
            url="https://example.com/full",
            selector="//div[@class='price']",
            selector_type="xpath",
            current_price=99.99,
            previous_price=120.00,
            notify_on_drop=True,
            target_price=80.0,
            use_selenium=True,
        )

        assert product.selector_type == "xpath"
        assert product.current_price == 99.99
        assert product.previous_price == 120.00
        assert product.target_price == 80.0
        assert product.use_selenium is True

    def test_product_to_dict(self, sample_product: Product) -> None:
        """Test product serialization to dictionary."""
        data = sample_product.to_dict()

        assert data["name"] == "Test Product"
        assert data["url"] == "https://example.com/product"
        assert data["selector"] == ".price"
        assert data["current_price"] == 99.99
        assert "id" in data
        assert "created_at" in data

    def test_product_from_dict(self) -> None:
        """Test product deserialization from dictionary."""
        data = {
            "id": "test-id-123",
            "name": "Dict Product",
            "url": "https://example.com/dict",
            "selector": ".price",
            "selector_type": "css",
            "current_price": 50.0,
            "created_at": "2024-01-01T12:00:00",
        }

        product = Product.from_dict(data)

        assert product.id == "test-id-123"
        assert product.name == "Dict Product"
        assert product.current_price == 50.0
        assert product.created_at == datetime(2024, 1, 1, 12, 0, 0)

    def test_has_price_dropped(self) -> None:
        """Test price drop detection."""
        product = Product(
            name="Test",
            url="https://example.com",
            selector=".price",
            current_price=80.0,
            previous_price=100.0,
        )

        assert product.has_price_dropped() is True

        product.current_price = 120.0
        assert product.has_price_dropped() is False

    def test_is_below_target(self) -> None:
        """Test target price comparison."""
        product = Product(
            name="Test",
            url="https://example.com",
            selector=".price",
            current_price=75.0,
            target_price=80.0,
        )

        assert product.is_below_target() is True

        product.current_price = 85.0
        assert product.is_below_target() is False

    def test_should_notify(self) -> None:
        """Test notification logic."""
        product = Product(
            name="Test",
            url="https://example.com",
            selector=".price",
            current_price=80.0,
            previous_price=100.0,
            notify_on_drop=True,
            target_price=90.0,
        )

        # Should notify - price dropped
        assert product.should_notify() is True

        # Should not notify if disabled
        product.notify_on_drop = False
        assert product.should_notify() is False


class TestPriceRecord:
    """Test cases for PriceRecord model."""

    def test_price_record_creation(self) -> None:
        """Test basic price record creation."""
        record = PriceRecord(
            product_id="product-123",
            price=99.99,
        )

        assert record.product_id == "product-123"
        assert record.price == 99.99
        assert record.id is not None
        assert record.timestamp is not None

    def test_price_record_to_dict(self) -> None:
        """Test price record serialization."""
        record = PriceRecord(
            product_id="product-123",
            price=99.99,
        )

        data = record.to_dict()

        assert data["product_id"] == "product-123"
        assert data["price"] == 99.99
        assert "id" in data
        assert "timestamp" in data

    def test_price_record_from_dict(self) -> None:
        """Test price record deserialization."""
        data = {
            "id": "record-123",
            "product_id": "product-123",
            "price": 75.50,
            "timestamp": "2024-01-15T10:30:00",
        }

        record = PriceRecord.from_dict(data)

        assert record.id == "record-123"
        assert record.product_id == "product-123"
        assert record.price == 75.50
        assert record.timestamp == datetime(2024, 1, 15, 10, 30, 0)
