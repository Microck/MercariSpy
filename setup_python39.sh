#!/bin/bash
# Python 3.9 Setup Script for Mercari Monitor

set -e

echo "🐍 Setting up Python 3.9 for Mercari Monitor..."

# Check if Python 3.9 is installed
if ! command -v python3.9 &> /dev/null; then
    echo "❌ Python 3.9 not found. Installing..."
    
    # Detect OS and install Python 3.9
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        if command -v apt &> /dev/null; then
            echo "Installing Python 3.9 via apt..."
            sudo apt update
            sudo apt install python3.9 python3.9-venv python3.9-pip -y
        elif command -v yum &> /dev/null; then
            # CentOS/RHEL
            echo "Installing Python 3.9 via yum..."
            sudo yum install python39 python39-pip -y
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "Installing Python 3.9 via Homebrew..."
            brew install python@3.9
        else
            echo "❌ Homebrew not found. Please install Homebrew first:"
            echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    else
        echo "❌ Unsupported OS. Please install Python 3.9 manually."
        exit 1
    fi
else
    echo "✅ Python 3.9 is already installed"
fi

# Verify Python 3.9 installation
python3.9 --version

# Create virtual environment
echo "🔄 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

python3.9 -m venv venv
echo "✅ Virtual environment created"

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

echo "🎉 Python 3.9 setup complete!"
echo ""
echo "To activate the environment in the future, run:"
echo "   source venv/bin/activate"
echo ""
echo "To verify Python version:"
echo "   python --version"