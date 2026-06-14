# A-Stock Scalpel 推广发布指南

## 第一步：创建 GitHub 仓库

在浏览器打开 https://github.com/new

```
Repository name: a-stock-scalpel
Description: 多因子A股短线量化评分系统 · 9技术因子 · 32条透明规则 · 零成本数据源
Visibility: Public
不要勾选任何初始化选项（仓库已就绪）
```

创建后执行：
```bash
cd /Users/xiaobeiray/.openclaw/workspace/finbot

# 改 remote 到新仓库
git remote set-url origin git@github.com:zhubohan190601-crypto/a-stock-scalpel.git
# 也可以留着旧的（finbot），加一个新的
git remote add gh-new git@github.com:zhubohan190601-crypto/a-stock-scalpel.git

# 推送到新仓库
git push -u gh-new main
```

## 第二步：发布后立即做

### 1. GitHub 仓库设置
- 开启 **Discussions**（Settings → General → Features）
- 开启 **Issues**
- 设置 Topics: `quantitative-trading` `a-share` `stock-analysis` `technical-analysis` `china-stock` `python`
- 设置 Website: 可以留空或链接到你的 ClawHub Skill 页面

### 2. 首页置顶 Issue
创建一条置顶 Issue 标题：
> "🎉 A-Stock Scalpel v2.2.0 发布！9个技术因子 + 32条确定性规则表"

内容：贴上中文 README 的核心段落 + architecture 图 + 用法示例

## 第三步：内容推广

### 📝 知乎文章（发布当天）

标题建议：
1. 「我用Python写了一个A股短线多因子评分系统，完全开源」
2. 「一个散户的量化自救：零成本A股分析工具开源了」

内容结构：
- 痛点：散户被黑盒AI收割
- 方案：可审计的确定性规则表
- 演示：GitHub 截图 + 终端输出截图
- 价值：60秒扫描80只龙头
- 链接：GitHub + 求 Star

发布时间：**周五晚 20:00-22:00**（知乎流量高峰）

### 📊 雪球（每天发）

格式：
```
【A-Stock Scalpel 每日扫描 2026-06-14】

今日信号分布：strong_buy X只 | buy Y只 | neutral Z只

📈 强烈买入 TOP 3:
1. 600519 贵州茅台 净分+52
2. 300750 宁德时代 净分+48
3. 600036 招商银行 净分+35

🔧 开源工具：github.com/zhubohan190601-crypto/a-stock-scalpel
```

每天15:30收盘后固定发。

### 🌐 V2EX（发布后第2-3天）

标题：「开源了一个A股量化评分工具，规则完全透明」

避坑：
- 不要承诺收益
- 强调"教育研究用途"
- 放 disclaimer 在前

### 🔴 小红书

发截图（终端输出）+ 简短文字：
"60秒扫描80只A股龙头，今天买/茅台/宁德"

话题：`#量化交易` `#A股` `#Python` `#开源`

## 第四步：SEO 关键词布局

README 中已覆盖的 SEO 关键词：
- `quantitative trading China A-share`
- `A股 量化分析 开源`
- `多因子 评分 系统 Python`
- `short term trading China stock`

仓库 Topics 设置：
```
quantitative-trading, a-share, stock-analysis, technical-analysis, 
china-stock, python, trading-bot, stock-market, 量化交易
```

## 第五步：社区互动

1. 在 GitHub 搜索 `china stock` `a-share` `quant` 相关仓库 → 关注 + 学习 → 偶尔 PR
2. 在 Reddit r/algotrading 和 r/quant 发帖子（英文 README + 链接）
3. 在知乎量化话题下回答相关问题，顺手放仓库链接

## 第六步：持续运营

| 周期 | 动作 |
|------|------|
| 每天 | 雪球发每日扫描结果 |
| 每周 | 写一篇知乎分析文章 |
| 每版发布 | Release note + CHANGELOG |
| 每月 | 检查 Issues + PR，回应社区 |
| 每季度 | 复盘数据：stars增长/PR数/Issue解决率 |

## 预计效果

- 第1周：10-30 stars（自然流量+知乎）
- 第2周：50-100 stars（V2EX+雪球传播）
- 第1月：200-500 stars（持续运营+口碑）
- 第3月：500-1000 stars（社区PR+论坛传播）

> 前提：坚持每日雪球+知乎周更。开源项目不运营=没人知道。
