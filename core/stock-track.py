#!/usr/bin/env python3
"""个股实时行情查询 - 用于cron job盘中推送"""
import urllib.request
import urllib.parse
import json
import re
import sys
from datetime import datetime

MARKET_PREFIX = {"0": "sz", "3": "sz", "6": "sh"}

def code_to_market(code):
    return MARKET_PREFIX.get(code[0], "sz")

def fetch_single(code):
    mkt = code_to_market(code)
    url = f"https://hq.sinajs.cn/list={mkt}{code}"
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        text = resp.read().decode("gbk")
        match = re.search(r'"(.*?)"', text)
        if not match:
            return None
        parts = match.group(1).split(",")
        if len(parts) < 32:
            return None
        yesterday_close = float(parts[2]) if parts[2] else 0
        price = float(parts[3]) if parts[3] else 0
        change_pct = round((price - yesterday_close) / yesterday_close * 100, 2) if yesterday_close > 0 else 0
        # 盘前容错：集合竞价前（9:15 前）或无成交价时 price=0，不应显示为 ¥0
        if price <= 0 or yesterday_close <= 0:
            return {
                "code": code,
                "name": parts[0] or code,
                "no_data": True,
                "note": "盘前无实时数据（集合竞价 9:15 后才有成交价）或停牌",
                "price": 0,
                "change_pct": 0,
                "yesterday_close": yesterday_close,
            }
        return {
            "code": code,
            "name": parts[0],
            "price": price,
            "change_pct": change_pct,
            "high": float(parts[4]) if parts[4] else 0,
            "low": float(parts[5]) if parts[5] else 0,
            "open": float(parts[1]) if parts[1] else 0,
            "volume": int(parts[8]) if parts[8] else 0,  # 股
            "amount": float(parts[9]) if parts[9] else 0,  # 元
            "yesterday_close": yesterday_close,
            "time": f"{parts[30]} {parts[31]}" if len(parts) > 31 else "",
        }
    except Exception as e:
        return {"code": code, "name": "?", "error": str(e), "price": 0, "change_pct": 0}

def format_output(data_list, time_label):
    """输出格式化文本"""
    lines = []
    lines.append(f"📊 {time_label}")
    lines.append(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    for d in data_list:
        if "error" in d and d.get("error"):
            lines.append(f"⚠️ {d['code']} 数据获取失败: {d['error']}")
            continue
        if d.get("no_data"):
            lines.append(f"⚪ **{d.get('name')} ({d['code']})** — 盘前无实时数据（集合竞价 9:15 后更新）")
            lines.append(f"   昨收: ¥{d.get('yesterday_close', 0)}")
            lines.append("")
            continue
        name = d.get("name", "?")
        code = d["code"]
        price = d.get("price", 0)
        change = d.get("change_pct", 0)
        sign = "🔴" if change > 0 else "🟢" if change < 0 else "⚪"
        vol_yi = round(d.get("volume", 0) / 100000000, 2) if d.get("volume") else 0
        amt_yi = round(d.get("amount", 0) / 100000000, 2) if d.get("amount") else 0
        
        lines.append(f"**{name} ({code})**")
        lines.append(f"{sign} ¥{price}  ({change:+.2f}%)")
        lines.append(f"   成交量: {vol_yi}亿股 | 成交额: ¥{amt_yi}亿")
        lines.append(f"   今开: ¥{d.get('open', 0)} 昨收: ¥{d.get('yesterday_close', 0)}")
        lines.append(f"   最高: ¥{d.get('high', 0)}  最低: ¥{d.get('low', 0)}")
        lines.append("")
    return "\n".join(lines)

if __name__ == "__main__":
    codes = ["300418", "300285"]
    time_label = sys.argv[1] if len(sys.argv) > 1 else "实时"
    results = [fetch_single(c) for c in codes]
    output = format_output(results, time_label)
    # 输出到stdout供cron agent读取
    print(output)
