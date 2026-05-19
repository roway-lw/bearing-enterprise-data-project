"""数据库 CRUD 操作"""
import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, func, desc, asc, Column, BigInteger, String, Float, Integer, Boolean, DateTime
from sqlalchemy.dialects.mysql import JSON
from backend.database.connection import Base, create_tables_for_models
import backend.database.connection as _conn
from backend.database.models import EnterpriseTag, EnterpriseFact


# ============================================================
# 动态输出表支持
# ============================================================

_dynamic_tag_models = {}
_dynamic_fact_models = {}


def _safe_table_name(table_name: str, default: str) -> str:
    import re
    name = table_name or default
    if not re.match(r"^[\w\u4e00-\u9fa5]+$", name):
        raise ValueError(f"非法表名: {name}")
    return name


def get_tag_model(table_name: str = None):
    table_name = _safe_table_name(table_name, EnterpriseTag.__tablename__)
    if table_name == EnterpriseTag.__tablename__:
        return EnterpriseTag
    if table_name not in _dynamic_tag_models:
        _dynamic_tag_models[table_name] = type(
            f"EnterpriseTag_{table_name}",
            (Base,),
            {
                "__tablename__": table_name,
                "__table_args__": {"extend_existing": True},
                "id": Column(BigInteger, primary_key=True, autoincrement=True),
                "enterprise_name": Column(String(200), nullable=False),
                "batch_no": Column(String(64), nullable=False),
                "main_products": Column(JSON),
                "core_products": Column(JSON),
                "high_end_products": Column(JSON),
                "product_keywords": Column(JSON),
                "product_desc": Column(String(500)),
                "process_tags": Column(JSON),
                "core_process": Column(JSON),
                "manufacturing_tags": Column(JSON),
                "special_process": Column(JSON),
                "process_desc": Column(String(500)),
                "application_tags": Column(JSON),
                "core_application": Column(JSON),
                "downstream_industry": Column(JSON),
                "application_desc": Column(String(1000)),
                "supply_chain_tags": Column(JSON),
                "customer_type_tags": Column(JSON),
                "supply_role_tags": Column(JSON),
                "supply_level_tags": Column(JSON),
                "supply_chain_desc": Column(String(1000)),
                "product_detail_tags": Column(JSON),
                "service_detail_tags": Column(JSON),
                "capability_detail_tags": Column(JSON),
                "flat_tags": Column(JSON),
                "overall_confidence": Column(Float),
                "pipeline_status": Column(String(20)),
                "crawl_status": Column(String(20)),
                "clean_status": Column(String(20)),
                "tag_status": Column(String(20)),
                "total_tokens": Column(Integer, default=0),
                "total_time_seconds": Column(Float, default=0),
                "registered_capital": Column(String(100)),
                "enterprise_short_name": Column(String(100)),
                "employee_scale": Column(String(50)),
                "execute_time": Column(DateTime),
                "created_at": Column(DateTime),
                "updated_at": Column(DateTime),
            },
        )
    return _dynamic_tag_models[table_name]


def get_fact_model(table_name: str = None):
    table_name = _safe_table_name(table_name, EnterpriseFact.__tablename__)
    if table_name == EnterpriseFact.__tablename__:
        return EnterpriseFact
    if table_name not in _dynamic_fact_models:
        _dynamic_fact_models[table_name] = type(
            f"EnterpriseFact_{table_name}",
            (Base,),
            {
                "__tablename__": table_name,
                "__table_args__": {"extend_existing": True},
                "id": Column(BigInteger, primary_key=True, autoincrement=True),
                "enterprise_name": Column(String(200), nullable=False),
                "batch_no": Column(String(64), nullable=False),
                "record_id": Column(String(20), nullable=False),
                "record_type": Column(String(20), nullable=False),
                "counterparty": Column(String(200)),
                "counterparty_short": Column(String(50)),
                "counterparty_industry": Column(String(50)),
                "project_name": Column(String(300)),
                "bid_type": Column(String(20)),
                "bid_role": Column(String(20)),
                "bid_date": Column(String(20)),
                "region": Column(String(50)),
                "amount": Column(String(50)),
                "amount_unit": Column(String(10)),
                "amount_raw": Column(String(100)),
                "currency": Column(String(10), default="人民币"),
                "products": Column(String(500)),
                "product_detail": Column(String(500)),
                "rel_type": Column(String(20)),
                "rel_desc": Column(String(500)),
                "rel_project": Column(String(300)),
                "rel_amount": Column(String(100)),
                "industry_domain": Column(String(50)),
                "inference_basis": Column(String(500)),
                "evidence_type": Column(String(30)),
                "evidence_text": Column(String(500)),
                "source_platform": Column(String(50)),
                "source_url": Column(String(500)),
                "source_snippet": Column(String(1000)),
                "confidence": Column(Float, nullable=False, default=0),
                "is_current": Column(Boolean, default=True),
                "extract_time": Column(DateTime),
                "created_at": Column(DateTime),
                "updated_at": Column(DateTime),
            },
        )
    return _dynamic_fact_models[table_name]


# ============================================================
# enterprise_tag CRUD
# ============================================================

async def upsert_enterprise_tag(data: dict, table_name: str = None) -> int:
    """插入或更新企业标签记录，返回 ID"""
    TagModel = get_tag_model(table_name)
    await create_tables_for_models([TagModel])
    async with _conn.async_session_factory() as session:
        # 检查是否已存在
        stmt = select(TagModel).where(
            TagModel.enterprise_name == data["enterprise_name"],
            TagModel.batch_no == data["batch_no"],
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # 更新
            for key, value in data.items():
                if key not in ("id", "created_at"):
                    setattr(existing, key, value)
            await session.commit()
            return existing.id
        else:
            # 插入
            row = TagModel(**data)
            session.add(row)
            await session.commit()
            return row.id


async def query_enterprises(
    keyword: str = None,
    sort_by: str = "execute_time",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询企业列表"""
    async with _conn.async_session_factory() as session:
        # 基础查询：每个企业取最新批次
        subq = select(
            EnterpriseTag.enterprise_name,
            func.max(EnterpriseTag.batch_no).label("latest_batch")
        ).group_by(EnterpriseTag.enterprise_name)
        if keyword:
            subq = subq.where(EnterpriseTag.enterprise_name.like(f"%{keyword}%"))
        subq = subq.subquery()

        stmt = select(EnterpriseTag).join(
            subq,
            (EnterpriseTag.enterprise_name == subq.c.enterprise_name) &
            (EnterpriseTag.batch_no == subq.c.latest_batch)
        )

        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(count_stmt)).scalar()

        # 排序
        order_col = getattr(EnterpriseTag, sort_by, EnterpriseTag.execute_time)
        if sort_order == "desc":
            stmt = stmt.order_by(desc(order_col))
        else:
            stmt = stmt.order_by(asc(order_col))

        # 分页
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
        rows = result.scalars().all()

        return {
            "enterprises": [_tag_to_dict(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


async def get_enterprise_tag(name: str, batch_no: str = None) -> Optional[dict]:
    """获取企业标签详情"""
    async with _conn.async_session_factory() as session:
        stmt = select(EnterpriseTag).where(EnterpriseTag.enterprise_name == name)
        if batch_no:
            stmt = stmt.where(EnterpriseTag.batch_no == batch_no)
        else:
            stmt = stmt.order_by(desc(EnterpriseTag.batch_no))
        stmt = stmt.limit(1)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return _tag_to_dict(row) if row else None


async def get_enterprise_batches(name: str) -> List[dict]:
    """获取企业所有批次"""
    async with _conn.async_session_factory() as session:
        stmt = select(EnterpriseTag).where(
            EnterpriseTag.enterprise_name == name
        ).order_by(desc(EnterpriseTag.batch_no))
        result = await session.execute(stmt)
        return [_tag_to_dict(row) for row in result.scalars().all()]


# ============================================================
# enterprise_fact CRUD
# ============================================================

async def insert_facts(facts: List[dict], table_name: str = None):
    """批量插入事实关系记录"""
    FactModel = get_fact_model(table_name)
    await create_tables_for_models([FactModel])
    async with _conn.async_session_factory() as session:
        for fact_data in facts:
            row = FactModel(**fact_data)
            session.add(row)
        await session.commit()


async def query_facts(
    enterprise_name: str,
    batch_no: str = None,
    record_type: str = None,
    sort_by: str = "confidence",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """分页查询企业事实关系"""
    async with _conn.async_session_factory() as session:
        stmt = select(EnterpriseFact).where(
            EnterpriseFact.enterprise_name == enterprise_name
        )
        if batch_no:
            stmt = stmt.where(EnterpriseFact.batch_no == batch_no)
        if record_type:
            stmt = stmt.where(EnterpriseFact.record_type == record_type)

        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(count_stmt)).scalar()

        # 汇总
        summary_stmt = select(
            EnterpriseFact.record_type,
            func.count().label("count")
        ).where(EnterpriseFact.enterprise_name == enterprise_name)
        if batch_no:
            summary_stmt = summary_stmt.where(EnterpriseFact.batch_no == batch_no)
        summary_stmt = summary_stmt.group_by(EnterpriseFact.record_type)
        summary_result = await session.execute(summary_stmt)
        summary = {row[0]: row[1] for row in summary_result.all()}

        # 排序
        order_col = getattr(EnterpriseFact, sort_by, EnterpriseFact.confidence)
        if sort_order == "desc":
            stmt = stmt.order_by(desc(order_col))
        else:
            stmt = stmt.order_by(asc(order_col))

        # 分页
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
        rows = result.scalars().all()

        return {
            "facts": [_fact_to_dict(row) for row in rows],
            "summary": summary,
            "total": total,
            "page": page,
            "page_size": page_size,
        }


# ============================================================
# 辅助函数
# ============================================================

def _tag_to_dict(row: EnterpriseTag) -> dict:
    """ORM 转字典，JSON 字段自动解析"""
    d = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if val is None:
            d[col.name] = None
        elif col.name in (
            "main_products", "core_products", "high_end_products", "product_keywords",
            "process_tags", "core_process", "manufacturing_tags", "special_process",
            "application_tags", "core_application", "downstream_industry",
            "supply_chain_tags", "customer_type_tags", "supply_role_tags", "supply_level_tags",
            "product_detail_tags", "service_detail_tags", "capability_detail_tags",
            "flat_tags",
        ):
            # JSON 字段：如果是字符串则解析
            if isinstance(val, str):
                try:
                    d[col.name] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    d[col.name] = val
            else:
                d[col.name] = val
        elif isinstance(val, datetime):
            d[col.name] = val.strftime("%Y-%m-%d %H:%M:%S")
        else:
            d[col.name] = val
    return d


def _fact_to_dict(row: EnterpriseFact) -> dict:
    d = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if isinstance(val, datetime):
            d[col.name] = val.strftime("%Y-%m-%d %H:%M:%S")
        else:
            d[col.name] = val
    return d
