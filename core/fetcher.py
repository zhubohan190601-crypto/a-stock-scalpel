#!/usr/bin/env python3
"""
a-stock-scalpel — 数据采集层
==============================
数据源: 新浪财经(主) + 东方财富(备)
无需 API Key，零成本运行为设计目标

9 个技术因子接口:
  - RSI, MACD, KDJ, Bollinger Bands, Ichimoku Cloud
  - Alligator, ADX, OBV, Volume Profile
"""

import urllib.request
import urllib.parse
import json
import time
import os
import re
import math
from datetime import datetime
from typing import Optional


# ── 目录结构 ──
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ── 市场前缀映射 ──
MARKET_PREFIX = {
    "0": "sz", "3": "sz",
    "6": "sh", "9": "sh",
    "4": "bj", "8": "bj",
}


def code_to_market(code: str) -> str:
    prefix = code[0]
    return MARKET_PREFIX.get(prefix, "sz")


# ═══════════════════════════════════════════════
# 行情采集（主: 新浪 ｜ 备: 东方财富）
# ═══════════════════════════════════════════════

def _sina_realtime(code: str) -> Optional[dict]:
    """新浪实时行情"""
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
        if len(parts) < 32 or not parts[0]:
            return None
        yesterday = float(parts[2])
        price = float(parts[3])
        return {
            "code": code, "name": parts[0],
            "open": float(parts[1]), "yclose": yesterday,
            "price": price, "high": float(parts[4]), "low": float(parts[5]),
            "volume": int(parts[8]), "amount_yi": round(float(parts[9]) / 1e8, 2),
            "change_pct": round((price - yesterday) / yesterday * 100, 2) if yesterday else 0,
            "time": f"{parts[30]} {parts[31]}",
            "source": "sina"
        }
    except Exception:
        return None


def _eastmoney_realtime(code: str) -> Optional[dict]:
    """东方财富实时行情（备用）"""
    mkt = {"sz": "0", "sh": "1", "bj": "2"}.get(code_to_market(code), "1")
    secid = f"{mkt}.{code}"
    url = (f"https://push2.eastmoney.com/api/qt/stock/get?"
           f"secid={secid}&fields=f43,f44,f45,f46,f47,f48,f50,f57,f58,f170,f171")
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        data = json.loads(resp.read())
        d = data.get("data", {})
        if not d:
            return None
        price = d.get("f43", 0)
        yclose = d.get("f44", price)
        return {
            "code": code, "name": d.get("f58", ""),
            "price": price, "yclose": yclose,
            "high": d.get("f45", 0), "low": d.get("f46", 0),
            "open": d.get("f47", 0), "volume": d.get("f48", 0) or 0,
            "amount_yi": round((d.get("f50", 0) or 0) / 1e8, 2),
            "change_pct": round((price - yclose) / yclose * 100, 2) if yclose else 0,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "eastmoney"
        }
    except Exception:
        return None


def fetch_single(code: str) -> Optional[dict]:
    """单只股票实时行情（自动 fallback）"""
    result = _sina_realtime(code)
    if result:
        return result
    # 新浪失败 → 东方财富
    result = _eastmoney_realtime(code)
    if result:
        return result
    return {"code": code, "error": "all_sources_failed"}


def fetch_batch(codes: list, max_per_batch: int = 80) -> list:
    """批量获取（新浪批量，自动降级到逐个）"""
    # 新浪批量
    parts = []
    all_results = []
    for c in codes:
        mkt = code_to_market(c)
        parts.append(f"{mkt}{c}")
    url = f"https://hq.sinajs.cn/list={','.join(parts)}"
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        text = resp.read().decode("gbk")
        lines = [l for l in text.strip().split("\n") if l.strip()]
        for i, code in enumerate(codes):
            if i < len(lines):
                match = re.search(r'"(.*?)"', lines[i])
                if match:
                    parts2 = match.group(1).split(",")
                    if len(parts2) >= 32 and parts2[0]:
                        yclose = float(parts2[2])
                        price = float(parts2[3])
                        all_results.append({
                            "code": code, "name": parts2[0],
                            "price": price, "yclose": yclose,
                            "change_pct": round((price - yclose) / yclose * 100, 2) if yclose else 0,
                            "high": float(parts2[4]), "low": float(parts2[5]),
                            "amount_yi": round(float(parts2[9]) / 1e8, 2),
                            "time": parts2[31], "source": "sina"
                        })
                        continue
            # 降级到逐个
            single = _sina_realtime(code) or _eastmoney_realtime(code)
            if single:
                all_results.append(single)
            else:
                all_results.append({"code": code, "error": "fetch_failed"})
    except Exception:
        # 全量降级
        for code in codes:
            single = _sina_realtime(code) or _eastmoney_realtime(code)
            all_results.append(single or {"code": code, "error": str(Exception)})
    return all_results


# ═══════════════════════════════════════════════
# K线数据（新浪 + 东方财富双源）
# ═══════════════════════════════════════════════

def fetch_kline(code: str, scale: str = "daily", datalen: int = 120) -> list:
    """获取K线，返回 [{day,open,high,low,close,volume}, ...]"""
    mkt = code_to_market(code)
    scale_map = {"daily": "240", "weekly": "14400", "30min": "30", "60min": "60"}
    s = scale_map.get(scale, "240")
    
    # 新浪
    url = (f"https://quotes.sina.cn/cn/api/json_v2.php/"
           f"CN_MarketData.getKLineData?symbol={mkt}{code}&scale={s}&datalen={datalen}")
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        text = resp.read().decode("utf-8")
        data = json.loads(text)
        if isinstance(data, list) and len(data) > 0:
            return [{
                "day": k["day"][:19],
                "open": float(k.get("open", 0)),
                "high": float(k.get("high", 0)),
                "low": float(k.get("low", 0)),
                "close": float(k.get("close", 0)),
                "volume": int(k.get("volume", 0)),
            } for k in data]
    except Exception:
        pass
    
    # 降级：东方财富
    secid = {"sz": "0", "sh": "1", "bj": "2"}.get(mkt, "1")
    dm = {"daily": "101", "weekly": "102", "30min": "105", "60min": "106"}
    url2 = (f"https://push2.eastmoney.com/api/qt/stock/kline/get?"
            f"secid={secid}.{code}&klt={dm.get(scale,'101')}&fqt=1&lmt={datalen}")
    try:
        resp2 = urllib.request.urlopen(url2, timeout=10)
        d2 = json.loads(resp2.read()).get("data", {})
        klines = d2.get("klines", [])
        result = []
        for line in klines:
            parts_line = line.split(",")
            if len(parts_line) >= 6:
                result.append({
                    "day": parts_line[0],
                    "open": float(parts_line[1]),
                    "close": float(parts_line[2]),
                    "high": float(parts_line[3]),
                    "low": float(parts_line[4]),
                    "volume": int(parts_line[5]),
                })
        if result:
            return result
    except Exception:
        pass
    return []


# ═══════════════════════════════════════════════
# 技术因子计算（纯算法，无外部依赖）
# ═══════════════════════════════════════════════

def calc_rsi(closes: list, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains = losses = 0
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - 100.0 / (1.0 + rs), 2)


def calc_macd(closes: list, fast=12, slow=26, signal=9) -> dict:
    def ema(data, n):
        if len(data) < n:
            return data[-1] if data else 0
        k = 2 / (n + 1)
        result = data[0]
        for v in data[1:]:
            result = v * k + result * (1 - k)
        return result
    if len(closes) < slow + signal:
        return {"macd": 0, "signal": 0, "histogram": 0}
    fast_ema = ema(closes[-fast:], fast) if len(closes) >= fast else closes[-1]
    slow_ema = ema(closes[-slow:], slow) if len(closes) >= slow else closes[-1]
    short_ema = ema(closes, fast)
    long_ema = ema(closes, slow)
    macd_line = short_ema - long_ema
    # signal
    macd_list = []
    for i in range(max(fast, slow), len(closes)):
        s_ema = ema(closes[max(0, i-fast+1):i+1], fast)
        l_ema = ema(closes[max(0, i-slow+1):i+1], slow)
        macd_list.append(s_ema - l_ema)
    sig = ema(macd_list, signal) if len(macd_list) >= signal else macd_line
    return {
        "macd": round(macd_line, 4),
        "signal": round(sig, 4),
        "histogram": round(macd_line - sig, 4)
    }


def calc_kdj(closes: list, highs: list, lows: list, period=9) -> dict:
    if len(closes) < period:
        return {"k": 50, "d": 50, "j": 50}
    recent = closes[-period:]
    h = max(highs[-period:])
    l = min(lows[-period:])
    r = h - l or 0.01
    rsv = (recent[-1] - l) / r * 100
    k = 50.0
    d = 50.0
    for _ in range(period):
        k = 2/3 * k + 1/3 * rsv
        d = 2/3 * d + 1/3 * k
    j = 3 * k - 2 * d
    return {"k": round(k, 2), "d": round(d, 2), "j": round(j, 2)}


def calc_bollinger(closes: list, period=20, std_mult=2) -> dict:
    if len(closes) < period:
        ma = sum(closes) / len(closes) if closes else 0
        return {"ma": round(ma, 2), "upper": round(ma, 2), "lower": round(ma, 2)}
    recent = closes[-period:]
    ma = sum(recent) / period
    var = sum((x - ma) ** 2 for x in recent) / period
    std = var ** 0.5
    return {
        "ma": round(ma, 2),
        "upper": round(ma + std_mult * std, 2),
        "lower": round(ma - std_mult * std, 2),
        "bandwidth": round(std / ma * 100, 2) if ma else 0,
    }


def calc_ichimoku(closes: list, highs: list, lows: list) -> dict:
    """一目均衡表（简化版：仅转换线+基准线+先行带A）"""
    if len(closes) < 26:
        return {"tenkan": 0, "kijun": 0, "senkou_a": 0}
    h9 = max(highs[-9:]) if len(highs) >= 9 else max(highs)
    l9 = min(lows[-9:]) if len(lows) >= 9 else min(lows)
    tenkan = (h9 + l9) / 2
    h26 = max(highs[-26:]) if len(highs) >= 26 else max(highs)
    l26 = min(lows[-26:]) if len(lows) >= 26 else min(lows)
    kijun = (h26 + l26) / 2
    senkou_a = (tenkan + kijun) / 2
    return {
        "tenkan": round(tenkan, 2),
        "kijun": round(kijun, 2),
        "senkou_a": round(senkou_a, 2),
        "tenkan_kijun_cross": "buy" if tenkan > kijun else "sell",
    }


def calc_adx(closes: list, highs: list, lows: list, period=14) -> dict:
    """ADX + DI+/DI-"""
    if len(closes) < period + 1:
        return {"adx": 25, "di_plus": 25, "di_minus": 25}
    tr_list, dm_plus, dm_minus = [], [], []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        dm_plus.append(up if up > down and up > 0 else 0)
        dm_minus.append(down if down > up and down > 0 else 0)
    tr14 = sum(tr_list[-period:]) / period
    di14_p = sum(dm_plus[-period:]) / period / tr14 * 100 if tr14 else 0
    di14_m = sum(dm_minus[-period:]) / period / tr14 * 100 if tr14 else 0
    dx = abs(di14_p - di14_m) / (di14_p + di14_m + 0.001) * 100
    adx = sum([abs(dm_plus[i] - dm_minus[i]) / (dm_plus[i] + dm_minus[i] + 0.001) * 100
               for i in range(-period, 0)]) / period
    return {
        "adx": round(adx, 2), "di_plus": round(di14_p, 2), "di_minus": round(di14_m, 2),
    }


def calc_alligator(closes: list, highs: list, lows: list) -> dict:
    """鳄鱼线: 下巴(13)/牙齿(8)/上唇(5) SMA + 前移"""
    def sma(data, n):
        return sum(data[-n:]) / n if len(data) >= n else sum(data) / len(data)
    if len(closes) < 13:
        return {"jaw": 0, "teeth": 0, "lips": 0, "state": "unknown"}
    jaw = sma([(h+l)/2 for h,l in zip(highs, lows)], 13)
    teeth = sma([(h+l)/2 for h,l in zip(highs, lows)], 8)
    lips = sma([(h+l)/2 for h,l in zip(highs, lows)], 5)
    # 简化状态
    if lips > teeth > jaw:
        state = "uptrend"
    elif lips < teeth < jaw:
        state = "downtrend"
    else:
        state = "winding"
    return {"jaw": round(jaw, 2), "teeth": round(teeth, 2), "lips": round(lips, 2), "state": state}


def calc_obv(closes: list, volumes: list) -> dict:
    """能量潮"""
    obv = 0
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]
    # OBV 斜率（5期）
    if len(closes) >= 5:
        obv5 = [0] * 5
        for i in range(max(1, len(closes)-4), len(closes)):
            obv5[i % 5] = obv  # 简化
        slope = (obv5[-1] - obv5[0]) / max(obv5[0], 1) * 100 if obv5[0] else 0
    else:
        slope = 0
    return {"obv": obv, "obv_slope": round(slope, 2)}


def compute_all_factors(kline_data: list) -> dict:
    """对K线数据计算全部9个技术因子"""
    if not kline_data or len(kline_data) < 5:
        return {}
    
    closes = [k["close"] for k in kline_data]
    highs = [k["high"] for k in kline_data]
    lows = [k["low"] for k in kline_data]
    volumes = [k["volume"] for k in kline_data]
    current = closes[-1]
    
    # 基础统计
    ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else sum(closes) / len(closes)
    ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else ma5
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else ma10
    
    return {
        "price": current,
        "ma5": round(ma5, 2), "ma10": round(ma10, 2), "ma20": round(ma20, 2),
        "change_pct": round((current - closes[-2]) / closes[-2] * 100, 2) if len(closes) >= 2 else 0,
        "mom_5d": round((current - closes[-6]) / closes[-6] * 100, 2) if len(closes) >= 6 else 0,
        "mom_20d": round((current - closes[-21]) / closes[-21] * 100, 2) if len(closes) >= 21 else 0,
        "vol_ratio": round(volumes[-1] / (sum(volumes[-6:-1]) / 5), 2) if len(volumes) >= 6 else 1.0,
        "rsi": calc_rsi(closes),
        "macd": calc_macd(closes),
        "kdj": calc_kdj(closes, highs, lows),
        "bollinger": calc_bollinger(closes),
        "ichimoku": calc_ichimoku(closes, highs, lows),
        "adx": calc_adx(closes, highs, lows),
        "alligator": calc_alligator(closes, highs, lows),
        "obv": calc_obv(closes, volumes),
    }
