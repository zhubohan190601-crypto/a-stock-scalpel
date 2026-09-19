#!/usr/bin/env python3
"""
浏览器自动化数据获取脚本 v2.0

设计哲学：不再绕路搜索引擎，而是直接用浏览器访问目标数据网站。
"你想搜什么，就让浏览器直接去那个网站搜。"

三条路径：
  1. smart <关键词>       — 智能判断目标网站，直接用浏览器在其站内搜索
  2. stock <代码>         — 个股基本面数据（东方财富 F10，已验证 ✅）
  3. url <完整URL>        — 直接打开任意 URL 抓取内容

智能路由规则：
  - 包含"两融"、"余额"、"杠杆" → 东方财富研究 / 21财经
  - 包含股票代码 / 公司名       → 东方财富个股页
  - 包含"研报"、"评级"、"目标价"→ 东方财富研报中心
  - 包含"公告"                  → 巨潮资讯网（官方公告源）
  - 包含"北向"、"南向"、"资金流向"→ 东方财富资金流向
  - 其他                      → 用浏览器打开 DuckDuckGo 执行真实搜索

输出：JSON 格式

依赖：
  - agent-browser CLI（npm install -g agent-browser）✅ v0.29.0
  - Google Chrome（/Applications/Google Chrome.app/）✅
  - 运行前确保 Chrome 已在运行
"""

import subprocess
import json
import re
import sys
import os
import shutil
import time
import urllib.parse
import sqlite3
import hashlib


# =============================================================
# SQLite 缓存系统
# =============================================================

CACHE_DB = os.path.join(os.path.dirname(__file__), "..", "data", "browser_cache.db")


def _get_cache_path():
    os.makedirs(os.path.dirname(CACHE_DB), exist_ok=True)
    return CACHE_DB


def _init_cache():
    conn = sqlite3.connect(_get_cache_path(), timeout=5)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS page_cache (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                ttl INTEGER NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def cache_get(key_prefix, identifier):
    _init_cache()
    cache_key = hashlib.md5(f"{key_prefix}:{identifier}".encode()).hexdigest()
    conn = sqlite3.connect(CACHE_DB, timeout=5)
    try:
        row = conn.execute(
            "SELECT data, created_at, ttl FROM page_cache WHERE key = ?",
            (cache_key,),
        ).fetchone()
        if row:
            data, created_at, ttl = row
            if int(time.time()) - created_at < ttl:
                return json.loads(data)
    finally:
        conn.close()
    return None


def cache_set(key_prefix, identifier, data, ttl_seconds=900):
    _init_cache()
    cache_key = hashlib.md5(f"{key_prefix}:{identifier}".encode()).hexdigest()
    conn = sqlite3.connect(CACHE_DB, timeout=5)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO page_cache (key, data, created_at, ttl) VALUES (?, ?, ?, ?)",
            (cache_key, json.dumps(data, ensure_ascii=False), int(time.time()), ttl_seconds),
        )
        conn.commit()
    finally:
        conn.close()


# =============================================================
# 底层: agent-browser 交互
# =============================================================

def run_cmd(args, timeout=30):
    cmd = ["agent-browser"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except FileNotFoundError:
        return -1, "", "agent-browser not found"
    except Exception as e:
        return -1, "", str(e)


def close_browser():
    run_cmd(["close"])


def fetch_page(url, wait_seconds=3, use_cache=True, cache_ttl=900):
    """
    打开一个 URL 获取页面文本内容。
    如果 use_cache=True，尝试从缓存读取。

    JSON 输出/td>:
      {title, url, text, html_snippet}
      或 {error: "..."}
    """
    if use_cache:
        cached = cache_get("url", url)
        if cached:
            cached["_from_cache"] = True
            return cached

    rc, out, err = run_cmd(["open", url])
    if rc != 0:
        close_browser()
        return {"error": f"open failed: {err}"}

    time.sleep(wait_seconds)

    rc, title, _ = run_cmd(["get", "title"])
    rc, current_url, _ = run_cmd(["get", "url"])
    rc, body_text, _ = run_cmd(["eval", "document.body.innerText"])
    rc, page_html, _ = run_cmd(["get", "html", "body"])

    close_browser()

    result = {
        "title": title.strip() if title else "",
        "url": current_url.strip() if current_url else url,
        "text": body_text[:8000] if body_text else "",
        "html_snippet": page_html[:3000] if page_html else "",
    }

    if use_cache:
        cache_set("url", url, result, cache_ttl)

    return result


# =============================================================
# 智能搜索路由
# =============================================================

# 路由规则表：关键词模式 → (网站名, URL模板, 等待秒数, 缓存TTL秒)
ROUTES = [
    # 个股基本面（龙头公司）
    (r"贵州茅台|600519", "eastmoney_f10",
     "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code=SH600519&color=w#/cwfx", 3, 3600),
    (r"宁德时代|300750", "eastmoney_f10",
     "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code=SZ300750&color=w#/cwfx", 3, 3600),

    # 两融/杠杆
    (r"两融|融资|融券|杠杆.*余额|保证金", "eastmoney_margin",
     "https://data.eastmoney.com/rzrq/total.html", 3, 1800),

    # 北向/资金流向
    (r"北向|北上|外资|沪股通|深股通", "eastmoney_north",
     "https://data.eastmoney.com/hsgt/index.html", 3, 1800),
    (r"资金流向|主力|大单", "eastmoney_flow",
     "https://data.eastmoney.com/zjlx/dpzjlx.html", 3, 1800),

    # 研报/评级
    (r"研报|评级|目标价|维持|买入|增持|卖出", "eastmoney_research",
     "https://data.eastmoney.com/report/stock.jshtml", 3, 3600),

    # 公告
    (r"公告|股东大会|分红|除权|除息", "cninfo",
     "https://www.cninfo.com.cn/new/fulltextSearch?notautosubmit=&keyWord=", 3, 1800),

    # 板块/行业
    (r"板块|行业|概念|半导体|AI|芯片|新能源|消费|医药|金融", "eastmoney_board",
     "https://quote.eastmoney.com/center/boardlist.html#industry_board", 3, 1800),

    # 宏观/指数
    (r"上证|深证|创业板|指数|大盘|A股|市场", "eastmoney_index",
     "https://quote.eastmoney.com/center/gridlist.html#hs_a_board", 3, 600),
]


def smart_search(query):
    """
    智能搜索：根据关键词判断目标网站，直接用浏览器访问。
    
    流程：
      1. 匹配路由规则 → 直接打开目标网站
      2. 没有匹配 → 用真实浏览器打开 DuckDuckGo 执行真实搜索
    """

    # 第 1 步：尝试匹配路由表
    for pattern, site_name, url_template, wait, ttl in ROUTES:
        if re.search(pattern, query):
            url = url_template
            # 如果 URL 包含查询参数占位，把关键词拼进去
            if "?q=" in url or "?keyWord=" in url or "?wd=" in url:
                url = url + urllib.parse.quote(query)
            page = fetch_page(url, wait_seconds=wait, cache_ttl=ttl)
            if "error" not in page:
                page["_source"] = site_name
                page["_query"] = query
                return page

    # 第 2 步：没有匹配 → 用浏览器打开 DuckDuckGo 做真实搜索
    # 这次不用解析 HTML，而是把搜索结果的文本全量返回
    search_url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}&ia=web"
    page = fetch_page(search_url, wait_seconds=5, use_cache=False)
    if "error" not in page:
        page["_source"] = "duckduckgo"
        page["_query"] = query
        # 从原始文本中提取有意义的片段
        text = page.get("text", "")
        # 过滤掉导航/广告类的噪音
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
        page["_filtered_text"] = lines[:30]

    return page


# =============================================================
# 个股数据（保持原有逻辑，已验证 ✅）
# =============================================================

STOCK_SOURCES = {
    "eastmoney": {
        "name": "东方财富 F10",
        "url_template": "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={code}{market}&color=w#/cwfx",
        "market_code": {"6": ".SH", "0": ".SZ", "3": ".SZ"},
        "verified": True,
    },
    "sohu": {
        "name": "搜狐证券",
        "url_template": "https://q.stock.sohu.com/cn/{code}/index.shtml",
        "verified": True,
    },
    "10jqka": {
        "name": "同花顺 F10",
        "url_template": "https://basic.10jqka.com.cn/{code}/",
        "verified": True,
    },
}


def get_stock_data(stock_code, source="eastmoney"):
    """获取个股财务数据"""
    if source == "eastmoney":
        market = ".SH" if stock_code.startswith("6") else ".SZ"
        url = STOCK_SOURCES["eastmoney"]["url_template"].replace("{code}", stock_code).replace("{market}", market)
    elif source == "sohu":
        url = STOCK_SOURCES["sohu"]["url_template"].replace("{code}", stock_code)
    elif source == "10jqka":
        url = STOCK_SOURCES["10jqka"]["url_template"].replace("{code}", stock_code)
    else:
        return {"error": f"不支持的数据源: {source}"}

    page_data = fetch_page(url, wait_seconds=3, cache_ttl=3600)
    if "error" in page_data:
        return page_data

    return extract_financial_data(page_data, stock_code, source)


def extract_financial_data(page_data, stock_code, source):
    text = page_data.get("text", "")
    result = {
        "source": source,
        "stock_code": stock_code,
        "title": page_data.get("title", ""),
        "url": page_data.get("url", ""),
    }

    patterns = [
        (r'基本每股收益[^0-9]*([0-9.]+)', "eps"),
        (r'每股收益[^0-9]*([0-9.]+)', "eps"),
        (r'归属净利润[^0-9]*([0-9.]+亿)', "net_profit"),
        (r'营业收入[^0-9]*([0-9.]+亿)', "revenue"),
        (r'营业总收入同比增长[^0-9]*([0-9.]+)', "revenue_growth_pct"),
        (r'归属净利润同比增长[^0-9]*([0-9.]+)', "profit_growth_pct"),
        (r'毛利率[^0-9]*([0-9.]+)', "gross_margin"),
        (r'资产负债率[^0-9]*([0-9.]+)', "debt_ratio"),
        (r'每股净资产[^0-9]*([0-9.]+)', "nav_per_share"),
    ]

    for pattern, key in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result[key] = match.group(1)

    result["_raw_text_length"] = len(text)
    result["_raw_text"] = text[:5000]
    return result


# =============================================================
# CLI
# =============================================================

def print_help():
    print("""
浏览器自动化 v2.0 — 直接访问目标网站，不再绕路搜索引擎

用法:
  python3 scripts/search_via_browser.py smart <关键词>
      智能搜索：自动判断目标网站，直接用浏览器访问
      例: smart "两融余额 3万亿"
          smart "中际旭创 融资余额"
          smart "北向资金 今日流向"

  python3 scripts/search_via_browser.py stock <代码>
      个股财务数据（东方财富 F10）
      例: stock 600519  (support: 6xxxxx / 00xxxx / 30xxxx / 688xxx)

  python3 scripts/search_via_browser.py url <完整URL>
      直接打开任意 URL

路由规则：
  - 两融/融资/融券 → data.eastmoney.com/rzrq
  - 北向/外资     → data.eastmoney.com/hsgt
  - 资金流向       → data.eastmoney.com/zjlx
  - 研报/评级     → data.eastmoney.com/report
  - 公告           → cninfo.com.cn
  - 板块/行业     → quote.eastmoney.com
  - 大盘/指数     → quote.eastmoney.com
  - 其他           → DuckDuckGo (真实浏览器搜索)
""")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_help()
        sys.exit(1)

    mode = sys.argv[1]

    # 依赖检查
    agent_browser = shutil.which("agent-browser")
    if not agent_browser:
        print(json.dumps({"error": "agent-browser CLI not found. Run: npm install -g agent-browser"}))
        sys.exit(1)

    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome_path):
        print(json.dumps({"error": "Chrome not found at " + chrome_path}))
        sys.exit(1)

    if mode == "smart":
        query = " ".join(sys.argv[2:])
        result = smart_search(query)

    elif mode == "stock":
        stock_code = sys.argv[2]
        source = "eastmoney"
        if "--source" in sys.argv:
            idx = sys.argv.index("--source")
            if idx + 1 < len(sys.argv):
                source = sys.argv[idx + 1]
        result = get_stock_data(stock_code, source)

    elif mode == "url":
        url = sys.argv[2]
        result = fetch_page(url, use_cache=False)

    else:
        print(json.dumps({"error": f"未知模式: {mode}，可用: smart / stock / url"}))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))
