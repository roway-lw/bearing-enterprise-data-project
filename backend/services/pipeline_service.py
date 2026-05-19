"""流水线调度服务 - 包装现有 PipelineOrchestrator，适配 FastAPI + WebSocket"""
import os
import sys
import json
import time
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import backend.config as config
from backend.services.progress_manager import progress_manager

# 确保项目根目录在 sys.path 中
_project_root = config.PROJECT_ROOT
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
_pipeline_scripts = os.path.join(_project_root, "bearing-enterprise-data-pipeline", "scripts")
if _pipeline_scripts not in sys.path:
    sys.path.insert(0, _pipeline_scripts)


# ============================================================
# WebSocket 进度报告器（替换控制台输出）
# ============================================================

class WebSocketProgressReporter:
    """将 pipeline 进度通过 ProgressManager 推送到 WebSocket"""

    MILESTONES = {0, 5, 25, 42, 50, 60, 62, 74, 80, 82, 90, 95, 97, 100}

    def __init__(self, task_id: str, enterprise_name: str = ""):
        self.task_id = task_id
        self.enterprise_name = enterprise_name
        self.current_progress = 0
        self.start_time = time.time()
        self._loop = None
        self.data_sources = []
        self.token_usage = {}

    def _get_loop(self):
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = None
        return self._loop

    def report(self, progress: int, stage: str, step: str, detail: str = ""):
        """进度报告 — 推送到 WebSocket"""
        self.current_progress = progress
        elapsed = round(time.time() - self.start_time, 1)

        message = {
            "type": "progress",
            "task_id": self.task_id,
            "enterprise_name": self.enterprise_name,
            "progress": progress,
            "stage": stage,
            "step": step,
            "detail": detail,
            "elapsed_seconds": elapsed,
            "data_sources": self.data_sources,
            "token_usage": self.token_usage,
        }
        progress_manager.broadcast_sync(self.task_id, message)

    def report_pipeline_start(self, enterprise_name: str):
        self.enterprise_name = enterprise_name
        self.start_time = time.time()
        self.report(0, "调度", "启动流水线", f"目标企业: {enterprise_name}")

    def report_pipeline_done(self, status, confidence, total_time, token_summary=None):
        self.report(100, "归档", "全流程完成", f"状态={status}, 置信度={confidence}")

    def report_pipeline_failed(self, stage, error, elapsed):
        self.report(100, stage, "流水线失败", error)

    def update_data_sources(self, sources: list):
        self.data_sources = sources

    def update_token_usage(self, usage: dict):
        self.token_usage = usage


# ============================================================
# 任务管理
# ============================================================

class TaskInfo:
    """单个流水线任务的状态"""
    def __init__(self, task_id: str, enterprise_names: List[str], output_config: dict):
        self.task_id = task_id
        self.enterprise_names = enterprise_names
        self.output_config = output_config
        self.status = "queued"  # queued / running / completed / failed
        self.results: List[dict] = []
        self.completed_count = 0
        self.failed_count = 0
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 全局任务存储
tasks: Dict[str, TaskInfo] = {}


# ============================================================
# PipelineService
# ============================================================

class PipelineService:
    """包装 PipelineOrchestrator，提供异步执行 + 进度推送"""

    def __init__(self):
        self._orchestrator_cls = None

    def _get_orchestrator_cls(self):
        """延迟加载 PipelineOrchestrator"""
        if self._orchestrator_cls is None:
            from pipeline import PipelineOrchestrator
            self._orchestrator_cls = PipelineOrchestrator
        return self._orchestrator_cls

    def create_task(self, enterprise_names: List[str], output_config: dict) -> str:
        """创建任务，返回 task_id"""
        task_id = uuid.uuid4().hex[:12]
        tasks[task_id] = TaskInfo(task_id, enterprise_names, output_config)
        return task_id

    async def run_task(self, task_id: str):
        """异步执行任务"""
        task = tasks.get(task_id)
        if not task:
            return

        task.status = "running"
        Orchestrator = self._get_orchestrator_cls()

        for name in task.enterprise_names:
            try:
                result = await asyncio.to_thread(
                    self._run_single_with_progress,
                    Orchestrator, task_id, name, task.output_config
                )

                task.results.append(result)
                if result.get("pipeline_info", {}).get("pipeline_status") == "failed":
                    task.failed_count += 1
                else:
                    task.completed_count += 1

                # 广播单企业完成
                summary = result.get("tags", {})
                tag_list = summary.get("主营产品标签", [])[:5]
                facts = result.get("structured_facts", {}).get("summary", {})
                fact_count = facts.get("total_records", 0)

                await progress_manager.broadcast(task_id, {
                    "type": "enterprise_complete",
                    "task_id": task_id,
                    "enterprise_name": name,
                    "status": result.get("pipeline_info", {}).get("pipeline_status", "unknown"),
                    "confidence": result.get("pipeline_info", {}).get("overall_confidence", 0),
                    "elapsed_seconds": result.get("pipeline_info", {}).get("total_time_seconds", 0),
                    "token_total": result.get("pipeline_info", {}).get("token_usage", {}).get("total_tokens", 0),
                    "tag_summary": tag_list,
                    "fact_count": fact_count,
                    "db_saved": task.output_config.get("db_output", False),
                    "db_tables": result.get("pipeline_info", {}).get("db_tables", {}),
                    "batch_progress": {
                        "completed": task.completed_count + task.failed_count,
                        "total": len(task.enterprise_names),
                    },
                })

                # 如果配置了数据库输出，写入 DB
                if task.output_config.get("db_output"):
                    await self._save_to_database(result, task_id)

            except Exception as e:
                task.failed_count += 1
                task.results.append({
                    "pipeline_info": {"pipeline_status": "failed"},
                    "structured_data": {"enterprise_name": name},
                    "error_info": str(e),
                })
                await progress_manager.broadcast(task_id, {
                    "type": "enterprise_complete",
                    "task_id": task_id,
                    "enterprise_name": name,
                    "status": "failed",
                    "confidence": 0,
                    "error": str(e),
                    "batch_progress": {
                        "completed": task.completed_count + task.failed_count,
                        "total": len(task.enterprise_names),
                    },
                })

        task.status = "completed"

        # 广播批量完成
        await progress_manager.broadcast(task_id, {
            "type": "batch_complete",
            "task_id": task_id,
            "results": [
                {
                    "enterprise_name": r.get("structured_data", {}).get("enterprise_name", ""),
                    "status": r.get("pipeline_info", {}).get("pipeline_status", "unknown"),
                    "confidence": r.get("pipeline_info", {}).get("overall_confidence", 0),
                }
                for r in task.results
            ],
        })

    def _run_single_with_progress(self, Orchestrator, task_id, enterprise_name, output_config):
        """在线程池中执行单个企业的流水线"""
        # 获取 LLM 客户端（如果已启用）
        llm_client = None
        try:
            from backend.services.llm_client import get_llm_client
            llm_client = get_llm_client()
        except Exception:
            pass

        orchestrator = Orchestrator(output_dir=config.OUTPUT_DIR, llm_client=llm_client)

        # 替换进度报告器为 WebSocket 版本
        ws_reporter = WebSocketProgressReporter(task_id, enterprise_name)
        orchestrator.progress = ws_reporter
        orchestrator._progress_callback = ws_reporter.report

        # 执行
        result = orchestrator.run_single(enterprise_name)
        result.setdefault("pipeline_info", {})["db_tables"] = {
            "tag_table": output_config.get("tag_table") or "enterprise_tag",
            "fact_table": output_config.get("fact_table") or "enterprise_fact",
        }

        # 补充结果中的 structured_facts（如果有）
        facts_file = orchestrator.output_files.get("facts")
        if facts_file and os.path.exists(facts_file):
            try:
                with open(facts_file, "r", encoding="utf-8") as f:
                    result["structured_facts"] = json.load(f)
            except Exception:
                result["structured_facts"] = {"records": [], "summary": {"total_records": 0}}

        return result

    async def _save_to_database(self, result: dict, task_id: str = ""):
        """将 pipeline 结果写入数据库"""
        try:
            from backend.database.crud import upsert_enterprise_tag, insert_facts
            from backend.database.connection import is_initialized

            if not is_initialized():
                msg = "数据库未初始化，写入跳过。请先在数据库导入中点击测试连接"
                print(f"[PipelineService] {msg}")
                if task_id:
                    await progress_manager.broadcast(task_id, {
                        "type": "progress",
                        "task_id": task_id,
                        "stage": "归档",
                        "step": "数据库写入失败",
                        "detail": msg,
                    })
                return

            pipeline_info = result.get("pipeline_info", {})
            structured_data = result.get("structured_data", {})
            tags = result.get("tags", {})
            enterprise_tags = result.get("enterprise_tags", {})
            enterprise_name = structured_data.get("enterprise_name", "")
            execute_time = pipeline_info.get("execute_time", "")

            batch_no = execute_time.replace(" ", "").replace(":", "").replace("-", "")[:14] if execute_time else datetime.now().strftime("%Y%m%d%H%M%S")

            # 写入 enterprise_tag
            tag_data = {
                "enterprise_name": enterprise_name,
                "batch_no": batch_no,
                "main_products": tags.get("主营产品标签", []),
                "core_products": tags.get("核心产品标签", []),
                "high_end_products": tags.get("高端产品标签", []),
                "product_keywords": tags.get("产品关键词", []),
                "product_desc": tags.get("产品结构描述", ""),
                "process_tags": tags.get("工艺能力标签", []),
                "core_process": tags.get("核心工艺标签", []),
                "manufacturing_tags": tags.get("制造能力标签", []),
                "special_process": tags.get("特种工艺标签", []),
                "process_desc": tags.get("工艺能力描述", ""),
                "application_tags": tags.get("应用领域标签", []),
                "core_application": tags.get("核心应用领域", []),
                "downstream_industry": tags.get("下游行业标签", []),
                "application_desc": tags.get("应用领域描述", ""),
                "supply_chain_tags": tags.get("客户供应链标签", []),
                "customer_type_tags": tags.get("客户类型标签", []),
                "supply_role_tags": tags.get("供应链角色标签", []),
                "supply_level_tags": tags.get("供应链层级标签", []),
                "supply_chain_desc": tags.get("客户供应链描述", ""),
                "product_detail_tags": enterprise_tags.get("产品标签", {}),
                "service_detail_tags": enterprise_tags.get("服务标签", {}),
                "capability_detail_tags": enterprise_tags.get("能力标签", {}),
                "flat_tags": tags,
                "overall_confidence": pipeline_info.get("overall_confidence", 0),
                "pipeline_status": pipeline_info.get("pipeline_status", "unknown"),
                "total_tokens": pipeline_info.get("token_usage", {}).get("total_tokens", 0),
                "total_time_seconds": pipeline_info.get("total_time_seconds", 0),
                "execute_time": execute_time or None,
                "registered_capital": structured_data.get("registered_capital", ""),
                "enterprise_short_name": structured_data.get("enterprise_short_name", ""),
                "employee_scale": structured_data.get("employee_scale", ""),
            }
            table_config = result.get("pipeline_info", {}).get("db_tables", {})
            await upsert_enterprise_tag(
                tag_data,
                table_config.get("tag_table") or "enterprise_tag"
            )

            def _safe(val):
                return val if val != "" else None

            # 写入 enterprise_fact
            facts_records = result.get("structured_facts", {}).get("records", [])
            if facts_records:
                fact_rows = []
                for rec in facts_records:

                    fact_rows.append({
                        "enterprise_name": enterprise_name,
                        "batch_no": batch_no,
                        "record_id": rec.get("record_id", ""),
                        "record_type": rec.get("record_type", ""),
                        "counterparty": _safe(rec.get("counterparty", rec.get("customer_name", rec.get("supplier_name", rec.get("partner_name", ""))))),
                        "counterparty_short": _safe(rec.get("customer_short_name", rec.get("supplier_short_name", rec.get("partner_short_name", "")))),
                        "counterparty_industry": _safe(rec.get("counterparty_industry", rec.get("customer_industry", ""))),
                        "project_name": _safe(rec.get("project_name", "")),
                        "bid_type": _safe(rec.get("bid_type", "")),
                        "bid_role": _safe(rec.get("role", "")),
                        "bid_date": _safe(rec.get("bid_date", rec.get("start_date", ""))),
                        "region": _safe(rec.get("region", "")),
                        "amount": _safe(rec.get("amount", "")),
                        "amount_unit": _safe(rec.get("amount_unit", "")),
                        "amount_raw": _safe(rec.get("amount_raw", "")),
                        "products": _safe(rec.get("products", rec.get("products_supplied", ""))),
                        "product_detail": _safe(rec.get("product_detail", "")),
                        "rel_type": _safe(rec.get("relationship_nature", "")),
                        "rel_desc": None,
                        "rel_project": None,
                        "industry_domain": None,
                        "inference_basis": None,
                        "evidence_type": _safe(rec.get("evidence_type", "")),
                        "evidence_text": _safe(rec.get("evidence_text", "")),
                        "source_platform": _safe(rec.get("source_platform", "")),
                        "source_url": _safe(rec.get("source_url", "")),
                        "confidence": rec.get("confidence", 0) or 0,
                        "is_current": rec.get("is_current", True),
                        "extract_time": _safe(execute_time),
                    })
                await insert_facts(fact_rows, table_config.get("fact_table") or "enterprise_fact")

            # 同样处理 fact_relationships
            fact_rels = result.get("fact_relationships", [])
            if fact_rels:
                rel_rows = []
                for i, rel in enumerate(fact_rels):
                    rel_rows.append({
                        "enterprise_name": enterprise_name,
                        "batch_no": batch_no,
                        "record_id": f"REL-{i+1:03d}",
                        "record_type": _map_rel_type(rel.get("关系类型", "")),
                        "counterparty": _safe(rel.get("关系客体", "")),
                        "counterparty_industry": _safe(rel.get("行业领域", "")),
                        "rel_type": _safe(rel.get("关系类型", "")),
                        "rel_desc": _safe(rel.get("关系描述", "")),
                        "rel_project": _safe(rel.get("关联项目", "")),
                        "rel_amount": _safe(rel.get("关联金额", "")),
                        "industry_domain": _safe(rel.get("行业领域", "")),
                        "inference_basis": _safe(rel.get("推断依据", "")),
                        "evidence_type": _safe(rel.get("数据来源", "")),
                        "confidence": rel.get("置信度", 0) or 0,
                        "extract_time": _safe(execute_time),
                    })
                await insert_facts(rel_rows, table_config.get("fact_table") or "enterprise_fact")

        except Exception as e:
            import traceback as _tb
            err_msg = f"数据库写入失败: {e}"
            print(f"[PipelineService] {err_msg}\n{_tb.format_exc()}")
            if task_id:
                await progress_manager.broadcast(task_id, {
                    "type": "progress",
                    "task_id": task_id,
                    "stage": "归档",
                    "step": "数据库写入失败",
                    "detail": err_msg,
                })


def _map_rel_type(rel_type: str) -> str:
    """映射中文关系类型到英文 record_type"""
    mapping = {
        "合作": "partnership",
        "客户": "customer",
        "供应商": "supplier",
        "投资": "investment",
        "下游行业": "downstream",
    }
    return mapping.get(rel_type, "other")


# 全局单例
pipeline_service = PipelineService()
