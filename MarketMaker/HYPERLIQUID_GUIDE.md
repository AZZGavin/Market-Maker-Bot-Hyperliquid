# Hyperliquid 做市机器人使用指南

## 🎯 快速开始

### 1. 安装新依赖

```bash
conda activate Marketmaker
pip install eth-account==0.10.0
```

### 2. 获取 Hyperliquid 私钥

Hyperliquid 使用以太坊钱包进行身份验证。你需要一个以太坊私钥。

#### 选项 A：创建新钱包（推荐用于测试）

```python
from eth_account import Account
import secrets

# 生成新钱包
priv = secrets.token_hex(32)
private_key = "0x" + priv
acct = Account.from_key(private_key)

print(f"Private Key: {private_key}")
print(f"Address: {acct.address}")
```

#### 选项 B：使用现有钱包

- 从 MetaMask 或其他钱包导出私钥
- ⚠️ **警告**：永远不要使用存有大量资金的主钱包！

### 3. 配置文件

编辑 `config/config.hyperliquid.yaml`:

```yaml
exchange:
  name: "hyperliquid"
  testnet: true  # 测试网
  private_key: "0x你的私钥"  # 填入你的私钥

symbol:
  name: "ETH"  # 交易对

capital:
  initial_usdc: 1000.0
  leverage: 5
```

### 4. 运行命令

#### 🔶 干运行模式（推荐第一次）
```bash
python main.py --config config/config.hyperliquid.yaml --mode dry-run
```
- 使用测试网数据
- 不会真的下单
- 只在日志中显示模拟订单

#### 🟡 测试网模式
```bash
python main.py --config config/config.hyperliquid.yaml --mode testnet
```
- 使用测试网
- 会真的下单（虚拟资金）
- 需要测试网有余额

#### 🔴 主网模式（⚠️ 真实资金）
```bash
python main.py --config config/config.hyperliquid.yaml --mode mainnet
```
- 使用主网
- 真实资金交易
- **极度谨慎！**

---

## 📋 命令行参数说明

### `--config` 参数

指定配置文件路径：

```bash
# 使用 Bybit
python main.py --config config/config.yaml --mode testnet

# 使用 Hyperliquid
python main.py --config config/config.hyperliquid.yaml --mode testnet
```

### `--mode` 参数

选择运行模式：

| 模式 | 说明 | 下单 | 资金 | 风险 |
|------|------|------|------|------|
| `dry-run` | 干运行 | ❌ 模拟 | 无 | 0% |
| `testnet` | 测试网 | ✅ 真实 | 虚拟 | 0% |
| `mainnet` | 主网 | ✅ 真实 | 真实 | 100% |

---

## 🔄 Bybit vs Hyperliquid 对比

### Bybit 配置

```yaml
exchange:
  name: "bybit"
  testnet: true
  api_key: "你的API密钥"
  api_secret: "你的API密钥秘密"

symbol:
  name: "ETHUSDC"
  category: "linear"
```

运行：
```bash
python main.py --config config/config.yaml --mode testnet
```

### Hyperliquid 配置

```yaml
exchange:
  name: "hyperliquid"
  testnet: true
  private_key: "0x你的私钥"

symbol:
  name: "ETH"
  category: "perp"
```

运行：
```bash
python main.py --config config/config.hyperliquid.yaml --mode testnet
```

---

## 🛡️ 安全最佳实践

### 1. 私钥安全

❌ **不要**：
- 在代码中硬编码私钥
- 提交私钥到 Git
- 使用主钱包私钥

✅ **应该**：
- 使用环境变量
- 创建专用交易钱包
- 限制钱包资金量

### 2. 使用环境变量

```bash
# 设置环境变量
export HYPERLIQUID_PRIVATE_KEY="0x你的私钥"

# 在配置中引用
# 修改 main.py 读取环境变量
```

### 3. 测试流程

```
1. 干运行 (5-10分钟) → 验证代码
2. 测试网 (24-48小时) → 验证策略
3. 主网小资金 (1-7天) → 验证实际效果
4. 逐步增加资金
```

---

## 📊 监控和日志

### 查看日志

```bash
# 主日志
tail -f logs/market_maker.log

# 交易日志
tail -f logs/trades.log

# 订单日志
tail -f logs/orders.log
```

### 日志示例

**干运行模式**：
```
🔶 Mode: DRY RUN (Testnet data, no real orders)
[DRY RUN] Would place: buy 0.0465 @ 3380.50
[DRY RUN] Would place: sell 0.0463 @ 3385.50
```

**测试网模式**：
```
🟡 Mode: TESTNET (Virtual funds, real orders)
ORDER PLACED | BUY 0.0465 @ 3380.50 | Order ID: 12345
ORDER FILLED | BUY 0.0465 @ 3380.50
```

**主网模式**：
```
🔴 Mode: MAINNET (REAL FUNDS, REAL ORDERS)
⚠️  WARNING: Trading with real funds!
```

---

## 🚀 完整示例

### 示例 1：Hyperliquid 测试网测试

```bash
# 1. 安装依赖
conda activate Marketmaker
pip install eth-account==0.10.0

# 2. 生成测试钱包（Python）
python -c "from eth_account import Account; import secrets; pk='0x'+secrets.token_hex(32); print(f'Private Key: {pk}\\nAddress: {Account.from_key(pk).address}')"

# 3. 编辑配置
nano config/config.hyperliquid.yaml
# 填入私钥

# 4. 干运行测试
python main.py --config config/config.hyperliquid.yaml --mode dry-run

# 5. 测试网测试
python main.py --config config/config.hyperliquid.yaml --mode testnet
```

### 示例 2：Bybit 测试网测试

```bash
# 1. 获取 Bybit 测试网 API（testnet.bybit.com）

# 2. 编辑配置
nano config/config.yaml
# 填入 API 密钥

# 3. 测试网测试
python main.py --config config/config.yaml --mode testnet
```

---

## ❓ 常见问题

### Q: Hyperliquid 需要 API 密钥吗？
A: 不需要！Hyperliquid 使用以太坊私钥进行身份验证。

### Q: 如何在测试网获得资金？
A: Hyperliquid 测试网通常会自动提供测试资金，或者访问测试网水龙头。

### Q: 可以同时运行多个交易所吗？
A: 可以！使用不同的配置文件和终端窗口。

### Q: 如何切换交易所？
A: 使用 `--config` 参数指定不同的配置文件。

### Q: 私钥安全吗？
A: 只要你：
1. 不提交到 Git
2. 使用专用钱包
3. 限制资金量
就是安全的。

---

## 🛑 紧急停止

按 `Ctrl+C` 即可停止机器人。程序会：
1. 取消所有订单
2. 保存状态
3. 优雅退出

---

## 📚 更多资源

- [Hyperliquid 文档](https://hyperliquid.gitbook.io/)
- [Bybit API 文档](https://bybit-exchange.github.io/docs/)
- [项目 README](README.md)

---

## ⚠️ 免责声明

此软件仅供教育和研究目的。加密货币交易存在风险，可能导致资金损失。使用风险自负。
