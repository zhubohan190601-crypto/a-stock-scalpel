# finbot — 本地的A股数据管家

> 一个跑在你 Mac 上的自主金融数据系统。零成本数据源，每日自动产出。

## 它能干什么

- **📊 每日收盘简报** — 板块轮动、成交额排名、异动监控
- **🏆 选股筛选** — 多因子模型评分（动量+量能+趋势+波动率）
- **⏰ 定时自动化** — 交易日 15:30 自动生成简报推送到你
- **📈 实时行情** — 支持任意A股标的的一键查询

## 快速开始

\`\`\`bash
# 克隆后
cd finbot
source venv/bin/activate  # 或: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
python3 core/analyzer.py --report
\`\`\`

## 数据源

新浪财经免费接口（无需 API Key，零成本）。实时可靠，2015年起持续运行。

## 合规声明

本工具仅提供市场数据整理与展示，不构成任何投资建议。**投资有风险，决策需自主。**

## 授权

MIT License — 随便用，随便改。
