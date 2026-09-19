#!/usr/bin/env python3
"""
搜索备用方案（v3.0）：三层降级搜索

策略：
  Layer 1: DuckDuckGo HTML 搜索（本脚本默认）
  Layer 2: 自动降级到 search_via_browser.py（agent-browser + Chrome）

成本：零成本（DuckDuckGo 免费 + Chrome 复用）
大陆可达：DuckDuckGo 可用，Chrome 自动化无地域限制

用法：
  python3 search_fallback.py <关键词>
  输出：JSON 数组 [{title, url, snippet}, ...]
  
  自动降级：如果 DuckDuckGo 返回错误或空结果，自动尝试 Chrome 浏览器搜索

v3.0 - 2026-06-23：加入 agent-browser 兜底
v2.0 - 切至 DuckDuckGo HTML 引擎
"""

import urllib.request
import urllib.parse
import json
import re
import sys
import os
import subprocess

def duck_search(query, count=8):
    """通过 DuckDuckGo HTML 搜索获取结果"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    data = urllib.parse.urlencode({"q": query}).encode()
    req = urllib.request.Request("https://html.duckduckgo.com/html/", data=data, headers=headers)
    
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return [{"error": f"HTTP request failed: {str(e)}"}]

    results = []

    # 方法1: 用 class="result" 块解析（标准路径）
    blocks = re.findall(r'<div class="result[^>]*>.*?</div>\s*</div>', html, re.DOTALL)
    
    for block in blocks[:count]:
        url_match = re.search(r'href="(https?://[^"]+)"', block)
        title_match = re.search(
            r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', block, re.DOTALL
        )
        snippet_match = re.search(
            r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>', block, re.DOTALL
        )

        if not url_match:
            continue

        link = url_match.group(1)
        # 过滤掉 DuckDuckGo 自己的页面
        if "duckduckgo.com" in link and "html" not in link:
            continue

        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else ""
        snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip() if snippet_match else ""

        if title and link:
            results.append({
                "title": title[:120],
                "url": link,
                "snippet": snippet[:250],
            })

    # 方法2: 兜底解析（如果上面的 block 方法没匹配到）
    if not results:
        urls = re.findall(r'class="result__url"[^>]*href="(https?://[^"]+)"', html)
        titles = re.findall(
            r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', html, re.DOTALL
        )
        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>', html, re.DOTALL
        )
        for i, link in enumerate(urls[:count]):
            if "duckduckgo.com" in link:
                continue
            title = re.sub(r"<[^>]+>", "", titles[i]).strip() if i < len(titles) else ""
            snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
            if title:
                results.append({
                    "title": title[:120],
                    "url": link,
                    "snippet": snippet[:250],
                })

    if not results:
        # DuckDuckGo 失败，自动降级到 Chrome 浏览器搜索
        return auto_fallback_search(query, count)

    return results


def auto_fallback_search(query, count=8):
    """自动降级到 Chrome 浏览器搜索（通过 search_via_browser.py）"""
    script_path = os.path.join(os.path.dirname(__file__), "search_via_browser.py")
    if not os.path.exists(script_path):
        return [{"error": "DuckDuckGo failed and search_via_browser.py not found"}]
    
    try:
        result = subprocess.run(
            [sys.executable, script_path, "search", query],
            capture_output=True, text=True, timeout=45
        )
        if result.returncode == 0:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, list) and len(parsed) > 0:
                # 浏览器搜索成功
                parsed.insert(0, {"note": "DuckDuckGo failed, results from browser fallback"})
                return parsed
            elif isinstance(parsed, dict) and "error" not in parsed:
                return [{"note": "Browser fallback returned non-error but unexpected format"}]
        
        return [{"error": f"Browser fallback failed: {result.stderr[:200]}"}]
    except Exception as e:
        return [{"error": f"Browser fallback exception: {str(e)}"}]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python3 search_fallback.py <query>"}))
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    results = duck_search(query)
    print(json.dumps(results, ensure_ascii=False, indent=2))
