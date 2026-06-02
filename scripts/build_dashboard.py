#!/usr/bin/env python3
"""
阿不看板数据处理器
将分析报告和账本打包成 Dashboard 可读的静态文件
"""
import sys
import os
import json
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(BASE_DIR, "reports")
DASH_DIR = os.path.join(BASE_DIR, "dashboard")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DASH_DIR, exist_ok=True)

def find_latest(pattern, directory):
    """找最新的匹配文件"""
    files = [f for f in os.listdir(directory) if f.startswith(pattern)]
    if not files:
        return None
    files.sort(reverse=True)
    return os.path.join(directory, files[0])

def extract_table_to_html(md_text):
    """将 Markdown 表格转成 HTML"""
    lines = md_text.split('\n')
    in_table = False
    html = '<table>\n'
    for line in lines:
        if line.startswith('|') and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if not in_table:
                html += '  <thead><tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr></thead>\n<tbody>\n'
                in_table = True
            else:
                row_class = ''
                for c in cells:
                    if c.endswith('%'):
                        try:
                            v = float(c.rstrip('%'))
                            if v > 0: row_class = 'up'
                            elif v < 0: row_class = 'down'
                        except: pass
                html += f'    <tr class="{row_class}">' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>\n'
        elif in_table and not line.startswith('|'):
            html += '</tbody>\n</table>\n'
            in_table = False
    if in_table:
        html += '</tbody>\n</table>\n'
    return html

def generate_dashboard():
    """生成看板数据"""
    result = {
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "market": "",
        "screening": "",
        "token_balance": "",
        "token_consumed": "",
    }
    
    # 1. 最新市场简报
    latest_market = find_latest("market_brief_", REPORT_DIR)
    if latest_market:
        with open(latest_market) as f:
            result["market"] = f.read()
    
    # 2. 最新筛选报告
    latest_screen = find_latest("screening_", REPORT_DIR)
    if latest_screen:
        with open(latest_screen) as f:
            text = f.read()
            table_html = extract_table_to_html(text)
            result["screening"] = table_html if table_html else text
    
    # 3. 账本摘要
    ledger_file = os.path.join(BASE_DIR, "ledger.md")
    if os.path.exists(ledger_file):
        with open(ledger_file) as f:
            text = f.read()
            # 提取余额行
            for line in text.split('\n'):
                if '当前余额' in line:
                    result["token_balance"] = line.split('：')[-1].strip() if '：' in line else line.strip()
                if '已消耗' in line:
                    result["token_consumed"] = line.strip()
    
    # 写入 dashboard 用文件
    with open(os.path.join(DASH_DIR, "dashboard_data.json"), "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 同时写两份 md 快照给前端直接读取
    if result["market"]:
        with open(os.path.join(DASH_DIR, "dashboard_market.md"), "w") as f:
            f.write(result["market"])
    if result["screening"]:
        with open(os.path.join(DASH_DIR, "dashboard_screening.md"), "w") as f:
            f.write(result["screening"])
    
    print(f"✅ 看板数据已更新: {os.path.join(DASH_DIR, 'dashboard_data.json')}")
    print(f"   简报: {'✓' if result['market'] else '✗'}")
    print(f"   筛选: {'✓' if result['screening'] else '✗'}")
    print(f"   余额: {result['token_balance']}")

if __name__ == "__main__":
    generate_dashboard()
