#!/usr/bin/env python3
"""
Kronos 因子模块 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
集成 Kronos-small 到面壁者体系，作为独立因子源。
输出: 个股的 Kronos 预测涨跌幅 + 置信度信号

使用方式:
  python3 kronos_factor.py <stock_code>      # 单只个股预测
  python3 kronos_factor.py batch <codes.json> # 批量全市场预测

依赖:
  - PyTorch (MPS/CPU)
  - Kronos-small 权重 (本地 /tmp/kronos_models/)
  - 东方财富日线 API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, sys, json, warnings
warnings.filterwarnings('ignore')

# ── 配置 ──
LOOKBACK = 128          # 日线128天 ≈ 6个月
PRED_LEN = 12           # 预测未来12个交易日
SAMPLE_COUNT = 5        # 采样次数（越多越稳定）
T = 0.8                 # 温度
TOP_P = 0.9             # 核采样
HF_ENDPOINT = "https://hf-mirror.com"
MODEL_DIR = "/tmp/kronos_models"

os.environ['HF_ENDPOINT'] = HF_ENDPOINT
sys.path.insert(0, '/tmp/Kronos')

import numpy as np
import pandas as pd
import urllib.request
from time import time

# ── 动态加载模型（首次调用时初始化） ──
_predictor = None

def _init_model():
    global _predictor
    if _predictor is not None:
        return _predictor
    
    import torch
    from model import Kronos, KronosTokenizer, KronosPredictor
    
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    
    tokenizer = KronosTokenizer.from_pretrained(f'{MODEL_DIR}/Kronos-Tokenizer-base')
    model = Kronos.from_pretrained(f'{MODEL_DIR}/Kronos-small')
    _predictor = KronosPredictor(model, tokenizer, device=device, max_context=512)
    
    return _predictor


# ── 数据获取 ──
def fetch_daily(code, days=700):
    """获取个股日线数据"""
    secid = f"1.{code}" if code.startswith(('6','5','9')) else f"0.{code}"
    url = (f"http://push2his.eastmoney.com/api/qt/stock/kline/get"
           f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
           f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
           f"&klt=101&fqt=2&end=20500101&lmt={days}")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        
        if not data.get('data') or not data['data'].get('klines'):
            return None
        
        records = []
        for line in data['data']['klines']:
            p = line.split(',')
            records.append({
                'date': p[0], 'open': float(p[1]), 'close': float(p[2]),
                'high': float(p[3]), 'low': float(p[4]),
                'volume': float(p[5]), 
                'amount': float(p[6]) if len(p) > 6 else 0,
            })
        
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # 剔除异常值
        df = df[df['close'] > 0].reset_index(drop=True)
        
        return df
    except Exception as e:
        return None


# ── 核心预测 ──
def predict(code):
    """
    对单个股票代码进行 Kronos 预测。
    
    返回:
        dict:
            code        : 股票代码
            pred_return : 预测涨跌幅 (未来 PRED_LEN 天)
            pred_close  : 预测收盘价
            confidence  : 置信度 (采样路径标准差归一化, 越低越确定)
            samples     : 各采样路径的预测结果
            lookback    : 使用的历史天数
            pred_len    : 预测天数
    """
    predictor = _init_model()
    
    df = fetch_daily(code)
    if df is None or len(df) < LOOKBACK:
        return {"code": code, "error": f"数据不足 (需要{LOOKBACK}天, 实际{len(df) if df is not None else 0}天)"}
    
    # 取最近 LOOKBACK 天的数据
    x_df = df.iloc[-LOOKBACK:][['open','high','low','close','volume','amount']].copy()
    x_ts = pd.Series(df['date'].iloc[-LOOKBACK:].values, name='timestamps')
    
    # 预测未来日期（推算交易日）
    last_date = df['date'].iloc[-1]
    from datetime import timedelta
    pred_dates = pd.date_range(last_date + timedelta(days=1), periods=PRED_LEN, freq='B')  # 仅交易日
    y_ts = pd.Series(pred_dates, name='timestamps')
    
    # 实际当前价格
    current_price = df['close'].iloc[-1]
    
    try:
        pred_df = predictor.predict(
            df=x_df, x_timestamp=x_ts, y_timestamp=y_ts,
            pred_len=PRED_LEN, T=T, top_p=TOP_P,
            sample_count=SAMPLE_COUNT
        )
        
        last_pred_close = float(pred_df['close'].iloc[-1])
        pred_return = (last_pred_close / current_price) - 1
        
        # 置信度：计算采样路径的离散程度
        # sample_count 越多, 价格预测越稳定 → 置信度越高
        # 这里用所有预测时刻的 close 标准差均值来衡量
        path_stds = pred_df[['close']].std().values
        avg_std = float(np.mean(path_stds))
        
        # 归一化置信度 (0~1), avg_std 越小越置信
        # 沪深300日均波动约 50点, 以此为参考
        confidence = max(0.0, min(1.0, 1.0 - avg_std / 100.0))
        
        return {
            "code": code,
            "pred_return": round(pred_return, 6),
            "pred_close": round(last_pred_close, 2),
            "current_price": round(current_price, 2),
            "confidence": round(confidence, 4),
            "lookback": LOOKBACK,
            "pred_len": PRED_LEN,
            "avg_path_std": round(float(avg_std), 2),
            "timestamp": pd.Timestamp.now().isoformat(),
        }
    
    except Exception as e:
        return {"code": code, "error": str(e)}


# ── 批量预测 ──
def batch_predict(codes, output_path=None):
    """
    批量预测多只股票。
    codes: list of stock codes or path to JSON file
    output_path: 输出文件路径 (可选)
    """
    if isinstance(codes, str) and codes.endswith('.json'):
        with open(codes) as f:
            codes = json.load(f)
    
    results = []
    total = len(codes)
    t0 = time()
    
    for i, code in enumerate(codes):
        result = predict(code)
        results.append(result)
        
        if (i + 1) % 50 == 0:
            elapsed = time() - t0
            print(f"[{i+1}/{total}] {elapsed:.0f}s", file=sys.stderr)
    
    # 输出
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(results, f, ensure_ascii=False)
        print(json.dumps({"status": "ok", "count": len(results), "output": output_path}))
    else:
        print(json.dumps(results, ensure_ascii=False))
    
    return results


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 kronos_factor.py <stock_code>          # 单只")
        print("  python3 kronos_factor.py batch <codes.json>    # 批量")
        print("  python3 kronos_factor.py batch <codes.json> -o result.json")
        sys.exit(1)
    
    if sys.argv[1] == "batch" and len(sys.argv) >= 3:
        codes_file = sys.argv[2]
        output = sys.argv[4] if len(sys.argv) > 3 and sys.argv[3] == "-o" else None
        batch_predict(codes_file, output)
    else:
        result = predict(sys.argv[1])
        print(json.dumps(result, ensure_ascii=False))
