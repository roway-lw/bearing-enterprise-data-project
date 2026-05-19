"""SQLAlchemy ORM 模型 - 企业标签表 + 事实关系表"""
import os
from sqlalchemy import (
    Column, BigInteger, String, Text, Float, Integer, Boolean,
    DateTime, func, UniqueConstraint, Index
)
from sqlalchemy.dialects.mysql import JSON
from backend.database.connection import Base


ENTERPRISE_TAG_TABLE = os.getenv("ENTERPRISE_TAG_TABLE", "enterprise_tag")
ENTERPRISE_FACT_TABLE = os.getenv("ENTERPRISE_FACT_TABLE", "enterprise_fact")


class EnterpriseTag(Base):
    """企业标签信息表"""
    __tablename__ = ENTERPRISE_TAG_TABLE

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    enterprise_name = Column(String(200), nullable=False, comment="企业全称")
    batch_no = Column(String(64), nullable=False, comment="批次号")

    # 产品维度标签
    main_products = Column(JSON, comment="主营产品标签")
    core_products = Column(JSON, comment="核心产品标签")
    high_end_products = Column(JSON, comment="高端产品标签")
    product_keywords = Column(JSON, comment="产品关键词")
    product_desc = Column(String(500), comment="产品结构描述")

    # 工艺维度标签
    process_tags = Column(JSON, comment="工艺能力标签")
    core_process = Column(JSON, comment="核心工艺标签")
    manufacturing_tags = Column(JSON, comment="制造能力标签")
    special_process = Column(JSON, comment="特种工艺标签")
    process_desc = Column(String(500), comment="工艺能力描述")

    # 应用维度标签
    application_tags = Column(JSON, comment="应用领域标签")
    core_application = Column(JSON, comment="核心应用领域")
    downstream_industry = Column(JSON, comment="下游行业标签")
    application_desc = Column(String(1000), comment="应用领域描述")

    # 供应链维度标签
    supply_chain_tags = Column(JSON, comment="客户供应链标签")
    customer_type_tags = Column(JSON, comment="客户类型标签")
    supply_role_tags = Column(JSON, comment="供应链角色标签")
    supply_level_tags = Column(JSON, comment="供应链层级标签")
    supply_chain_desc = Column(String(1000), comment="客户供应链描述")

    # 三维标签详情（模块3原始标签体系，含 tag/source_field/confidence）
    product_detail_tags = Column(JSON, comment="产品标签详情")
    service_detail_tags = Column(JSON, comment="服务标签详情")
    capability_detail_tags = Column(JSON, comment="能力标签详情")

    # 扁平化标签汇总
    flat_tags = Column(JSON, comment="扁平化业务标签汇总")

    # 流水线元信息
    overall_confidence = Column(Float, comment="整体置信度 0~1")
    pipeline_status = Column(String(20), comment="流水线状态: success/partial/failed")
    crawl_status = Column(String(20), comment="采集状态")
    clean_status = Column(String(20), comment="清洗状态")
    tag_status = Column(String(20), comment="打标状态")
    total_tokens = Column(Integer, default=0, comment="Token总用量")
    total_time_seconds = Column(Float, default=0, comment="总耗时(秒)")

    # 结构化数据摘要
    registered_capital = Column(String(100), comment="注册资本")
    enterprise_short_name = Column(String(100), comment="企业简称")
    employee_scale = Column(String(50), comment="员工规模")

    # 时间戳
    execute_time = Column(DateTime, comment="流水线执行时间")
    created_at = Column(DateTime, server_default=func.now(), comment="入库时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        UniqueConstraint("enterprise_name", "batch_no", name="uk_enterprise_batch"),
        Index("idx_enterprise", "enterprise_name"),
        Index("idx_batch", "batch_no"),
        Index("idx_confidence", "overall_confidence"),
        Index("idx_execute_time", "execute_time"),
        Index("idx_pipeline_status", "pipeline_status"),
    )


class EnterpriseFact(Base):
    """企业事实关系数据表"""
    __tablename__ = ENTERPRISE_FACT_TABLE

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    enterprise_name = Column(String(200), nullable=False, comment="主体企业全称")
    batch_no = Column(String(64), nullable=False, comment="批次号")
    record_id = Column(String(20), nullable=False, comment="记录ID: CUS-001/BID-002等")
    record_type = Column(String(20), nullable=False, comment="记录类型: customer/bidding/supplier/investment/partnership")

    # 对方企业信息
    counterparty = Column(String(200), comment="对方企业名称")
    counterparty_short = Column(String(50), comment="对方企业简称")
    counterparty_industry = Column(String(50), comment="对方所属行业")

    # 招投标字段
    project_name = Column(String(300), comment="项目名称")
    bid_type = Column(String(20), comment="招标类型: 招标/中标/采购")
    bid_role = Column(String(20), comment="角色: 中标方/招标方/投标方")
    bid_date = Column(String(20), comment="招投标日期")
    region = Column(String(50), comment="地区")

    # 金额
    amount = Column(String(50), comment="金额数值")
    amount_unit = Column(String(10), comment="金额单位: 万元/亿元/元")
    amount_raw = Column(String(100), comment="原始金额文本")
    currency = Column(String(10), default="人民币", comment="币种")

    # 产品
    products = Column(String(500), comment="涉及产品")
    product_detail = Column(String(500), comment="产品详情/规格")

    # 关系字段（fact_relationships 通用）
    rel_type = Column(String(20), comment="关系类型: 合作/客户/供应商/投资/下游行业")
    rel_desc = Column(String(500), comment="关系描述")
    rel_project = Column(String(300), comment="关联项目")
    rel_amount = Column(String(100), comment="关联金额(原始文本)")
    industry_domain = Column(String(50), comment="行业领域")
    inference_basis = Column(String(500), comment="推断依据")

    # 证据与来源
    evidence_type = Column(String(30), comment="证据类型")
    evidence_text = Column(String(500), comment="证据原文")
    source_platform = Column(String(50), comment="来源平台")
    source_url = Column(String(500), comment="来源URL")
    source_snippet = Column(String(1000), comment="来源摘要")

    # 质量
    confidence = Column(Float, nullable=False, default=0, comment="置信度 0~1")
    is_current = Column(Boolean, default=True, comment="是否当前有效关系")

    # 时间戳
    extract_time = Column(DateTime, comment="提取时间")
    created_at = Column(DateTime, server_default=func.now(), comment="入库时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        UniqueConstraint("enterprise_name", "batch_no", "record_id", name="uk_record"),
        Index("idx_fact_enterprise", "enterprise_name"),
        Index("idx_fact_batch", "batch_no"),
        Index("idx_fact_type", "record_type"),
        Index("idx_fact_counterparty", "counterparty"),
        Index("idx_fact_confidence", "confidence"),
        Index("idx_fact_bid_date", "bid_date"),
        Index("idx_fact_rel_type", "rel_type"),
        Index("idx_fact_extract_time", "extract_time"),
    )
