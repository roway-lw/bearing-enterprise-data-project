"""企业查询 API — 基于 enterprise_tag + enterprise_fact 表"""
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from backend.schemas.enterprise import FactQueryParams
from backend.database.crud import (
    query_enterprises, get_enterprise_tag, get_enterprise_batches,
    query_facts
)
from backend.database.connection import is_initialized

router = APIRouter(prefix="/api/enterprises", tags=["企业查询"])

ENTERPRISE_SORT_FIELDS = {"execute_time", "overall_confidence", "enterprise_name", "batch_no", "total_tokens", "total_time_seconds"}
FACT_SORT_FIELDS = {"confidence", "bid_date", "record_type", "counterparty", "created_at", "extract_time"}
SORT_ORDERS = {"asc", "desc"}


def _validate_sort(sort_by: str, sort_order: str, allowed_fields: set[str]) -> tuple[str, str]:
    if sort_by not in allowed_fields:
        raise HTTPException(400, f"不支持的排序字段: {sort_by}")
    if sort_order not in SORT_ORDERS:
        raise HTTPException(400, f"不支持的排序方向: {sort_order}")
    return sort_by, sort_order


@router.get("")
async def list_enterprises(
    keyword: str = Query(None, description="企业名称模糊搜索"),
    sort_by: str = Query("execute_time", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """企业列表查询"""
    if not is_initialized():
        raise HTTPException(400, "数据库未初始化，请先在数据库导入中点击测试连接")
    sort_by, sort_order = _validate_sort(sort_by, sort_order, ENTERPRISE_SORT_FIELDS)
    try:
        return await query_enterprises(keyword, sort_by, sort_order, page, page_size)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(500, f"企业列表查询失败: {str(e)}")


@router.get("/batches/{name}")
async def list_batches(name: str):
    """获取企业所有历史批次"""
    if not is_initialized():
        raise HTTPException(400, "数据库未初始化")
    batches = await get_enterprise_batches(name)
    if not batches:
        raise HTTPException(404, f"未找到企业: {name}")
    return batches


@router.get("/{name}")
async def get_enterprise(name: str, batch_no: str = Query(None)):
    """企业标签详情"""
    if not is_initialized():
        raise HTTPException(400, "数据库未初始化")
    data = await get_enterprise_tag(name, batch_no)
    if not data:
        raise HTTPException(404, f"未找到企业: {name}")
    return data


@router.get("/{name}/facts")
async def get_facts(
    name: str,
    batch_no: str = Query(None),
    record_type: str = Query(None),
    sort_by: str = Query("confidence"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """企业事实关系"""
    if not is_initialized():
        raise HTTPException(400, "数据库未初始化")
    sort_by, sort_order = _validate_sort(sort_by, sort_order, FACT_SORT_FIELDS)
    try:
        return await query_facts(name, batch_no, record_type, sort_by, sort_order, page, page_size)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(500, f"企业事实关系查询失败: {str(e)}")
