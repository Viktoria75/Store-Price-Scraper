"""JSON file storage for products and price history."""

import json
import os
from pathlib import Path
from threading import Lock
from typing import Optional

from price_tracker.models.product import Product
from price_tracker.models.price_record import PriceRecord


class JsonStorage:
    """Saves everything to JSON files in the data folder."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path.cwd() / "data"

        self.products_file = self.data_dir / "products.json"
        self.history_file = self.data_dir / "price_history.json"
        self.settings_file = self.data_dir / "settings.json"
        self._lock = Lock()
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Make sure the data folder exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _read_json(self, file_path: Path) -> list:
        """Load JSON file, return empty list if missing or corrupt."""
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _write_json(self, file_path: Path, data: list) -> None:
        """Save list to JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # --- Products ---

    def get_all_products(self) -> list[Product]:
        """Load all saved products."""
        with self._lock:
            data = self._read_json(self.products_file)
            return [Product.from_dict(item) for item in data]

    def get_product(self, product_id: str) -> Optional[Product]:
        """Find product by ID."""
        products = self.get_all_products()
        for product in products:
            if product.id == product_id:
                return product
        return None

    def add_product(self, product: Product) -> None:
        """Save a new product."""
        with self._lock:
            data = self._read_json(self.products_file)
            data.append(product.to_dict())
            self._write_json(self.products_file, data)

    def update_product(self, product: Product) -> bool:
        """Update product data, returns True if found."""
        with self._lock:
            data = self._read_json(self.products_file)
            for i, item in enumerate(data):
                if item.get("id") == product.id:
                    data[i] = product.to_dict()
                    self._write_json(self.products_file, data)
                    return True
            return False

    def delete_product(self, product_id: str) -> bool:
        """Remove product and its price history."""
        with self._lock:
            data = self._read_json(self.products_file)
            original_len = len(data)
            data = [item for item in data if item.get("id") != product_id]
            if len(data) < original_len:
                self._write_json(self.products_file, data)
                self._delete_product_history(product_id)
                return True
            return False

    def _delete_product_history(self, product_id: str) -> None:
        """Remove all price records for a product."""
        history = self._read_json(self.history_file)
        history = [r for r in history if r.get("product_id") != product_id]
        self._write_json(self.history_file, history)

    # --- Price History ---

    def add_price_record(self, record: PriceRecord) -> None:
        """Save a price snapshot."""
        with self._lock:
            data = self._read_json(self.history_file)
            data.append(record.to_dict())
            self._write_json(self.history_file, data)

    def get_price_history(
        self, product_id: str, limit: Optional[int] = None
    ) -> list[PriceRecord]:
        """Get price history for one product, newest first."""
        with self._lock:
            data = self._read_json(self.history_file)
            records = [
                PriceRecord.from_dict(item)
                for item in data
                if item.get("product_id") == product_id
            ]
            records.sort(key=lambda r: r.timestamp, reverse=True)
            if limit:
                records = records[:limit]
            return records

    def get_all_history(self) -> list[PriceRecord]:
        """Get all price records."""
        with self._lock:
            data = self._read_json(self.history_file)
            return [PriceRecord.from_dict(item) for item in data]

    # --- Settings ---

    def get_settings(self) -> dict:
        """Load app settings."""
        with self._lock:
            if not self.settings_file.exists():
                return self._default_settings()
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return self._default_settings()

    def save_settings(self, settings: dict) -> None:
        """Save app settings."""
        with self._lock:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)

    def _default_settings(self) -> dict:
        """Default config for new installs."""
        return {
            "check_interval_minutes": 60,
            "email": {
                "enabled": False,
                "smtp_server": "",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_address": "",
                "to_address": "",
            },
            "discord": {
                "enabled": False,
                "webhook_url": "",
            },
            "use_selenium_fallback": True,
        }
