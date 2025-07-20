#!/usr/bin/env python3.9
"""
Mercari.jp Monitoring Tool
Main orchestrator for automated product monitoring and notification system.
"""

import json
import time
import schedule
from dotenv import load_dotenv
from pathlib import Path

from logging_config import get_logger
from mercari_scraper import MercariScraper
from telegram_notifier import TelegramNotifier
from product_storage import ProductStorage
from image_filter import ImageFilter

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger(__name__)


class MercariMonitor:
    """Main orchestrator for the Mercari monitoring system."""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = self.load_config()

        # Initialize components
        self.logger = get_logger("MercariMonitor")
        # --- CORRECTED to match your config.json ---
        self.storage = ProductStorage(
            max_storage_days=self.config["storage"]["cleanup_after_days"]
        )
        self.scraper = MercariScraper(self.config)
        self.notifier = TelegramNotifier(self.config)
        self.image_filter = ImageFilter(self.config)

        self.logger.info(
            "Mercari Monitor initialized",
            headless=self.config["browser"]["headless"],
        )

    def load_config(self) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load config", error=str(e))
            raise

    def load_search_queries(self) -> list:
        """Load search queries from text file."""
        try:
            queries_file = Path("search_queries.txt")
            if not queries_file.exists():
                self.logger.warning(
                    "search_queries.txt not found, creating empty file"
                )
                queries_file.touch()
                return []

            with open(queries_file, "r", encoding="utf-8") as f:
                queries = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]

            self.logger.info(
                "Loaded search queries", query_count=len(queries)
            )
            return queries

        except Exception as e:
            self.logger.error("Failed to load search queries", error=str(e))
            return []

    def process_query(self, query: str) -> None:
        """Process a single search query and notify of new products."""
        try:
            self.logger.info("Processing query", query=query)

            products = self.scraper.search_products(query)
            self.logger.debug(
                "Products found by scraper",
                count=len(products),
                query=query,
            )

            new_products = []
            for product in products:
                if not self.storage.is_product_known(product["id"]):
                    # Apply background filter if enabled
                    if self.config["filtering"]["background_filter_enabled"]:
                        try:
                            if not self.image_filter.filter_background(
                                product["image_url"]
                            ):
                                self.logger.debug(
                                    "Skipped product due to background filter",
                                    product_id=product["id"],
                                )
                                continue
                        except Exception:
                            self.logger.log_exception(
                                "Background filter failed",
                                product_id=product["id"],
                            )

                    new_products.append(product)
                    self.storage.add_product(product)

            if new_products:
                self.logger.info(
                    "Found new products, attempting to send notification...",
                    count=len(new_products),
                    query=query,
                )
                self.notifier.send_notifications(new_products, query)
            else:
                self.logger.debug("No new products for query", query=query)

        except Exception:
            # --- THIS IS THE CRITICAL FIX ---
            # This will now print the full, detailed error traceback from the notifier
            # instead of hiding it.
            self.logger.log_exception(
                "A critical error occurred during process_query",
                query=query,
            )

    def run_once(self) -> None:
        """Run monitoring once for all queries."""
        try:
            queries = self.load_search_queries()
            if not queries:
                self.logger.warning("No search queries configured. Skipping run.")
                return

            self.logger.info("Starting monitoring cycle")

            for query in queries:
                self.process_query(query)
                time.sleep(self.config["timing"]["search_delay"])

            self.storage.cleanup_old_products()
            self.logger.info("Monitoring cycle completed")

        except Exception as e:
            self.logger.error("Monitoring cycle failed", error=str(e))

    def run_continuous(self, interval_minutes: int = 15) -> None:
        """Run monitoring continuously at specified intervals."""
        self.logger.info(
            "Starting continuous monitoring",
            interval_minutes=interval_minutes,
        )
        schedule.every(interval_minutes).minutes.do(self.run_once)
        try:
            self.run_once()
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error("Continuous monitoring failed", error=str(e))

    def close(self):
        """Cleanup resources and save data."""
        try:
            self.logger.info("Saving product database...")
            self.storage.save_products()
            self.scraper.close()
            self.logger.info("Mercari Monitor closed")
        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Mercari.jp product monitor")
    parser.add_argument(
        "--once", action="store_true", help="Run once and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Monitoring interval in minutes",
    )
    parser.add_argument(
        "--config", default="config.json", help="Configuration file path"
    )
    args = parser.parse_args()
    monitor = None
    try:
        monitor = MercariMonitor(args.config)
        if args.once:
            monitor.run_once()
        else:
            monitor.run_continuous(args.interval)
    except Exception:
        # --- CORRECTED to use your logger's specific method ---
        logger.log_exception("A fatal error occurred in main:")
    finally:
        if monitor:
            monitor.close()


if __name__ == "__main__":
    main()