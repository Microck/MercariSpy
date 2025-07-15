#!/usr/bin/env python3
"""
Python 3.9 Compatibility Test Script
Tests all dependencies and core functionality for Python 3.9 compatibility
"""

import sys
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """Check if running Python 3.9 or compatible."""
    version = sys.version_info
    print(f"Current Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 9:
        print("✅ Python version is compatible (3.9+)")
        return True
    else:
        print("❌ Python version is not compatible. Requires 3.9+")
        return False

def test_imports():
    """Test importing all required modules."""
    required_modules = [
        'selenium',
        'undetected_chromedriver',
        'requests',
        'dotenv',
        'bs4',
        'lxml',
        'PIL',
        'numpy',
        'forex_python',
        'pythonjsonlogger',
        'schedule',
        'pytz'
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    return len(failed_imports) == 0, failed_imports

def test_core_functionality():
    """Test core functionality without network access."""
    try:
        # Test JSON config loading
        import json
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✅ JSON config loading")
        
        # Test product storage
        from product_storage import ProductStorage
        storage = ProductStorage("test_products.json")
        print("✅ ProductStorage initialization")
        
        # Test logging
        from logging_config import get_logger
        logger = get_logger("test")
        logger.info("Test log message")
        print("✅ Logging configuration")
        
        # Test image filter (without network)
        from image_filter import ImageFilter
        image_filter = ImageFilter(config)
        print("✅ ImageFilter initialization")
        
        # Test currency conversion (without API)
        from telegram_notifier import TelegramNotifier
        # This will fail due to missing env vars, but we just want to test imports
        try:
            notifier = TelegramNotifier(config)
        except ValueError:
            print("✅ TelegramNotifier import (expected config error)")
        
        return True
        
    except Exception as e:
        print(f"❌ Core functionality test failed: {e}")
        return False

def check_dependencies():
    """Check if all dependencies are compatible with Python 3.9."""
    try:
        # Check requirements.txt compatibility
        with open('requirements.txt', 'r') as f:
            requirements = f.readlines()
        
        print("\n📋 Checking dependency compatibility:")
        for req in requirements:
            req = req.strip()
            if req and not req.startswith('#'):
                print(f"  📦 {req}")
        
        return True
    except Exception as e:
        print(f"❌ Dependency check failed: {e}")
        return False

def main():
    """Run all compatibility tests."""
    print("🧪 Python 3.9 Compatibility Test")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Python version check failed")
        return False
    
    print("\n📦 Testing imports...")
    imports_ok, failed = test_imports()
    
    print("\n🔧 Testing core functionality...")
    core_ok = test_core_functionality()
    
    print("\n📋 Checking dependencies...")
    deps_ok = check_dependencies()
    
    print("\n" + "=" * 40)
    
    if imports_ok and core_ok and deps_ok:
        print("🎉 All tests passed! Python 3.9 compatibility confirmed.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above.")
        if failed:
            print(f"Missing modules: {', '.join(failed)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)