"""Import/export products and history to CSV and JSON."""

import csv
import json
from pathlib import Path
from typing import Union

from price_tracker.models.product import Product
from price_tracker.models.price_record import PriceRecord


class DataExporter:
    """Handles exporting data to files and importing it back."""

    @staticmethod
    def export_products_to_csv(
        products: list[Product], filepath: Union[str, Path]
    ) -> None:
        """Save products to a CSV file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "id", "name", "url", "selector", "selector_type",
            "current_price", "target_price", "notify_on_drop",
            "use_selenium", "created_at", "last_checked",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for product in products:
                row = {k: v for k, v in product.to_dict().items() if k in fieldnames}
                writer.writerow(row)

    @staticmethod
    def import_products_from_csv(filepath: Union[str, Path]) -> list[Product]:
        """Load products from a CSV file."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        products = []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Fix boolean fields
                if "notify_on_drop" in row:
                    row["notify_on_drop"] = row["notify_on_drop"].lower() in ("true", "1", "yes")
                if "use_selenium" in row:
                    row["use_selenium"] = row["use_selenium"].lower() in ("true", "1", "yes")
                    
                # Fix price fields
                for field in ["current_price", "target_price"]:
                    if field in row and row[field]:
                        try:
                            row[field] = float(row[field])
                        except ValueError:
                            row[field] = None
                    else:
                        row[field] = None

                try:
                    products.append(Product.from_dict(row))
                except (KeyError, ValueError) as e:
                    raise ValueError(f"Invalid CSV row: {row}") from e

        return products

    @staticmethod
    def export_products_to_json(
        products: list[Product], filepath: Union[str, Path]
    ) -> None:
        """Save products to a JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = [product.to_dict() for product in products]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def import_products_from_json(filepath: Union[str, Path]) -> list[Product]:
        """Load products from a JSON file."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}") from e

        if not isinstance(data, list):
            raise ValueError("JSON must contain a list of products")

        products = []
        for item in data:
            try:
                products.append(Product.from_dict(item))
            except (KeyError, ValueError) as e:
                raise ValueError(f"Invalid product data: {item}") from e

        return products

    @staticmethod
    def export_history_to_csv(
        records: list[PriceRecord], filepath: Union[str, Path]
    ) -> None:
        """Save price history to CSV."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = ["id", "product_id", "price", "timestamp"]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(record.to_dict())

    @staticmethod
    def export_history_to_json(
        records: list[PriceRecord], filepath: Union[str, Path]
    ) -> None:
        """Save price history to JSON."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = [record.to_dict() for record in records]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
