#!/usr/bin/env python3
"""
阿不 选股筛选器
基于基础数据做多因子筛选，生成关注列表
"""
import sys
import os
import json
import urllib.request
import re
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.fetcher import fetch_batch, code_to_market

REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")

# 常用A股标的池（沪深300核心+行业龙头）
A_POOL = [
    # 银行金融
    "600036","601398","601939","601288","601328","601166","600030","601318","601211",
    # 消费
    "600519","000858","000568","600809","600887","002714","000333","000651",
    # 科技
    "002415","002475","002594","300750","300760","300124","002371","603501",
    # 能源/资源
    "601857","600028","600585","601088","601899","600900",
    # 半导体/芯片
    "688981","688256","688036","688008","688012","002049",
    # 医药
    "600276","300015","300759","000538",
    # 通信/运营商
    "601728","600941","600050",
    # 地产/基建
    "000002","601668","600585",
    # 汽车
    "600104","000625","002594","601238",
    # 其他龙头
    "000725","000063","002230","300059","002352","601012","600438","002129",
]

def fetch_kline_sina(code, scale="daily", datalen=60):
    """从新浪获取K线数据 - 使用30分钟线数据近似"""
    from core.fetcher import fetch_kline
    # 日线接口被墙了，用30分钟线 (scale=30) 聚合成近似日线
    if scale == "daily":
        data_30 = fetch_kline(code, scale="30min", datalen=datalen*4)
        if data_30 and len(data_30) > 0:
            # 按日期聚合
            days = {}
            for k in data_30:
                day = k["day"][:10]
                if day not in days:
                    days[day] = {"open": float(k["open"]), "high": float(k["high"]), "low": float(k["low"]), "close": float(k["close"]), "volume": int(k["volume"]), "day": day}
                else:
                    d = days[day]
                    d["high"] = max(d["high"], float(k["high"]))
                    d["low"] = min(d["low"], float(k["low"]))
                    d["close"] = float(k["close"])
                    d["volume"] += int(k["volume"])
            return list(days.values())
        return []
    return fetch_kline(code, scale=scale, datalen=datalen)

def calc_momentum(kline_data, periods=[5, 20, 60]):
    """计算动量指标"""
    if not kline_data or len(kline_data) < max(periods):
        return {}
    
    closes = [float(k["close"]) for k in kline_data]
    volumes = [int(k["volume"]) for k in kline_data]
    current = closes[-1]
    
    result = {}
    for p in periods:
        if len(closes) > p:
            prev = closes[-p-1] if len(closes) > p else closes[0]
            result[f"mom_{p}d"] = round((current - prev) / prev * 100, 2)
    
    # 成交量变化
    if len(volumes) > 20:
        avg_vol_20 = sum(volumes[-21:-1]) / 20
        result["vol_ratio"] = round(volumes[-1] / avg_vol_20, 2) if avg_vol_20 > 0 else 0
    
    # 波动率(20日)
    if len(closes) > 20:
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(-20, 0)]
        avg_ret = sum(returns) / len(returns)
        variance = sum((r - avg_ret)**2 for r in returns) / len(returns)
        result["volatility_20d"] = round((variance**0.5) * 100, 2)
    
    # 趋势强度：近5日均线斜率
    if len(closes) > 5:
        ma5 = sum(closes[-5:]) / 5
        ma5_prev = sum(closes[-10:-5]) / 5
        result["ma5_slope"] = round((ma5 - ma5_prev) / ma5_prev * 100, 2) if ma5_prev > 0 else 0
    
    return result

def finance_indicator(code):
    """获取基本面参考指标（市盈率等）- 通过新浪基础信息"""
    mkt = code_to_market(code)
    url = f"https://hq.sinajs.cn/list={mkt}{code}"
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        text = resp.read().decode("gbk")
        # 第3个字段是昨收，可以算日内表现
        match = re.search(r'"(.*?)"', text)
        if match:
            parts = match.group(1).split(",")
            if len(parts) >= 10:
                return {
                    "name": parts[0],
                    "open": float(parts[1]) if parts[1] else 0,
                    "yclose": float(parts[2]) if parts[2] else 0,
                }
        return None
    except:
        return None

def run_screening():
    """执行多因子筛选"""
    print(f"\n🔍 阿不 选股筛选 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 第一步：获取实时行情
    batch_size = 50
    all_stocks = []
    for i in range(0, len(A_POOL), batch_size):
        batch = A_POOL[i:i+batch_size]
        results = fetch_batch(batch)
        all_stocks.extend(results)
        time.sleep(0.5)
    
    valid = [s for s in all_stocks if "error" not in s and "price" in s]
    print(f"有效数据: {len(valid)}/{len(A_POOL)} 只")
    
    # 第二步：对部分候选标的分析K线
    # 先筛选：今日涨跌幅前30的
    valid.sort(key=lambda x: abs(x.get("change_pct", 0)), reverse=True)
    candidates = valid[:40]  # 最活跃的前40只
    
    print(f"\n📊 技术面分析 {len(candidates)} 只标的...")
    
    screened = []
    for s in candidates:
        code = s["code"]
        kline = fetch_kline_sina(code, scale="daily", datalen=65)
        if not kline:
            continue
        
        mom = calc_momentum(kline)
        if not mom:
            continue
        
        s.update(mom)
        screened.append(s)
        time.sleep(0.3)  # 礼貌间隔
    
    # 第三步：多因子评分
    # 因子: 近期动量 + 成交量放大 + 趋势强度 + 波动率
    def score(stock):
        s = 0
        # 5日动量 > 3% 加分
        if stock.get("mom_5d", 0) > 3:
            s += 2
        elif stock.get("mom_5d", 0) > 1:
            s += 1
        # 成交量放大
        if stock.get("vol_ratio", 1) > 2:
            s += 2
        elif stock.get("vol_ratio", 1) > 1.5:
            s += 1
        # 趋势向上
        if stock.get("ma5_slope", 0) > 1:
            s += 2
        elif stock.get("ma5_slope", 0) > 0.3:
            s += 1
        # 今日涨幅
        if abs(stock.get("change_pct", 0)) > 3:
            s += 1
        # 波动适当（不太低也不太高）
        vol = stock.get("volatility_20d", 3)
        if 1.5 <= vol <= 5:
            s += 1
        return s
    
    for s in screened:
        s["score"] = score(s)
    
    # 去重
    seen_codes = set()
    unique_screened = []
    for s in screened:
        if s["code"] not in seen_codes:
            seen_codes.add(s["code"])
            unique_screened.append(s)
    screened = unique_screened
    
    # 按分数排序
    screened.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("🏆 多因子筛选 TOP 15")
    print("=" * 60)
    print(f"{'代码':>6} {'名称':<8} {'价格':>8} {'今日%':>6} {'5日%':>6} {'量比':>5} {'趋势%':>6} {'评分':>4}")
    print("-" * 55)
    
    top15 = screened[:15]
    for s in top15:
        print(f"{s['code']:>6} {s.get('name',''):<8} {s['price']:>8.2f} "
              f"{s.get('change_pct',0):>+5.1f}% {s.get('mom_5d',0):>+5.1f}% "
              f"{s.get('vol_ratio',1):>4.1f}x {s.get('ma5_slope',0):>+5.1f}% "
              f"{s.get('score',0):>4d}")
    
    # 保存报告
    lines = [
        f"# 📊 阿不 选股筛选报告",
        f"",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**扫描范围**: {len(A_POOL)} 只沪深核心标的",
        f"**筛选方法**: 多因子评分（动量+量能+趋势+波动）",
        f"",
        f"---",
        f"",
        f"## 🏆 综合评分 TOP 15",
        f"",
        f"| 代码 | 名称 | 价格 | 今日 | 5日动量 | 量比 | 趋势 | 评分 |",
        f"|------|------|------|------|---------|------|------|------|",
    ]
    for s in top15:
        lines.append(
            f"| {s['code']} | {s.get('name','')} | {s['price']:.2f} | "
            f"{s.get('change_pct',0):+.1f}% | {s.get('mom_5d',0):+.1f}% | "
            f"{s.get('vol_ratio',1):.1f}x | {s.get('ma5_slope',0):+.1f}% | {s.get('score',0)} |"
        )
    
    # 低评分但值得关注的（跌幅超大/超卖）
    lines.append(f"\n## ⚠️ 超卖关注（跌幅较大）\n")
    oversold = [s for s in screened if s.get("mom_5d", 0) < -5]
    if oversold:
        for s in oversold[:5]:
            lines.append(f"- {s.get('name','')}({s['code']}): 5日跌{s.get('mom_5d',0):.1f}%")
    else:
        lines.append("- 无明显超卖标的")
    
    content = "\n".join(lines)
    filename = f"screening_{datetime.now().strftime('%Y%m%d')}.md"
    filepath = os.path.join(REPORT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n✅ 报告保存: {filepath}")

if __name__ == "__main__":
    run_screening()
