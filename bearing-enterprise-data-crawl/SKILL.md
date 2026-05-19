---
name: bearing-enterprise-data-crawl
description: |
  本 Skill 基于 Crawl4AI 的 AI 爬虫能力，自动完成企业多渠道信息采集。
  当用户需要查询企业公开信息、采集企业工商数据、获取招投标信息、查询专利商标、
  或需要批量采集企业多维度数据时触发。
  输入为单个企业名称，输出为标准化 JSON 格式的结构化数据。
  聚焦四大核心数据：官网 / 工商 / 招投标 / 专利。
---

# 企业信息采集 Skill

## 功能概述

聚焦采集企业四大核心公开数据，全程无人工介入：

1. **官网发现与深度采集**：多关键词×多搜索引擎定位真实官网，站内深度爬取关于我们/产品中心/资质荣誉等重要板块
2. **工商信息采集**：直采天眼查/企查查/爱企查/启信宝/工商公示平台，获取注册信息/法人/资本/经营范围等
3. **招投标信息采集**：直采政府采购网/公共资源交易平台/招标投标平台/采招网，获取招标/中标/采购公告
4. **专利信息采集**：直采国家知识产权局/中国商标网/soopat/专利之星，获取发明专利/实用新型/外观设计

## 合规原则

- 遵循 robots.txt 协议
- 低频访问，请求间隔 1.5-4 秒随机
- 不采集付费平台、加密页面、需登录内容
- 不采集个人隐私信息

## 输入格式

单个企业名称，例如：
```
美林数据技术股份有限公司
```

## 输出格式

采集结果自动写入**调用项目的 `output/` 目录**（通过 `--output-dir` 指定），文件名格式为 `{企业名称}_{时间戳}_crawl.json`。

```json
{
  "enterprise_name": "美林数据技术股份有限公司",
  "source_urls": ["..."],
  "raw_content": {
    "official_website": "【官网内容】关于我们、产品中心、资质荣誉...",
    "business_info": "【工商内容】注册资本、法人代表、经营范围、股东信息...",
    "bidding_info": "【招投标内容】中标公告、采购项目、招标信息...",
    "patent_info": "【专利内容】发明专利、实用新型、商标注册...",
    "all_content": "【合并全部内容】..."
  },
  "crawl_status": "success",
  "confidence": 0.88,
  "crawl_time": "2026-XX-XX XX:XX:XX",
  "note": "采集成功，覆盖全部 4 个核心渠道，共 12 个页面"
}
```

## 四阶段采集流程

### 阶段1: 官网发现与深度采集

**目标**：精准定位企业真实官网，深度采集站内核心页面

1. **多关键词搜索**：`{名称} 官网` / `{名称} 官方网站` / `{简称} 官网` / `{名称} 公司简介` / `{名称} 关于我们` / `{名称} 联系方式`
2. **智能官网识别**：优先选择域名包含企业名称关键字的链接，爬取后验证内容是否包含企业名称
3. **站内深度爬取**：发现官网后，提取站内链接，按优先级爬取重要板块：
   - 关于我们 / 公司简介 / 团队介绍
   - 产品中心 / 解决方案 / 技术服务
   - 资质荣誉 / 合作伙伴
   - 联系方式
   - 最多爬取 10 个站内页面

### 阶段2: 工商信息采集

**目标**：获取企业注册信息、法人、资本、经营范围、股东等

1. **直接平台采集**：
   - 天眼查（tianyancha.com）
   - 企查查（qcc.com）
   - 爱企查（aiqicha.baidu.com）
   - 启信宝（qixin.com）
   - 国家企业信用信息公示系统（gsxt.gov.cn）
2. **详情页爬取**：识别并爬取企业详情页链接
3. **搜索引擎补充**：`{名称} 工商信息` / `{名称} 注册资本` / `{名称} 法人代表` / `{名称} site:gsxt.gov.cn`

### 阶段3: 招投标信息采集

**目标**：获取企业相关招标/中标/采购公告

1. **直接平台采集**：
   - 中国政府采购网（ccgp.gov.cn）
   - 全国公共资源交易平台（ggzy.gov.cn）
   - 中国招标投标公共服务平台（cebpubservice.com）
   - 采招网（bidcenter.com.cn）
   - 中国采购与招标网（chinabidding.cn）
2. **详情页爬取**：识别并爬取招投标详情页
3. **搜索引擎补充**：`{名称} 招标` / `{名称} 中标` / `{名称} 采购` / `{名称} site:ccgp.gov.cn` / `{名称} site:ggzy.gov.cn`

### 阶段4: 专利信息采集

**目标**：获取企业专利、商标等知识产权信息

1. **直接平台采集**：
   - 国家知识产权局专利检索（cponline.cnipa.gov.cn）
   - 中国商标网（sbj.cnipa.gov.cn）
   - soopat 专利检索（soopat.com）
   - 专利之星（cprs.patentstar.com）
2. **详情页爬取**：识别并爬取专利详情页
3. **搜索引擎补充**：`{名称} 专利` / `{名称} 发明专利` / `{名称} 实用新型` / `{名称} site:cnipa.gov.cn`

## 置信度计算

```
置信度 = min(0.95, 0.2 + 有效分类数 × 0.18 + min(内容总字数/15000, 0.15))
```

| 有效分类数 | 置信度范围 | 状态 |
|-----------|-----------|------|
| 4 | >= 0.92 | success（全覆盖） |
| 2-3 | 0.56-0.74 | partial |
| 1 | 0.38 | partial |
| 0 | 0.2 | failed |

## 使用方式

### 基础用法（推荐：使用数据源配置）

默认读取 `bearing-data-source-filter` 生成的 `data_source_config.json`，动态加载平台列表：

```bash
pip install crawl4ai
python scripts/crawl_enterprise.py "企业名称" --source-config ../../bearing-data-source-filter/scripts/output/data_source_config.json
```

**配置消费逻辑**：
- 配置中 `data_types` 包含 `business_info` 且 `enabled=true` 的平台 → 作为工商采集平台
- 配置中 `data_types` 包含 `bidding_info` 且 `enabled=true` 的平台 → 作为招投标采集平台
- 配置中 `data_types` 包含 `patent_info` 且 `enabled=true` 的平台 → 作为专利采集平台
- 未提供 `--source-config` 时，自动在同级目录查找配置文件；找不到则回退到内置平台列表

### 仅使用内置平台（无外部配置）

```bash
python scripts/crawl_enterprise.py "企业名称"
```

### 输出目录设置

当通过 Agent 调用本 Skill 时，需确保输出文件写入调用项目的目录（而非 Skill 自身目录）。有两种方式：

1. **方式一**：设置 `PROJECT_DIR` 环境变量为调用项目根目录（推荐，设置一次即可）：
```bash
# Linux/macOS
export PROJECT_DIR=/path/to/calling/project
# Windows PowerShell
$env:PROJECT_DIR = "C:\path\to\calling\project"
python scripts/crawl_enterprise.py "企业名称"
```

2. **方式二**：每次调用时传 `--output-dir` 参数：
```bash
python scripts/crawl_enterprise.py "企业名称" --output-dir /path/to/calling/project/output
```

## 注意事项

1. **速率控制**：请求间隔 1.5-4 秒随机
2. **官网验证**：爬取后验证内容是否包含企业名称，防止误采
3. **详情页深度**：每个平台最多爬取 2-3 个详情页
4. **黑名单过滤**：自动排除电商/视频/社交/广告/招聘等无关域名
5. **内容上限**：每个来源最多保留 5000 字

## 依赖环境

```bash
pip install crawl4ai
```

Crawl4AI 支持 Python 3.8+，需要 Chrome/Chromium 浏览器环境。

