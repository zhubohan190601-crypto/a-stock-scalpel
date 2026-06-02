#!/usr/bin/env python3
"""
阿不 金融数据采集核心
数据源: 新浪财经免费接口 (最稳定，无需token)
"""

import urllib.request
import urllib.parse
import json
import time
import os
import csv
from datetime import datetime, timedelta
import re

# ========== 配置区 ==========
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 深交所: sz, 上交所: sh
MARKET_PREFIX = {
    "0": "sz",  # 深市
    "3": "sz",  # 创业板
    "6": "sh",  # 沪市
}

def code_to_market(code):
    """根据股票代码前缀判断市场"""
    prefix = code[0]
    return MARKET_PREFIX.get(prefix, "sz")

def fetch_single(code):
    """获取单只股票实时行情"""
    mkt = code_to_market(code)
    url = f"https://hq.sinajs.cn/list={mkt}{code}"
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        text = resp.read().decode("gbk")
        # 解析返回数据
        match = re.search(r'"(.*?)"', text)
        if not match:
            return None
        parts = match.group(1).split(",")
        if len(parts) < 30:
            return None
        return {
            "code": code,
            "name": parts[0],
            "open": float(parts[1]),
            "yesterday_close": float(parts[2]),
            "price": float(parts[3]),
            "high": float(parts[4]),
            "low": float(parts[5]),
            "buy": float(parts[6]),
            "sell": float(parts[7]),
            "volume": int(parts[8]),  # 成交量(股)
            "amount": float(parts[9]),  # 成交额(元)
            "time": f"{parts[30]} {parts[31]}",
        }
    except Exception as e:
        return {"code": code, "error": str(e)}

def fetch_batch(codes):
    """批量获取实时行情, 同一次请求"""
    codes_str = ",".join(f"{code_to_market(c)}{c}" for c in codes)
    url = f"https://hq.sinajs.cn/list={codes_str}"
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        text = resp.read().decode("gbk")
        results = []
        lines = [l for l in text.strip().split("\n") if l.strip()]
        for i, code in enumerate(codes):
            if i < len(lines):
                match = re.search(r'"(.*?)"', lines[i])
                if match:
                    parts = match.group(1).split(",")
                    if len(parts) >= 32 and parts[0]:
                        results.append({
                            "code": code,
                            "name": parts[0],
                            "price": float(parts[3]),
                            "change_pct": round((float(parts[3]) - float(parts[2])) / float(parts[2]) * 100, 2) if float(parts[2]) > 0 else 0,
                            "high": float(parts[4]),
                            "low": float(parts[5]),
                            "amount_yi": round(float(parts[9]) / 100000000, 2),
                            "time": parts[31],
                        })
                    else:
                        results.append({"code": code, "error": "parse_failed"})
                else:
                    results.append({"code": code, "error": "no_match"})
            else:
                results.append({"code": code, "error": "no_line"})
        return results
    except Exception as e:
        return [{"code": c, "error": str(e)} for c in codes]

def fetch_kline(code, scale="daily", datalen=120):
    """获取历史K线数据"""
    mkt = code_to_market(code)
    # scale: 30=30分钟线, 240=日线, 14400=周线
    scale_map = {"daily": "240", "weekly": "14400", "30min": "30", "60min": "60"}
    s = scale_map.get(scale, "240")
    url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={mkt}{code}&scale={s}&datalen={datalen}"
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        text = resp.read().decode("utf-8")
        data = json.loads(text)
        if isinstance(data, dict) and "__ERROR" in data:
            return []
        return data
    except Exception as e:
        return []

def save_snapshot(data, filename=None):
    """保存快照到CSV"""
    if filename is None:
        filename = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(DATA_DIR, filename)
    if not data:
        return None
    
    keys = data[0].keys()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    return filepath

def fetch_all_a_spot():
    """获取全市场实时行情(通过新浪批量接口,每请求最多100只)"""
    # 生成沪深两市所有股票代码列表
    # 这里用已知的常见股票做样本,后续可以扩展
    all_codes = []
    # 沪深300成分股 (常用前50个)
    codes_sample = [
        "000001","000002","000333","000651","000858","000568","000725","000063",
        "002415","002714","002475","002594","300750","300059","300760","300124",
        "600519","600036","600900","600276","600887","600030","601318","601166",
        "601398","601288","601857","601988","600028","600585","601088","600690",
        "601012","600809","601899","600406","600436","600309","600438","600196",
        "688981","688256","688036","688008","601728","601658","601939","601328",
    ]
    # 分批请求,每批80个
    batch_size = 80
    all_results = []
    for i in range(0, len(codes_sample), batch_size):
        batch = codes_sample[i:i+batch_size]
        results = fetch_batch(batch)
        all_results.extend(results)
        time.sleep(0.3)  # 礼貌间隔
    return all_results

if __name__ == "__main__":
    # 测试
    result = fetch_single("000001")
    print("单只测试:", result)
    
    print("\n批量测试(前5只):")
    batch = fetch_batch(["000001","000002","600519","300750","000333"])
    for r in batch:
        if "error" not in r:
            print(f"  {r['code']} {r['name']}: {r['price']} ({r['change_pct']}%)")
    
    print("\n快照保存位置:", DATA_DIR)
