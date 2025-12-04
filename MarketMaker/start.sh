#!/bin/bash
# Quick start script for market maker

echo "🚀 Market Maker Quick Start"
echo "============================"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Create necessary directories
mkdir -p logs state

# Check config
if [ ! -f "config/config.yaml" ]; then
    echo "❌ Error: config/config.yaml not found!"
    echo "Please copy config/config.yaml and add your API keys"
    exit 1
fi

# Check API keys
if grep -q "api_key: \"\"" config/config.yaml; then
    echo "⚠️  Warning: API keys not configured in config/config.yaml"
    echo "Please add your Bybit API keys before running"
    exit 1
fi

echo "✅ Setup complete!"
echo ""
echo "To run the bot:"
echo "  python main.py"
echo ""
echo "To run in dry mode (recommended for first test):"
echo "  1. Set 'dry_run: true' in config/config.yaml"
echo "  2. Run: python main.py"
echo ""
echo "Monitor logs:"
echo "  tail -f logs/market_maker.log"
