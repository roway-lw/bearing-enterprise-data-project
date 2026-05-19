---
name: bearing-data-source-filter
version: 1.0.0
description: |
  轴承行业企业信息数据源筛选与评价 Skill。
  针对轴承行业（含滚动轴承、滑动轴承、关节轴承、直线运动轴承、轴承零部件等细分领域），
  全网搜索并发现有企业信息的网站，通过自动化访问测试评价各网站的数据质量和响应效率，
  最终遴选出20个优质数据源网站。
  当用户需要寻找轴承行业企业信息数据源、筛选企业数据库网站、评价数据网站质量时触发。
trigger: 当用户需要寻找/筛选/评价轴承行业企业信息数据源、企业数据库网站时触发
input: 行业关键词（可选，默认为轴承行业相关）
output: 网站评价报告JSON，写入项目output目录
---

# bearing-data-source-filter: 轴承行业企业信息数据源筛选与评价

## 功能概述

本 Skill 专注于为轴承行业（滚动轴承、滑动轴承、关节轴承、直线运动轴承、轴承零部件、轴承钢材料等）筛选高质量的企业信息数据源网站，核心功能：

1. **全网网站发现**：通过多搜索引擎、多关键词策略，自动发现可能有轴承企业信息的网站
2. **网站采集测试**：对每个候选网站进行访问测试，测量响应时间、可用性、稳定性
3. **数据质量评价**：评估网站的企业信息丰富度、行业相关性、数据结构化程度、更新频率
4. **响应效率评价**：评估网站的访问速度、成功率、反爬策略友好度
5. **优质网站遴选**：基于综合评价模型，自动遴选出TOP20优质数据源网站

## 搜索策略

### 行业关键词体系

针对轴承行业7大细分领域，构建多维度搜索关键词：

| 维度 | 示例关键词 |
|------|-----------|
| 企业名录 | 轴承企业名录、轴承零部件厂家名录、滚动轴承制造商名录 |
| 企业查询 | 轴承企业查询、轴承公司工商信息、轴承企业信息查询 |
| 行业黄页 | 轴承行业黄页、轴承零部件采购平台、轴承供应商名录 |
| 产业数据库 | 轴承产业数据库、轴承制造厂商库、轴承钢材料供应商库 |
| 招投标 | 轴承行业招投标、轴承采购招标、轴承设备招标 |
| 工商信息 | 轴承企业工商信息、轴承公司注册信息 |
| 专利信息 | 轴承专利查询、轴承技术专利检索、轴承专利数据库 |

### 搜索引擎覆盖

- 百度搜索 (baidu.com)
- 必应搜索 (bing.com)
- 搜狗搜索 (sogou.com)
- 360搜索 (so.com)

## 评价指标体系

### 1. 响应效率指标（权重30%）

| 指标 | 说明 | 评分标准 |
|------|------|---------|
| 响应时间 | 首次访问的耗时 | <1秒得满分，>10秒得0分 |
| 访问成功率 | 多次访问的成功比例 | 成功率×100 |
| 稳定性 | 是否存在频繁超时/阻断 | 基于多次访问统计 |

### 2. 数据质量指标（权重40%）

| 指标 | 说明 | 评分标准 |
|------|------|---------|
| 企业信息丰富度 | 页面是否包含企业名称、地址、产品等信息 | 内容匹配度评分 |
| 行业相关性 | 内容是否与轴承行业强相关 | 关键词匹配评分 |
| 数据结构化 | 信息是否有结构化展示（表格、列表等） | 结构化程度评分 |
| 数据时效性 | 内容是否包含近期信息 | 时间戳检测评分 |

### 3. 网站质量指标（权重30%）

| 指标 | 说明 | 评分标准 |
|------|------|---------|
| 页面质量 | 页面加载完整性、是否有错误 | 完整性评分 |
| 反爬友好度 | 是否有过强的反爬机制 | 可采集性评分 |
| 内容可信度 | 是否来自权威/官方渠道 | 来源权威性评分 |

## 综合评价模型

```
综合得分 = 响应效率得分 × 0.30 + 数据质量得分 × 0.40 + 网站质量得分 × 0.30

响应效率得分 = (响应时间得分 × 0.4 + 访问成功率得分 × 0.4 + 稳定性得分 × 0.2)

数据质量得分 = (企业信息丰富度 × 0.35 + 行业相关性 × 0.35 + 数据结构化 × 0.2 + 数据时效性 × 0.1)

网站质量得分 = (页面质量 × 0.4 + 反爬友好度 × 0.3 + 内容可信度 × 0.3)
```

## 输入格式

```bash
# 使用默认轴承行业关键词
python scripts/filter_data_sources.py

# 指定自定义行业关键词
python scripts/filter_data_sources.py --keywords "滚动轴承,圆锥滚子轴承,深沟球轴承"

# 指定搜索深度（每个关键词搜索的页面数）
python scripts/filter_data_sources.py --search-depth 3

# 指定评价采样数（每个网站测试次数）
python scripts/filter_data_sources.py --eval-samples 3
```

## 输出格式

### 1. 评价报告

结果自动写入**调用项目的 `output/` 目录**（通过 `--output-dir` 指定），文件名格式为 `data_source_evaluation_{时间戳}.json`。

```json
{
  "evaluation_summary": {
    "total_discovered": 150,
    "total_evaluated": 120,
    "evaluation_time": "2026-05-06 17:30:00",
    "top20_selected": true
  },
  "all_sites": [...],
  "top20_sites": [...],
  "category_distribution": {...}
}
```

### 2. 数据源配置文件（供 crawl skill 消费）

无论 `seed-only` 还是 `full` 模式，都会生成标准化的 **`data_source_config.json`**：

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-05-09T13:48:16",
  "generated_by": "bearing-data-source-filter",
  "industry": "轴承",
  "update_policy": {
    "seed_list_source": "references/bearing_industry_sites.md",
    "auto_promote_threshold": 70
  },
  "sources": [
    {
      "id": "tianyancha",
      "name": "天眼查",
      "category": "工商查询",
      "base_url": "https://www.tianyancha.com",
      "search_url_template": "https://www.tianyancha.com/search?key={name}",
      "search_keywords_template": ["{name} 工商信息", "{name} 股东信息"],
      "data_types": ["business_info", "commercial_relation"],
      "priority": 1,
      "enabled": true,
      "overall_score": 85.0,
      "notes": "企业工商信息、股权结构"
    }
  ]
}
```

**`data_types` 说明**：
- `business_info`：工商注册信息
- `bidding_info`：招投标/采购信息
- `patent_info`：专利/商标信息
- `commercial_relation`：商业关系（供应链、投资、合作等）

## 使用方式

### 两阶段工作流

```bash
# 阶段一（低频）：基于种子列表快速生成默认配置（无网络请求，秒级完成）
python scripts/filter_data_sources.py --mode seed-only

# 阶段二（按需）：完整搜索+评价，生成带评分的动态配置（有网络请求，耗时较长）
python scripts/filter_data_sources.py --mode full

# 指定细分行业（仅 full 模式有效）
python scripts/filter_data_sources.py --mode full --keywords "深沟球轴承,圆锥滚子轴承,调心滚子轴承"

# 指定输出目录和配置文件路径
python scripts/filter_data_sources.py --mode seed-only --output-dir ./my_output --config-output ./my_output/data_source_config.json

# 完整参数
python scripts/filter_data_sources.py --mode full --keywords "轴承,滚动轴承" --search-depth 5 --eval-samples 3 --max-sites 200
```

### 与 bearing-enterprise-data-crawl 协作

```bash
# 1. bearing-data-source-filter 生成配置
python scripts/filter_data_sources.py --mode seed-only --output-dir ../shared_output

# 2. bearing-enterprise-data-crawl 读取配置执行采集
python ../bearing-enterprise-data-crawl/scripts/crawl_enterprise.py "企业名称" --source-config ../shared_output/data_source_config.json
```

**重要**：当通过 Agent 调用本 Skill 时，需确保输出文件写入调用项目的目录（而非 Skill 自身目录）。有两种方式：

1. **方式一**：设置 `PROJECT_DIR` 环境变量为调用项目根目录（推荐，设置一次即可）：
```bash
# Linux/macOS
export PROJECT_DIR=/path/to/calling/project
# Windows PowerShell
$env:PROJECT_DIR = "C:\path\to\calling\project"
python scripts/filter_data_sources.py
```

2. **方式二**：每次调用时传 `--output-dir` 参数：
```bash
python scripts/filter_data_sources.py --output-dir /path/to/calling/project/output
```

## 注意事项

1. **搜索深度**：默认每个关键词搜索前2页结果，可通过 `--search-depth` 调整
2. **访问速率**：遵循礼貌访问原则，请求间隔 1.5-3 秒随机
3. **超时控制**：单个网站访问超时时间为15秒
4. **黑名单过滤**：自动排除搜索引擎、电商、社交、视频等无关网站
5. **已知种子网站**：内置轴承行业已知优质网站种子列表，加速发现过程

## 依赖环境

```bash
pip install crawl4ai
```

Crawl4AI 支持 Python 3.8+，需要 Chrome/Chromium 浏览器环境。

## 参考文件

- `references/bearing_industry_sites.md` - 轴承行业已知优质网站种子列表
- `references/evaluation_criteria.md` - 详细评价标准说明

