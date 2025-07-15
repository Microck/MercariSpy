#!/usr/bin/env python3.9
import os
import time
import requests
from datetime import datetime
from typing import List, Dict

from logging_config import get_logger


class TelegramNotifier:
    """
    Telegram bot notification system with a fixed JPY to EUR currency conversion.
    Provides instant notifications with product details and images.
    """

    def __init__(self, config: dict):
        self.config = config
        self.logger = get_logger("TelegramNotifier")

        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")

        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        # Default JPY to EUR rate. Update this value if the rate changes significantly.
        # Example: If 1 EUR = 155 JPY, then 1 JPY = 1/155 = 0.0064 EUR
        self.current_exchange_rate = 0.0064

    def _get_exchange_rate(self) -> float:
        """
        Returns the default exchange rate to avoid slow and unreliable API calls.
        """
        self.logger.debug("Using default exchange rate to prevent API timeout.")
        return self.current_exchange_rate

    def _convert_jpy_to_eur(self, jpy_amount: int) -> float:
        """Convert JPY amount to EUR using the stored rate."""
        rate = self._get_exchange_rate()
        eur_amount = jpy_amount * rate
        return round(eur_amount, 2)
        
    def _format_price_message(self, jpy_price: int, eur_price: float) -> str:
        """Format price message with both currencies, escaping all special characters."""
        # Format the euro price to a string and escape the decimal point.
        eur_price_str = f"{eur_price:.2f}".replace('.', '\\.')
        
        # Construct the final string, escaping '(', '~', and ')' for Telegram.
        return f"¥{jpy_price:,} \\(\\~€{eur_price_str}\\)"
        
        # Construct the final string with escaped parentheses and the escaped price
        return f"¥{jpy_price:,} \\(~€{escaped_eur_price}\\)"

    def _format_product_message(self, product: Dict, query: str) -> str:
        """Format individual product message for Telegram."""
        eur_price = self._convert_jpy_to_eur(product['price'])
        price_msg = self._format_price_message(product['price'], eur_price)

        # Using MarkdownV2 requires escaping special characters.
        # This is a basic set of characters to escape.
        title = product['title']
        for char in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
            title = title.replace(char, f'\\{char}')

        message = f"🚀 *New Product Found*\n\n"
        message += f"*{title}*\n"
        message += f"{price_msg}\n\n"
        message += f"Query: `{query}`\n"
        message += f"[View on Mercari]({product['url']})"

        return message

    def send_telegram_message(self, message: str, photo_url: str = None) -> bool:
        """Sends a message to Telegram, trying photo first, then text."""
        time.sleep(self.config["notifications"]["rate_limit_delay"])

        payload = {'chat_id': self.chat_id, 'parse_mode': 'MarkdownV2'}
        
        try:
            # Try sending with a photo first if available
            if photo_url:
                payload.update({'photo': photo_url, 'caption': message[:1024]})
                url = f"{self.base_url}/sendPhoto"
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    self.logger.debug("Telegram photo message sent successfully.")
                    return True
                else:
                    self.logger.warning(f"Failed to send photo, trying text only. Reason: {response.text}")

            # Fallback to text-only message if photo fails or is not provided
            payload.pop('photo', None)
            payload.pop('caption', None)
            payload['text'] = message[:4096]
            url = f"{self.base_url}/sendMessage"
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                self.logger.debug("Telegram text message sent successfully.")
                return True
            else:
                self.logger.error(f"Failed to send Telegram message: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Exception while sending Telegram message: {e}")
            return False

    def send_notification(self, product: Dict, query: str) -> bool:
        """Formats and sends a notification for a single product."""
        try:
            message = self._format_product_message(product, query)
            return self.send_telegram_message(message, product.get('image_url'))
        except Exception as e:
            self.logger.error(f"Error formatting single product notification: {e}")
            return False

    def send_notifications(self, products: List[Dict], query: str):
        """Main entry point to send notifications for a list of products."""
        if not products:
            return

        self.logger.info(f"Sending {len(products)} notifications for query: '{query}'")
        for product in products:
            self.send_notification(product, query)


if __name__ == "__main__":
    # This block allows for direct testing of the notifier script.
    print("--- Testing TelegramNotifier ---")
    
    # Load environment variables for testing
    from dotenv import load_dotenv
    load_dotenv()
    
    # Load config for testing
    try:
        with open("config.json", 'r', encoding="utf-8") as f:
            test_config = json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found. Please create it before running the test.")
        exit(1)
    except Exception as e:
        print(f"Error loading config.json: {e}")
        exit(1)

    try:
        notifier = TelegramNotifier(test_config)
        
        print("Sending test notification...")
        test_product = {
            'id': 'm123456789',
            'title': 'Test Product - Nintendo Switch (OLED Model)!',
            'price': 35000,
            'url': 'https://jp.mercari.com/item/m123456789',
            'image_url': 'https://static.mercdn.net/c!/w=240/thumb/photos/m19215340744_1.jpg' # Example image
        }
        
        success = notifier.send_notification(test_product, "test query")
        
        if success:
            print("[SUCCESS] Test notification sent. Please check your Telegram.")
        else:
            print("[FAILURE] Failed to send test notification. Check logs and .env file.")
            
    except ValueError as e:
        print(f"Error: {e}. Make sure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are in your .env file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")