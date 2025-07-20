#!/usr/bin/env python3.9
"""
Manages persistent storage of known products to prevent duplicate notifications.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from logging_config import get_logger


class ProductStorage:
    """
    Manages a persistent JSON database of products to track seen items.

    This class handles loading from and saving to a file, but crucially,
    it does not save on every modification. The calling class should explicitly
    call `save_products()` to persist changes to disk after a batch of
    operations is complete to ensure good performance.
    """

    def __init__(
        self,
        storage_path: str = "mercari_known_products.json",
        max_storage_days: int = 7,
    ):
        """
        Initializes the ProductStorage.

        Args:
            storage_path: The path to the JSON file for storage.
            max_storage_days: How long to keep product records before cleanup.
        """
        self.storage_path = Path(storage_path)
        self.logger = get_logger("ProductStorage")
        self.products: Dict[str, dict] = {}
        self.max_storage_days = max_storage_days

        self._load_from_disk()

    def _load_from_disk(self):
        """Loads existing products from the storage file into memory."""
        if not self.storage_path.exists():
            # MODIFIED: Switched to structured logging format
            self.logger.info(
                "No existing product storage file found. A new one will be created on save.",
                path=str(self.storage_path),
            )
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.products = data.get("products", {})
                # MODIFIED: Switched to structured logging format
                self.logger.info(
                    "Loaded known products",
                    count=len(self.products),
                    path=str(self.storage_path),
                )
        except (IOError, json.JSONDecodeError) as e:
            # MODIFIED: Switched to structured logging format
            self.logger.error(
                "Failed to load product storage file. Starting with empty database.",
                error=e,
            )
            self.products = {}

    def add_product(self, product: dict):
        """
        Adds a product to the in-memory storage. Does NOT save to disk.

        Args:
            product: Product dictionary containing at least an 'id'.
        """
        product_id = str(product["id"])
        if product_id in self.products:
            return  # Product already exists

        self.products[product_id] = {
            "id": product_id,
            "title": product.get("title", ""),
            "price": product.get("price", 0),
            "url": product.get("url", ""),
            "image_url": product.get("image_url", ""),
            "added_at": datetime.now().isoformat(),
        }
        # MODIFIED: Switched to structured logging format
        self.logger.debug(
            "Added product to in-memory store", product_id=product_id
        )

    def is_product_known(self, product_id: str) -> bool:
        """Checks if a product ID is in the in-memory storage."""
        return str(product_id) in self.products

    def cleanup_old_products(self) -> int:
        """
        Removes old products from the in-memory storage. Does NOT save to disk.

        Returns:
            The number of products removed.
        """
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
            # MODIFIED: Switched to structured logging format
            self.logger.info(
                "Cleaned up old products from memory", count=removed_count
            )

        return removed_count

    def save_products(self):
        """
        Saves the current state of the in-memory product database to the JSON file.
        """
        backup_path = self.storage_path.with_suffix(".backup.json")
        try:
            data_to_save = {
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "total_count": len(self.products),
                },
                "products": self.products,
            }

            if self.storage_path.exists():
                self.storage_path.rename(backup_path)

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)

            if backup_path.exists():
                backup_path.unlink()

            # MODIFIED: Switched to structured logging format
            self.logger.info(
                "Successfully saved products",
                count=len(self.products),
                path=str(self.storage_path),
            )

        except (IOError, TypeError) as e:
            # MODIFIED: Switched to structured logging format
            self.logger.error("Failed to save product storage", error=e)
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