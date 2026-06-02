#!/usr/bin/env python3
"""
阿不 金融数据分析引擎
基于采集的行情数据做分析,产出投资参考信息
"""

import json
import os
import sys
from datetime import datetime
from collections import defaultdict

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.fetcher import fetch_batch, fetch_single, fetch_kline, save_snapshot, fetch_all_a_spot

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

def scan_market():
    """扫描全市场,输出今日异动"""
    codes = {
        "龙头": ["000001","000002","000333","000651","000858","000568","000725","600519","600036","600900"],
        "科技": ["002415","002475","002594","300750","300059","300760","688981","688256","688036","688008"],
        "金融": ["600030","601318","601166","601398","601288","600036","601328","601939","601658","601728"],
        "消费": ["600887","600809","600519","000858","000568","002714","600690"],
        "能源": ["601857","600028","600585","601088","601899"],
    }
    
    print("=" * 60)
    print(f"📊 阿不 市场扫描 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    for sector, code_list in codes.items():
        results = fetch_batch(code_list)
        # 过滤有效数据
        valid = [r for r in results if "error" not in r and "price" in r]
        if not valid:
            continue
        
        # 排序: 按涨跌幅
        valid.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
        
        gainers = [r for r in valid if r.get("change_pct", 0) > 2]
        losers = [r for r in valid if r.get("change_pct", 0) < -2]
        
        print(f"\n📍 {sector} ({len(valid)}只)")
        if gainers:
            for r in gainers[:3]:
                print(f"   🔴 {r['name']}({r['code']}): {r['price']} +{r['change_pct']}%")
        if losers:
            for r in losers[:3]:
                print(f"   🟢 {r['name']}({r['code']}): {r['price']} {r['change_pct']}%")
        if not gainers and not losers:
            top = valid[0]
            bottom = valid[-1]
            print(f"   最高: {top['name']} {top['price']} ({top['change_pct']}%)")
            print(f"   最低: {bottom['name']} {bottom['price']} ({bottom['change_pct']}%)")
    
    # 全市场扫描: 抓前20大成交额
    print(f"\n{'=' * 60}")
    print("💰 成交额TOP (估值)")
    all_results = fetch_batch([
        "000001","000002","000333","000651","000858","000568","000725","000063",
        "002415","002714","002475","002594","300750","300059","300760","300124",
        "600519","600036","600900","600276","600887","600030","601318","601166",
        "601398","601288","601857","601988","600028","600585","601088","600690",
        "601012","600809","601899","600406","600436","600309","600438","600196",
        "688981","688256","688036","688008","601728","601658","601939","601328",
    ])
    valid_results = [r for r in all_results if "error" not in r and "amount_yi" in r]
    valid_results.sort(key=lambda x: x.get("amount_yi", 0), reverse=True)
    for r in valid_results[:10]:
        print(f"  {r['name']}({r['code']}): ¥{r['amount_yi']}亿  {r.get('change_pct',0)}%")

def generate_daily_report():
    """生成每日市场报告并保存"""
    lines = []
    lines.append("# 📊 阿不 每日市场简报")
    lines.append(f"\n**日期**: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"**时间**: {datetime.now().strftime('%H:%M')}")
    lines.append("\n---\n")
    
    # 取关键标的
    key_codes = {
        "上证50": ["600519","600036","600900","601318","600030"],
        "创业板": ["300750","300059","300760","300124"],
        "科技": ["002415","002475","002594","688981","688256"],
    }
    
    for category, codes in key_codes.items():
        results = fetch_batch(codes)
        lines.append(f"## {category}\n")
        lines.append("| 代码 | 名称 | 最新价 | 涨跌幅 | 成交额(亿) |")
        lines.append("|------|------|--------|--------|-----------|")
        for r in results:
            if "error" not in r and "price" in r:
                lines.append(f"| {r['code']} | {r['name']} | {r['price']} | {r.get('change_pct', 'N/A')}% | {r.get('amount_yi', 'N/A')} |")
        lines.append("")
    
    # 异动提醒
    lines.append("## ⚡ 今日异动\n")
    all_results = fetch_batch([
        "000333","000651","000858","000568","002415","002475","002594",
        "300750","300059","600519","600036","600900","601318","600030",
        "600887","600809","601857","600585","300124","688981",
    ])
    valid = [r for r in all_results if "error" not in r and "change_pct" in r]
    big_movers = [r for r in valid if abs(r.get("change_pct", 0)) >= 3]
    if big_movers:
        big_movers.sort(key=lambda x: abs(x.get("change_pct", 0)), reverse=True)
        for r in big_movers:
            direction = "🔴" if r["change_pct"] > 0 else "🟢"
            lines.append(f"- {direction} **{r['name']}({r['code']})**: {r['change_pct']}% (¥{r['price']})")
    else:
        lines.append("- 今日无明显异动(涨跌幅均<3%)\n")
    
    content = "\n".join(lines)
    
    filename = f"market_brief_{datetime.now().strftime('%Y%m%d')}.md"
    filepath = os.path.join(REPORT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ 报告已保存: {filepath}")
    return filepath

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        generate_daily_report()
    elif len(sys.argv) > 1 and sys.argv[1] == "--scan":
        scan_market()
    else:
        print("用法: python3 analyzer.py [--scan | --report]")
