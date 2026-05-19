---
name: bearing-enterprise-data-clean
description: |
  本 Skill 承接 bearing-enterprise-data-crawl 输出的原始数据，针对轴承行业特性，
  自动完成清洗、结构化提取、字段标准化，输出标准化 JSON 格式数据。
  当用户需要对采集的企业原始数据进行结构化清洗、提取轴承行业专属字段时触发。
  输入为 crawl skill 输出的 JSON，输出为标准化结构化数据。
---

# 轴承行业数据结构化清洗 Skill

## 功能概述

承接 `bearing-enterprise-data-crawl` 输出的原始数据（非结构化文本+零散表格），结合轴承行业特性，自动完成：

1. **文本预处理**：清洗无效字符、冗余内容，统一文本格式，剔除广告噪声残留
2. **关键实体提取**：针对轴承行业，提取轴承类型/规格/材料等相关字段，转化为标准字段
3. **字段标准化**：统一企业名称/地址/细分领域/经营状态等格式，消除歧义（如"深沟球轴承""DGBB"统一标注）
4. **数据清洗**：去重、纠错、补齐缺失字段，标注模糊/不确定信息
5. **结构化封装**：整理为标准化格式，便于后续标签打标 Skill 调用
6. **异常处理**：对无法提取/模糊不清的字段进行标注，不影响整体流程

## 输入格式

直接对接 `bearing-enterprise-data-crawl` 输出的 JSON 文件：

```bash
python scripts/clean_enterprise_data.py output/企业名称_20260423_235200.json
```

## 输出格式

清洗结果自动写入**调用项目的 `output/` 目录**（通过 `--output-dir` 指定），文件名格式为 `{企业名称}_{时间戳}_clean.json`。

输出包含 25 个轴承行业专属结构化字段：

```json
{
  "enterprise_name": "洛阳XX轴承有限公司",
  "enterprise_short_name": "洛阳XX轴承",
  "establish_time": "2015-08-12",
  "register_address": "河南省洛阳市涧西区轴承产业园10号",
  "actual_address": "河南省洛阳市涧西区科技路28号",
  "legal_person": "李四",
  "registered_capital": "8000万元人民币",
  "enterprise_type": "有限责任公司（自然人投资或控股）",
  "operating_status": "存续",
  "business_scope": "轴承及轴承零部件的研发、生产、销售；轴承钢材料加工",
  "main_business": "深沟球轴承研发与生产、圆锥滚子轴承制造",
  "core_products": "深沟球轴承、圆锥滚子轴承、调心滚子轴承、轴承保持架",
  "product_spec": "轴承内径10-500mm；精度等级P0-P4；额定载荷动态60kN",
  "employee_scale": "500-1000人",
  "high_tech_enterprise": "是",
  "specialized_enterprise": "是",
  "patent_count": "42项（发明专利18项，含轴承设计、热处理相关）",
  "industry_cert": "ISO9001、AS9100、CRCC认证",
  "bidding_projects": "2024年中标XX风电设备厂轴承采购项目，金额3200万元",
  "investment_projects": "2023年新增精密轴承生产线项目，总投资1.5亿元",
  "cooperative_enterprise": "一汽、中车、金风科技、SKF",
  "industry_category": "制造业-通用设备制造业-轴承制造",
  "industry_segment": "滚动轴承制造/轴承零部件制造",
  "data_source": "企业官网、天眼查、政府公示平台",
  "confidence": 0.94,
  "clean_status": "success",
  "uncertain_fields": [],
  "clean_time": "2026-XX-XX XX:XX:XX",
  "note": "所有核心字段提取完整"
}
```

## 清洗流程（7步）

### Step 1: 文本预处理
- 移除来源标注（【企业官网内容】等）
- 移除 HTML 残留标签
- 移除特殊字符
- 统一空白
- 去除重复句子

### Step 2: 企业基础信息提取
- 企业全称（标准化）
- 企业简称（去除有限公司后缀）
- 成立时间（正则匹配+上下文验证）
- 注册地址/实际经营地址（省级开头地址提取）
- 法定代表人
- 注册资本（标准化带单位）
- 企业类型（映射标准值）
- 经营状态（映射标准值）

### Step 3: 轴承行业经营信息提取
- 经营范围（精简，突出行业特性）
- 主营业务（7大细分领域关键词匹配）
- 核心产品（产品关键词提取+同类合并）
- 产品规格（轴承内径/外径/精度等级/额定载荷/极限转速）
- 用工规模（分6档标准化）

### Step 4: 资质信息提取
- 高新技术企业（是/否/未明确）
- 专精特新企业（是/否/未明确）
- 专利数量（发明专利数+轴承相关标注）
- 行业资质认证（AS9100/API/CRCC/IRIS等认证关键词匹配）

### Step 5: 项目与招投标提取
- 招投标项目（轴承相关中标/采购信息）
- 投资项目（轴承相关生产线/产线投资）
- 核心合作企业（25家常见轴承行业客户匹配）

### Step 6: 行业分类
- 行业大类（制造业-通用设备制造业-轴承制造）
- 细分领域（7大细分领域自动分类）
- 数据来源溯源（根据 URL 域名标注来源平台）

### Step 7: 置信度计算
```
confidence = min(0.98, 0.3 + 核心字段完成数 × 0.085 + 专利加分 + 资质加分 + 招投标加分)
```

## 轴承行业7大细分领域

| 细分领域 | 关键词 |
|---------|-------|
| 滚动轴承制造 | 深沟球轴承、圆锥滚子轴承、调心滚子轴承、圆柱滚子轴承、角接触球轴承 |
| 滑动轴承制造 | 滑动轴承、自润滑轴承、轴瓦、衬套、含油轴承 |
| 关节轴承制造 | 关节轴承、杆端关节、向心关节 |
| 直线运动轴承 | 直线轴承、直线导轨、滚珠丝杠、直线运动 |
| 轴承零部件制造 | 保持架、滚动体、钢球、滚子、密封圈、防尘盖 |
| 轴承钢材料 | GCr15、轴承钢、高碳铬轴承钢、渗碳轴承钢、不锈钢轴承 |
| 轴承装备制造 | 轴承磨床、超精机、轴承装配线、锻造设备 |

## 参考文件

- `references/industry_terminology.md` - 行业术语标准化映射
- `references/field_extraction_patterns.md` - 字段提取正则模板

## 使用方式

```bash
# 先运行 crawl skill 采集原始数据
python bearing-enterprise-data-crawl/scripts/crawl_enterprise.py "企业名称"

# 再运行 clean skill 清洗数据
python bearing-enterprise-data-clean/scripts/clean_enterprise_data.py output/企业名称_xxx.json
```

**重要**：当通过 Agent 调用本 Skill 时，需确保输出文件写入调用项目的目录（而非 Skill 自身目录）。有两种方式：

1. **方式一**：设置 `PROJECT_DIR` 环境变量为调用项目根目录（推荐，设置一次即可）：
```bash
# Linux/macOS
export PROJECT_DIR=/path/to/calling/project
# Windows PowerShell
$env:PROJECT_DIR = "C:\path\to\calling\project"
python scripts/clean_enterprise_data.py output/企业名称_xxx.json
```

2. **方式二**：每次调用时传 `--output-dir` 参数：
```bash
python scripts/clean_enterprise_data.py output/企业名称_xxx.json --output-dir /path/to/calling/project/output
```

## 依赖环境

无额外依赖，仅需 Python 3.8+ 标准库。

