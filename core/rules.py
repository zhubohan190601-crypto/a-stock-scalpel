#!/usr/bin/env python3
"""
a-stock-scalpel — 评分规则表（Factor Rules）
============================================
18 条多头规则 + 14 条空头规则
全部基于确定性因子判断，无 LLM 自由发挥

规则格式: {"id": "R01", "name": "...", "condition": "...", "weight": 1.5}

版本: v2.2.0
"""

MULTI_RULES = [
    # ── 动量趋势 ──
    {"id": "M01", "name": "5日动量为正", "desc": "mom_5d > 3%",
     "check": lambda f: f.get("mom_5d", -100) > 3, "weight": 2.0},
    {"id": "M02", "name": "20日动量为正", "desc": "mom_20d > 5%",
     "check": lambda f: f.get("mom_20d", -100) > 5, "weight": 1.5},
    {"id": "M03", "name": "均线多头排列", "desc": "ma5 > ma10 > ma20",
     "check": lambda f: f.get("ma5", 0) > f.get("ma10", 0) > f.get("ma20", 0), "weight": 2.0},
    {"id": "M04", "name": "价格站上布林中轨", "desc": "price > bollinger.ma",
     "check": lambda f: f.get("price", 0) > f.get("bollinger", {}).get("ma", 999999), "weight": 1.5},
    
    # ── 震荡指标 ──
    {"id": "M05", "name": "RSI强势非超买", "desc": "50 < RSI < 75",
     "check": lambda f: 50 < f.get("rsi", 50) < 75, "weight": 1.5},
    {"id": "M06", "name": "KDJ金叉", "desc": "K上穿D（K>D且前值K≤D）",
     "check": lambda f: f.get("kdj", {}).get("k", 0) > f.get("kdj", {}).get("d", 0), "weight": 2.0},
    {"id": "M07", "name": "MACD零轴上方", "desc": "MACD > 0",
     "check": lambda f: f.get("macd", {}).get("macd", -1) > 0, "weight": 1.5},
    {"id": "M08", "name": "MACD柱状体扩大", "desc": "histogram > 0",
     "check": lambda f: f.get("macd", {}).get("histogram", -1) > 0, "weight": 1.0},
    
    # ── 量能 ──
    {"id": "M09", "name": "成交量放大", "desc": "vol_ratio > 1.5",
     "check": lambda f: f.get("vol_ratio", 0) > 1.5, "weight": 1.5},
    {"id": "M10", "name": "OBV向上", "desc": "obv_slope > 0",
     "check": lambda f: f.get("obv", {}).get("obv_slope", 0) > 0, "weight": 1.0},
    {"id": "M11", "name": "量价配合", "desc": "上涨+放量",
     "check": lambda f: f.get("change_pct", 0) > 1 and f.get("vol_ratio", 0) > 1.2, "weight": 2.0},
    
    # ── 趋势强度 ──
    {"id": "M12", "name": "ADX趋势确认", "desc": "ADX > 25",
     "check": lambda f: f.get("adx", {}).get("adx", 0) > 25, "weight": 1.5},
    {"id": "M13", "name": "DI+ > DI-", "desc": "多头力量大于空头",
     "check": lambda f: f.get("adx", {}).get("di_plus", 0) > f.get("adx", {}).get("di_minus", 999), "weight": 1.5},
    
    # ── 结构确认 ──
    {"id": "M14", "name": "鳄鱼线多头", "desc": "嘴唇>牙齿>下巴",
     "check": lambda f: f.get("alligator", {}).get("state", "") == "uptrend", "weight": 2.0},
    {"id": "M15", "name": "一目均衡买入", "desc": "转换线>基准线",
     "check": lambda f: f.get("ichimoku", {}).get("tenkan_kijun_cross", "") == "buy", "weight": 1.5},
    
    # ── 布林带 ──
    {"id": "M16", "name": "布林带宽扩张", "desc": "bandwidth > 5% (波动性启动)",
     "check": lambda f: f.get("bollinger", {}).get("bandwidth", 0) > 5, "weight": 1.0},
    {"id": "M17", "name": "价格突破上轨", "desc": "price > upper (强势信号)",
     "check": lambda f: f.get("price", 0) > f.get("bollinger", {}).get("upper", 999999), "weight": 1.0},
    
    # ── 综合 ──
    {"id": "M18", "name": "多指标共振", "desc": "同时满足M05+M06+M09",
     "check": lambda f: (50 < f.get("rsi", 50) < 75 and
                         f.get("kdj", {}).get("k", 0) > f.get("kdj", {}).get("d", 0) and
                         f.get("vol_ratio", 0) > 1.5), "weight": 2.5},
]

SHORT_RULES = [
    # ── 动量反转 ──
    {"id": "S01", "name": "5日动量转负", "desc": "mom_5d < -3%",
     "check": lambda f: f.get("mom_5d", 100) < -3, "weight": 2.0},
    {"id": "S02", "name": "20日动量转负", "desc": "mom_20d < -5%",
     "check": lambda f: f.get("mom_20d", 100) < -5, "weight": 1.5},
    {"id": "S03", "name": "均线空头排列", "desc": "ma5 < ma10 < ma20",
     "check": lambda f: f.get("ma5", 999999) < f.get("ma10", 999999) < f.get("ma20", 999999), "weight": 2.0},
    
    # ── 超买反转 ──
    {"id": "S04", "name": "RSI超买", "desc": "RSI > 75",
     "check": lambda f: f.get("rsi", 50) > 75, "weight": 1.5},
    {"id": "S05", "name": "RSI顶背离", "desc": "价格新高但RSI未新高（简化: RSI>80）",
     "check": lambda f: f.get("rsi", 50) > 80, "weight": 2.0},
    
    # ── 指标死叉 ──
    {"id": "S06", "name": "KDJ死叉", "desc": "K下穿D（K<D）",
     "check": lambda f: f.get("kdj", {}).get("k", 0) < f.get("kdj", {}).get("d", 0), "weight": 2.0},
    {"id": "S07", "name": "MACD零轴下方", "desc": "MACD < 0",
     "check": lambda f: f.get("macd", {}).get("macd", 1) < 0, "weight": 1.5},
    {"id": "S08", "name": "MACD柱状体缩小", "desc": "histogram < 0",
     "check": lambda f: f.get("macd", {}).get("histogram", 1) < 0, "weight": 1.0},
    
    # ── 量能异常 ──
    {"id": "S09", "name": "缩量上涨", "desc": "上涨但量缩",
     "check": lambda f: f.get("change_pct", 0) > 1 and f.get("vol_ratio", 2) < 0.8, "weight": 1.5},
    {"id": "S10", "name": "放量下跌", "desc": "下跌+放量",
     "check": lambda f: f.get("change_pct", 0) < -1 and f.get("vol_ratio", 0) > 1.5, "weight": 2.0},
    
    # ── 趋势转弱 ──
    {"id": "S11", "name": "DI- > DI+", "desc": "空头力量主导",
     "check": lambda f: f.get("adx", {}).get("di_minus", 0) > f.get("adx", {}).get("di_plus", 999), "weight": 1.5},
    {"id": "S12", "name": "鳄鱼线空头", "desc": "嘴唇<牙齿<下巴(空头排列)",
     "check": lambda f: f.get("alligator", {}).get("state", "") == "downtrend", "weight": 2.0},
    {"id": "S13", "name": "一目均衡卖出", "desc": "转换线<基准线",
     "check": lambda f: f.get("ichimoku", {}).get("tenkan_kijun_cross", "") == "sell", "weight": 1.5},
    
    # ── 布林带 ──
    {"id": "S14", "name": "价格跌破下轨", "desc": "price < lower (超卖但趋势弱)",
     "check": lambda f: f.get("price", 999) < f.get("bollinger", {}).get("lower", 0), "weight": 1.0},
]


def score_factors(factors: dict) -> dict:
    """
    给一组因子数据打分
    
    返回:
        multi_score: 多头信号命中数 × 加权总分
        short_score: 空头信号命中数 × 加权总分
        net_score: multi - short（正则化到 -100 ~ +100）
        hit_rules: 命中的规则ID列表
    """
    multi_hits = []
    short_hits = []
    multi_weighted = 0.0
    short_weighted = 0.0
    
    for rule in MULTI_RULES:
        if rule["check"](factors):
            multi_hits.append(rule["id"])
            multi_weighted += rule["weight"]
    
    for rule in SHORT_RULES:
        if rule["check"](factors):
            short_hits.append(rule["id"])
            short_weighted += rule["weight"]
    
    total_possible_multi = sum(r["weight"] for r in MULTI_RULES)
    total_possible_short = sum(r["weight"] for r in SHORT_RULES)
    
    multi_norm = multi_weighted / total_possible_multi * 100 if total_possible_multi else 0
    short_norm = short_weighted / total_possible_short * 100 if total_possible_short else 0
    net = multi_norm - short_norm
    
    return {
        "multi_score": round(multi_norm, 1),
        "short_score": round(short_norm, 1),
        "net_score": round(net, 1),
        "multi_hits": len(multi_hits),
        "short_hits": len(short_hits),
        "multi_rules": multi_hits,
        "short_rules": short_hits,
        "signal": "strong_buy" if net >= 40 else
                  "buy" if net >= 20 else
                  "neutral" if net > -20 else
                  "sell" if net > -40 else
                  "strong_sell",
    }


def describe_signal(signal: str) -> str:
    descs = {
        "strong_buy": "🔴 强烈买入信号 — 多头共振，多指标确认上涨趋势",
        "buy": "🟠 买入信号 — 偏向多头，需确认",
        "neutral": "⚪ 中性 — 多空均衡，观望",
        "sell": "🟢 卖出信号 — 偏向空头，注意风险",
        "strong_sell": "🔵 强烈卖出信号 — 空头共振，回避或减仓",
    }
    return descs.get(signal, "未知信号")


if __name__ == "__main__":
    # 演示
    sample = {
        "price": 15.80,
        "ma5": 15.60, "ma10": 15.20, "ma20": 14.80,
        "change_pct": 2.3, "mom_5d": 5.2, "mom_20d": 8.1,
        "vol_ratio": 1.8,
        "rsi": 62,
        "macd": {"macd": 0.15, "signal": 0.10, "histogram": 0.05},
        "kdj": {"k": 65, "d": 55, "j": 85},
        "bollinger": {"ma": 15.20, "upper": 16.50, "lower": 13.90, "bandwidth": 8.5},
        "ichimoku": {"tenkan": 15.80, "kijun": 15.10, "senkou_a": 15.30, "tenkan_kijun_cross": "buy"},
        "adx": {"adx": 28, "di_plus": 30, "di_minus": 18},
        "alligator": {"jaw": 15.00, "teeth": 15.30, "lips": 15.60, "state": "uptrend"},
        "obv": {"obv": 100000, "obv_slope": 3.5},
    }
    result = score_factors(sample)
    print(f"多头命中: {result['multi_hits']}/{len(MULTI_RULES)}")
    print(f"多头加权: {result['multi_score']:.1f}%")
    print(f"空头命中: {result['short_hits']}/{len(SHORT_RULES)}")
    print(f"空头加权: {result['short_score']:.1f}%")
    print(f"净得分: {result['net_score']:.1f}")
    print(f"信号: {result['signal']} — {describe_signal(result['signal'])}")
    print(f"命中规则: {result['multi_rules'] + result['short_rules']}")
