#!/usr/bin/env python3
"""pick_review.py — 推荐前瞻复盘（追踪闭环第二步，借鉴 ALTA forward outcomes）

读取 tracking/picks_*.jsonl 推荐记录 → 取推荐日之后的日K →
计算 N 日收益 / 止损目标命中 → 输出复盘报告与胜率统计。

用法:
  python3 scripts/pick_review.py                    # 复盘全部记录
  python3 scripts/pick_review.py --days 5           # 主观察窗口（默认5日）
  python3 scripts/pick_review.py --file tracking/picks_202609.jsonl
产出:
  reports/pick-review-YYYYMMDD.md   复盘报告（含胜率统计）
"""
import json, os, sys, urllib.request, time
from datetime import datetime

WS = os.environ.get("ASTOCK_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACK_DIR = os.path.join(WS, "tracking")
REPORT_DIR = os.path.join(WS, "reports")


def market_of(code):
    return "1" if code.startswith(("6", "688", "900")) else "0"


def fetch_kline(code, limit=180, retries=2):
    """东财日K（前复权 fqt=1）；返回 [(date, close, high, low), ...] 升序"""
    secid = f"{market_of(code)}.{code}"
    url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
           f"?secid={secid}&fields1=f1,f2,f3,f4,f5&fields2=f51,f52,f53,f54,f55,f56,f57"
           f"&klt=101&fqt=1&end=20500101&lmt={limit}")
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
            data = json.loads(raw)
            klines = (data.get("data") or {}).get("klines") or []
            out = []
            for k in klines:
                parts = k.split(",")
                # 日期,开,收,高,低,量,额
                out.append((parts[0], float(parts[2]), float(parts[3]), float(parts[4])))
            return out
        except Exception:
            if attempt < retries:
                time.sleep(1.5)
    return []


def review_record(rec, days):
    code, date = rec.get("code"), rec.get("date")
    entry = rec.get("entry") or 0
    stop = rec.get("stop") or 0
    target = rec.get("target") or 0
    name = rec.get("name") or code
    if not code or not date:
        return None
    klines = fetch_kline(code)
    if not klines:
        return {"code": code, "name": name, "date": date, "status": "数据缺失", "bars_after": 0}

    after = [k for k in klines if k[0] > date]
    if not after:
        return {"code": code, "name": name, "date": date, "status": "尚无后续交易日",
                "entry": entry, "bars_after": 0}

    base = entry if entry else after[0][1]
    window = after[:days] if len(after) >= days else after
    seg = window if days == 1 else after[:days]
    closes = [k[1] for k in seg]
    highs = [k[2] for k in window]
    lows = [k[3] for k in window]

    ret_n = round((closes[-1] / base - 1) * 100, 2) if closes and base else None
    max_gain = round((max(highs) / base - 1) * 100, 2) if highs and base else None
    max_dd = round((min(lows) / base - 1) * 100, 2) if lows and base else None

    hit_stop = bool(stop and lows and min(lows) <= stop)
    hit_target = bool(target and highs and max(highs) >= target)
    if hit_stop and hit_target:
        status = "止损目标同触(需看顺序)"
    elif hit_target:
        status = "✅ 达标"
    elif hit_stop:
        status = "❌ 止损"
    else:
        status = "持有中"

    return {"code": code, "name": name, "date": date, "entry": base,
            "days_held": len(after), "window_bars": len(window),
            "ret_n": ret_n, "max_gain": max_gain, "max_dd": max_dd,
            "status": status, "stop": stop, "target": target,
            "reason": rec.get("reason", "")}


def main():
    args = sys.argv[1:]
    days = 5
    files = []
    if "--days" in args:
        days = int(args[args.index("--days") + 1])
    if "--file" in args:
        files = [args[args.index("--file") + 1]]
    else:
        if os.path.isdir(TRACK_DIR):
            files = [os.path.join(TRACK_DIR, f) for f in sorted(os.listdir(TRACK_DIR))
                     if f.startswith("picks_") and f.endswith(".jsonl")]
    if not files:
        print("无推荐记录（tracking/picks_*.jsonl 不存在）")
        return 0

    records = []
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    results = [r for r in (review_record(rec, days) for rec in records) if r]

    # 统计
    scored = [r for r in results if r.get("ret_n") is not None]
    wins = [r for r in scored if (r.get("ret_n") or 0) > 0]
    stops = [r for r in results if r.get("status") == "❌ 止损"]
    targets = [r for r in results if r.get("status") == "✅ 达标"]
    avg_ret = round(sum(r["ret_n"] for r in scored) / len(scored), 2) if scored else None
    win_rate = round(len(wins) / len(scored) * 100, 1) if scored else None

    today = datetime.now().strftime("%Y%m%d")
    lines = [f"# 推荐前瞻复盘 {datetime.now().strftime('%Y-%m-%d %H:%M')}", "",
             f"**观察窗口**：{days} 个交易日 | **记录数**：{len(results)} | **可评分**：{len(scored)}", "",
             "| 代码 | 名称 | 推荐日 | 成本 | 总交易日 | 窗口 | N日收益% | 最高浮盈% | 最大回撤% | 状态 |",
             "|------|------|--------|------|----------|------|----------|-----------|-----------|------|"]
    for r in results:
        lines.append("| {code} | {name} | {date} | {entry} | {days_held} | {window_bars} | {ret_n} | {max_gain} | {max_dd} | {status} |".format(
            code=r.get("code"), name=r.get("name"), date=r.get("date"), entry=r.get("entry", "-"),
            days_held=r.get("days_held", 0), window_bars=r.get("window_bars", 0),
            ret_n=r.get("ret_n", "-"), max_gain=r.get("max_gain", "-"),
            max_dd=r.get("max_dd", "-"), status=r.get("status", "-")))
    lines += ["", "## 统计", "",
              f"- **胜率**（N日收益>0）：{win_rate}%" if win_rate is not None else "- 胜率：N/A",
              f"- **平均收益**：{avg_ret}%" if avg_ret is not None else "- 平均收益：N/A",
              f"- **达标 {len(targets)} 只 / 止损 {len(stops)} 只**", "",
              f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · pick_review.py"]

    os.makedirs(REPORT_DIR, exist_ok=True)
    out = os.path.join(REPORT_DIR, f"pick-review-{today}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({"ok": True, "report": out, "records": len(results),
                      "scored": len(scored), "win_rate": win_rate, "avg_ret": avg_ret},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
