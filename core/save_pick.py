#!/usr/bin/env python3
"""save_pick.py — 选股结果落盘（追踪闭环）
用法:
  echo '<JSON>' | python3 scripts/save_pick.py --stdin
  python3 scripts/save_pick.py --json '<JSON>'
JSON 格式:
  {"date":"2026-09-15","market":"震荡市/冰点期...","picks":[
     {"code":"002842","name":"翔鹭钨业","score":85,"reason":"钨涨价+分歧转一致",
      "entry":35.76,"stop":32.0,"target":42.0}]}
产出:
  reports/stock-pick-YYYYMMDD.md   人类可读报告
  tracking/picks_YYYYMM.jsonl      结构化记录（可做胜率复盘）
"""
import json, os, sys
from datetime import datetime

WORKSPACE = os.environ.get("ASTOCK_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(WORKSPACE, "reports")
TRACK_DIR = os.path.join(WORKSPACE, "tracking")

def main():
    raw = None
    args = sys.argv[1:]
    if "--stdin" in args:
        raw = sys.stdin.read()
    elif "--json" in args:
        i = args.index("--json")
        if i + 1 < len(args):
            raw = args[i + 1]
    if not raw or not raw.strip():
        print("ERROR: 需要 --stdin 或 --json 提供数据", file=sys.stderr)
        return 2
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON 解析失败: {e}", file=sys.stderr)
        return 2

    date_str = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    compact = date_str.replace("-", "")
    market = data.get("market", "")
    picks = data.get("picks", [])

    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(TRACK_DIR, exist_ok=True)

    # 1) 报告 md
    lines = [f"# 选股候选清单 {date_str}", ""]
    if market:
        lines += [f"**市场状态**：{market}", ""]
    lines += ["| 代码 | 名称 | 评分 | 入场 | 止损 | 目标 | 理由 |", "|------|------|------|------|------|------|------|"]
    for p in picks:
        lines.append("| {code} | {name} | {score} | {entry} | {stop} | {target} | {reason} |".format(
            code=p.get("code","-"), name=p.get("name","-"), score=p.get("score","-"),
            entry=p.get("entry","-"), stop=p.get("stop","-"), target=p.get("target","-"),
            reason=(p.get("reason","") or "").replace("|","/")))
    lines += ["", f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · 由 save_pick.py 落盘"]
    report_path = os.path.join(REPORT_DIR, f"stock-pick-{compact}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # 2) 结构化 jsonl（同日同代码去重）
    trail_path = os.path.join(TRACK_DIR, f"picks_{compact[:6]}.jsonl")
    existing = set()
    if os.path.exists(trail_path):
        with open(trail_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    existing.add((r.get("date"), r.get("code")))
                except Exception:
                    pass
    added = 0
    with open(trail_path, "a", encoding="utf-8") as f:
        for p in picks:
            key = (date_str, p.get("code"))
            if key in existing:
                continue
            rec = {"date": date_str, "code": p.get("code"), "name": p.get("name"),
                   "score": p.get("score"), "action": p.get("action", "watch"),
                   "entry": p.get("entry"), "stop": p.get("stop"), "target": p.get("target"),
                   "reason": p.get("reason"), "market": market,
                   "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            added += 1

    print(json.dumps({"ok": True, "report": report_path, "tracking": trail_path,
                      "picks": len(picks), "new_records": added}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
