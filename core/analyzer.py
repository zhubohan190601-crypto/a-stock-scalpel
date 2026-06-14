#!/usr/bin/env python3
"""
a-stock-scalpel — 分析引擎
==============================
整合采集层 + 因子计算 + 规则评分
"""

import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.fetcher import fetch_batch, fetch_kline, compute_all_factors
from core.rules import score_factors, describe_signal

# ── 股票池定义 ──
STOCK_POOL = {
    "金融": ["600036","601398","601939","601288","601328","601166","600030","601318","601211"],
    "消费": ["600519","000858","000568","600809","600887","002714","000333","000651"],
    "科技": ["002415","002475","002594","300750","300760","300124","002371","603501"],
    "能源": ["601857","600028","600585","601088","601899","600900"],
    "半导体": ["688981","688256","688036","688008","688012","002049"],
    "医药": ["600276","300015","300759","000538"],
    "通信": ["601728","600941","600050"],
}


def run_scan(codes: list = None, show_progress: bool = True) -> list:
    """
    全量扫描: 获取实时价格 + K线 → 因子 → 规则评分
    
    返回: [{code, name, price, change_pct, score, signal, ...}, ...]
    """
    if codes is None:
        codes = [c for cl in STOCK_POOL.values() for c in cl]
    
    # 去重
    codes = list(dict.fromkeys(codes))
    
    if show_progress:
        print(f"\n🔍 A-Stock Scalpel 扫描 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"   候选池: {len(codes)} 只标的")
        print("=" * 65)
    
    # 实时行情
    quotes = fetch_batch(codes)
    valid = [q for q in quotes if "error" not in q]
    if show_progress:
        print(f"   实时数据: {len(valid)}/{len(codes)} 有效")
    
    # K线 + 评分
    results = []
    for i, q in enumerate(valid):
        code = q["code"]
        kline = fetch_kline(code, scale="daily", datalen=65)
        if not kline or len(kline) < 5:
            if show_progress:
                print(f"   [{i+1}/{len(valid)}] {code} — K线不足，跳过")
            continue
        
        factors = compute_all_factors(kline)
        # 注入实时价格和涨跌幅
        factors["price"] = q.get("price", factors.get("price", 0))
        factors["change_pct"] = q.get("change_pct", factors.get("change_pct", 0))
        
        scores = score_factors(factors)
        
        results.append({
            "code": code,
            "name": q.get("name", ""),
            "price": q.get("price", 0),
            "change_pct": q.get("change_pct", 0),
            "amount_yi": q.get("amount_yi", 0),
            **scores,
        })
        
        if show_progress:
            pct_str = f"{q.get('change_pct', 0):+.1f}%"
            net_str = f"{scores['net_score']:+.0f}"
            sig_str = scores["signal"]
            print(f"   [{i+1}/{len(valid)}] {code} {q.get('name',''):<6} "
                  f"¥{q.get('price',0):<8.2f} {pct_str:<6} "
                  f"净{net_str} {sig_str}")
        
        time.sleep(0.3)  # 礼貌间隔
    
    # 按净分排序
    results.sort(key=lambda r: r.get("net_score", 0), reverse=True)
    return results


def print_summary(results: list, top_n: int = 20):
    """打印扫描摘要"""
    if not results:
        print("\n❌ 无有效结果")
        return
    
    print("\n" + "=" * 65)
    print(f"🏆 综合评分 TOP {min(top_n, len(results))}")
    print("=" * 65)
    print(f"{'代码':>6} {'名称':<8} {'价格':>8} {'涨跌':>6} {'多':>3} {'空':>3} {'净分':>4} {'信号':<12}")
    print("-" * 65)
    
    for s in results[:top_n]:
        pct = f"{s['change_pct']:+.1f}%"
        print(f"{s['code']:>6} {s['name']:<8} {s['price']:>8.2f} "
              f"{pct:>6} {s['multi_hits']:>3} {s['short_hits']:>3} "
              f"{s['net_score']:>+4.0f} {s['signal']:<12}")
    
    # 统计分布
    signals = {}
    for s in results:
        signals[s["signal"]] = signals.get(s["signal"], 0) + 1
    print(f"\n📊 信号分布: {signals}")
    
    # 强烈买入
    strong_buys = [s for s in results if s["signal"] == "strong_buy"]
    if strong_buys:
        print(f"\n🔴 强烈买入 ({len(strong_buys)}):")
        for s in strong_buys:
            print(f"   {s['code']} {s['name']} — 净分{s['net_score']:+.0f} 命中{s['multi_hits']}条多头规则")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="A-Stock Scalpel — 多因子短线评分系统")
    parser.add_argument("--scan", action="store_true", help="全量扫描")
    parser.add_argument("--top", type=int, default=20, help="显示前N只")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    parser.add_argument("code", nargs="?", help="单只股票分析")
    
    args = parser.parse_args()
    
    if args.code:
        # 单只
        results = run_scan([args.code])
        if results:
            s = results[0]
            print(f"\n{'='*50}")
            print(f"{s['name']}({s['code']}) — {describe_signal(s['signal'])}")
            print(f"{'='*50}")
            print(f"  价格: ¥{s['price']:.2f}  ({s['change_pct']:+.1f}%)")
            print(f"  多头命中: {s['multi_hits']}条  空头命中: {s['short_hits']}条")
            print(f"  多头分: {s['multi_score']:.1f}%  空头分: {s['short_score']:.1f}%")
            print(f"  净分: {s['net_score']:+.0f}")
            if s.get("multi_rules"):
                print(f"  多头规则: {', '.join(s['multi_rules'])}")
            if s.get("short_rules"):
                print(f"  空头规则: {', '.join(s['short_rules'])}")
        else:
            print(f"\n❌ {args.code} 分析失败")
    elif args.scan:
        results = run_scan()
        print_summary(results, top_n=args.top)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
