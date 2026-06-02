#!/usr/bin/env node
/**
 * 阿不 统一数据引擎 (Node.js 版)
 * 数据源: 东方财富 API (通过 Node-fetch, 绕过反爬)
 * 
 * 用法: node engine.js <command> [args]
 *   kline <code> [datalen=120]  - 获取日K线
 *   spot <code1,code2,...>      - 获取实时行情
 *   live <code>                  - 实时快照
 */

const fetch = require('node-fetch');

// 市场前缀: 0=深 1=上
const MARKET = c => {
  const f = c[0];
  if (f === '6' || f === '9') return '1';
  return '0';
};

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36';
const REF = 'https://quote.eastmoney.com';

async function kline(code, datalen = 120) {
  const mkt = MARKET(code);
  const url = `https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=${mkt}.${code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=${datalen}`;
  const r = await fetch(url, { headers: { 'User-Agent': UA, 'Referer': REF } });
  const d = await r.json();
  const klines = d.data?.klines || [];
  return klines.map(k => {
    const p = k.split(',');
    return {
      date: p[0], open: parseFloat(p[1]), close: parseFloat(p[2]),
      high: parseFloat(p[3]), low: parseFloat(p[4]),
      volume: parseInt(p[5]), amount: parseFloat(p[6]),
      amplitude: parseFloat(p[7]), change_pct: parseFloat(p[8]),
      turnover: parseFloat(p[9]),
    };
  });
}

async function spot(codes) {
  const list = codes.map(c => `${MARKET(c)}.${c}`).join(',');
  const url = `https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f4,f12,f14,f15,f16,f17,f18,f20,f21&secids=${list}`;
  const r = await fetch(url, { headers: { 'User-Agent': UA, 'Referer': REF } });
  const d = await r.json();
  const items = d.data?.diff || [];
  return items.map(i => ({
    code: i.f12, name: i.f14,
    price: i.f2 ?? 0, change_pct: i.f3 ?? 0,
    high: i.f15 ?? 0, low: i.f16 ?? 0,
    open: i.f17 ?? 0, volume: i.f18 ?? 0, amount: i.f20 ?? 0,
    amplitude: i.f21 ?? 0,
  }));
}

async function live(code) {
  const res = await spot([code]);
  return res[0] || null;
}

async function main() {
  const cmd = process.argv[2];
  const arg = process.argv[3];
  
  if (cmd === 'kline') {
    const data = await kline(arg, parseInt(process.argv[4]) || 120);
    console.log(JSON.stringify(data));
  } else if (cmd === 'spot') {
    const codes = arg ? arg.split(',') : ['000001','000002','600519','300750'];
    const data = await spot(codes);
    console.log(JSON.stringify(data));
  } else if (cmd === 'live') {
    const data = await live(arg || '000001');
    console.log(JSON.stringify(data));
  } else {
    console.error('用法: node engine.js kline|spot|live [code]');
  }
}

main().catch(e => {
  console.error('Fatal:', e.message);
  process.exit(1);
});
