import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from logging_config import get_logger


class ProductStorage:
    """
    Manages persistent storage of known products to prevent duplicate notifications.
    Uses JSON file-based storage with automatic cleanup of old entries.
    """
    
    def __init__(self, storage_path: str = "mercari_known_products.json"):
        self.storage_path = Path(storage_path)
        self.logger = get_logger("ProductStorage")
        self.products: Dict[str, dict] = {}
        self.max_storage_days = 7
        
        self._load_existing_products()
    
    def _load_existing_products(self):
        """Load existing products from storage file."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.products = data.get('products', {})
                    self.logger.info(f"Loaded {len(self.products)} known products")
            else:
                self.logger.info("No existing product storage found")
                self._create_empty_storage()
                
        except Exception as e:
            self.logger.error(f"Failed to load product storage: {e}")
            self.products = {}
    
    def _create_empty_storage(self):
        """Create empty storage file."""
        self.save_to_file()
    
    def add_product(self, product: dict) -> bool:
        """
        Add a product to known products.
        
        Args:
            product: Product dictionary with 'id', 'title', 'price', etc.
        
        Returns:
            bool: True if product was added, False if already exists
        """
        product_id = str(product['id'])
        
        if product_id in self.products:
            return False
        
        self.products[product_id] = {
            'id': product_id,
            'title': product.get('title', ''),
            'price': product.get('price', 0),
            'url': product.get('url', ''),
            'image_url': product.get('image_url', ''),
            'added_at': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat()
        }
        
        self.save_to_file()
        return True
    
    def is_product_known(self, product_id: str) -> bool:
        """Check if a product is already known."""
        return str(product_id) in self.products
    
    def get_product_info(self, product_id: str) -> Optional[dict]:
        """Get information about a known product."""
        return self.products.get(str(product_id))
    
    def get_all_products(self) -> List[dict]:
        """Get all known products."""
        return list(self.products.values())
    
    def get_recent_products(self, hours: int = 24) -> List[dict]:
        """Get products added in the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = []
        
        for product in self.products.values():
            try:
                added_time = datetime.fromisoformat(product['added_at'])
                if added_time > cutoff:
                    recent.append(product)
            except ValueError:
                continue
        
        return recent
    
    def get_products_count(self) -> dict:
        """Get various counts of stored products."""
        total = len(self.products)
        
        # Count products added in last 24 hours
        recent_24h = self.get_recent_products(24)
        recent_7d = self.get_recent_products(24 * 7)
        
        return {
            'total': total,
            'last_24h': len(recent_24h),
            'last_7d': len(recent_7d)
        }
    
    def cleanup_old_products(self, max_days: Optional[int] = None) -> int:
        """
        Remove old products from storage.
        
        Args:
            max_days: Maximum days to keep products. Defaults to 7.
        
        Returns:
            int: Number of products removed
        """
        if max_days is None:
            max_days = self.max_storage_days
        
        cutoff = datetime.now() - timedelta(days=max_days)
        removed_count = 0
        
        products_to_remove = []
        
        for product_id, product in self.products.items():
            try:
                added_time = datetime.fromisoformat(product['added_at'])
                if added_time < cutoff:
                    products_to_remove.append(product_id)
            except ValueError:
                # If date parsing fails, consider it old
                products_to_remove.append(product_id)
        
        # Remove old products
        for product_id in products_to_remove:
            del self.products[product_id]
            removed_count += 1
        
        if removed_count > 0:
            self.save_to_file()
            self.logger.info(f"Removed {removed_count} old products")
        
        return removed_count
    
    def save_to_file(self):
        """Save products to storage file."""
        try:
            data = {
                'products': self.products,
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.products)
            }
            
            # Create backup of existing file
            if self.storage_path.exists():
                backup_path = self.storage_path.with_suffix('.backup.json')
                self.storage_path.rename(backup_path)
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Remove backup if save successful
            backup_path = self.storage_path.with_suffix('.backup.json')
            if backup_path.exists():
                backup_path.unlink()
                
            self.logger.debug(f"Saved {len(self.products)} products to storage")
            
        except Exception as e:
            self.logger.error(f"Failed to save product storage: {e}")
            # Restore backup
            backup_path = self.storage_path.with_suffix('.backup.json')
            if backup_path.exists():
                backup_path.rename(self.storage_path)
            raise
    
    def clear_all_products(self) -> bool:
        """
        Clear all stored products (use with caution).
        
        Returns:
            bool: True if successful
        """
        try:
            old_count = len(self.products)
            self.products.clear()
            self.save_to_file()
            self.logger.warning(f"Cleared all products ({old_count} removed)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear products: {e}")
            return False
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics for monitoring."""
        return {
            'file_exists': self.storage_path.exists(),
            'file_size_bytes': self.storage_path.stat().st_size if self.storage_path.exists() else 0,
            **self.get_products_count(),
            'last_updated': datetime.now().isoformat()
        }