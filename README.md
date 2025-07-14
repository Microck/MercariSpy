# Mercari.jp Monitoring Tool

A sophisticated Python-based monitoring system for tracking new product listings on Mercari.jp with instant Telegram notifications, anti-bot detection bypass, and intelligent image filtering.

## Features

- Real-time Monitoring: Tracks new Mercari listings based on configurable search queries
- Anti-Bot Protection: Uses undetected-chromedriver and human-like behavior patterns
- Instant Notifications: Telegram bot with formatted messages and product images
- Automatic Currency Conversion: Real-time JPY to EUR conversion using live exchange rates
- Persistent State: JSON-based storage to prevent duplicate notifications
- Optional Image Filtering: Background quality filtering using Pillow
- Configurable: All settings via JSON config and .env environment variables
- Structured Logging: JSON logs with rotation and debugging screenshots
- Secure: Secrets managed via .env file

## Project Structure

```
mercari_monitor/
├── .env                        # Environment variables (secrets)
├── config.json                 # Configurable settings and CSS selectors
├── requirements.txt            # Python dependencies
├── search_queries.txt          # Search terms for monitoring
├── mercari_known_products.json # Persistent state storage
├── main.py                     # Application orchestrator
├── mercari_scraper.py          # Web scraping with Selenium
├── telegram_notifier.py        # Telegram bot and currency conversion
├── product_storage.py          # JSON-based product state management
├── image_filter.py             # Background filtering with Pillow
├── logging_config.py           # Structured JSON logging setup
├── logs/                       # Rotating log files
└── screenshots/                # Debug screenshots on error
```

## Installation

### 1. Setup Project
```bash
mkdir -p Projects/mercari_monitor
cd Projects/mercari_monitor
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.example` to `.env` and fill in your values:

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Optional Exchange Rate API
EXCHANGE_RATE_API_KEY=your_api_key_here
```

### 4. Setup Telegram Bot
1. Message [@BotFather](https://t.me/BotFather)
2. Create new bot: `/newbot`
3. Get bot token and add to `.env`
4. Get chat ID: Message [@userinfobot](https://t.me/userinfobot)

### 5. Configure Queries
Edit `search_queries.txt`:
```
# Mercari search terms
iPhone 14 Pro
MacBook Air M2
Sony WH-1000XM5
Nintendo Switch OLED
```

## Usage

### Basic Usage
```bash
# Run once
python main.py --once

# Run every 15 minutes
python main.py --interval 15

# With custom config
python main.py --config custom_config.json --interval 10
```

### Keyboard Controls
- **Ctrl+C**: Gracefully shutdown monitoring
- **Ctrl+Z**: Emergency stop (may leave processes running)

## Configuration

### Key Settings in config.json

```json
{
  "browser": {
    "headless": false,
    "window_size": [1920, 1080],
    "page_load_timeout": 30
  },
  "filtering": {
    "min_price_jpy": 100,
    "max_price_jpy": 50000,
    "background_filter_enabled": false
  },
  "notifications": {
    "rate_limit_delay": 1
  }
}
```

### CSS Selectors (Easy Updates)
When Mercari changes layout, update selectors without code changes:

```json
{
  "selectors": {
    "product_listings": "[data-testid='item-list'] > div",
    "product_item": {
      "title": "span[data-testid='item-title']",
      "price": "span[data-testid='item-price']",
      "image": "img[src*='merc-images']"
    }
  }
}
```

## Advanced Features

### Image Filtering
Enable smart background filtering:

```json
{
  "filtering": {
    "background_filter_enabled": true,
    "max_solid_color_ratio": 0.7,
    "background_color_threshold": 240
  }
}
```

### Structured Logging
All logs are JSON-formatted with rotation:
```bash
tail -f logs/mercari_monitor.json
jq . logs/mercari_monitor.json  # Pretty print
```

## Troubleshooting

### Common Issues

#### Bot Authorization Failed
```bash
# Check .env format
cat .env
# Ensure no quotes around values
```

#### No Products Found
1. Check `search_queries.txt` format
2. Verify selectors in `config.json`
3. Check logs for Mercari layout changes
4. Test with broader search terms

#### Rate Limiting
- Telegram: ~30 messages/minute
- Mercari: Built-in delays prevent blocking

### Debug Screenshots
Error screenshots saved to `screenshots/` folder:
- Format: `search_error_<timestamp>.png`
- Includes current page state
- Useful for diagnosing layout changes

## Monitoring Stats

Access product storage statistics:

```python
from product_storage import ProductStorage
storage = ProductStorage()
print(storage.get_storage_stats())
```

Example output:
```json
{
  "total": 254,
  "last_24h": 12,
  "last_7d": 89,
  "file_size_bytes": 42536
}
```

## Maintenance

### CSS Selector Updates
1. Use browser dev tools (F12)
2. Find stable selectors (data-testid preferred)
3. Update `config.json`
4. Restart monitoring

### Log Cleanup
Logs auto-rotate at 10MB with 5 backup files old

### Product Storage Cleanup
Old products cleaned automatically every 7 days
Manual cleanup: `storage.cleanup_old_products()`

## Example Notifications

### Single Product
```
New Product Found

**Nintendo Switch OLED - White**
¥32,800 (~€211.61)

_Found: 2024-01-15 14:30:22_
_Query: Nintendo Switch_
[View on Mercari](https://www.mercari.jp/item/m123456789/)
```

### Batch Notification
```
3 New Products Found

_Query: iPhone 14_

**Products:**
1. **iPhone 14 128GB Blue** ¥89,800 (~€579.36)
[Link](https://www.mercari.jp/item/m111111111/)

2. **iPhone 14 Pro Max** ¥120,500 (~€777.42)
[Link](https://www.mercari.jp/item/m222222222/)

... and 1 more products
```

## License

This project is educational software. Users are responsible for complying with Mercari terms of service and local laws.