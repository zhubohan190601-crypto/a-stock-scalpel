#!/usr/bin/env python3
"""Fetch comprehensive market data via East Money API"""
import urllib.request
import json

def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")

def parse_jsonp(text):
    start = text.find("(")
    end = text.rfind(")")
    if start >= 0 and end > start:
        text = text[start+1:end]
    return json.loads(text)

# === 1. A股指数 ===
# East Money uses integer*100 for prices (e.g. 3200.15 -> 320015)
# f2=最新价, f3=涨跌幅, f4=涨跌额, f12=代码, f14=名称
codes_str = "1.000001,0.399001,0.399006,1.000688"
url = f"https://push2.eastmoney.com/api/qt/ulist.np/get?fields=f2,f3,f4,f12,f14,f20,f21&secids={codes_str}"
data = parse_jsonp(fetch_json(url))

print("=== A股主要指数 (2026-07-09 收盘) ===")
if data.get("data") and data["data"].get("diff"):
    for item in data["data"]["diff"]:
        name = item.get("f14", "")
        raw_price = item.get("f2", 0)
        price = raw_price / 100.0 if raw_price else 0
        pct = item.get("f3", 0)
        if pct:
            pct = pct / 100.0  # already percentage * 100
        change = item.get("f4", 0) / 100.0 if item.get("f4") else 0
        open_p = item.get("f20", 0) / 100.0 if item.get("f20") else 0
        high = item.get("f21", 0) / 100.0 if item.get("f21") else 0
        print(f"{name}: {price:.2f}  涨跌幅: {pct:+.2f}%  涨跌额: {change:+.2f}")

# === 2. 成交额 ===
print("\n=== 沪深两市成交额 ===")
# Use 1.000001 for SH composite, 0.399001 for SZ component
# f169 = 成交额(元)
sh_url = "https://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f169"
sz_url = "https://push2.eastmoney.com/api/qt/stock/get?secid=0.399001&fields=f169"
try:
    sh_d = parse_jsonp(fetch_json(sh_url)).get("data", {})
    sz_d = parse_jsonp(fetch_json(sz_url)).get("data", {})
    sh_amt = (sh_d.get("f169") or 0) / 1e8
    sz_amt = (sz_d.get("f169") or 0) / 1e8
    print(f"沪市成交额: {sh_amt:.2f} 亿元")
    print(f"深市成交额: {sz_amt:.2f} 亿元")
    print(f"两市合计: {sh_amt+sz_amt:.2f} 亿元")
except Exception as e:
    print(f"成交额获取失败: {e}")

# === 3. 北向资金 ===
print("\n=== 北向资金净流入 ===")
try:
    # Kamt API for northbound
    nurl = "https://push2.eastmoney.com/api/qt/kamt.kline/get?fields1=f1,f2,f3&fields2=f51,f52,f53,f54&klt=1&lmt=1&secid=100"
    nd = parse_jsonp(fetch_json(nurl))
    if nd.get("data"):
        hk2sh = nd["data"].get("hk2sh", [])
        hk2sz = nd["data"].get("hk2sz", [])
        if hk2sh:
            parts = hk2sh[0].split(",")
            print(f"日期: {parts[0]}")
            print(f"沪股通(港->沪)净买入: {float(parts[1]):.2f} 亿元")
        if hk2sz:
            parts2 = hk2sz[0].split(",")
            print(f"深股通(港->深)净买入: {float(parts2[1]):.2f} 亿元")
            total = float(parts[1]) + float(parts2[1]) if hk2sh else float(parts2[1])
            print(f"北向资金合计净流入: {total:.2f} 亿元")
    else:
        print("北向资金接口未返回数据")
except Exception as e:
    print(f"北向资金获取失败: {e}")

print("\n=== 数据来源: 东方财富 API ===")
