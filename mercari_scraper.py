#!/usr/bin/env python3.9
import re
import time
import json
from typing import List, Dict, Optional
from urllib.parse import urlencode, quote

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from logging_config import get_logger
import os


class MercariScraper:
    """
    Mercari scraping utility using undetected-chromedriver to bypass detection.
    Uses configurable CSS selectors for robust scraping maintenance.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = get_logger("MercariScraper")
        self.driver = None
        
    def _create_driver(self) -> uc.Chrome:
        """Create and configure Chrome WebDriver."""
        try:
            options = uc.ChromeOptions()
            
            # Apply Chrome options from config
            for option in self.config["browser"]["chrome_options"]:
                options.add_argument(option)
            
            if self.config["browser"]["headless"]:
                options.add_argument("--headless")
            
            # Set window size
            window_size = self.config["browser"]["window_size"]
            options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
            
            # Additional anti-detection options
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins-discovery")
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            driver = uc.Chrome(options=options)
            driver.set_page_load_timeout(self.config["browser"]["page_load_timeout"])
            
            return driver
            
        except Exception as e:
            self.logger.error("Failed to create WebDriver", error=str(e))
            raise
    
    def _wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """Wait for element to be present and visible."""
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            return True
        except TimeoutException:
            return False
    
    def _parse_price(self, price_text: str) -> int:
        """Parse price from Mercari format (¥1,234 → 1234)."""
        try:
            # Remove currency symbols, commas, and spaces
            cleaned = re.sub(r'[¥,\s]', '', price_text)
            # Handle cases like "¥100-¥500"
            if '-' in cleaned:
                parts = cleaned.split('-')
                return int(parts[0])
            # Handle cases like "商品価格"
            if cleaned.isdigit():
                return int(cleaned)
            return 0
        except Exception:
            return 0
    
    def _extract_product_data(self, element) -> Optional[Dict]:
        """Extract product data from a single listing element."""
        try:
            soup = BeautifulSoup(element.get_attribute('outerHTML'), 'html.parser')
            selectors = self.config["selectors"]["product_item"]
            
            # Extract product ID from URL
            product_url_elem = element.find_element(By.CSS_SELECTOR, selectors["id"])
            product_url = product_url_elem.get_attribute('href')
            product_id = re.search(r'/item/(\w+)', product_url)
            if not product_id:
                return None
            
            # Get price and apply filtering
            price_element = element.find_element(By.CSS_SELECTOR, selectors["price"])
            price_text = price_element.text.strip()
            price_jpy = self._parse_price(price_text)
            
            # Apply price filtering
            min_price = self.config["filtering"]["min_price_jpy"]
            max_price = self.config["filtering"]["max_price_jpy"]
            
            if price_jpy < min_price or (max_price > 0 and price_jpy > max_price):
                return None
            
            # Extract other data
            title_element = element.find_element(By.CSS_SELECTOR, selectors["title"])
            title = title_element.text.strip()
            
            # Apply keyword exclusions
            exclude_keywords = [kw.lower() for kw in self.config["filtering"]["exclude_keywords"]]
            title_lower = title.lower()
            
            if any(keyword in title_lower for keyword in exclude_keywords):
                return None
            
            # Get image URL
            try:
                image_element = element.find_element(By.CSS_SELECTOR, selectors["image"])
                image_url = image_element.get_attribute('src')
                if not image_url or image_url.startswith('data:'):
                    image_url = None
            except NoSuchElementException:
                image_url = None
            
            product_data = {
                'id': product_id.group(1),
                'title': title,
                'price': price_jpy,
                'price_text': price_text,
                'url': self.config["mercari_urls"]["base_url"] + product_url,
                'image_url': image_url,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return product_data
            
        except Exception as e:
            self.logger.debug("Failed to extract product data", error=str(e))
            return None
    
    def search_products(self, query: str, limit: int = 100) -> List[Dict]:
        """
        Search for products on Mercari by query.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of product dictionaries
        """
        products = []
        
        try:
            if not self.driver:
                self.driver = self._create_driver()
            
            self.logger.info(f"Searching for query: {query}")
            
            # Construct search URL
            search_params = {
                'keyword': query,
                'status=sold_out': 'false',  # Exclude sold items
                'status=on_sale': 'true'     # Only available items
            }
            
            search_url = f"{self.config['mercari_urls']['search_url']}?{urlencode(search_params)}"
            
            # Navigate to search page
            self.driver.get(search_url)
            time.sleep(self.config["timing"]["page_transition_delay"])
            
            # Wait for product listings to load
            if not self._wait_for_element(self.config["selectors"]["product_listings"]):
                self.logger.warning("No product listings found")
                return products
            
            # Scroll to load more products (simulate real user)
            self._scroll_to_load_products(limit)
            
            # Find all product listings
            listings = self.driver.find_elements(
                By.CSS_SELECTOR, 
                self.config["selectors"]["product_listings"] + " " + self.config["selectors"]["product_listings"]
            )
            
            # Extract product data
            for listing in listings:
                if len(products) >= limit:
                    break
                
                product_data = self._extract_product_data(listing)
                if product_data:
                    products.append(product_data)
            
            self.logger.info(f"Found {len(products)} products for query: {query}")
            return products
            
        except Exception as e:
            self.logger.error(f"Search failed for query '{query}': {e}")
            # Take screenshot on error
            self.take_screenshot(f"search_error_{int(time.time())}")
            return products
    
    def _scroll_to_load_products(self, desired_count: int):
        """Scroll down to load more products."""
        current_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scrolls = 5
        
        while len(self.driver.find_elements(By.CSS_SELECTOR, self.config["selectors"]["product_listings"])) < desired_count and scroll_attempts < max_scrolls:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for lazy loading
            scroll_attempts += 1
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == current_height:
                try:
                    # Try to click load more button
                    load_more_btn = self.driver.find_element(By.CSS_SELECTOR, self.config["selectors"]["load_more_button"])
                    if load_more_btn.is_displayed():
                        load_more_btn.click()
                        time.sleep(2)
                except NoSuchElementException:
                    break
            current_height = new_height
    
    def take_screenshot(self, filename: str) -> str:
        """Take a screenshot for debugging."""
        try:
            screenshot_path = f"screenshots/{filename}.png"
            os.makedirs("screenshots", exist_ok=True)
            
            if self.driver:
                self.driver.save_screenshot(screenshot_path)
                self.logger.info(f"Screenshot saved: {screenshot_path}")
                return screenshot_path
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
        return ""
    
    def test_connection(self) -> bool:
        """Test if we can connect to Mercari."""
        try:
            if not self.driver:
                self.driver = self._create_driver()
            
            self.driver.get(self.config["mercari_urls"]["base_url"])
            
            # Check if page loads correctly
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            self.logger.info("Successfully connected to Mercari")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Mercari: {e}")
            return False
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.logger.info("WebDriver closed")
            except Exception as e:
                self.logger.error(f"Error closing WebDriver: {e}")


if __name__ == "__main__":
    # Test the scraper
    import json
    
    # Load config
    with open("config.json", 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    scraper = MercariScraper(config)
    
    try:
        # Test connection
        if scraper.test_connection():
            print("✓ Connection successful")
            
            # Test search
            products = scraper.search_products("iPhone")
            print(f"✓ Found {len(products)} products")
            
            if products:
                print("\nSample product:")
                print(json.dumps(products[0], indent=2, ensure_ascii=False))
        else:
            print("✗ Connection failed")
            
    finally:
        scraper.close()