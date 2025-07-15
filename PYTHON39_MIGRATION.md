# Python 3.9 Migration Guide

This guide provides step-by-step instructions for migrating the Mercari Monitor from Python 3.12 to Python 3.9.

## ✅ Migration Status

- **Code Compatibility**: ✅ Already Python 3.9 compatible
- **Dependencies**: ✅ All dependencies support Python 3.9
- **Virtual Environment**: ⚠️ Needs recreation with Python 3.9
- **Documentation**: ✅ Updated with Python 3.9 instructions

## 🔧 Step-by-Step Migration

### 1. Install Python 3.9

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-pip -y
```

#### CentOS/RHEL
```bash
sudo yum install epel-release -y
sudo yum install python39 python39-pip -y
```

#### macOS
```bash
brew install python@3.9
```

#### Using pyenv (Recommended)
```bash
curl https://pyenv.run | bash
# Add pyenv to shell (follow instructions from installer)
pyenv install 3.9.19
pyenv local 3.9.19
```

### 2. Backup Current Environment
```bash
# Backup existing virtual environment
mv test_env test_env_backup_$(date +%Y%m%d_%H%M%S)

# Backup known products
mv mercari_known_products.json mercari_known_products_backup.json
```

### 3. Create New Python 3.9 Environment
```bash
# Create new virtual environment
python3.9 -m venv venv

# Activate environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 4. Install Dependencies
```bash
# Install all dependencies
pip install -r requirements.txt

# Or use the automated setup script
./setup_python39.sh
```

### 5. Verify Installation
```bash
# Check Python version
python --version  # Should show Python 3.9.x

# Run compatibility test
python test_python39_compatibility.py

# Test basic functionality
python main.py --once --config config.json
```

## 📋 Compatibility Checklist

### Core Dependencies (Python 3.9 Compatible)
- ✅ `selenium==4.18.1` - Web automation
- ✅ `undetected-chromedriver==3.5.3` - Anti-bot detection
- ✅ `requests==2.31.0` - HTTP requests
- ✅ `beautifulsoup4==4.12.2` - HTML parsing
- ✅ `lxml==4.9.3` - XML/HTML processing
- ✅ `Pillow==10.1.0` - Image processing
- ✅ `numpy==1.24.3` - Numerical operations
- ✅ `forex-python==1.6` - Currency conversion
- ✅ `python-json-logger==2.0.7` - Structured logging
- ✅ `schedule==1.2.0` - Task scheduling
- ✅ `pytz==2023.3` - Timezone handling

### Python 3.9 Features Used
- ✅ Type hints (PEP 484)
- ✅ f-strings (PEP 498)
- ✅ Pathlib (PEP 519)
- ✅ Dataclasses (PEP 557) - Not used
- ✅ Async/await - Not used
- ✅ Assignment expressions (walrus operator) - Not used

## 🚨 Common Issues & Solutions

### Issue: Python 3.9 Not Found
**Solution:**
```bash
# Check available Python versions
ls /usr/bin/python*

# Install via deadsnakes PPA (Ubuntu)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-pip
```

### Issue: Missing distutils
**Solution:**
```bash
# Ubuntu/Debian
sudo apt install python3.9-distutils

# CentOS/RHEL
sudo yum install python39-distutils
```

### Issue: pip install fails
**Solution:**
```bash
# Use --break-system-packages flag (if needed)
pip install --break-system-packages -r requirements.txt

# Or use virtual environment
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: ChromeDriver Issues
**Solution:**
```bash
# Install Chrome (if not already installed)
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt update
sudo apt install google-chrome-stable
```

## 🧪 Testing Python 3.9 Compatibility

### Automated Testing
```bash
# Run the compatibility test
python test_python39_compatibility.py

# Expected output:
# ✅ Python version is compatible (3.9+)
# ✅ All imports successful
# ✅ Core functionality working
```

### Manual Testing
```bash
# Test each component
python -c "from mercari_scraper import MercariScraper; print('✅ MercariScraper import successful')"
python -c "from telegram_notifier import TelegramNotifier; print('✅ TelegramNotifier import successful')"
python -c "from product_storage import ProductStorage; print('✅ ProductStorage import successful')"
python -c "from image_filter import ImageFilter; print('✅ ImageFilter import successful')"
```

## 🔄 Rollback Plan

If you encounter issues, you can rollback:

```bash
# Deactivate current environment
deactivate

# Restore backup
rm -rf venv
mv test_env_backup_* test_env

# Or restore from git
git checkout HEAD~1
```

## 📊 Performance Notes

Python 3.9 vs 3.12 performance:
- **Memory usage**: Similar
- **Startup time**: Python 3.9 slightly faster
- **Runtime performance**: Negligible difference for this use case
- **Library compatibility**: All libraries tested work identically

## 🎯 Next Steps

1. **Complete the migration** using the steps above
2. **Update CI/CD** if applicable
3. **Test with real data** by running a monitoring session
4. **Update documentation** references
5. **Clean up** old environments after successful migration

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Run the compatibility test: `python test_python39_compatibility.py`
3. Check logs in the `logs/` directory
4. Create an issue on GitHub with error details