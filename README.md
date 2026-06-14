<div align="center">
  <h1>🔪 A-Stock Scalpel</h1>
  <p><em>Multi-Factor Quantitative Analysis Tool for China A-Share Market</em></p>

  <p>
    <img src="https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
    <img src="https://img.shields.io/badge/version-2.2.0-orange?style=flat-square" alt="Version">
    <img src="https://img.shields.io/badge/data-sina%20%7C%20eastmoney-yellow?style=flat-square" alt="Data Sources">
    <img src="https://img.shields.io/badge/status-beta-brightgreen?style=flat-square" alt="Status">
  </p>

  <p>
    <b>Zero API Cost</b> · <b>Rule-Based Scoring</b> · <b>9 Technical Factors</b> · <b>32 Transparent Rules</b>
  </p>

  <hr>
</div>

## 🎯 What is A-Stock Scalpel?

A transparent, **deterministic** scoring system for China A-share short-term trading signals. It uses 9 technical factors (RSI, MACD, KDJ, Bollinger, Ichimoku, Alligator, ADX, OBV, Volume) evaluated against **18 bullish + 14 bearish rules** to produce a net score and actionable signal.

```
┌─────────────────────────────────────────────────────┐
│                  A-Stock Scalpel                     │
├─────────────┬──────────────┬───────────────────────┤
│  Fetcher    │  Analyzer    │  Rules Engine         │
│  (Sina + EM)│  (9 Factors) │  (18 Bull + 14 Bear)  │
├─────────────┴──────────────┴───────────────────────┤
│  Backtest Engine (0.457% friction cost modeled)     │
└─────────────────────────────────────────────────────┘
```

### Why not AI black box?

Most "AI trading" tools use LLMs to generate signals — you can't audit them. **A-Stock Scalpel** is different: every score is computed from a **deterministic rule table**. You can read `core/rules.py` and understand exactly why a stock scored what it did.

## ✨ Features

| Feature | Detail |
|---------|--------|
| **9 Technical Factors** | RSI, MACD, KDJ, Bollinger Bands, Ichimoku Cloud, Alligator, ADX, OBV, Volume Profile |
| **32 Scoring Rules** | 18 bullish + 14 bearish, fully transparent in `core/rules.py` |
| **Dual Data Sources** | Sina Finance (primary) + East Money (fallback) — no API key needed |
| **Backtesting Engine** | Simulates past N days with ~0.457% trading cost modeled |
| **Auto-Fallback** | If Sina API fails, automatically switches to East Money |
| **Batch Scan** | Scans 100+ stocks in one command, outputs ranked table |

## 🚀 Quick Start

```bash
# 1. Clone
git clone git@github.com:zhubohan190601-crypto/a-stock-scalpel.git
cd a-stock-scalpel

# 2. Install
pip install -r requirements.txt

# 3. Scan the market (top 80 A-share stocks)
python3 core/analyzer.py --scan
```

### Example output

```
🔍 A-Stock Scalpel 扫描 | 2026-06-14 15:30
   候选池: 80 只标的
=================================================================
🏆 综合评分 TOP 20
=================================================================
  代码    名称        价格    涨跌    多  空  净分   信号
-----------------------------------------------------------------
 600519  贵州茅台   1520.00   +2.1%   8   2   +52   strong_buy
 300750  宁德时代    218.50   +3.4%   7   1   +48   strong_buy
 000858  五粮液     145.20   +1.8%   6   2   +35   buy
 ...
```

### Analyze a single stock

```bash
python3 core/analyzer.py 600519
```

### Run backtest

```bash
python3 core/backtest.py
```

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Command Line / Cron                    │
├─────────────────────────────────────────────────────────┤
│  core/fetcher.py    — Market data (Sina + East Money)    │
│       ↓                                                 │
│  core/analyzer.py   — 9-factor computation engine        │
│       ↓                                                 │
│  core/rules.py      — 18 Bullish + 14 Bearish rules      │
│       ↓                                                 │
│  core/backtest.py   — Backtesting with cost modeling     │
└─────────────────────────────────────────────────────────┘
```

## 📈 Factor Details

| Factor | Config | What It Measures |
|--------|--------|-----------------|
| **RSI** | Period 14 | Overbought (>75) / Oversold (<25) |
| **MACD** | Fast 12, Slow 26, Signal 9 | Trend momentum & crossover |
| **KDJ** | Period 9 | Stochastic oscillator with K/D/J lines |
| **Bollinger** | Period 20, 2σ | Volatility bands & mean reversion |
| **Ichimoku** | 9/26/52 | Cloud-based trend & support/resistance |
| **Alligator** | 13/8/5 SMA | Trend direction (lips/teeth/jaw) |
| **ADX** | Period 14 | Trend strength with DI+/DI- |
| **OBV** | — | Volume confirmation of price moves |
| **Volume** | 5-day ratio | Volume expansion/contraction |

## 📝 Trading Costs

The backtest engine models **0.457% per round-trip trade**:
- Stamp duty: 0.10% (sell only)
- Commission: ~0.03% (negotiable, up to 0.03%)
- Slippage: ~0.327% (modeled)

> For daily-turnover strategies, ignoring friction costs inflates returns by 20-40%.

## ⚠️ Disclaimer

**This is NOT financial advice.** A-Stock Scalpel is an **educational/research tool** for quantitative analysis experimentation. Past backtest performance does not guarantee future results. Trading stocks involves risk of financial loss. Consult a licensed financial advisor before making investment decisions.

---

<div align="center">
  <p>Built with ❤️ for the Chinese quant community</p>
  <p>
    <a href="https://github.com/zhubohan190601-crypto/a-stock-scalpel/issues">Report Bug</a>
    ·
    <a href="https://github.com/zhubohan190601-crypto/a-stock-scalpel/issues">Feature Request</a>
  </p>
</div>
