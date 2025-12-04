# 安全测试指南

## 🛡️ 三层测试策略

### 第一层：干运行模式（Dry Run）✅ 最安全
**完全不需要 API 密钥，不会产生任何影响**

```bash
# 编辑 config/config.yaml
operational:
  dry_run: true

# 运行
conda activate Marketmaker
python main.py

# 观察日志
tail -f logs/market_maker.log
```

**你会看到**：
```
[DRY RUN] Would place: buy 0.0465 @ 2150.50
[DRY RUN] Would place: sell 0.0463 @ 2152.50
```

**时长**：5-10分钟，确认代码能正常运行

---

### 第二层：测试网测试（Testnet）✅ 100% 安全，虚拟资金

#### 1. 注册测试网账号

访问：**https://testnet.bybit.com**

- 点击 "Sign Up"
- 注册新账号（不需要真实资金）
- 登录

#### 2. 领取测试币

1. 登录后，去 **Assets** 页面
2. 点击 **"Get Test Coins"** 或 **"Faucet"**
3. 领取 USDT, ETH, BTC 等测试币
4. 这些都是**虚拟币**，不值钱，免费的

#### 3. 创建测试网 API 密钥

1. 去 **API Management**
2. 点击 **"Create API Key"**
3. 设置：
   - Name: `MarketMaker`
   - Permissions: `Read-Write`
   - 选择：Order + Position
4. **保存 API Key 和 Secret**（只显示一次）

#### 4. 配置测试网

编辑 `config/config.testnet.yaml`：

```yaml
exchange:
  testnet: true  # ✅ 必须是 true
  api_key: "你的测试网API密钥"      # ← 粘贴这里
  api_secret: "你的测试网密钥秘密"  # ← 粘贴这里

operational:
  dry_run: false  # false = 真实下单（但在测试网）
```

#### 5. 运行测试网测试

```bash
conda activate Marketmaker

# 使用测试网配置运行
python main.py config/config.testnet.yaml

# 监控日志
tail -f logs/market_maker.log
tail -f logs/orders.log
tail -f logs/trades.log
```

#### 6. 观察内容

✅ **正常现象**：
- 看到订单下单成功
- 看到网格生成
- 看到订单成交（如果价格波动）
- 看到仓位变化
- 全部使用虚拟资金，不影响真实账户

❌ **需要修复的问题**：
- 连接失败 → 检查 API 密钥
- 认证错误 → 检查密钥配置
- 订单被拒 → 检查余额/权限

**测试时长**：至少 24-48 小时

---

### 第三层：主网测试（Mainnet）⚠️ 真实资金

**仅在测试网测试完全成功后使用！**

#### 准备工作

- [ ] 测试网运行 24+ 小时无问题
- [ ] 完全理解策略逻辑
- [ ] 理解风险控制参数
- [ ] 准备好监控和干预

#### 配置主网

```yaml
# config/config.yaml
exchange:
  testnet: false  # ⚠️ false = 主网（真实资金）
  api_key: "主网API密钥"
  api_secret: "主网密钥秘密"

capital:
  initial_usdc: 100.0  # ← 从小金额开始！

operational:
  dry_run: false
```

#### 运行主网

```bash
conda activate Marketmaker
python main.py

# 密切监控
tail -f logs/market_maker.log
```

**第一天监控重点**：
- [ ] 订单是否正确下单
- [ ] 风险限制是否生效
- [ ] 异常情况处理是否正确
- [ ] 盈亏是否符合预期

---

## ⚡ 快速测试命令

### 干运行测试（0风险）
```bash
# 编辑 config.yaml: dry_run: true
python main.py
```

### 测试网测试（虚拟资金）
```bash
# 1. 从 testnet.bybit.com 获取密钥
# 2. 填入 config/config.testnet.yaml
# 3. 运行
python main.py config/config.testnet.yaml
```

### 主网测试（真实资金）⚠️
```bash
# 仅在测试网完全成功后！
# 从小金额开始
python main.py
```

---

## 🛑 紧急停止

如果需要立即停止机器人：

1. **按 Ctrl+C** → 优雅停止，会自动取消所有订单
2. 或者手动去交易所取消订单

---

## 📊 测试网 vs 主网对比

| 特性 | 干运行 | 测试网 | 主网 |
|------|--------|--------|------|
| 需要API密钥 | ❌ 不需要 | ✅ 测试网密钥 | ✅ 主网密钥 |
| 下真实订单 | ❌ 否 | ✅ 是（虚拟） | ✅ 是（真实） |
| 使用真钱 | ❌ 否 | ❌ 否 | ✅ **是** |
| 风险 | 0% | 0% | 100% |
| 推荐测试时长 | 5-10分钟 | 24-48小时 | 持续监控 |

---

## ✅ 测试清单

### 干运行测试
- [ ] 程序能正常启动
- [ ] 没有代码错误
- [ ] 日志显示模拟订单

### 测试网测试
- [ ] API 连接成功
- [ ] WebSocket 连接正常
- [ ] 订单能正常下单
- [ ] 网格正确生成
- [ ] 订单成交后仓位正确更新
- [ ] 风险管理参数生效
- [ ] 运行 24+ 小时稳定

### 主网测试
- [ ] 测试网完全成功
- [ ] 从小金额开始（100-200 USDC）
- [ ] 第一天密切监控
- [ ] 理解所有风险

---

## 📝 常见问题

**Q: 测试网的钱是真的吗？**
A: 不是！是虚拟币，不值钱，可以无限领取。

**Q: 测试网会影响我的真实账户吗？**
A: 完全不会！测试网和主网是独立的系统。

**Q: 如何确认我在测试网？**
A: 看配置文件 `testnet: true` 和 URL `testnet.bybit.com`

**Q: 干运行模式需要 API 密钥吗？**
A: 不需要！可以留空。

**Q: 建议在测试网测试多久？**
A: 至少 24-48 小时，确保各种情况都测试到。
