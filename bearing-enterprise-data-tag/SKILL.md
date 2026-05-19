---
name: bearing-enterprise-data-tag
version: 1.0.0
description: 轴承行业企业基础静态属性标签分析 - 基于bearing-enterprise-data-clean结构化数据，自动生成产品/服务/能力三大维度标签
trigger: 当用户需要对企业生成轴承行业标签、标签打标、企业画像标签、产业标签分类时触发
input: bearing-enterprise-data-clean输出的JSON结构化数据文件路径
output: 标准化标签JSON数据，写入项目output目录
---

# bearing-enterprise-data-tag: 轴承行业企业基础静态属性标签分析

## 功能概述

本Skill承接bearing-enterprise-data-clean（bearing-enterprise-data-clean）输出的轴承行业企业结构化数据，聚焦**产品、服务、能力**三大核心维度，自动完成标签生成、分类、标准化，核心功能如下：

1. **标签自动生成**：基于bearing-enterprise-data-clean的结构化字段（核心产品、主营业务、行业资质等），自动匹配轴承行业专属标签，无需人工干预；
2. **标签分类管理**：将标签按"产品标签、服务标签、能力标签"三大核心维度分类，每个维度下细分二级标签，逻辑清晰，便于后续调用；
3. **标签标准化**：统一标签名称、表述格式，消除歧义（如"深沟球轴承""DGBB"统一为"深沟球轴承"标签）；
4. **标签溯源**：每个标签对应明确的数据源（bearing-enterprise-data-clean的具体结构化字段），确保标签可追溯、可验证；
5. **标签扩展**：支持根据轴承行业细分领域（滚动轴承、滑动轴承、轴承零部件等），灵活新增、修改标签，适配不同企业类型；
6. **异常处理**：针对bearing-enterprise-data-clean中"未提取到""未明确"的字段，标注对应标签为"未明确"，不影响整体标签体系，同时提示补充数据。

## 标签体系

### 三大核心维度

```
标签体系
├── 产品标签
│   ├── 核心产品类型    ← core_products + industry_segment
│   ├── 产品规格标签    ← product_spec
│   ├── 产品应用场景    ← cooperative_enterprise + main_business
│   └── 产品合规标签    ← industry_cert
├── 服务标签
│   ├── 核心服务类型    ← business_scope + main_business
│   ├── 合作模式标签    ← cooperative_enterprise + bidding_projects
│   ├── 服务覆盖范围    ← cooperative_enterprise + register_address
│   └── 增值服务标签    ← business_scope
└── 能力标签
    ├── 技术能力标签    ← patent_count + high_tech_enterprise
    ├── 生产能力标签    ← employee_scale + investment_projects
    ├── 资质能力标签    ← specialized_enterprise + industry_cert
    └── 资金实力标签    ← registered_capital + investment_projects
```

## 工作流程

1. **读取结构化数据**：加载bearing-enterprise-data-clean输出的JSON文件
2. **产品标签生成**：基于核心产品、产品规格、合作企业、行业资质生成产品维度标签
3. **服务标签生成**：基于经营范围、合作模式、覆盖范围、增值服务生成服务维度标签
4. **能力标签生成**：基于专利、规模、资质、资金生成能力维度标签
5. **标签标准化**：统一术语（深沟球轴承/DGBB等）、简化表述、消除歧义
6. **置信度计算**：基于源字段完整度和内容量计算标签置信度
7. **异常标注**：对未明确字段生成"未明确"标签，记录原因
8. **标准化输出**：生成JSON格式标签数据，写入项目 `output/` 目录

## 输入格式

输入为bearing-enterprise-data-clean（bearing-enterprise-data-clean）输出的JSON结构化数据，包含以下关键字段：

- `enterprise_name` - 企业全称
- `core_products` - 核心产品
- `product_spec` - 产品规格
- `main_business` - 主营业务
- `business_scope` - 经营范围
- `industry_cert` - 行业资质
- `cooperative_enterprise` - 合作企业
- `bidding_projects` - 招投标项目
- `investment_projects` - 投资项目
- `patent_count` - 专利数量
- `high_tech_enterprise` - 高新技术企业
- `specialized_enterprise` - 专精特新企业
- `employee_scale` - 用工规模
- `registered_capital` - 注册资本
- `industry_segment` - 细分领域

## 输出格式

标签结果自动写入**调用项目的 `output/` 目录**（通过 `--output-dir` 指定），文件名格式为 `{企业名称}_{时间戳}_tag.json`。

输出为JSON格式，包含企业基础信息、三大核心维度标签、标签溯源、标签置信度：

```json
{
  "enterprise_info": {
    "enterprise_name": "洛阳XX轴承有限公司",
    "enterprise_short_name": "洛阳XX轴承",
    "industry_segment": "滚动轴承制造",
    "data_source": "企业官网、河南省工信局公示",
    "tag_confidence": 0.93,
    "tag_generate_time": "2024-XX-XX XX:XX:XX"
  },
  "tag_system": {
    "产品标签": {
      "核心产品类型": [
        {"tag": "深沟球轴承", "source_field": "core_products", "confidence": 0.95}
      ],
      "产品规格标签": [
        {"tag": "轴承内径10-500mm", "source_field": "product_spec", "confidence": 0.94}
      ],
      "产品应用场景": [
        {"tag": "风电设备", "source_field": "cooperative_enterprise", "confidence": 0.92}
      ],
      "产品合规标签": [
        {"tag": "AS9100认证", "source_field": "industry_cert", "confidence": 0.94}
      ]
    },
    "服务标签": { ... },
    "能力标签": { ... }
  },
  "uncertain_tags": [],
  "note": "标签生成正常，所有核心标签均基于bearing-enterprise-data-clean结构化字段，无异常"
}
```

## 使用方式

```bash
# 第三步：标签生成（承接bearing-enterprise-data-clean输出）
python scripts/tag_enterprise.py output/企业名称_xxx_cleaned.json
```

**重要**：当通过 Agent 调用本 Skill 时，需确保输出文件写入调用项目的目录（而非 Skill 自身目录）。有两种方式：

1. **方式一**：设置 `PROJECT_DIR` 环境变量为调用项目根目录（推荐，设置一次即可）：
```bash
# Linux/macOS
export PROJECT_DIR=/path/to/calling/project
# Windows PowerShell
$env:PROJECT_DIR = "C:\path\to\calling\project"
python scripts/tag_enterprise.py output/企业名称_xxx_clean.json
```

2. **方式二**：每次调用时传 `--output-dir` 参数：
```bash
python scripts/tag_enterprise.py output/企业名称_xxx_clean.json --output-dir /path/to/calling/project/output
```

## 依赖关系

```
bearing-enterprise-data-crawl: bearing-enterprise-data-crawl   → 原始数据采集
bearing-enterprise-data-clean: bearing-enterprise-data-clean   → 数据结构化清洗
bearing-enterprise-data-tag: bearing-enterprise-data-tag     → 标签生成 ← 本Skill
```

## 注意事项

1. 本Skill必须承接bearing-enterprise-data-clean的输出，不可直接使用bearing-enterprise-data-crawl的原始数据
2. 标签置信度基于bearing-enterprise-data-clean字段完整度计算，字段越完整置信度越高
3. "未明确"标签表示源字段缺失，需回溯bearing-enterprise-data-crawl补充采集
4. 标签体系支持扩展，可通过修改 `references/tag_system.md` 新增行业标签

