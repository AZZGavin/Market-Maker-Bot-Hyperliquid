# Market Maker Bot

A production-ready market-making bot supporting **Hyperliquid** exchanges with inventory-based grid strategy and comprehensive risk management.

## 🎯 Features

- **Multi-Exchange Support**:
  - Hyperliquid (Ethereum wallet authentication)
- **Inventory Management**: Dynamic position tracking with automatic grid bias adjustment
- **Sliding Grid**: Automatically re-centers grid when price moves beyond threshold
- **Command-Line Modes**:
  - 🔶 **Dry Run**: Simulate trading without real orders
  - 🟡 **Testnet**: Trade with virtual funds
  - 🔴 **Mainnet**: Trade with real funds
- **Risk Management**: 
  - Max loss protection (20% default)
  - Leverage monitoring (5x default)
  - Emergency stop mechanism
- **Exchange Integration**:
  - REST API for order management
  - WebSocket for real-time market data and order updates
  - Auto-reconnection with exponential backoff
- **Operational**:
  - State persistence for recovery
  - Comprehensive logging (trades, orders, errors)
  - Dry-run mode for testing
  - Graceful shutdown

## 📋 Prerequisites

- Python 3.9+
- Bybit API keys (testnet or mainnet)
- Virtual environment (venv or conda)
- For deployment: Ubuntu server (Tokyo/Singapore recommended)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd /Users/zhouguanwei/Documents/Crypto/MarketMaker

# Create and activate environment
conda create -n Marketmaker python=3.9
conda activate Marketmaker

# Install dependencies
pip install -r requirements.txt
```

### 2. Choose Your Exchange

#### Option A: Bybit

1. Get API keys from https://testnet.bybit.com
2. Edit `config/config.yaml`:
```yaml
exchange:
  name: "bybit"
  api_key: "YOUR_API_KEY"
  api_secret: "YOUR_API_SECRET"
```

#### Option B: Hyperliquid

1. Generate a wallet:
```bash
python utils/generate_wallet.py
```

2. Edit `config/config.hyperliquid.yaml`:
```yaml
exchange:
  name: "hyperliquid"
  private_key: "0xYOUR_PRIVATE_KEY"
```

### 3. Run with Mode Selection

#### 🔶 Dry Run (Recommended First)
```bash
# Bybit
python main.py --mode dry-run

# Hyperliquid
python main.py --config config/config.hyperliquid.yaml --mode dry-run
```

#### 🟡 Testnet
```bash
# Bybit
python main.py --mode testnet

# Hyperliquid
python main.py --config config/config.hyperliquid.yaml --mode testnet
```

#### 🔴 Mainnet (⚠️ Real Funds)
```bash
# Bybit
python main.py --mode mainnet

# Hyperliquid
python main.py --config config/config.hyperliquid.yaml --mode mainnet
```

## 📊 Monitoring

### Logs

All logs are stored in `logs/` directory:

- `market_maker.log`: General application logs
- `trades.log`: Trade executions
- `orders.log`: Order placements and cancellations
- `errors.log`: Error-level events only

### Real-time Monitoring

```bash
# Watch main log
tail -f logs/market_maker.log

# Watch trades
tail -f logs/trades.log

# Watch orders
tail -f logs/orders.log
```

## 🏗️ Architecture

```
market-maker/
├── config/              # Configuration
├── exchange/            # Bybit REST & WebSocket clients
├── data/                # Orderbook management
├── strategy/            # Inventory & grid maker
├── risk/                # Risk management
├── engine/              # Order management
├── utils/               # Logging & persistence
├── logs/                # Log files
└── main.py              # Application entry
```

## 🔒 Risk Controls

The bot includes multiple safety mechanisms:

1. **Max Loss Limit**: Stops trading if total loss exceeds threshold (default 20%)
2. **Leverage Monitoring**: Emergency stop if leverage exceeds limit
3. **Position Limits**: Maximum position size in contracts
4. **Inventory Skew**: Automatically adjusts grid to reduce position risk
5. **Graceful Shutdown**: Cancels all orders on exit

## 🚢 Deployment

### Using Supervisor

```bash
# Copy config
sudo cp deploy/supervisor.conf /etc/supervisor/conf.d/market_maker.conf

# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Start
sudo supervisorctl start market_maker

# Check status
sudo supervisorctl status market_maker
```

### Using systemd

```bash
# Copy service file
sudo cp deploy/systemd.service /etc/systemd/system/market_maker.service

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable market_maker

# Start service
sudo systemctl start market_maker

# Check status
sudo systemctl status market_maker
```

## 🧪 Testing

Before running on mainnet:

1. **Testnet Testing**: 
   - Get testnet credentials from https://testnet.bybit.com
   - Run for 24-48 hours on testnet
   - Monitor logs and behavior

2. **Dry Run**: 
   - Test with `dry_run: true`
   - Validates logic without real orders

3. **Small Capital**: 
   - Start with minimal capital on mainnet
   - Gradually increase as confidence builds

## ⚠️ Important Notes

- **API Keys**: Never commit API keys to git. Use environment variables or local config overrides
- **Testnet First**: Always test thoroughly on testnet before mainnet
- **Monitor Closely**: Especially in first few hours of live trading
- **Risk Management**: Understand that trading involves risk of loss
- **Network Stability**: Requires stable internet connection

## 🛠️ Troubleshooting

### WebSocket Disconnections

The bot automatically reconnects. Check logs for:
```
Private WebSocket error: ...
Reconnecting private stream in Xs...
```

### Orders Not Placing

1. Check API keys and permissions
2. Verify sufficient balance
3. Check leverage is set correctly
4. Look for rate limiting errors in logs

### Emergency Stop Triggered

Check `logs/market_maker.log` for reason:
```
🚨 EMERGENCY STOP TRIGGERED: Max loss limit breached
```

To reset (use caution):
- Fix underlying issue
- Manually reset in code or restart with fresh state

## 📝 Configuration Reference

See `config/config.yaml` for all available settings.

Key parameters:
- `grid.spacing_pct`: Distance between grid levels
- `grid.slide_threshold_pct`: When to re-center grid
- `inventory.skew_threshold_pct`: When to start adjusting bias
- `risk.max_loss_pct`: Stop loss threshold

## 📚 Further Development

Potential enhancements:
- [ ] Add database for trade history
- [ ] Telegram notifications
- [ ] Web dashboard for monitoring
- [ ] Multi-symbol support
- [ ] Advanced order types
- [ ] Backtesting framework

## 📄 License

For personal use. Modify as needed.

## ⚠️ Disclaimer

This software is for educational purposes. Trading cryptocurrencies carries risk. Use at your own risk.
