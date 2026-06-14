#!/usr/bin/env python3
"""
a-stock-scalpel — 回测引擎
==============================
模拟过去60个交易日的规则评分表现

交易成本: 0.457%（印花税0.1%+佣金0.03%+滑点0.327%）
基准: 沪深300 ETF（510300）
"""

import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.fetcher import fetch_kline, compute_all_factors
from core.rules import score_factors

TRADING_COST = 0.00457  # 0.457% 单边


def backtest_single(code: str, name: str = "", days: int = 120) -> dict:
    """
    回测单只股票:
    遍历每一天，用历史K线模拟当日评分 → 根据信号模拟交易
    """
    kline = fetch_kline(code, scale="daily", datalen=days + 30)
    if not kline or len(kline) < 30:
        return None
    
    closes = [k["close"] for k in kline]
    
    trades = []
    position = False
    entry_price = 0
    total_return = 0
    wins = 0
    losses = 0
    
    for i in range(20, len(kline)):
        # 用第i天之前的全部数据计算因子
        past = kline[:i+1]
        factors = compute_all_factors(past)
        scores = score_factors(factors)
        current_price = kline[i]["close"]
        
        # 买入信号
        if not position and scores["signal"] in ("strong_buy", "buy"):
            entry_price = current_price
            position = True
            trades.append({"day": kline[i]["day"][:10], "action": "BUY", "price": entry_price})
        
        # 卖出信号
        elif position and scores["signal"] in ("strong_sell", "sell"):
            exit_price = current_price
            cost = entry_price * TRADING_COST
            ret = (exit_price - entry_price) / entry_price - TRADING_COST
            if ret > 0:
                wins += 1
            else:
                losses += 1
            total_return += ret
            trades.append({"day": kline[i]["day"][:10], "action": "SELL",
                           "price": exit_price, "return": f"{ret*100:.2f}%"})
            position = False
    
    # 最后平仓
    if position and len(kline) > 0:
        exit_price = kline[-1]["close"]
        cost = entry_price * TRADING_COST
        ret = (exit_price - entry_price) / entry_price - TRADING_COST
        if ret > 0:
            wins += 1
        else:
            losses += 1
        total_return += ret
        trades.append({"day": kline[-1]["day"][:10], "action": "SELL(强制)",
                       "price": exit_price, "return": f"{ret*100:.2f}%"})
    
    total_trades = wins + losses
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0
    
    return {
        "code": code,
        "name": name,
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": f"{win_rate:.1f}%",
        "total_return": f"{total_return*100:.2f}%",
        "avg_return_per_trade": f"{total_return/max(total_trades,1)*100:.2f}%",
        "max_drawdown": "待计算",
        "trades_detail": trades,
    }


def run_backtest_batch(codes: list) -> list:
    """批量回测"""
    results = []
    for code in codes:
        print(f"  回测 {code}...", end=" ")
        r = backtest_single(code)
        if r:
            results.append(r)
            print(f"交易{r['trades']}次, 胜率{r['win_rate']}, 总收益{r['total_return']}")
        else:
            print("数据不足")
        time.sleep(0.5)
    
    results.sort(key=lambda r: float(r["total_return"].rstrip("%")), reverse=True)
    return results


def main():
    TEST_POOL = [
        ("000001", "平安银行"), ("000333", "美的集团"), ("000568", "泸州老窖"),
        ("000858", "五粮液"), ("002415", "海康威视"), ("002475", "立讯精密"),
        ("002594", "比亚迪"), ("300750", "宁德时代"), ("300059", "东方财富"),
        ("600519", "贵州茅台"), ("600036", "招商银行"), ("600900", "长江电力"),
        ("600030", "中信证券"), ("601318", "中国平安"), ("601398", "工商银行"),
    ]
    
    print("=" * 60)
    print("📊 A-Stock Scalpel 回测引擎")
    print(f"  交易成本: {TRADING_COST*100:.2f}%（印花税+佣金+滑点）")
    print(f"  测试标的: {len(TEST_POOL)} 只沪深龙头")
    print("=" * 60)
    
    codes_only = [c[0] for c in TEST_POOL]
    results = run_backtest_batch(codes_only)
    
    print("\n" + "=" * 60)
    print("🏆 回测排名（按总收益降序）")
    print("-" * 60)
    print(f"{'代码':>6} {'交易次数':<8} {'胜率':<8} {'总收益':<10} {'次均收益':<10}")
    print("-" * 60)
    for r in results:
        print(f"{r['code']:>6} {r['trades']:>4}次    {r['win_rate']:<7} "
              f"{r['total_return']:<9} {r['avg_return_per_trade']:<9}")
    print("-" * 60)
    
    # 平均统计
    avg_win = sum(float(r["total_return"].rstrip("%")) for r in results) / len(results) if results else 0
    avg_trades = sum(r["trades"] for r in results) / len(results) if results else 0
    print(f"\n📈 平均总收益: {avg_win:.2f}%")
    print(f"📈 平均交易次数: {avg_trades:.1f} 次/只")


if __name__ == "__main__":
    main()
