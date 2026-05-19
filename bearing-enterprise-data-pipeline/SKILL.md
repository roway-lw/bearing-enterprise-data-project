---
name: bearing-enterprise-data-pipeline
version: 1.0.0
description: 企业产业标签全流程调度整合 - 串联采集→清洗→标签三模块流水线，一键输出完整企业画像
trigger: 当用户需要对单企业或批量企业执行完整采集+清洗+标签流水线、一键生成企业标签画像时触发
input: 企业名称（单个或批量）
output: 标准化JSON全流程结果，写入项目output目录
---

# bearing-enterprise-data-pipeline: 企业产业标签全流程调度整合

## 功能概述

本Skill严格按照 **bearing-enterprise-data-crawl采集 → bearing-enterprise-data-clean结构化清洗 → bearing-enterprise-data-tag标签生成** 标准流水线自动执行，核心功能：

1. **流程串行调度**：严格按照三步流水线顺序自动执行，数据链路透传
2. **数据链路透传**：上一模块输出结果，无缝作为下一模块输入，不篡改、不丢失字段
3. **节点异常拦截**：任意模块执行失败、数据异常，自动终止后续流程并返回异常原因
4. **全结果归档汇总**：统一整理原始网页数据、结构化字段、产品/服务/能力全维度标签
5. **日志溯源管理**：记录每一步执行节点、执行耗时、数据状态、置信度
6. **Token用量统计**：估算各阶段数据等效token数，输出全流程token用量汇总
6. **批量任务兼容**：支持单企业检索、批量企业名单批量跑通整套标签流水线

## 标准执行流水线

```
Step1 接收企业名称
  → Step2 调用【bearing-enterprise-data-crawl】全网采集企业公开原始数据
    → Step3 校验采集状态(success/partial)，正常则调用【bearing-enterprise-data-clean】
      → Step4 校验结构化数据(success/partial)，正常则调用【bearing-enterprise-data-tag】
        → Step5 三模块数据合并归一 + 扁平化标签提取
          → Step6 返回完整结果、链路日志、异常备注
```

## 各模块调用规则

| 模块 | 输入 | 输出 | 判定条件 |
|------|------|------|----------|
| bearing-enterprise-data-crawl | 企业名称 | 原始网页文本、来源URL、采集状态 | crawl_status=success/partial |
| bearing-enterprise-data-clean | bearing-enterprise-data-crawl JSON | 标准化企业字段、产品/资质/经营信息 | clean_status=success/partial |
| bearing-enterprise-data-tag | bearing-enterprise-data-clean JSON | 产品/服务/能力标签、标签溯源 | 无论是否完整均正常输出 |

## 扁平化标签体系

从三维标签体系进一步提取5大业务维度扁平标签：

| 维度 | 标签字段 | 说明 |
|------|----------|------|
| 产品维度 | 主营产品标签、核心产品标签、高端产品标签、产品关键词、产品结构描述 | 从核心产品/规格/合规提取 |
| 工艺维度 | 工艺能力标签、核心工艺标签、制造能力标签、特种工艺标签、工艺能力描述 | 从专利/产品/生产信息推断 |
| 应用维度 | 应用领域标签、核心应用领域、下游行业标签、应用领域描述 | 从合作企业/业务范围推断 |
| 供应链维度 | 客户供应链标签、客户类型标签、供应链角色标签、供应链层级标签、客户供应链描述 | 从合作模式/企业推断 |

## 输出格式

结果自动写入**调用项目的 `output/` 目录**（通过 `--output-dir` 指定），文件名格式为 `{企业名称}_{时间戳}_pipeline.json`。

```json
{
  "pipeline_info": {
    "pipeline_status": "success",
    "execute_time": "2026-04-24 xx:xx:xx",
    "execute_node": ["bearing-enterprise-data-crawl采集", "bearing-enterprise-data-clean清洗", "bearing-enterprise-data-tag打标"],
    "overall_confidence": 0.92,
    "total_time_seconds": 125.3,
    "token_usage": {
      "stages": {
        "采集": {"input_tokens": 5, "output_tokens": 15000, "total_tokens": 15005},
        "清洗": {"input_tokens": 15000, "output_tokens": 3000, "total_tokens": 18000},
        "打标": {"input_tokens": 3000, "output_tokens": 5000, "total_tokens": 8000}
      },
      "total_input_tokens": 18005,
      "total_output_tokens": 23000,
      "total_tokens": 41005
    }
  },
  "raw_crawl_data": {},
  "structured_data": {},
  "enterprise_tags": {
    "产品标签": {},
    "服务标签": {},
    "能力标签": {}
  },
  "tags": {
    "主营产品标签": [],
    "核心产品标签": [],
    "高端产品标签": [],
    "产品关键词": [],
    "产品结构描述": "",
    "工艺能力标签": [],
    "核心工艺标签": [],
    "制造能力标签": [],
    "特种工艺标签": [],
    "工艺能力描述": "",
    "应用领域标签": [],
    "核心应用领域": [],
    "下游行业标签": [],
    "应用领域描述": "",
    "客户供应链标签": [],
    "客户类型标签": [],
    "供应链角色标签": [],
    "供应链层级标签": [],
    "客户供应链描述": ""
  },
  "error_info": "",
  "log_record": "全流程节点执行正常，链路数据完整无缺失",
  "log_detail": []
}
```

## Agent 交互指引（重要）

当用户通过 Skill 调用本流水线时，**必须**遵循以下交互规范，确保用户在长耗时任务中有清晰感知：

### 1. 启动前告知（必做）
执行脚本前，**必须**先向用户说明：
- 目标企业名称
- 预计耗时（单企业约2-4分钟，批量按数量估算）
- 告知用户"执行期间无实时输出，请耐心等待"

示例话术：
> 正在启动企业标签全流程调度，目标企业：XXX公司。预计耗时2-4分钟，执行期间无实时输出，请耐心等待。

### 2. 执行中不重复输出
脚本执行期间不需要额外提示，脚本内部的进度日志会在执行完毕后一并展示。

### 3. 结果摘要（必做）
脚本执行完毕后，**必须**从输出中提取关键信息，向用户展示简洁摘要：
- 执行状态（success/partial/failed）
- 总体置信度
- 总耗时
- Token用量估算
- 核心标签摘要（主营产品、核心工艺、应用领域、供应链角色）
- 输出文件路径

### 4. 异常告知
如执行失败，需明确告知用户失败环节和原因，并建议下一步操作。

## 使用方式

```bash
# 单企业
python scripts/pipeline.py "企业名称"

# 批量（逗号分隔）
python scripts/pipeline.py "企业1,企业2,企业3"

# 批量（从文件读取）
python scripts/pipeline.py --file enterprises.txt
```

**重要**：当通过 Agent 调用本 Skill 时，需确保输出文件写入调用项目的目录（而非 Skill 自身目录）。有两种方式：

1. **方式一**：设置 `PROJECT_DIR` 环境变量为调用项目根目录（推荐，设置一次即可）：
```bash
# Linux/macOS
export PROJECT_DIR=/path/to/calling/project
# Windows PowerShell
$env:PROJECT_DIR = "C:\path\to\calling\project"
python scripts/pipeline.py "企业名称"
```

2. **方式二**：每次调用时传 `--output-dir` 参数：
```bash
python scripts/pipeline.py "企业名称" --output-dir /path/to/calling/project/output
```

Pipeline 会自动将输出目录传递给所有子模块（crawl/clean/tag），确保所有过程文件和最终结果都输出到同一目录。

## 依赖关系

```
bearing-enterprise-data-crawl: bearing-enterprise-data-crawl    → 原始数据采集
bearing-enterprise-data-clean: bearing-enterprise-data-clean    → 数据结构化清洗
bearing-enterprise-data-tag: bearing-enterprise-data-tag      → 标签生成
bearing-enterprise-data-pipeline: bearing-enterprise-data-pipeline → 全流程调度 ← 本Skill
```

本Skill通过动态导入直接调用bearing-enterprise-data-crawl/2/3的类，无需中间文件传递。

## 注意事项

1. 本Skill依赖bearing-enterprise-data-crawl/2/3已安装在同级目录
2. bearing-enterprise-data-crawl/2失败会阻断后续流程，bearing-enterprise-data-tag失败不影响整体（标记为partial）
3. 批量模式下每个企业独立执行，单个失败不影响其他企业
4. 结果文件包含完整的原始数据、结构化数据和标签数据，便于审计追溯

