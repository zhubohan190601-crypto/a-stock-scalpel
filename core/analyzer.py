#!/usr/bin/env python3
"""
analyzer.py — 市场状态判定
接入腾讯/新浪实时数据，根据真实指数数据判断市场状态。
输出：结构化JSON供下游流程（debater.py、收盘总结等）使用。

依赖：无第三方库，仅用标准库 urllib。
"""

import urllib.request
import re
import json
import os
import sys
import time
from datetime import datetime


def fetch_qq_index(code):
    """获取腾讯行情接口数据"""
    url = f"https://qt.gtimg.cn/q={code}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=8)
    text = resp.read().decode("gbk")
    m = re.search(r'"(.*)"', text)
    if not m:
        return None
    parts = m.group(1).split("~")
    return {
        "name": parts[1],
        "code": parts[2],
        "price": float(parts[3]),
        "yclose": float(parts[4]),
        "open": float(parts[5]),
        "change": float(parts[31]),
        "change_pct": float(parts[32]),
        "high": float(parts[33]),
        "low": float(parts[34]),
        "volume": int(parts[36]) if parts[36] else 0,
        "amount": float(parts[37]) / 1e4 if parts[37] else 0,  # 亿元
    }


def check_market():
    """判断市场状态：normal / cautious / risky"""
    try:
        sh = fetch_qq_index("sh000001")
        sz = fetch_qq_index("sz399001")
        cy = fetch_qq_index("sz399006")
    except Exception as e:
        # 降级：用模拟数据兜底
        return {
            "status": "unknown",
            "reason": f"数据获取失败: {e}。降级使用默认值。",
            "suggestion": "仓位建议 50%（数据异常，保守操作）",
            "data_ok": False,
        }

    if not sh or not sz:
        return {
            "status": "unknown",
            "reason": "指数数据缺失",
            "suggestion": "仓位建议 50%",
            "data_ok": False,
        }

    # 核心判定逻辑
    sh_pct = abs(sh["change_pct"])
    sz_pct = abs(sz["change_pct"])
    max_pct = max(sh_pct, sz_pct)

    if max_pct >= 3.0:
        status = "cautious"
        reason = f"三大指数全线大跌：上证{sh['change_pct']:+.2f}% 深证{sz['change_pct']:+.2f}% 创业板{cy['change_pct']:+.2f}%（如获取到），沪市成交{sh['amount']:.0f}亿，深市成交{sz['amount']:.0f}亿"
        suggestion = "仓位建议 ≤30%，市场恐慌，等待企稳信号"
    elif max_pct >= 1.5:
        status = "cautious"
        reason = f"指数跌幅较大：上证{sh['change_pct']:+.2f}% 深证{sz['change_pct']:+.2f}%，沪市成交{sh['amount']:.0f}亿，深市成交{sz['amount']:.0f}亿"
        suggestion = "仓位建议 ≤50%，控制风险"
    elif max_pct >= 0.5:
        status = "normal"
        reason = f"指数窄幅震荡：上证{sh['change_pct']:+.2f}% 深证{sz['change_pct']:+.2f}%，沪市成交{sh['amount']:.0f}亿，深市成交{sz['amount']:.0f}亿"
        suggestion = "仓位建议 60%，精选个股"
    else:
        status = "normal"
        reason = f"指数微涨/持平：上证{sh['change_pct']:+.2f}% 深证{sz['change_pct']:+.2f}%，沪市成交{sh['amount']:.0f}亿，深市成交{sz['amount']:.0f}亿"
        suggestion = "仓位建议 60%-80%，可适当参与"

    return {
        "status": status,
        "reason": reason,
        "suggestion": suggestion,
        "data_ok": True,
        "sh_price": sh["price"],
        "sh_change_pct": sh["change_pct"],
        "sz_price": sz["price"],
        "sz_change_pct": sz["change_pct"],
        "cy_price": cy["price"] if cy else None,
        "cy_change_pct": cy["change_pct"] if cy else None,
        "sh_amount": sh["amount"],
        "sz_amount": sz["amount"],
        "total_amount": sh["amount"] + sz["amount"],
    }


SCAN_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "analyzer_scan.log")


def log_scan(source, count, errors=None):
    """记录每次 scan 调用的数据源/时间戳/条数（可复现验证依据）"""
    try:
        os.makedirs(os.path.dirname(SCAN_LOG), exist_ok=True)
        with open(SCAN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": source, "count": count, "errors": errors or [],
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


def fetch_sectors_qq(count=90):
    """主源：腾讯行业板块（name / zdf 涨跌幅% / zljlr 主力净流入万元）"""
    url = ("https://proxy.finance.qq.com/cgi/cgi-bin/rank/pt/getRank"
           f"?board_type=hy&sort_type=price&direct=down&offset=0&count={count}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
    rl = (json.loads(raw).get("data") or {}).get("rank_list") or []
    rows = []
    for r in rl:
        try:
            rows.append({"name": r.get("name"), "pct": float(r.get("zdf")),
                         "inflow_yi": round(float(r.get("zljlr") or 0) / 1e4, 2)})
        except (TypeError, ValueError):
            continue
    return rows


def fetch_sectors_sina():
    """备源：新浪行业板块（GBK；字段 名称/涨跌幅%）"""
    url = "http://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    text = urllib.request.urlopen(req, timeout=10).read().decode("gbk", errors="ignore")
    m = re.search(r"=\s*(\{.*\})", text, re.S)
    if not m:
        raise RuntimeError("新浪返回格式无法解析")
    data = json.loads(m.group(1))
    rows = []
    for _k, v in data.items():
        parts = str(v).split(",")
        if len(parts) >= 6:
            try:
                rows.append({"name": parts[1], "pct": float(parts[5]), "inflow_yi": None})
            except (TypeError, ValueError):
                continue
    return rows


def scan():
    """第1关：板块扫描（多源 + 降级链：腾讯 → 新浪 → 明确失败）
    不做旧缓存兑底：两源都失败时返回 data_ok=false，由调用方决定降级策略。"""
    rows, used, errors = [], None, []
    for name, fn in (("qq", fetch_sectors_qq), ("sina", fetch_sectors_sina)):
        try:
            r = fn()
            if r:
                rows, used = r, name
                break
            errors.append(f"{name}: 返回空数据")
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")

    if not rows:
        log_scan(None, 0, errors)
        return {"data_ok": False, "error": "数据源不可用（腾讯+新浪均失败）",
                "sources_tried": errors}

    by_pct = sorted(rows, key=lambda r: r["pct"], reverse=True)
    by_inflow = sorted([r for r in rows if r.get("inflow_yi") is not None],
                       key=lambda r: r["inflow_yi"], reverse=True)
    log_scan(used, len(rows))
    return {
        "data_ok": True,
        "source": used,
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sector_count": len(rows),
        "sectors_top": by_pct[:10],
        "sectors_bottom": by_pct[-10:],
        "inflow_top": by_inflow[:10],
        "summary": ("领涨: " + "/".join(r["name"] for r in by_pct[:5])
                    + " | 领跌: " + "/".join(r["name"] for r in by_pct[-5:])),
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "regime"
    if cmd == "scan":
        out = scan()
    else:
        out = check_market()
        if cmd not in ("regime", "check", "market"):
            out["note"] = f"未知子命令 '{cmd}'，已回退为 regime"
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0)
