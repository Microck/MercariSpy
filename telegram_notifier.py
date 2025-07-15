#!/usr/bin/env python3.9
import os
import time
import requests
from datetime import datetime
from typing import List, Dict
from decimal import Decimal

from logging_config import get_logger


class TelegramNotifier:
    """
    Telegram bot notification system with JPY to EUR currency conversion.
    Provides instant notifications with product details and images.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = get_logger("TelegramNotifier")
        
        # Load credentials from environment
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.current_exchange_rate = 155.0  # Default JPY to EUR rate
        
    def _get_exchange_rate(self, base_currency: str = 'JPY', target_currency: str = 'EUR') -> float:
        """
        Get current exchange rate from forex API.
        
        Args:
            base_currency: Base currency (typically 'JPY')
            target_currency: Target currency (typically 'EUR')
            
        Returns:
            float: Exchange rate
        """
        try:
            # Using forex-python for currency conversion
            from forex_python.converter import CurrencyRates
            
            c = CurrencyRates()
            rate = c.get_rate(base_currency, target_currency)
            
            self.current_exchange_rate = rate
            self.logger.info(f"Exchange rate updated: 1 {base_currency} = {rate:.2f} {target_currency}")
            
            return rate
            
        except Exception as e:
            self.logger.warning(f"Failed to get exchange rate, using cached value: {e}")
            return self.current_exchange_rate
    
    def _convert_jpy_to_eur(self, jpy_amount: int) -> float:
        """Convert JPY amount to EUR."""
        rate = self._get_exchange_rate()
        eur_amount = jpy_amount * rate / 100
        return round(eur_amount, 2)
    
    def _format_price_message(self, jpy_price: int, eur_price: float) -> str:
        """Format price message with both currencies."""
        return f"¥{jpy_price:,} (~€{eur_price:.2f})"
    
    def _format_product_message(self, product: Dict, query: str) -> str:
        """Format individual product message."""
        eur_price = self._convert_jpy_to_eur(product['price'])
        price_msg = self._format_price_message(product['price'], eur_price)
        
        message = f"🚀 **New Product Found**\n\n"
        message += f"**{product['title']}**\n"
        message += f"{price_msg}\n\n"
        
        if 'scraped_at' in product:
            message += f"_Found: {product['scraped_at']}_\n"
        
        message += f"_Query: {query}_\n\n"
        message += f"[View on Mercari]({product['url']})"
        
        return message
    
    def send_telegram_message(self, message: str, photo_url: str = None) -> bool:
        """
        Send a message to Telegram.
        
        Args:
            message: Message text (Markdown format)
            photo_url: Optional photo URL to send with message
            
        Returns:
            bool: Success status
        """
        try:
            # Rate limiting
            time.sleep(self.config["notifications"]["rate_limit_delay"])
            
            if photo_url and self.config["notifications"].get("max_images_per_notification", 5) > 0:
                # Send photo with caption
                payload = {
                    'chat_id': self.chat_id,
                    'photo': photo_url,
                    'caption': message[:1024],  # Telegram caption limit
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': True
                }
                
                url = f"{self.base_url}/sendPhoto"
                response = requests.post(url, json=payload, timeout=30)
                
            else:
                # Send text message only
                payload = {
                    'chat_id': self.chat_id,
                    'text': message[:4096],  # Telegram message limit
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': False
                }
                
                url = f"{self.base_url}/sendMessage"
                response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                self.logger.debug("Telegram message sent successfully")
                return True
            else:
                error_data = response.json()
                self.logger.error(f"Failed to send Telegram message: {error_data}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def send_notification_batch(self, products: List[Dict], query: str) -> bool:
        """
        Send a batch notification for multiple products.
        
        Args:
            products: List of product dictionaries
            query: Search query that found these products
            
        Returns:
            bool: Success status
        """
        try:
            if len(products) == 1:
                # Send single product notification
                return self.send_notification(products[0], query)
            
            # Build batch message
            total_products = len(products)
            total_jpy = sum(p['price'] for p in products)
            
            # Use current exchange rate for total
            rate = self._get_exchange_rate()
            total_eur = total_jpy * rate / 100
            
            message = f"🎯 **{total_products} New Products Found**\n\n"
            message += f"_Query: {query}_\n\n"
            message += "**Products:**\n"
            
            # Limit to prevent message too long
            max_display = min(3, len(products))
            
            for i, product in enumerate(products[:max_display]):
                eur_price = self._convert_jpy_to_eur(product['price'])
                price_msg = self._format_price_message(product['price'], eur_price)
                
                truncated_title = product['title'][:50] + "..." if len(product['title']) > 50 else product['title']
                message += f"{i+1}. **{truncated_title}** {price_msg}\n"
                message += f"[Link]({product['url']})\n\n"
            
            if len(products) > max_display:
                hidden_count = len(products) - max_display
                message += f"_... and {hidden_count} more products_\n"
            
            # Try to send with image of first product
            image_url = products[0].get('image_url') if products else None
            return self.send_telegram_message(message, image_url)
            
        except Exception as e:
            self.logger.error(f"Error sending batch notification: {e}")
            return False
    
    def send_notification(self, product: Dict, query: str) -> bool:
        """
        Send single product notification.
        
        Args:
            product: Product dictionary
            query: Search query
            
        Returns:
            bool: Success status
        """
        try:
            message = self._format_product_message(product, query)
            return self.send_telegram_message(message, product.get('image_url'))
            
        except Exception as e:
            self.logger.error(f"Error sending product notification: {e}")
            return False
    
    def send_error_notification(self, error_message: str, context: str = None) -> bool:
        """Send error notification to Telegram."""
        try:
            message = f"⚠️ **Mercari Monitor Error**\n\n"
            
            if context:
                message += f"Context: {context}\n\n"
            
            message += f"Error: {error_message}\n\n"
            message += f"_Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
            
            return self.send_telegram_message(message)
            
        except Exception as e:
            self.logger.error(f"Failed to send error notification: {e}")
            return False
    
    def get_bot_info(self) -> dict:
        """Get information about the Telegram bot."""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                return response.json().get('result', {})
            else:
                self.logger.error(f"Failed to get bot info: {response.json()}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Error getting bot info: {e}")
            return {}
    
    def verify_credentials(self) -> bool:
        """Verify that bot credentials are valid."""
        try:
            bot_info = self.get_bot_info()
            if bot_info and 'id' in bot_info:
                self.logger.info(f"Bot credentials valid: {bot_info.get('username', 'Unknown')}")
                return True
            else:
                self.logger.error("Invalid bot credentials")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to verify credentials: {e}")
            return False
    
    def send_notifications(self, products: List[Dict], query: str) -> bool:
        """Main method to send notifications for new products."""
        try:
            if not products:
                return True
            
            # Batch notifications for efficiency
            if len(products) <= 5:
                return self.send_notification_batch(products, query)
            else:
                # Split large batches
                batch_size = 3
                for i in range(0, len(products), batch_size):
                    batch = products[i:i+batch_size]
                    success = self.send_notification_batch(batch, f"{query} (Batch {i//batch_size + 1})")
                    if not success:
                        return False  # Stop on first failure
                return True
                
        except Exception as e:
            self.logger.error(f"Error sending notifications: {e}")
            self.send_error_notification(str(e), f"Notification for query: {query}")
            return False


if __name__ == "__main__":
    import json
    
    # Test configuration
    with open("config.json", 'r') as f:
        config = json.load(f)
    
    notifier = TelegramNotifier(config)
    
    # Test bot credentials
    if notifier.verify_credentials():
        print("✓ Bot credentials verified")
        
        # Test notification
        test_product = {
            'id': 'test123',
            'title': 'Test Product - Nintendo Switch',
            'price': 25000,
            'url': 'https://www.mercari.jp/item/test123',
            'scraped_at': datetime.now().isoformat()
        }
        
        success = notifier.send_notification(test_product, "test query")
        print(f"Notification sent: {success}")
    else:
        print("✗ Bot credentials invalid")