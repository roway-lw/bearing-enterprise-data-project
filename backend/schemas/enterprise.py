"""企业数据 Pydantic 模型"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class EnterpriseListItem(BaseModel):
    enterprise_name: str
    batch_no: str = ""
    overall_confidence: Optional[float] = None
    pipeline_status: Optional[str] = None
    execute_time: Optional[str] = None
    total_tokens: Optional[int] = None
    total_time_seconds: Optional[float] = None
    main_products: Optional[List[str]] = None
    application_tags: Optional[List[str]] = None
    fact_count: int = 0


class EnterpriseListResponse(BaseModel):
    enterprises: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


class FactQueryParams(BaseModel):
    record_type: Optional[str] = None
    sort_by: str = "confidence"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 50


class FactResponse(BaseModel):
    facts: List[Dict[str, Any]]
    summary: Dict[str, int]
    total: int
    page: int
    page_size: int


class DbConnectionTest(BaseModel):
    host: str
    port: int = 3306
    user: str
    password: str = ""
    database: str = ""


class DbQueryNames(BaseModel):
    table_name: str
    name_column: str
    where_clause: Optional[str] = None
    limit: Optional[int] = None


class DbInitRequest(DbConnectionTest):
    tag_table: str = "enterprise_tag"
    fact_table: str = "enterprise_fact"
