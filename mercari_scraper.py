#!/usr/bin/env python3.9
"""
Mercari.jp scraping utility using undetected-chromedriver to bypass bot detection.
This version is corrected to parse the true Yen price from the aria-label.
"""

import re
import time
import os
import json
from typing import List, Dict, Optional
from urllib.parse import quote

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from logging_config import get_logger


class MercariScraper:
    """
    Handles browser automation and data extraction from Mercari.jp.
    """

    def __init__(self, config: dict):
        self.config = config
        self.logger = get_logger("MercariScraper")
        self.driver = None

    def _create_driver(self) -> uc.Chrome:
        """
        Initializes a new instance of the undetected-chromedriver.
        """
        try:
            options = uc.ChromeOptions()
            if self.config["browser"]["headless"]:
                options.add_argument("--headless=new")

            for option in self.config["browser"]["chrome_options"]:
                options.add_argument(option)

            self.logger.info("Creating new WebDriver instance...")
            driver = uc.Chrome(options=options)
            driver.set_page_load_timeout(
                self.config["browser"]["page_load_timeout"]
            )
            return driver
        except Exception as e:
            self.logger.error(f"Failed to create WebDriver: {e}")
            raise

    def _get_driver(self) -> uc.Chrome:
        """
        Provides a WebDriver instance, creating one if it doesn't exist.
        """
        if self.driver is None:
            self.driver = self._create_driver()
        return self.driver

    def _parse_price_from_label(self, label_text: str) -> Optional[int]:
        """
        Extracts the Yen price from an aria-label string (e.g., "... 17,700円 ...").
        """
        if not label_text:
            return None
        # Regex to find a number (with or without commas) followed by '円'
        match = re.search(r"([\d,]+)円", label_text)
        if match:
            try:
                price_str = match.group(1).replace(",", "")
                return int(price_str)
            except (ValueError, IndexError):
                self.logger.warning(
                    f"Could not parse price from label: '{label_text}'"
                )
                return None
        return None

    def _extract_product_data(self, listing_element) -> Optional[Dict]:
        """
        Extracts all relevant data from a single product listing web element.
        Returns None if the listing is invalid or filtered out.
        """
        selectors = self.config["selectors"]["product_item"]
        try:
            # --- CORRECTED PRICE LOGIC ---
            # Find the specific div that contains the aria-label with the price.
            price_container = listing_element.find_element(
                By.CSS_SELECTOR, "div[role='img']"
            )
            aria_label = price_container.get_attribute("aria-label")
            price = self._parse_price_from_label(aria_label)

            # If we can't get a price, the listing is invalid. Skip it.
            if price is None:
                self.logger.debug(
                    "Could not find Yen price in aria-label. Skipping item."
                )
                return None

            # URL and ID are derived from the 'href' inside the listing.
            link_element = listing_element.find_element(
                By.CSS_SELECTOR, selectors["url"]
            )
            url = link_element.get_attribute("href")
            match = re.search(r"/item/(m\d+)", url)
            if not match:
                return None
            product_id = match.group(1)

            # Title
            title = listing_element.find_element(
                By.CSS_SELECTOR, selectors["title"]
            ).text.strip()

            # Image URL
            try:
                img_element = listing_element.find_element(
                    By.CSS_SELECTOR, selectors["image"]
                )
                image_url = img_element.get_attribute("src")
            except NoSuchElementException:
                image_url = None  # No image found

            return {
                "id": product_id,
                "title": title,
                "price": price,
                "url": url,
                "image_url": image_url,
            }
        except NoSuchElementException as e:
            self.logger.debug(f"Missing required element in product card: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing product card: {e}")
            return None

    def search_products(self, query: str) -> List[Dict]:
        """
        Performs a search on Mercari and scrapes the results.
        """
        try:
            driver = self._get_driver()
            search_url = (
                f"{self.config['mercari_urls']['search_url']}?keyword={quote(query)}"
            )
            self.logger.info(f"Searching for query: '{query}'")
            driver.get(search_url)

            listings_container_selector = self.config["selectors"][
                "listings_container"
            ]
            timeout = self.config["browser"]["implicit_wait"]
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, listings_container_selector)
                )
            )

            # Find all individual product elements
            listing_elements = driver.find_elements(
                By.CSS_SELECTOR, self.config["selectors"]["product_listings"]
            )
            self.logger.info(
                f"Found {len(listing_elements)} potential listings on page."
            )

            products = []
            for element in listing_elements:
                product_data = self._extract_product_data(element)
                if product_data:
                    products.append(product_data)

            self.logger.info(
                f"Successfully extracted {len(products)} valid products."
            )
            return products

        except TimeoutException:
            self.logger.error(
                f"Timed out waiting for product listings for query: '{query}'. "
                "Mercari may be blocking the request or has changed its layout."
            )
            self.take_screenshot(f"failure_{query.replace(' ', '_')}")
            return []
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during search: {e}")
            self.take_screenshot(f"error_{query.replace(' ', '_')}")
            self.close()
            return []

    def take_screenshot(self, filename: str):
        """
        Saves a screenshot of the current browser page for debugging.
        """
        if not self.driver:
            self.logger.warning("Cannot take screenshot, driver is not active.")
            return

        safe_filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        path = os.path.join("screenshots", f"{safe_filename}_{timestamp}.png")

        os.makedirs("screenshots", exist_ok=True)
        try:
            self.driver.save_screenshot(path)
            self.logger.info(f"Screenshot saved to: {path}")
        except Exception as e:
            self.logger.error(f"Failed to save screenshot: {e}")

    def close(self):
        """
        Closes the WebDriver session if it exists.
        """
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver closed successfully.")
            except Exception as e:
                self.logger.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None


if __name__ == "__main__":
    # Example usage for testing the scraper directly
    print("--- Testing MercariScraper ---")
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            test_config = json.load(f)
    except FileNotFoundError:
        print(
            "Error: config.json not found. Please create it before running the test."
        )
        exit(1)

    test_config["browser"]["headless"] = False

    scraper = MercariScraper(test_config)
    try:
        # A query likely to have results
        test_query = "レッツノート CF-SV8"
        products_found = scraper.search_products(test_query)
        if products_found:
            print(
                f"\n[SUCCESS] Found {len(products_found)} products for '{test_query}'."
            )
            print("Sample product:")
            print(json.dumps(products_found[0], indent=2, ensure_ascii=False))
        else:
            print(
                f"\n[FAILURE] Found 0 products. Check logs and screenshots folder."
            )
    finally:
        print("\n--- Test finished. Closing driver. ---")
        scraper.close()