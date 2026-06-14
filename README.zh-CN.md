<div align="center">
  <h1>🔪 A-Stock Scalpel · A股短线手术刀</h1>
  <p><em>多因子量化分析工具 · 透明规则表 · 零成本数据源</em></p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python">
    <img src="https://img.shields.io/badge/%E5%8D%8F%E8%AE%AE-MIT-green" alt="License">
    <img src="https://img.shields.io/badge/%E7%89%88%E6%9C%AC-2.2.0-orange" alt="Version">
    <img src="https://img.shields.io/badge/%E6%95%B0%E6%8D%AE%E6%BA%90-%E6%96%B0%E6%B5%AA%20%7C%20%E4%B8%9C%E6%96%B9%E8%B4%A2%E5%AF%8C-yellow" alt="Data">
  </p>

  <p>
    <b>🆓 零成本</b> · <b>🔍 完全透明</b> · <b>📊 9因子 + 32规则</b> · <b>⏱ 60秒全市场扫描</b>
  </p>
</div>

## 它能做什么？

A股短线多因子量化评分系统。获取**新浪财经 + 东方财富**免费行情数据，计算9个技术指标，用32条确定性规则打分，60秒输出全市场排名。

**不是黑盒AI打分，每一条规则都写在 `core/rules.py` 里，你可以审计每一分。**

## 适用人群

- 🏦 散户交易者 — 想用量化思维辅助决策，但不想折腾券商API
- 📚 量化学习者 — 想理解多因子评分系统的工程实现
- 🔧 开发者 — 想基于A股数据构建自己的交易信号系统

## 特色

| 特性 | 说明 |
|------|------|
| **9个技术因子** | RSI · MACD · KDJ · 布林带 · 一目均衡 · 鳄鱼线 · ADX · OBV · 量能 |
| **32条确定性规则** | 18条多头 + 14条空头规则表，逻辑完全透明 |
| **双数据源自动切换** | 新浪财经（主）+ 东方财富（备），都不需要API Key |
| **回测引擎** | 模拟过去N个交易日的规则表现，含0.457%交易成本 |
| **60秒全量扫描** | 一次命令输出80+只沪深龙头排名 |
| **支持终端的CLI** | 在服务器上跑，cron定时自动分析 |

## 快速开始

```bash
# 安装
git clone https://github.com/zhubohan190601-crypto/a-stock-scalpel.git
cd a-stock-scalpel
pip install -r requirements.txt

# 全市场扫描
python3 core/analyzer.py --scan

# 单只股票分析
python3 core/analyzer.py 600519

# 回测
python3 core/backtest.py
```

### 输出样例

```
🏆 综合评分 TOP 20
=================================================================
  代码    名称        价格    涨跌    多  空  净分   信号
-----------------------------------------------------------------
 600519  贵州茅台   1520.00   +2.1%   8   2   +52   strong_buy
 300750  宁德时代    218.50   +3.4%   7   1   +48   strong_buy
 000858  五粮液     145.20   +1.8%   6   2   +35   buy
```

## 架构

```
线上/终端
    │
core/fetcher.py  ← 采集层（新浪财经 + 东方财富）
    │
core/analyzer.py ← 分析层（计算9个技术因子）
    │
core/rules.py    ← 评分层（18多头 + 14空头规则）
    │
core/backtest.py ← 回测层（含0.457%摩擦成本）
```

## 技术因子一览

| 因子 | 参数 | 用途 |
|------|------|------|
| RSI | 周期14 | 超买/超卖判断 |
| MACD | 12/26/9 | 趋势动量与金叉死叉 |
| KDJ | 周期9 | 随机指标震荡区间 |
| 布林带 | 20日/2σ | 波动率与均值回归 |
| 一目均衡 | 9/26/52 | 云层趋势判断 |
| 鳄鱼线 | 13/8/5 SMA | 趋势方向确认 |
| ADX | 周期14 | 趋势强度+多空对比 |
| OBV | — | 量价配合验证 |
| 量比 | 5日均值 | 成交量放大/缩小 |

## 回测参数

单边交易成本 **0.457%**：
- 印花税：0.10%（仅卖出）
- 佣金：~0.03%
- 滑点：~0.327%

> 日内高频策略忽略摩擦成本会导致回测高估20-40%。

## 关于"短线手术刀"

本系统的核心逻辑最初是作为 [OpenClaw](https://github.com/openclaw/openclaw) 的技能（Skill）开发的，ClawHub 版本亦同步维护。这个GitHub仓库是独立的 Python 实现，可在任意环境中运行。

- **OpenClaw 用户**：在 ClawHub 搜索 "短线手术刀" 即可安装
- **纯 Python 用户**：clone 本仓库，`python3 core/analyzer.py --scan`

## ⚠️ 免责声明

**这不是投资建议。** 本工具仅供教育和研究目的。过去的表现不代表未来的收益。投资有风险，决策须谨慎。

---

<div align="center">
  <p>如果对你有用，请给一个 ⭐</p>
  <p>
    <a href="https://github.com/zhubohan190601-crypto/a-stock-scalpel/issues">报告问题</a>
    ·
    <a href="https://github.com/zhubohan190601-crypto/a-stock-scalpel">GitHub</a>
  </p>
</div>
