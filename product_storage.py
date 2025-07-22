#!/usr/bin/env python3.9
"""
Manages persistent storage of known products to prevent duplicate notifications.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from logging_config import get_logger

class ProductStorage:
    """
    Manages a persistent JSON database of products to track seen items.
    """

    def __init__(
        self,
        storage_path: str = "mercari_known_products.json",
        max_storage_days: int = 7,
    ):
        self.storage_path = Path(storage_path)
        self.logger = get_logger("ProductStorage")
        self.products: Dict[str, dict] = {}
        self.max_storage_days = max_storage_days
        self._load_existing_products()

    def _load_existing_products(self):
        """Loads existing products from the storage file into memory."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.products = data.get("products", {})
                self.logger.info(
                    "Loaded known products",
                    count=len(self.products),
                    path=str(self.storage_path),
                )
            except Exception as e:
                self.logger.error(
                    "Failed to load product storage file. Starting with empty database.",
                    error=str(e),
                )
                self.products = {}
        else:
            self.logger.info(
                "No existing product storage file found. A new one will be created on save.",
                path=str(self.storage_path),
            )
            self.products = {}

    def add_product(self, product: dict):
        """Adds a product to the in-memory storage. Does NOT save to disk."""
        product_id = str(product["id"])
        if product_id not in self.products:
            self.products[product_id] = {
                "id": product_id,
                "title": product.get("title", ""),
                "price": product.get("price", 0),
                "url": product.get("url", ""),
                "image_url": product.get("image_url", ""),
                "added_at": datetime.now().isoformat(),
            }
            self.logger.debug(
                "Added product to in-memory store", product_id=product_id
            )

    def is_product_known(self, product_id: str) -> bool:
        """Checks if a product ID is in the in-memory storage."""
        return str(product_id) in self.products

    def cleanup_old_products(self) -> int:
        """Removes old products from the in-memory storage. Does NOT save to disk."""
        cutoff = datetime.now() - timedelta(days=self.max_storage_days)
        initial_count = len(self.products)
        products_to_keep = {}
        for product_id, product_data in self.products.items():
            try:
                added_time = datetime.fromisoformat(product_data["added_at"])
                if added_time >= cutoff:
                    products_to_keep[product_id] = product_data
            except (ValueError, KeyError):
                continue
        removed_count = initial_count - len(products_to_keep)
        if removed_count > 0:
            self.products = products_to_keep
            self.logger.info(
                "Cleaned up old products from memory", count=removed_count
            )
        return removed_count

    def save_products(self):
        """Saves the current state of the in-memory product database to the JSON file."""
        backup_path = self.storage_path.with_suffix(".backup.json")
        try:
            data_to_save = {
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "total_count": len(self.products),
                },
                "products": self.products,
            }
            # Only backup if the file exists and we're not saving an empty database
            if self.storage_path.exists() and self.products:
                self.storage_path.rename(backup_path)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            if backup_path.exists():
                backup_path.unlink()
            self.logger.info(
                "Successfully saved products",
                count=len(self.products),
                path=str(self.storage_path),
            )
        except Exception as e:
            self.logger.error("Failed to save product storage", error=str(e))
            if backup_path.exists() and not self.storage_path.exists():
                backup_path.rename(self.storage_path)
                self.logger.warning("Restored database from backup.")
            raise

    def get_storage_stats(self) -> dict:
        """Gets statistics about the current storage state."""
        try:
            file_size = (
                self.storage_path.stat().st_size
                if self.storage_path.exists()
                else 0
            )
        except FileNotFoundError:
            file_size = 0
        return {
            "total_products": len(self.products),
            "file_path": str(self.storage_path),
            "file_size_bytes": file_size,
            "max_storage_days": self.max_storage_days,
        }