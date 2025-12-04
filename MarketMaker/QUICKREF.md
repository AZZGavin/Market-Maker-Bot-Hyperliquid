# 🚀 快速参考

## 安装新依赖
```bash
conda activate Marketmaker
pip install eth-account==0.10.0
```

## 命令速查

### Bybit
```bash
# 干运行
python main.py --mode dry-run

# 测试网
python main.py --mode testnet

# 主网 ⚠️
python main.py --mode mainnet
```

### Hyperliquid
```bash
# 生成钱包
python utils/generate_wallet.py

# 干运行
python main.py --config config/config.hyperliquid.yaml --mode dry-run

# 测试网
python main.py --config config/config.hyperliquid.yaml --mode testnet

# 主网 ⚠️
python main.py --config config/config.hyperliquid.yaml --mode mainnet
```

## 模式说明

| 模式 | 符号 | 说明 |
|------|------|------|
| dry-run | 🔶 | 模拟，不下真实订单 |
| testnet | 🟡 | 虚拟资金，真实订单 |
| mainnet | 🔴 | 真实资金 ⚠️ |

## 配置文件

| 交易所 | 配置文件 |
|--------|----------|
| Bybit | `config/config.yaml` |
| Hyperliquid | `config/config.hyperliquid.yaml` |

## 查看日志
```bash
tail -f logs/market_maker.log
```

## 帮助
```bash
python main.py --help
```

## 详细文档
- [UPDATES.md](UPDATES.md) - 更新说明
- [HYPERLIQUID_GUIDE.md](HYPERLIQUID_GUIDE.md) - Hyperliquid 指南
- [README.md](README.md) - 完整文档
