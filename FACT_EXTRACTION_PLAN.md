# 企业事实性商业关系数据结构化提取方案

## 一、目标

从采集的原始网页文本中，深度提取**结构化的事实性商业关系记录**，每条记录包含完整的交易/合作/投资要素（对方企业、金额、日期、项目名、产品、来源等），输出为独立的结构化 JSON 文件。

与现有 `FactRelationshipExtractor` 的区别：

| 维度 | 现有 FactRelationshipExtractor | 本方案 FactDataExtractor |
|------|------|------|
| 粒度 | 关系级（谁和谁有关系） | 记录级（具体哪次交易/合作） |
| 招投标 | 提取1条摘要文本 | 拆分为N条独立中标/采购记录 |
| 字段 | 10个通用字段 | 按类型定制不同字段集（15-20个） |
| 金额 | 上下文50字内正则匹配 | 整句/整段解析，区分亿/万/元 |
| 日期 | 不提取 | 提取并标准化为 yyyy-MM-dd |
| 项目名 | 不提取 | 提取项目名称 |
| 来源 | 仅标注"招投标信息" | 记录来源平台+来源URL |
| 输出 | 嵌入pipeline JSON | 独立 facts JSON + Excel |

---

## 二、数据Schema设计

### 2.1 统一外层结构

```json
{
  "enterprise_name": "洛阳LYC轴承有限公司",
  "extract_time": "2026-05-17 15:30:00",
  "summary": {
    "total_records": 23,
    "bidding_records": 8,
    "customer_records": 5,
    "supplier_records": 3,
    "investment_records": 2,
    "partnership_records": 3,
    "product_supply_records": 2
  },
  "records": [...],
  "source_coverage": {
    "official_website": true,
    "business_info": true,
    "bidding_info": true,
    "patent_info": false
  },
  "extraction_confidence": 0.88
}
```

### 2.2 招投标记录（bidding_records）

```json
{
  "record_type": "bidding",
  "record_id": "BID-001",
  "project_name": "XX风电设备厂2024年轴承采购项目",
  "bid_type": "中标",
  "role": "中标方",
  "counterparty": "XX风电设备厂",
  "counterparty_industry": "风力发电",
  "amount": "3200",
  "amount_unit": "万元",
  "amount_raw": "3,200万元",
  "currency": "人民币",
  "bid_date": "2024-03-15",
  "announce_date": "",
  "products": "轴承",
  "product_detail": "风电主轴轴承",
  "region": "河北省",
  "source_platform": "中国政府采购网",
  "source_url": "http://search.ccgp.gov.cn/...",
  "source_snippet": "2024年3月，洛阳LYC轴承有限公司中标XX风电设备厂轴承采购项目，金额3,200万元",
  "confidence": 0.92
}
```

### 2.3 客户关系记录（customer_records）

```json
{
  "record_type": "customer",
  "record_id": "CUS-001",
  "customer_name": "一汽解放汽车有限公司",
  "customer_short_name": "一汽",
  "customer_industry": "汽车工业",
  "relationship_nature": "供应商",
  "products_supplied": "深沟球轴承、圆锥滚子轴承",
  "evidence_type": "官网提及",
  "evidence_text": "公司为一汽解放提供配套轴承产品",
  "contract_amount": "",
  "start_date": "",
  "is_current": true,
  "source_platform": "企业官网",
  "source_url": "https://www.lycbearing.com/partners",
  "confidence": 0.85
}
```

### 2.4 供应商关系记录（supplier_records）

```json
{
  "record_type": "supplier",
  "record_id": "SUP-001",
  "supplier_name": "NSK中国",
  "supplier_industry": "轴承制造",
  "relationship_nature": "技术合作",
  "products_supplied": "精密轴承技术、磨削工艺",
  "evidence_type": "官网提及",
  "evidence_text": "与NSK开展精密轴承技术合作",
  "source_platform": "企业官网",
  "source_url": "https://www.lycbearing.com/about",
  "confidence": 0.82
}
```

### 2.5 投资项目记录（investment_records）

```json
{
  "record_type": "investment",
  "record_id": "INV-001",
  "project_name": "精密轴承生产线扩建项目",
  "investment_type": "扩建",
  "amount": "1.5",
  "amount_unit": "亿元",
  "amount_raw": "1.5亿元",
  "start_date": "2023-06",
  "completion_date": "",
  "project_content": "新增精密轴承生产线3条，设计产能200万套/年",
  "products": "精密轴承",
  "region": "河南省洛阳市",
  "source_platform": "企业官网",
  "source_url": "https://www.lycbearing.com/news/xxx",
  "source_snippet": "2023年新增精密轴承生产线项目，总投资1.5亿元",
  "confidence": 0.90
}
```

### 2.6 合作关系记录（partnership_records）

```json
{
  "record_type": "partnership",
  "record_id": "PTN-001",
  "partner_name": "洛阳轴承研究所",
  "partner_industry": "科研院所",
  "partnership_type": "产学研合作",
  "cooperation_content": "联合研发高速铁路轴承技术",
  "evidence_text": "与洛阳轴承研究所联合开展高铁轴承技术攻关",
  "start_date": "",
  "source_platform": "企业官网",
  "source_url": "https://www.lycbearing.com/about",
  "confidence": 0.88
}
```

### 2.7 产品供货记录（product_supply_records）

从招投标/官网中提取的具体产品供应关系：

```json
{
  "record_type": "product_supply",
  "record_id": "PSR-001",
  "buyer": "中车株洲电力机车研究所",
  "buyer_industry": "轨道交通",
  "product_category": "轴承",
  "product_detail": "高铁轴箱轴承",
  "spec": "内径100mm，精度P4",
  "quantity": "",
  "amount": "",
  "amount_unit": "",
  "supply_type": "配套",
  "evidence_type": "招投标",
  "source_platform": "全国公共资源交易平台",
  "source_url": "https://deal.ggzy.gov.cn/...",
  "confidence": 0.85
}
```

---

## 三、提取策略设计

### 3.1 整体架构

```
                    原始爬虫数据 (raw_crawl_data)
                            │
                            ▼
                ┌───────────────────────┐
                │  FactDataExtractor    │
                │                       │
                │  1. 文本分段器         │
                │     └─ 按来源URL分段  │
                │  2. 逐段分类路由       │
                │     ├─ 招投标段落     │──→ BiddingRecordParser
                │     ├─ 官网页面       │──→ WebsiteRecordParser
                │     ├─ 工商信息       │──→ BusinessInfoParser
                │     └─ 专利信息       │──→ PatentRecordParser
                │  3. 记录合并去重       │
                │  4. 置信度评分         │
                │  5. 标准化输出         │
                └───────────────────────┘
                            │
                            ▼
              {企业名}_facts.json + {企业名}_facts.xlsx
```

### 3.2 核心类：FactDataExtractor

```python
class FactDataExtractor:
    """企业事实性商业关系数据结构化提取器"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir
        self.parsers = {
            "bidding_info": BiddingRecordParser(),
            "official_website": WebsiteRecordParser(),
            "business_info": BusinessInfoParser(),
            "patent_info": PatentRecordParser(),
        }

    def extract(self, enterprise_name: str,
                raw_crawl_data: dict,
                structured_data: dict) -> dict:
        """主提取入口"""
        all_records = []

        # Step 1: 按来源URL分段原始文本
        source_segments = self._segment_by_source(raw_crawl_data)

        # Step 2: 逐段路由到专用解析器
        for segment in source_segments:
            parser = self._route_parser(segment)
            if parser:
                records = parser.parse(enterprise_name, segment, structured_data)
                all_records.extend(records)

        # Step 3: 跨来源合并去重
        all_records = self._deduplicate_records(all_records)

        # Step 4: 置信度评分
        for record in all_records:
            record["confidence"] = self._score_confidence(record)

        # Step 5: 生成ID和排序
        self._assign_ids(all_records)
        all_records.sort(key=lambda r: r.get("confidence", 0), reverse=True)

        return self._build_output(enterprise_name, all_records, raw_crawl_data)
```

### 3.3 文本分段器

关键改进：不再把 all_content 当作一块文本处理，而是按**来源URL**分段，每段携带来源平台信息。

```python
def _segment_by_source(self, raw_crawl_data: dict) -> List[dict]:
    """按来源URL分段原始文本

    将 raw_content 中的文本按 【来源: xxx】 标记拆分，
    每段保留来源URL和平台分类信息。
    """
    segments = []
    raw_content = raw_crawl_data.get("raw_content", {})

    for content_type in ["official_website", "business_info",
                         "bidding_info", "patent_info"]:
        text = raw_content.get(content_type, "")
        if not text:
            continue

        # 解析 【来源: URL】 标记，拆分为多个子段
        sub_segments = self._split_by_source_tags(text, content_type)
        segments.extend(sub_segments)

    return segments
```

### 3.4 招投标记录解析器（最核心）

```python
class BiddingRecordParser:
    """招投标事实记录解析器

    核心能力：从招投标相关文本中拆分出每一条独立的招投标记录，
    并提取项目名、金额、日期、对方企业、产品等字段。
    """

    # 招投标句子边界关键词（用于拆分多条记录）
    RECORD_BOUNDARIES = [
        r'\d{4}\s*年',                    # 年份开头
        r'(?:中标|成交|招标|采购)公告',      # 公告标题
        r'项目名称[：:]',                    # 项目名标记
        r'中标(?:供应商|单位)[：:]',          # 中标方标记
        r'(?:成交|中标)金额[：:]',           # 金额标记
    ]

    def parse(self, enterprise_name: str,
              segment: dict, structured_data: dict) -> List[dict]:
        text = segment.get("text", "")
        source_url = segment.get("source_url", "")
        source_platform = segment.get("source_platform", "")

        if not text:
            return []

        # Step 1: 拆分为独立的事实句子/段落
        sentences = self._split_into_factual_sentences(text)

        # Step 2: 对每个句子尝试提取结构化记录
        records = []
        for sentence in sentences:
            record = self._parse_single_sentence(
                enterprise_name, sentence, source_url, source_platform
            )
            if record:
                records.append(record)

        return records

    def _split_into_factual_sentences(self, text: str) -> List[str]:
        """将文本拆分为包含招投标事实的独立句子"""
        factual_sentences = []
        for sentence in re.split(r'[。；\n]', text):
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            # 必须包含招投标关键词
            bid_keywords = ["中标", "成交", "招标", "采购", "竞标", "投标",
                           "采购项目", "中标公告", "成交公告"]
            if not any(kw in sentence for kw in bid_keywords):
                continue
            factual_sentences.append(sentence)
        return factual_sentences

    def _parse_single_sentence(self, enterprise_name: str,
                                sentence: str,
                                source_url: str,
                                source_platform: str) -> Optional[dict]:
        """从单个句子中提取结构化招投标记录"""
        record = {
            "record_type": "bidding",
            "source_url": source_url,
            "source_platform": source_platform,
            "source_snippet": sentence[:200],
        }

        # 提取项目名
        record["project_name"] = self._extract_project_name(sentence)

        # 提取招投标类型
        record["bid_type"] = self._extract_bid_type(sentence)

        # 提取对方企业
        counterparty = self._extract_counterparty(enterprise_name, sentence)
        record["counterparty"] = counterparty

        # 提取金额（多策略）
        amount_info = self._extract_amount(sentence)
        record.update(amount_info)

        # 提取日期
        record["bid_date"] = self._extract_date(sentence)

        # 提取产品
        record["products"] = self._extract_products(sentence)

        # 提取地区
        record["region"] = self._extract_region(sentence)

        # 判断角色（中标方 vs 招标方）
        record["role"] = self._infer_role(enterprise_name, sentence)

        # 最少需要：金额或对方企业或项目名
        has_content = (record.get("amount") or record.get("counterparty")
                       or record.get("project_name"))
        if not has_content:
            return None

        return record
```

#### 关键提取方法实现

```python
# ---- 项目名提取 ----
def _extract_project_name(self, sentence: str) -> str:
    patterns = [
        r'项目名称[：:]\s*([^\n,，。；;]{4,60})',
        r'(?:中标|成交)\s*[项目]*(.{4,40}?)(?:项目)',
        r'((?:\w{2,20})(?:采购|招标|项目)).{0,5}(?:金额|中标|成交)',
        r'(\w{2,15}(?:采购项目|招标项目|项目))',
    ]
    for p in patterns:
        m = re.search(p, sentence)
        if m:
            name = m.group(1).strip()
            # 清洗噪声
            name = re.sub(r'^[的为于在]', '', name)
            if 4 <= len(name) <= 60:
                return name
    return ""

# ---- 金额提取（多策略，区分亿/万） ----
def _extract_amount(self, sentence: str) -> dict:
    result = {"amount": "", "amount_unit": "", "amount_raw": "", "currency": "人民币"}

    # 策略1: "金额X万元" 格式
    m = re.search(r'(?:金额|总额|成交金额|中标金额|合同金额)[：:为]?\s*([\d,.]+)\s*万(元|人民币)', sentence)
    if m:
        result["amount"] = m.group(1).replace(",", "")
        result["amount_unit"] = "万元"
        result["amount_raw"] = m.group(0)
        return result

    # 策略2: "X.X亿元" 格式
    m = re.search(r'([\d,.]+)\s*亿(元|人民币)', sentence)
    if m:
        result["amount"] = m.group(1).replace(",", "")
        result["amount_unit"] = "亿元"
        result["amount_raw"] = m.group(0)
        return result

    # 策略3: "X万元" 格式（无金额前缀，需上下文验证）
    m = re.search(r'([\d,.]+)\s*万(元|人民币)', sentence)
    if m and any(kw in sentence for kw in ["中标", "成交", "采购", "金额", "合同"]):
        result["amount"] = m.group(1).replace(",", "")
        result["amount_unit"] = "万元"
        result["amount_raw"] = m.group(0)
        return result

    # 策略4: 纯数字+元
    m = re.search(r'(?:金额|总价|合计)[：:为]?\s*([\d,.]+)\s*元', sentence)
    if m:
        val = float(m.group(1).replace(",", ""))
        if val >= 10000:
            result["amount"] = f"{val/10000:.1f}"
            result["amount_unit"] = "万元"
        else:
            result["amount"] = m.group(1).replace(",", "")
            result["amount_unit"] = "元"
        result["amount_raw"] = m.group(0)
        return result

    return result

# ---- 日期提取 ----
def _extract_date(self, sentence: str) -> str:
    patterns = [
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
        r'(\d{4})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})',
        r'(\d{4})\s*年\s*(\d{1,2})\s*月',
    ]
    for p in patterns:
        m = re.search(p, sentence)
        if m:
            groups = m.groups()
            if len(groups) >= 3:
                return f"{groups[0]}-{int(groups[1]):02d}-{int(groups[2]):02d}"
            elif len(groups) >= 2:
                return f"{groups[0]}-{int(groups[1]):02d}"
    return ""

# ---- 对方企业提取 ----
def _extract_counterparty(self, enterprise_name: str, sentence: str) -> str:
    # 使用 FactRelationshipExtractor 的企业名正则
    company_patterns = [
        r'([\u4e00-\u9fa5]+(?:集团|股份|科技|技术|工业|装备|机械|电气|汽车|轴承|精密|重工|动力|机电)(?:有限)?(?:责任)?(?:公司|厂))',
        r'([\u4e00-\u9fa5]{2,8}(?:有限公司|集团))',
    ]
    for p in company_patterns:
        for m in re.finditer(p, sentence):
            name = m.group(1).strip()
            if name == enterprise_name or enterprise_name in name:
                continue
            if len(name) >= 4:
                return name
    return ""

# ---- 招投标类型 ----
def _extract_bid_type(self, sentence: str) -> str:
    if "中标" in sentence:
        return "中标"
    elif "成交" in sentence:
        return "成交"
    elif "招标" in sentence:
        return "招标"
    elif "采购" in sentence:
        return "采购"
    elif "竞标" in sentence:
        return "竞标"
    return "招标"

# ---- 角色推断 ----
def _infer_role(self, enterprise_name: str, sentence: str) -> str:
    """推断主体企业在本次招投标中的角色"""
    # "XX公司中标" → 中标方
    if re.search(rf'{re.escape(enterprise_name)}.*?中标', sentence):
        return "中标方"
    # "中标供应商：XX公司" → 中标方
    if re.search(rf'中标.*?{re.escape(enterprise_name)}', sentence):
        return "中标方"
    # "XX公司采购/招标" → 招标方
    if re.search(rf'{re.escape(enterprise_name)}.*?(?:采购|招标)', sentence):
        return "招标方"
    return "中标方"  # 默认（大多数情况下，被采集企业是中标方）
```

### 3.5 官网页面解析器

```python
class WebsiteRecordParser:
    """从企业官网内容中提取客户/供应商/合作伙伴记录"""

    def parse(self, enterprise_name: str,
              segment: dict, structured_data: dict) -> List[dict]:
        text = segment.get("text", "")
        source_url = segment.get("source_url", "")
        records = []

        # 提取客户关系
        customer_records = self._extract_customer_records(
            enterprise_name, text, source_url, structured_data
        )
        records.extend(customer_records)

        # 提取供应商关系
        supplier_records = self._extract_supplier_records(
            enterprise_name, text, source_url, structured_data
        )
        records.extend(supplier_records)

        # 提取合作关系
        partner_records = self._extract_partner_records(
            enterprise_name, text, source_url, structured_data
        )
        records.extend(partner_records)

        # 提取投资项目
        invest_records = self._extract_investment_records(
            enterprise_name, text, source_url
        )
        records.extend(invest_records)

        return records
```

### 3.6 去重策略

```python
def _deduplicate_records(self, records: List[dict]) -> List[dict]:
    """跨来源去重

    去重规则：
    1. 招投标：相同(对方企业+项目名)视为重复，保留金额更完整的
    2. 客户关系：相同(对方企业+产品)视为重复，保留证据更丰富的
    3. 投资项目：相同(项目名)视为重复，保留金额更完整的
    """
    seen = {}

    for record in records:
        rtype = record.get("record_type", "")

        if rtype == "bidding":
            key = (rtype,
                   record.get("counterparty", ""),
                   record.get("project_name", "")[:30])
        elif rtype == "customer":
            key = (rtype,
                   record.get("customer_name", ""),
                   record.get("products_supplied", "")[:20])
        elif rtype == "supplier":
            key = (rtype,
                   record.get("supplier_name", ""))
        elif rtype == "investment":
            key = (rtype,
                   record.get("project_name", "")[:30])
        elif rtype == "partnership":
            key = (rtype,
                   record.get("partner_name", ""))
        else:
            key = (rtype, record.get("counterparty", ""),
                   record.get("source_snippet", "")[:50])

        if key in seen:
            existing = seen[key]
            # 保留字段更完整的记录
            if self._record_completeness(record) > self._record_completeness(existing):
                seen[key] = record
        else:
            seen[key] = record

    return list(seen.values())

def _record_completeness(self, record: dict) -> int:
    """计算记录完整度（非空字段数）"""
    core_fields = {
        "bidding": ["project_name", "counterparty", "amount", "bid_date", "products"],
        "customer": ["customer_name", "products_supplied", "evidence_text"],
        "supplier": ["supplier_name", "products_supplied", "evidence_text"],
        "investment": ["project_name", "amount", "start_date"],
        "partnership": ["partner_name", "cooperation_content"],
    }
    rtype = record.get("record_type", "")
    fields = core_fields.get(rtype, [])
    return sum(1 for f in fields if record.get(f))
```

### 3.7 置信度评分

```python
def _score_confidence(self, record: dict) -> float:
    """基于字段完整度和来源可信度计算置信度"""
    rtype = record.get("record_type", "")
    base = 0.60

    # 来源可信度加分
    source_platform = record.get("source_platform", "")
    platform_bonus = {
        "中国政府采购网": 0.15,
        "全国公共资源交易平台": 0.15,
        "中国招标投标公共服务平台": 0.12,
        "国家企业信用公示": 0.10,
        "天眼查": 0.08,
        "企查查": 0.08,
        "企业官网": 0.05,
    }
    for platform, bonus in platform_bonus.items():
        if platform in source_platform:
            base += bonus
            break

    # 字段完整度加分
    if rtype == "bidding":
        if record.get("amount"): base += 0.05
        if record.get("counterparty"): base += 0.05
        if record.get("project_name"): base += 0.03
        if record.get("bid_date"): base += 0.03
        if record.get("products"): base += 0.02
    elif rtype == "customer":
        if record.get("customer_name"): base += 0.08
        if record.get("products_supplied"): base += 0.05
        if record.get("evidence_text"): base += 0.05
    elif rtype == "investment":
        if record.get("amount"): base += 0.08
        if record.get("project_name"): base += 0.05
        if record.get("start_date"): base += 0.03

    return round(min(0.98, base), 2)
```

---

## 四、集成到Pipeline

### 4.1 在Pipeline中的位置

```
Step1 采集(raw) → Step2 清洗(structured) → Step3 标签(tags)
                                                 │
                                                 ▼
                                          Step4 事实数据提取(facts) ← 新增
                                                 │
                                                 ▼
                                          Step5 扁平化标签 + 归档
```

### 4.2 Pipeline代码改动

```python
# pipeline.py 的 run_single 方法中新增 Step 4

# ==================== Step 4: 事实数据提取 ====================
try:
    self.progress.report(95, "调度", "事实数据提取",
                         "提取招投标/客户/供应商/投资结构化记录")

    from common.fact_extractor import FactDataExtractor
    fact_extractor = FactDataExtractor(output_dir=self.output_dir)
    facts_result = fact_extractor.extract(
        enterprise_name, raw_crawl_data, structured_data
    )

    # 独立保存事实数据文件
    facts_path = self._save_stage_file(
        facts_result, safe_name, archive_timestamp, "facts"
    )
    self.output_files["facts"] = facts_path

    # 同时保留在pipeline结果中（向后兼容）
    structured_facts = facts_result

    self._log("调度",
              f"事实数据提取完成，共{facts_result['summary']['total_records']}条记录",
              "success")
except Exception as e:
    self._log("调度", f"事实数据提取异常: {str(e)}", "warning")
    structured_facts = {"records": [], "summary": {"total_records": 0}}
```

### 4.3 Excel导出增强

在现有 ExcelExporter 中新增一个 Sheet：

```python
# Sheet4: 事实商业关系明细
def _write_fact_details(ws, facts_result: dict):
    """写入事实商业关系明细Sheet"""
    headers = [
        "记录类型", "记录ID", "对方企业", "项目名称",
        "关系类型", "角色", "产品", "产品详情",
        "金额", "金额单位", "日期", "地区",
        "行业", "证据类型", "来源平台", "置信度"
    ]
    # ... 按record_type分组，组内按置信度排序 ...
    # 颜色区分：中标=蓝底 客户=绿底 供应商=黄底 投资=红底 合作=紫底
```

---

## 五、输出示例

### 文件结构

```
output/
├── 洛阳LYC_20260517_153000_crawl.json       # 模块1原始采集
├── 洛阳LYC_20260517_153000_clean.json       # 模块2清洗结果
├── 洛阳LYC_20260517_153000_tag.json         # 模块3标签结果
├── 洛阳LYC_20260517_153000_facts.json       # ★ 新增：事实数据
├── 洛阳LYC_20260517_153000_pipeline.json    # 流水线汇总
└── 洛阳LYC_20260517_153000_report.xlsx      # Excel报告（含事实Sheet）
```

### facts.json 输出示例

```json
{
  "enterprise_name": "洛阳LYC轴承有限公司",
  "extract_time": "2026-05-17 15:30:00",
  "summary": {
    "total_records": 18,
    "bidding_records": 6,
    "customer_records": 4,
    "supplier_records": 2,
    "investment_records": 2,
    "partnership_records": 3,
    "product_supply_records": 1
  },
  "records": [
    {
      "record_type": "bidding",
      "record_id": "BID-001",
      "project_name": "金风科技2024年风电主轴轴承采购项目",
      "bid_type": "中标",
      "role": "中标方",
      "counterparty": "金风科技股份有限公司",
      "counterparty_industry": "风力发电",
      "amount": "3200",
      "amount_unit": "万元",
      "amount_raw": "3,200万元",
      "currency": "人民币",
      "bid_date": "2024-03-15",
      "products": "风电主轴轴承",
      "source_platform": "中国政府采购网",
      "source_url": "http://search.ccgp.gov.cn/...",
      "source_snippet": "2024年3月洛阳LYC轴承有限公司中标金风科技风电主轴轴承采购项目，金额3,200万元",
      "confidence": 0.92
    },
    {
      "record_type": "customer",
      "record_id": "CUS-001",
      "customer_name": "一汽解放汽车有限公司",
      "customer_short_name": "一汽",
      "customer_industry": "汽车工业",
      "relationship_nature": "供应商",
      "products_supplied": "深沟球轴承、圆锥滚子轴承",
      "evidence_type": "官网提及",
      "evidence_text": "公司长期为一汽解放提供配套轴承产品",
      "is_current": true,
      "source_platform": "企业官网",
      "source_url": "https://www.lycbearing.com/partners",
      "confidence": 0.85
    }
  ],
  "source_coverage": {
    "official_website": true,
    "business_info": true,
    "bidding_info": true,
    "patent_info": true
  },
  "extraction_confidence": 0.88
}
```

---

## 六、实施步骤

| 步骤 | 内容 | 工作量 |
|------|------|--------|
| Step 1 | 实现 `BiddingRecordParser`（招投标解析器） | 最核心，占60%工作量 |
| Step 2 | 实现 `WebsiteRecordParser`（官网解析器） | 复用现有逻辑，增量改造 |
| Step 3 | 实现 `FactDataExtractor` 主类 + 分段路由 | 串联各解析器 |
| Step 4 | 实现去重 + 置信度评分 | 核心质量保证 |
| Step 5 | 集成到 Pipeline | 改动 pipeline.py 约30行 |
| Step 6 | Excel 导出增强 | 新增事实Sheet |
| Step 7 | 端到端测试 | 用3-5家真实企业验证 |

**建议优先级**：先做 Step 1（招投标解析器），因为招投标数据是事实性最强的商业关系来源，格式也最规范，提取成功率最高。
