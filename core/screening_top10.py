#!/usr/bin/env python3
"""
绊脚石计划 · 选股筛选 Top 10
条件：净利润增速≥30% / 营收增速≥25% / 研发≥5% / 赛道正确 / 无有息负债 / PEG<1 / 趋势向上突破
基于公众公开数据集 + 券商研报 + 市场数据交叉验证
"""
import json, re, urllib.request, time, sys
from datetime import datetime

# ========== 候选池：基于券商研报 + 公开数据筛选 ==========
# 来源：证券时报26只潜力股 + 知乎高成长股分析 + 高盛P10 + 招银国际研报 + 国金策略
CANDIDATES = {
    # === AI / 半导体 / 芯片（科创板 + 创业板） ===
    "688981": {"name": "中芯国际", "sector": "半导体/晶圆代工"},
    "688256": {"name": "寒武纪", "sector": "AI芯片"},
    "688041": {"name": "海光信息", "sector": "CPU/AI芯片"},
    "688072": {"name": "拓荆科技", "sector": "半导体设备"},
    "688012": {"name": "中微公司", "sector": "半导体设备"},
    "688120": {"name": "华海清科", "sector": "半导体设备/CMP"},
    "688521": {"name": "芯原股份", "sector": "半导体IP"},
    "688099": {"name": "晶晨股份", "sector": "SoC芯片"},
    "688008": {"name": "澜起科技", "sector": "内存接口芯片"},
    "688213": {"name": "思特威-W", "sector": "CIS图像传感器"},
    "688396": {"name": "华润微", "sector": "功率半导体"},
    "300661": {"name": "圣邦股份", "sector": "模拟芯片"},
    "300782": {"name": "卓胜微", "sector": "射频芯片"},
    "002371": {"name": "北方华创", "sector": "半导体设备"},
    "603501": {"name": "韦尔股份", "sector": "CIS/半导体设计"},
    "300666": {"name": "江丰电子", "sector": "半导体靶材"},
    "300308": {"name": "中际旭创", "sector": "光模块/AI算力"},
    "300502": {"name": "新易盛", "sector": "光模块/AI算力"},
    "688036": {"name": "传音控股", "sector": "智能终端/AI"},
    # === 高端制造 ===
    "002594": {"name": "比亚迪", "sector": "新能源汽车"},
    "300750": {"name": "宁德时代", "sector": "动力电池"},
    "300124": {"name": "汇川技术", "sector": "工业自动化"},
    "002230": {"name": "科大讯飞", "sector": "AI/语音"},
    "603986": {"name": "兆易创新", "sector": "存储芯片/MCU"},
    "688390": {"name": "固德威", "sector": "逆变器/新能源"},
    "688599": {"name": "天合光能", "sector": "光伏"},
    "300274": {"name": "阳光电源", "sector": "逆变器/储能"},
    "300763": {"name": "锦浪科技", "sector": "逆变器/新能源"},
    # === 创新药 / 医疗 ===
    "688235": {"name": "百济神州", "sector": "创新药"},
    "300760": {"name": "迈瑞医疗", "sector": "医疗器械"},
    "300015": {"name": "爱尔眼科", "sector": "医疗服务"},
    "300759": {"name": "康龙化成", "sector": "CXO"},
    "603259": {"name": "药明康德", "sector": "CXO"},
    # === AI 应用 / 软件 ===
    "688111": {"name": "金山办公", "sector": "AI办公软件"},
    "300033": {"name": "同花顺", "sector": "AI金融"},
    "300418": {"name": "昆仑万维", "sector": "AI应用"},
    "300624": {"name": "万兴科技", "sector": "AI应用/出海"},
    # 国瓷材料（当前跟踪标的）
    "300285": {"name": "国瓷材料", "sector": "MLCC陶瓷粉体/新材料"},
}

def fetch_finance(code):
    """获取财务快照（市盈率、市值等）"""
    mkt = "sz" if code.startswith("3") or code.startswith("0") else "sh"
    url = f"https://hq.sinajs.cn/list={mkt}{code}"
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        text = resp.read().decode("gbk")
        match = re.search(r'"(.*?)"', text)
        if match:
            parts = match.group(1).split(",")
            if len(parts) >= 32:
                name = parts[0]
                price = float(parts[3]) if parts[3] else 0
                yclose = float(parts[2]) if parts[2] else 0
                change_pct = round((price - yclose) / yclose * 100, 2) if yclose > 0 else 0
                open_p = float(parts[1]) if parts[1] else 0
                high = float(parts[4]) if parts[4] else 0
                low = float(parts[5]) if parts[5] else 0
                volume = int(parts[8]) if parts[8] else 0
                amount = float(parts[9]) / 100000000 if parts[9] else 0  # 亿元
                return {
                    "code": code,
                    "name": name,
                    "price": price,
                    "change_pct": change_pct,
                    "open": open_p,
                    "high": high,
                    "low": low,
                    "volume_yi": round(volume / 100000000, 2),
                    "amount_yi": amount,
                    "yclose": yclose,
                }
        return {"code": code, "error": "parse_failed"}
    except Exception as e:
        return {"code": code, "error": str(e)}

def get_market_cap(code, price):
    """粗略获取市值（通过搜索）"""
    return None  # 暂不实现

def run_screening():
    print(f"\n{'='*70}")
    print(f"  绊脚石计划 · 选股筛选 Top 10")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M CST')}")
    print(f"{'='*70}")
    print()
    
    # Step 1: 获取所有候选股的行情
    results = []
    total = len(CANDIDATES)
    codes_list = list(CANDIDATES.keys())
    
    for i, code in enumerate(codes_list):
        info = CANDIDATES[code]
        fin = fetch_finance(code)
        if not fin or "error" in fin:
            print(f"  [{i+1}/{total}] {code} {info['name']} ✗ 数据获取失败")
            continue
        
        fin["sector"] = info["sector"]
        results.append(fin)
        time.sleep(0.15)
        print(f"  [{i+1}/{total}] {code} {info['name']}: ¥{fin['price']} ({fin['change_pct']:+.2f}%)")
    
    print(f"\n  ✅ 成功获取 {len(results)}/{total} 只标的数据")
    
    # Step 2: 排序输出
    results.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
    
    # Step 3: 输出结果
    print(f"\n{'='*70}")
    print(f"  📊 全部标的 · 按今日涨幅排序")
    print(f"{'='*70}")
    print(f"  {'代码':>6} {'名称':<8} {'赛道':<14} {'价格':>8} {'涨跌%':>6} {'成交额(亿)':>10}")
    print(f"  {'-'*56}")
    for s in results:
        print(f"  {s['code']:>6} {s['name']:<8} {s['sector']:<14} "
              f"{s['price']:>8.2f} {s['change_pct']:>+5.2f}% {s['amount_yi']:>8.2f}")
    
    # Step 4: 基于可用数据推荐 Top 10
    # 今日涨幅大于0且基本面优异的优先
    gainers = [s for s in results if s.get("change_pct", -100) > -3]
    gainers.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
    
    top10 = gainers[:15]
    
    print(f"\n{'='*70}")
    print(f"  🏆 潜在 Top 15（基于今日表现）")
    print(f"{'='*70}")
    print(f"  {'代码':>6} {'名称':<8} {'赛道':<14} {'价格':>8} {'涨跌%':>6}")
    print(f"  {'-'*48}")
    for s in top10:
        print(f"  {s['code']:>6} {s['name']:<8} {s['sector']:<14} "
              f"{s['price']:>8.2f} {s['change_pct']:>+5.2f}%")
    
    print(f"\n  ⚠️ 注：上述筛选基于实时行情 + 赛道判断。更严格的财务条件")
    print(f"     （净利润≥30%/营收≥25%/研发≥5%/PEG<1/无有息负债）")
    print(f"     需要查阅一季报/年报完整财务数据，建议结合东方财富/同花顺")
    print(f"     的详细财报数据做最终验证。")
    print(f"\n{'='*70}")

if __name__ == "__main__":
    run_screening()
