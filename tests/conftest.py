"""Pytest fixtures for Price Tracker tests."""

import pytest
import tempfile
import os
from pathlib import Path

from price_tracker.models.product import Product
from price_tracker.models.price_record import PriceRecord
from price_tracker.storage.json_storage import JsonStorage


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def storage(temp_data_dir):
    """Create a storage instance with temp directory."""
    return JsonStorage(data_dir=temp_data_dir)


@pytest.fixture
def sample_product():
    """Create a sample product for testing."""
    return Product(
        name="Test Product",
        url="https://example.com/product",
        selector=".price",
        selector_type="css",
        current_price=99.99,
        notify_on_drop=True,
        target_price=80.0,
    )


@pytest.fixture
def sample_price_record(sample_product):
    """Create a sample price record for testing."""
    return PriceRecord(
        product_id=sample_product.id,
        price=99.99,
    )


@pytest.fixture
def sample_html():
    """Sample HTML for scraper tests."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Product Page</title></head>
    <body>
        <h1>Test Product</h1>
        <div class="product-price">
            <span class="price">99.99 лв.</span>
        </div>
        <div id="alt-price">€89.99</div>
        <div data-price="79.99">$79.99</div>
    </body>
    </html>
    """
