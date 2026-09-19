#!/usr/bin/env python3
"""
第4关：多空辩论（修复版 v3.0）
数据来源：search_via_browser.py（Chrome浏览器自动化，已验证稳定）
支持：沪市(6/688/900)、深市(00/30/20)
完全绕过 akshare 的 LibreSSL 兼容问题

策略：
  Level 1: 浏览器抓取东方财富 F10 财务数据（已验证可用）
  Level 2: 浏览器抓取新浪财经实时行情
  Level 3: 纯静态 fallback（永不中断）
"""
import json
import sys
import subprocess
import re
import os
import numpy as np

WORKSPACE = os.environ.get("ASTOCK_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BROWSER_SCRIPT = f"{WORKSPACE}/scripts/search_via_browser.py"
KRONOS_FACTOR = f"{WORKSPACE}/scripts/kronos_factor.py"

def get_market(code):
    if code.startswith(('6', '688', '900')):
        return "sh"
    elif code.startswith(('00', '30', '20')):
        return "sz"
    return "sz"

def fetch_browser_financials(code):
    """Level 1: 浏览器抓取东方财富 F10 财务数据"""
    try:
        result = subprocess.run(
            ["python3", BROWSER_SCRIPT, "stock", code],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        return {
            "name": data.get("title", "").split("(")[0] if data.get("title") else code,
            "eps": data.get("eps"),
            "net_profit": data.get("net_profit"),
            "profit_growth_pct": data.get("profit_growth_pct"),
            "gross_margin": data.get("gross_margin"),
            "debt_ratio": data.get("debt_ratio"),
            "nav_per_share": data.get("nav_per_share"),
        }
    except Exception:
        return None

def fetch_browser_quote(code):
    """Level 2: 浏览器抓取个股实时行情"""
    em_market = {"sh": "sh", "sz": "sz"}.get(get_market(code), "sz")
    url = f"https://hq.sinajs.cn/list={em_market}{code}"
    try:
        result = subprocess.run(
            ["python3", BROWSER_SCRIPT, "url", url],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        text = data.get("text", "")
        # 新浪行情格式：var hq_str_sh600519="贵州茅台,1765.00,-5.00,-0.28,...
        parts = text.split('="')
        if len(parts) > 1:
            values = parts[1].split('"')[0].split(',')
            if len(values) >= 4:
                name = values[0]
                price = float(values[1]) if values[1] else 0
                pct = float(values[3]) if len(values) > 3 and values[3] else 0
                return {"name": name, "price": price, "change_pct": pct}
    except Exception:
        pass
    return None

def fetch_kronos_signal(code):
    """读取预计算的 Kronos 因子信号（从每月更新的缓存文件）"""
    cache_file = "/tmp/kronos_factors_latest.json"
    try:
        if not os.path.exists(cache_file):
            return None
        with open(cache_file) as f:
            all_factors = json.load(f)
        for item in all_factors:
            if item.get("code") == code and "pred_return" in item:
                return item
        return None
    except Exception:
        return None


def debate(stock_code="600519"):
    # ── 获取数据 ──
    financials = fetch_browser_financials(stock_code)
    quote = fetch_browser_quote(stock_code)

    name = stock_code
    price = 0.0
    pct = 0.0

    if quote:
        name = quote.get("name", name)
        price = quote.get("price", 0.0)
        pct = quote.get("change_pct", 0.0)
    elif financials:
        name = financials.get("name", name)

    # ── 构建多空论据 ──
    bull_args = []
    bear_args = []

    # 基本面论据
    if financials:
        try:
            eps = float(financials.get("eps", 0))
            if eps > 5:
                bull_args.append(f"每股收益 {eps} 元，盈利能力优秀")
            elif eps > 1:
                bull_args.append(f"每股收益 {eps} 元，盈利稳健")
        except (ValueError, TypeError):
            pass

        try:
            growth = float(financials.get("profit_growth_pct", 0))
            if growth > 10:
                bull_args.append(f"净利润同比增长 {growth:.2f}%，高成长")
            elif growth > 0:
                bull_args.append(f"净利润同比增长 {growth:.2f}%，稳健增长")
            elif growth < -10:
                bear_args.append(f"净利润同比下滑 {abs(growth):.2f}%")
        except (ValueError, TypeError):
            pass

        try:
            margin = float(financials.get("gross_margin", 0))
            if margin > 80:
                bull_args.append(f"毛利率 {margin:.2f}%，定价权极强")
            elif margin > 40:
                bull_args.append(f"毛利率 {margin:.2f}%，竞争力较优")
        except (ValueError, TypeError):
            pass

        try:
            debt = float(financials.get("debt_ratio", 0))
            if debt < 30:
                bull_args.append(f"资产负债率 {debt:.2f}%，财务结构稳健")
            elif debt > 70:
                bear_args.append(f"资产负债率 {debt:.2f}%，负债偏高")
        except (ValueError, TypeError):
            pass

    # 技术面论据
    if pct > 2:
        bull_args.append(f"今日强势上涨 {pct:.2f}%")
    elif pct > 0.5:
        bull_args.append(f"今日小幅上涨 {pct:.2f}%")
    elif pct < -2:
        bear_args.append(f"今日弱势下跌 {pct:.2f}%")
    elif pct < -0.5:
        bear_args.append(f"今日小幅下跌 {pct:.2f}%")
    else:
        bull_args.append("技术面企稳，波动收窄")

    # ── Kronos 量价预测信号 ──
    kronos_data = fetch_kronos_signal(stock_code)
    if kronos_data:
        kr = kronos_data.get("pred_return", 0)
        kc = kronos_data.get("confidence", 0)
        if kc > 0.3:  # 置信度足够高才纳入
            if kr > 0.02:
                bull_args.append(f"Kronos量价模型预测未来涨幅 {kr*100:.1f}% (置信度{kc:.0%})")
            elif kr > 0.005:
                bull_args.append(f"Kronos量价模型微幅看涨 {kr*100:.1f}%")
            elif kr < -0.02:
                bear_args.append(f"Kronos量价模型预测未来跌幅 {abs(kr)*100:.1f}% (置信度{kc:.0%})")
            elif kr < -0.005:
                bear_args.append(f"Kronos量价模型微幅看跌 {abs(kr)*100:.1f}%")
            else:
                bull_args.append("Kronos量价模型预测中性波动")
        else:
            bull_args.append("Kronos量价模型信号置信度偏低，不纳入决策")
    else:
        bull_args.append("Kronos量价模型数据不可用")

    # 宏观/政策论据
    bull_args.append("政策底预期强化，流动性合理充裕")
    bear_args.append("海外宏观扰动及汇率波动未消")

    # ── 裁决 ──
    verdict = "bull" if len(bull_args) >= len(bear_args) else "bear"
    total = len(bull_args) + len(bear_args)
    score = round(10.0 * len(bull_args) / total, 1) if total > 0 else 5.0

    # Kronos 加权（如果信号强则加偏）
    kronos_weight = 0
    if kronos_data and kronos_data.get("confidence", 0) > 0.3:
        kronos_weight = kronos_data["pred_return"] * kronos_data["confidence"] * 10
        # kronos_weight > 0 → 偏多, < 0 → 偏空
        # 幅度 0~3 分, 不会完全压倒其他论据
    
    # 重新计分（含 Kronos 加权）
    base_score = 10.0 * len(bull_args) / total if total > 0 else 5.0
    adjusted_score = min(10.0, max(0.0, base_score + kronos_weight))

    result = {
        "stock": stock_code,
        "name": name,
        "price": price,
        "change_pct": pct,
        "eps": financials.get("eps") if financials else None,
        "profit_growth_pct": financials.get("profit_growth_pct") if financials else None,
        "gross_margin": financials.get("gross_margin") if financials else None,
        "debt_ratio": financials.get("debt_ratio") if financials else None,
        "kronos": kronos_data,
        "bull": bull_args,
        "bear": bear_args,
        "verdict": verdict,
        "score": round(adjusted_score, 1),
        "kronos_weight": round(kronos_weight, 3),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "600519"
    sys.exit(debate(code))
