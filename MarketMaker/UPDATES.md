# 🎉 更新完成：Hyperliquid 支持 + 命令行模式选择

## ✅ 已完成的改动

### 1. 新增 Hyperliquid 支持

#### 新文件：
- `exchange/hyperliquid_rest_client.py` - Hyperliquid REST API 客户端
- `exchange/hyperliquid_ws_client.py` - Hyperliquid WebSocket 客户端
- `exchange/factory.py` - 交易所工厂类（自动选择 Bybit 或 Hyperliquid）
- `config/config.hyperliquid.yaml` - Hyperliquid 专用配置
- `utils/generate_wallet.py` - 以太坊钱包生成工具

#### 关键特性：
- ✅ 使用以太坊私钥进行身份验证
- ✅ 支持测试网和主网
- ✅ 完整的订单管理（下单、撤单、查询）
- ✅ WebSocket 实时数据订阅
- ✅ EIP-712 签名支持

### 2. 命令行模式选择

#### 新增参数：

```bash
python main.py --mode <MODE> --config <CONFIG_FILE>
```

**`--mode` 选项**：
- `dry-run` 🔶 - 干运行模式（测试网数据，不下真实订单）
- `testnet` 🟡 - 测试网模式（虚拟资金，真实订单）
- `mainnet` 🔴 - 主网模式（真实资金，真实订单）

**`--config` 选项**：
- 指定配置文件路径
- 默认：`config/config.yaml`

#### 使用示例：

```bash
# Bybit 干运行
python main.py --mode dry-run

# Hyperliquid 测试网
python main.py --config config/config.hyperliquid.yaml --mode testnet

# Bybit 主网（真实资金）
python main.py --config config/config.yaml --mode mainnet
```

### 3. 更新的文件

#### 核心文件：
- `main.py` - 添加 argparse 支持，模式选择逻辑
- `requirements.txt` - 添加 `eth-account==0.10.0`

#### 文档：
- `README.md` - 更新为多交易所支持
- `HYPERLIQUID_GUIDE.md` - 完整的 Hyperliquid 使用指南

---

## 🚀 快速开始

### 步骤 1：安装新依赖

```bash
conda activate Marketmaker
pip install eth-account==0.10.0
```

### 步骤 2：选择交易所

#### 使用 Hyperliquid

```bash
# 1. 生成钱包
python utils/generate_wallet.py

# 2. 编辑配置
nano config/config.hyperliquid.yaml
# 填入 private_key

# 3. 运行（干运行）
python main.py --config config/config.hyperliquid.yaml --mode dry-run
```

#### 使用 Bybit

```bash
# 1. 获取 API 密钥（testnet.bybit.com）

# 2. 编辑配置
nano config/config.yaml
# 填入 api_key 和 api_secret

# 3. 运行（测试网）
python main.py --mode testnet
```

---

## 📋 命令参考

### 完整命令格式

```bash
python main.py [--config CONFIG_FILE] [--mode MODE]
```

### 常用命令

| 命令 | 说明 |
|------|------|
| `python main.py --mode dry-run` | Bybit 干运行 |
| `python main.py --mode testnet` | Bybit 测试网 |
| `python main.py --mode mainnet` | Bybit 主网 ⚠️ |
| `python main.py --config config/config.hyperliquid.yaml --mode dry-run` | Hyperliquid 干运行 |
| `python main.py --config config/config.hyperliquid.yaml --mode testnet` | Hyperliquid 测试网 |
| `python main.py --config config/config.hyperliquid.yaml --mode mainnet` | Hyperliquid 主网 ⚠️ |

### 查看帮助

```bash
python main.py --help
```

输出：
```
usage: main.py [-h] [--config CONFIG] [--mode {dry-run,testnet,mainnet}]

Market Maker Bot

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       Path to configuration file (default: config/config.yaml)
  --mode {dry-run,testnet,mainnet}
                        Operating mode: dry-run (simulate), testnet (virtual funds), mainnet (real funds)

Examples:
  # Dry run mode (testnet data, no real orders)
  python main.py --mode dry-run
  
  # Testnet mode (virtual funds, real orders)
  python main.py --mode testnet
  
  # Mainnet mode (REAL FUNDS!)
  python main.py --mode mainnet
  
  # Use specific config file
  python main.py --config config/config.hyperliquid.yaml --mode testnet
```

---

## 🔄 Bybit vs Hyperliquid 对比

| 特性 | Bybit | Hyperliquid |
|------|-------|-------------|
| **认证方式** | API Key + Secret | 以太坊私钥 |
| **配置文件** | `config/config.yaml` | `config/config.hyperliquid.yaml` |
| **交易对格式** | `ETHUSDC` | `ETH` |
| **测试网** | testnet.bybit.com | 内置测试网 |
| **获取凭证** | 网站创建 API | 生成钱包 |
| **安全性** | API 权限控制 | 私钥控制 |

---

## 🛡️ 安全建议

### Bybit
- ✅ 使用测试网 API 进行测试
- ✅ 限制 API 权限（只需要 Orders + Positions）
- ✅ 不要勾选 Withdrawal 权限
- ✅ 设置 IP 白名单（生产环境）

### Hyperliquid
- ✅ 使用专用钱包（不要用主钱包）
- ✅ 限制钱包资金量
- ✅ 不要提交私钥到 Git
- ✅ 使用环境变量存储私钥

---

## 📊 模式对比

| 模式 | 标识 | 数据来源 | 下单 | 资金 | 风险 | 用途 |
|------|------|----------|------|------|------|------|
| **Dry Run** | 🔶 | 测试网 | ❌ 模拟 | 无 | 0% | 验证代码逻辑 |
| **Testnet** | 🟡 | 测试网 | ✅ 真实 | 虚拟 | 0% | 验证策略效果 |
| **Mainnet** | 🔴 | 主网 | ✅ 真实 | 真实 | 100% | 正式交易 |

---

## 🧪 推荐测试流程

```
1. Dry Run (5-10分钟)
   └─> 验证代码能正常运行
   
2. Testnet (24-48小时)
   └─> 验证策略逻辑正确
   
3. Mainnet 小资金 (1-7天)
   └─> 验证实际效果
   
4. 逐步增加资金
   └─> 扩大规模
```

---

## 📚 相关文档

- [HYPERLIQUID_GUIDE.md](HYPERLIQUID_GUIDE.md) - Hyperliquid 详细使用指南
- [README.md](README.md) - 项目总体说明
- [TEST_GUIDE.md](TEST_GUIDE.md) - 测试指南

---

## ❓ 常见问题

### Q: 如何切换交易所？
A: 使用 `--config` 参数指定不同的配置文件。

### Q: 模式参数会覆盖配置文件吗？
A: 是的，`--mode` 参数会覆盖配置文件中的 `dry_run` 和 `testnet` 设置。

### Q: 可以不指定模式吗？
A: 可以，会使用配置文件中的设置。但建议明确指定模式以避免误操作。

### Q: Hyperliquid 需要 gas 费吗？
A: 不需要！Hyperliquid 的交易不需要 gas 费。

### Q: 如何生成新钱包？
A: 运行 `python utils/generate_wallet.py`

---

## 🎯 下一步

1. **安装依赖**：
   ```bash
   pip install eth-account==0.10.0
   ```

2. **选择交易所**：
   - Bybit：获取 API 密钥
   - Hyperliquid：生成钱包

3. **测试运行**：
   ```bash
   python main.py --mode dry-run
   ```

4. **查看日志**：
   ```bash
   tail -f logs/market_maker.log
   ```

---

## ✨ 总结

现在你的做市机器人支持：
- ✅ 两个交易所（Bybit + Hyperliquid）
- ✅ 三种运行模式（Dry Run + Testnet + Mainnet）
- ✅ 灵活的命令行配置
- ✅ 完整的文档和工具

开始测试吧！🚀
