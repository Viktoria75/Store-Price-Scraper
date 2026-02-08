"""Tests for storage modules."""

import pytest
import json
from pathlib import Path

from price_tracker.models.product import Product
from price_tracker.models.price_record import PriceRecord
from price_tracker.storage.json_storage import JsonStorage
from price_tracker.storage.exporter import DataExporter


class TestJsonStorage:
    """Test cases for JSON storage."""

    def test_storage_creation(self, temp_data_dir: str) -> None:
        """Test storage initialization."""
        storage = JsonStorage(data_dir=temp_data_dir)

        assert storage.data_dir.exists()
        assert storage.products_file.parent.exists()

    def test_add_and_get_product(
        self, storage: JsonStorage, sample_product: Product
    ) -> None:
        """Test adding and retrieving a product."""
        storage.add_product(sample_product)

        products = storage.get_all_products()
        assert len(products) == 1
        assert products[0].name == sample_product.name
        assert products[0].url == sample_product.url

    def test_get_product_by_id(
        self, storage: JsonStorage, sample_product: Product
    ) -> None:
        """Test getting a product by ID."""
        storage.add_product(sample_product)

        product = storage.get_product(sample_product.id)
        assert product is not None
        assert product.id == sample_product.id

        # Test non-existent ID
        product = storage.get_product("non-existent-id")
        assert product is None

    def test_update_product(
        self, storage: JsonStorage, sample_product: Product
    ) -> None:
        """Test updating a product."""
        storage.add_product(sample_product)

        sample_product.current_price = 75.00
        sample_product.name = "Updated Name"
        success = storage.update_product(sample_product)

        assert success is True

        product = storage.get_product(sample_product.id)
        assert product is not None
        assert product.current_price == 75.00
        assert product.name == "Updated Name"

    def test_delete_product(
        self, storage: JsonStorage, sample_product: Product
    ) -> None:
        """Test deleting a product."""
        storage.add_product(sample_product)

        success = storage.delete_product(sample_product.id)
        assert success is True

        products = storage.get_all_products()
        assert len(products) == 0

        # Try deleting non-existent
        success = storage.delete_product("non-existent")
        assert success is False

    def test_price_history(
        self,
        storage: JsonStorage,
        sample_product: Product,
        sample_price_record: PriceRecord,
    ) -> None:
        """Test price history operations."""
        storage.add_product(sample_product)
        storage.add_price_record(sample_price_record)

        history = storage.get_price_history(sample_product.id)
        assert len(history) == 1
        assert history[0].price == sample_price_record.price

    def test_settings(self, storage: JsonStorage) -> None:
        """Test settings operations."""
        # Get default settings
        settings = storage.get_settings()
        assert "check_interval_minutes" in settings
        assert "email" in settings

        # Save and load settings
        settings["check_interval_minutes"] = 30
        storage.save_settings(settings)

        loaded = storage.get_settings()
        assert loaded["check_interval_minutes"] == 30


class TestDataExporter:
    """Test cases for data exporter."""

    def test_export_import_csv(
        self, temp_data_dir: str, sample_product: Product
    ) -> None:
        """Test CSV export and import."""
        filepath = Path(temp_data_dir) / "test_export.csv"
        products = [sample_product]

        # Export
        DataExporter.export_products_to_csv(products, filepath)
        assert filepath.exists()

        # Import
        imported = DataExporter.import_products_from_csv(filepath)
        assert len(imported) == 1
        assert imported[0].name == sample_product.name
        assert imported[0].url == sample_product.url

    def test_export_import_json(
        self, temp_data_dir: str, sample_product: Product
    ) -> None:
        """Test JSON export and import."""
        filepath = Path(temp_data_dir) / "test_export.json"
        products = [sample_product]

        # Export
        DataExporter.export_products_to_json(products, filepath)
        assert filepath.exists()

        # Verify JSON content
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["name"] == sample_product.name

        # Import
        imported = DataExporter.import_products_from_json(filepath)
        assert len(imported) == 1
        assert imported[0].name == sample_product.name

    def test_import_nonexistent_file(self, temp_data_dir: str) -> None:
        """Test importing from non-existent file."""
        filepath = Path(temp_data_dir) / "nonexistent.csv"

        with pytest.raises(FileNotFoundError):
            DataExporter.import_products_from_csv(filepath)

        with pytest.raises(FileNotFoundError):
            DataExporter.import_products_from_json(filepath)

    def test_export_history_csv(
        self,
        temp_data_dir: str,
        sample_price_record: PriceRecord,
    ) -> None:
        """Test price history CSV export."""
        filepath = Path(temp_data_dir) / "history_export.csv"
        records = [sample_price_record]

        DataExporter.export_history_to_csv(records, filepath)
        assert filepath.exists()

        # Verify content
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert str(sample_price_record.price) in content
