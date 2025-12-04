# ✅ Hyperliquid 做市机器人 - 已完成

## 🎯 已完成的改动

### 1. 使用官方 Hyperliquid SDK
- ✅ 安装了 `hyperliquid-python-sdk`
- ✅ 重写了所有交易所客户端
- ✅ 移除了 Bybit 相关代码
- ✅ 简化了项目结构

### 2. 新文件
- `exchange/hyperliquid_client.py` - 基于官方 SDK 的客户端
- `exchange/hyperliquid_ws.py` - WebSocket 客户端
- `exchange/adapter.py` - 简化的适配器
- `exchange/factory.py` - 简化的工厂
- `run.sh` - 快速启动脚本

### 3. 更新的文件
- `main.py` - 简化为只支持 Hyperliquid
- `config/config.hyperliquid.yaml` - Hyperliquid 配置

---

## 🚀 如何运行

### 方法 1：使用启动脚本（推荐）

```bash
./run.sh
```

### 方法 2：手动运行

```bash
# 激活环境
conda activate Marketmaker

# 干运行模式
python main.py --config config/config.hyperliquid.yaml --mode dry-run

# 测试网模式
python main.py --config config/config.hyperliquid.yaml --mode testnet

# 主网模式 ⚠️
python main.py --config config/config.hyperliquid.yaml --mode mainnet
```

---

## 📋 配置

编辑 `config/config.hyperliquid.yaml`:

```yaml
exchange:
  name: "hyperliquid"
  testnet: true
  private_key: "0x你的私钥"  # 已填入

symbol:
  name: "ETH"

capital:
  initial_usdc: 1000.0
  leverage: 5
```

---

## 🧪 测试流程

1. **干运行** (5-10分钟)
   ```bash
   ./run.sh
   # 或
   python main.py --config config/config.hyperliquid.yaml --mode dry-run
   ```

2. **测试网** (24-48小时)
   ```bash
   python main.py --config config/config.hyperliquid.yaml --mode testnet
   ```

3. **主网** (谨慎！)
   ```bash
   python main.py --config config/config.hyperliquid.yaml --mode mainnet
   ```

---

## 📊 监控

```bash
# 主日志
tail -f logs/market_maker.log

# 交易日志
tail -f logs/trades.log

# 订单日志
tail -f logs/orders.log
```

---

## ⚠️ 重要提示

1. **私钥安全**
   - 不要提交到 Git
   - 使用专用钱包
   - 限制资金量

2. **测试优先**
   - 先在测试网运行 24+ 小时
   - 确认策略正常
   - 再考虑主网

3. **风险管理**
   - 20% 最大亏损自动停止
   - 5x 杠杆限制
   - 实时监控日志

---

## 🛑 停止机器人

按 `Ctrl+C` 即可优雅停止

---

## 📚 下一步

1. ✅ 配置已完成
2. ⏳ 运行干运行模式测试
3. ⏳ 测试网测试
4. ⏳ 主网部署

开始测试吧！🚀
