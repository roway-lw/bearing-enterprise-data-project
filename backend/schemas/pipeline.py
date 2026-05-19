"""流水线相关 Pydantic 模型"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class OutputConfig(BaseModel):
    file_output: bool = True
    db_output: bool = False
    tag_table: str = "enterprise_tag"
    fact_table: str = "enterprise_fact"


class PipelineRunRequest(BaseModel):
    enterprise_names: List[str]
    output_config: OutputConfig = OutputConfig()


class PipelineRunResponse(BaseModel):
    task_id: str
    enterprise_count: int
    status: str = "queued"


class TaskSummary(BaseModel):
    task_id: str
    enterprise_count: int
    status: str
    completed_count: int = 0
    failed_count: int = 0
    created_at: Optional[str] = None


class EnterpriseResult(BaseModel):
    enterprise_name: str
    status: str
    confidence: float = 0
    elapsed_seconds: float = 0
    token_total: int = 0
    tag_summary: List[str] = []
    fact_count: int = 0


class ProgressMessage(BaseModel):
    type: str = "progress"
    enterprise_name: str = ""
    progress: int = 0
    stage: str = ""
    step: str = ""
    detail: str = ""
    elapsed_seconds: float = 0
    data_sources: List[Dict[str, Any]] = []
    token_usage: Dict[str, Any] = {}
