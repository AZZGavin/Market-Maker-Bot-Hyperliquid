#!/bin/bash

# Hyperliquid Market Maker - Quick Start Script

echo "🚀 Starting Hyperliquid Market Maker..."
echo ""

# Activate conda environment
echo "📦 Activating Marketmaker environment..."
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate Marketmaker

# Check if activation was successful
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate Marketmaker environment"
    echo "Please run: conda activate Marketmaker"
    exit 1
fi

# Run the bot
echo "🤖 Starting bot..."
python main.py --config config/config.hyperliquid.yaml --mode dry-run

# Note: Change --mode to 'testnet' or 'mainnet' when ready
