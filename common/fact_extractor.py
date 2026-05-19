"""
企业事实性商业关系数据结构化提取器

从采集的原始网页文本中，深度提取结构化的事实性商业关系记录，
每条记录包含完整的交易/合作/投资要素（对方企业、金额、日期、项目名等），
输出为独立的结构化 JSON 文件。
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ========== 招投标记录解析器 ==========

class BiddingRecordParser:
    """招投标事实记录解析器

    核心能力：从招投标相关文本中拆分出每一条独立的招投标记录，
    并提取项目名、金额、日期、对方企业、产品等字段。
    """

    # 招投标句子边界关键词
    RECORD_BOUNDARIES = [
        r'\d{4}\s*年',
        r'(?:中标|成交|招标|采购)公告',
        r'项目名称[：:]',
        r'中标(?:供应商|单位)[：:]',
        r'(?:成交|中标)金额[：:]',
    ]

    # 招投标关键词（句子必须包含至少一个）
    BID_KEYWORDS = ["中标", "成交", "招标", "采购", "竞标", "投标",
                    "采购项目", "中标公告", "成交公告"]

    # 知名企业→行业映射
    ENTERPRISE_INDUSTRY = {
        "一汽": "汽车工业", "东风": "汽车工业", "上汽": "汽车工业",
        "长安": "汽车工业", "广汽": "汽车工业", "吉利": "汽车工业",
        "比亚迪": "汽车工业", "北汽": "汽车工业",
        "中车": "轨道交通行业", "中国中车": "轨道交通行业",
        "金风科技": "风力发电行业", "明阳智能": "风力发电行业",
        "远景能源": "风力发电行业",
        "三一重工": "工程机械行业", "徐工": "工程机械行业",
        "中联重科": "工程机械行业",
        "西门子": "电力设备行业", "ABB": "电力设备行业",
        "宝钢": "冶金行业", "鞍钢": "冶金行业",
        "中国商飞": "航空航天行业", "中航工业": "航空航天行业",
    }

    # 轴承产品关键词
    BEARING_PRODUCT_KEYWORDS = [
        "轴承", "深沟球轴承", "圆锥滚子轴承", "调心滚子轴承",
        "圆柱滚子轴承", "角接触球轴承", "推力轴承", "关节轴承",
        "直线轴承", "滚珠丝杠", "直线导轨", "轴承座",
        "保持架", "钢球", "滚子", "密封件", "轴承套圈",
        "风电轴承", "高铁轴承", "汽车轴承", "精密轴承",
        "陶瓷轴承", "不锈钢轴承", "绝缘轴承", "转盘轴承",
        "主轴轴承", "轧机轴承", "矿山轴承",
    ]

    # 来源平台可信度加分
    PLATFORM_BONUS = {
        "中国政府采购网": 0.15,
        "全国公共资源交易": 0.15,
        "全国公共资源交易平台": 0.15,
        "中国招标投标": 0.12,
        "中国招标投标平台": 0.12,
        "国家企业信用公示": 0.10,
        "天眼查": 0.08,
        "企查查": 0.08,
        "爱企查": 0.08,
        "企业官网": 0.05,
    }

    def parse(self, enterprise_name: str, segment: dict,
              structured_data: dict) -> List[dict]:
        text = segment.get("text", "")
        source_url = segment.get("source_url", "")
        source_platform = segment.get("source_platform", "")

        if not text:
            return []

        sentences = self._split_into_factual_sentences(text)
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
            if not any(kw in sentence for kw in self.BID_KEYWORDS):
                continue
            factual_sentences.append(sentence)
        return factual_sentences

    def _parse_single_sentence(self, enterprise_name: str, sentence: str,
                                source_url: str, source_platform: str) -> Optional[dict]:
        """从单个句子中提取结构化招投标记录"""
        record = {
            "record_type": "bidding",
            "source_url": source_url,
            "source_platform": source_platform,
            "source_snippet": sentence[:200],
        }

        record["project_name"] = self._extract_project_name(sentence)
        record["bid_type"] = self._extract_bid_type(sentence)
        counterparty = self._extract_counterparty(enterprise_name, sentence)
        record["counterparty"] = counterparty
        record["counterparty_industry"] = self._infer_counterparty_industry(counterparty, sentence)

        amount_info = self._extract_amount(sentence)
        record.update(amount_info)

        record["bid_date"] = self._extract_date(sentence)
        record["products"] = self._extract_products(sentence)
        record["region"] = self._extract_region(sentence)
        record["role"] = self._infer_role(enterprise_name, sentence)

        # 最少需要：金额或对方企业或项目名
        has_content = (record.get("amount") or record.get("counterparty")
                       or record.get("project_name"))
        if not has_content:
            return None
        return record

    def _extract_project_name(self, sentence: str) -> str:
        patterns = [
            r'项目名称[：:]\s*([^\n,，。；;]{4,60})',
            r'(?:中标|成交)\s*[项目的]*(.{4,40}?)项目',
            r'((?:\w{2,20})(?:采购|招标|项目)).{0,5}(?:金额|中标|成交)',
            r'(\w{2,15}(?:采购项目|招标项目|项目))',
        ]
        for p in patterns:
            m = re.search(p, sentence)
            if m:
                name = m.group(1).strip()
                name = re.sub(r'^[的为于在]', '', name)
                if 4 <= len(name) <= 60:
                    return name
        return ""

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

        # 策略3: "X万元" 格式
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

    def _extract_counterparty(self, enterprise_name: str, sentence: str) -> str:
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

    def _extract_bid_type(self, sentence: str) -> str:
        for bid_type, keywords in [("中标", ["中标"]), ("成交", ["成交"]),
                                    ("招标", ["招标"]), ("采购", ["采购"]),
                                    ("竞标", ["竞标"])]:
            if any(kw in sentence for kw in keywords):
                return bid_type
        return "招标"

    def _infer_role(self, enterprise_name: str, sentence: str) -> str:
        if re.search(rf'{re.escape(enterprise_name)}.*?中标', sentence):
            return "中标方"
        if re.search(rf'中标.*?{re.escape(enterprise_name)}', sentence):
            return "中标方"
        if re.search(rf'{re.escape(enterprise_name)}.*?(?:采购|招标)', sentence):
            return "招标方"
        return "中标方"

    def _extract_products(self, sentence: str) -> str:
        for kw in self.BEARING_PRODUCT_KEYWORDS:
            if kw in sentence:
                return kw
        return ""

    def _extract_region(self, sentence: str) -> str:
        provinces = ["北京", "上海", "天津", "重庆", "河北", "河南", "山东", "山西",
                     "江苏", "浙江", "广东", "广西", "湖南", "湖北", "安徽", "福建",
                     "江西", "四川", "陕西", "辽宁", "吉林", "黑龙江", "贵州", "云南",
                     "甘肃", "青海", "海南", "宁夏", "新疆", "西藏", "内蒙古"]
        for p in provinces:
            if p in sentence:
                return p + ("市" if p in ["北京", "上海", "天津", "重庆"] else "省")
        return ""

    def _infer_counterparty_industry(self, name: str, sentence: str) -> str:
        if name in self.ENTERPRISE_INDUSTRY:
            return self.ENTERPRISE_INDUSTRY[name]
        for known, industry in self.ENTERPRISE_INDUSTRY.items():
            if known in name or name in known:
                return industry
        # 从句子上下文推断
        for kw, industry in [("风电", "风力发电"), ("汽车", "汽车工业"),
                             ("铁路", "轨道交通"), ("航空", "航空航天"),
                             ("冶金", "冶金行业"), ("机床", "机床工具"),
                             ("矿山", "矿山机械"), ("石油", "石油装备")]:
            if kw in sentence:
                return industry
        return ""


# ========== 官网页面解析器 ==========

class WebsiteRecordParser:
    """从企业官网内容中提取客户/供应商/合作伙伴/投资记录"""

    # 客户上下文关键词
    CUSTOMER_CONTEXT = [
        "供货", "供应", "提供", "配套", "交付", "服务",
        "为客户", "向.*?提供", "客户", "合作伙伴",
    ]
    # 供应商上下文关键词
    SUPPLIER_CONTEXT = [
        "采购自", "采购于", "供应商", "由.*?供应", "进口",
    ]
    # 合作上下文关键词
    COOPERATION_CONTEXT = [
        "合作", "战略合作", "联合", "携手", "协作",
        "共同开发", "联合研发", "技术合作", "产学研",
    ]
    # 投资关键词
    INVESTMENT_CONTEXT = [
        "投资", "建设", "新增产线", "扩建", "技改", "新增",
    ]

    # 知名企业→行业映射
    ENTERPRISE_INDUSTRY = {
        "SKF": "轴承制造", "NSK": "轴承制造", "NTN": "轴承制造",
        "铁姆肯": "轴承制造", "Timken": "轴承制造", "舍弗勒": "轴承制造",
        "人本集团": "轴承制造", "万向钱潮": "轴承制造",
        "一汽": "汽车工业", "东风": "汽车工业", "上汽": "汽车工业",
        "中车": "轨道交通行业", "中国中车": "轨道交通行业",
        "金风科技": "风力发电行业", "远景能源": "风力发电行业",
        "三一重工": "工程机械行业", "徐工": "工程机械行业",
        "西门子": "电力设备行业", "ABB": "电力设备行业",
    }

    # 企业名提取正则
    COMPANY_PATTERNS = [
        r'([\u4e00-\u9fa5]+(?:集团|股份|科技|技术|工业|装备|机械|电子|电气|汽车|轴承|精密|传动|冶金|重工|动力|机电|五金|钢铁|新材料|新能源)(?:有限)?(?:责任)?(?:公司|厂))',
        r'([\u4e00-\u9fa5]{2,8}(?:有限公司|集团))',
    ]

    # 知名企业列表（含简称）
    KNOWN_ENTERPRISES = [
        "SKF", "NSK", "NTN", "铁姆肯", "Timken", "舍弗勒", "Schaeffler",
        "FAG", "INA", "KOYO", "NMB", "Nachi", "不二越",
        "人本集团", "万向钱潮", "洛阳LYC", "瓦轴ZWZ", "哈尔滨轴承HRB",
        "天马轴承", "五洲新春", "一汽", "东风", "中车", "金风科技",
        "三一重工", "徐工", "中联重科", "西门子", "ABB",
        "宝钢", "鞍钢", "中国商飞", "中航工业",
        "格力", "美的", "海尔", "比亚迪", "蔚来", "理想", "小鹏",
    ]

    def parse(self, enterprise_name: str, segment: dict,
              structured_data: dict) -> List[dict]:
        text = segment.get("text", "")
        source_url = segment.get("source_url", "")
        records = []

        records.extend(self._extract_customer_records(enterprise_name, text, source_url, structured_data))
        records.extend(self._extract_supplier_records(enterprise_name, text, source_url, structured_data))
        records.extend(self._extract_partner_records(enterprise_name, text, source_url, structured_data))
        records.extend(self._extract_investment_records(enterprise_name, text, source_url))

        return records

    def _extract_enterprises(self, text: str, exclude_name: str) -> List[Tuple[str, str]]:
        """提取文本中的企业名和行业"""
        found = []
        seen = set()

        # 正则提取
        for pattern in self.COMPANY_PATTERNS:
            for m in re.finditer(pattern, text):
                name = m.group(1).strip()
                if name and len(name) >= 4 and name not in seen:
                    if name == exclude_name or exclude_name in name:
                        continue
                    seen.add(name)
                    industry = self.ENTERPRISE_INDUSTRY.get(name, "")
                    found.append((name, industry))

        # 知名企业匹配（覆盖简称）
        for known in self.KNOWN_ENTERPRISES:
            if known in text and known not in seen:
                if known == exclude_name or known in exclude_name:
                    continue
                seen.add(known)
                industry = self.ENTERPRISE_INDUSTRY.get(known, "")
                found.append((known, industry))

        return found

    def _extract_customer_records(self, enterprise_name: str, text: str,
                                   source_url: str, structured_data: dict) -> List[dict]:
        """提取客户关系记录"""
        records = []

        # 找到含客户上下文的句子
        customer_sentences = []
        for sentence in re.split(r'[。；\n]', text):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue
            for kw in self.CUSTOMER_CONTEXT:
                if re.search(kw, sentence):
                    customer_sentences.append(sentence)
                    break

        if not customer_sentences:
            # 回退：从structured_data中的合作企业提取
            coop = structured_data.get("cooperative_enterprise", "")
            if coop and coop not in ("未提取到", "未明确"):
                for name in re.split(r'[,，、；;]+', coop):
                    name = name.strip()
                    if name and len(name) >= 2:
                        industry = self.ENTERPRISE_INDUSTRY.get(name, "")
                        records.append({
                            "record_type": "customer",
                            "customer_name": name,
                            "customer_short_name": name[:4],
                            "customer_industry": industry,
                            "relationship_nature": "供应商",
                            "products_supplied": structured_data.get("core_products", ""),
                            "evidence_type": "结构化字段",
                            "evidence_text": f"合作企业列表中包含{name}",
                            "contract_amount": "",
                            "start_date": "",
                            "is_current": True,
                            "source_platform": "结构化数据",
                            "source_url": "",
                            "confidence": 0.70,
                        })
            return records

        for sentence in customer_sentences:
            enterprises = self._extract_enterprises(sentence, enterprise_name)
            for name, industry in enterprises:
                # 提取供应的产品
                products = ""
                for kw in ["轴承", "滚子", "保持架", "密封", "滚珠丝杠", "导轨", "套圈"]:
                    if kw in sentence:
                        products = kw
                        break
                if not products:
                    products = structured_data.get("core_products", "")

                records.append({
                    "record_type": "customer",
                    "customer_name": name,
                    "customer_short_name": name[:4],
                    "customer_industry": industry,
                    "relationship_nature": "供应商",
                    "products_supplied": products,
                    "evidence_type": "官网提及",
                    "evidence_text": sentence[:100],
                    "contract_amount": "",
                    "start_date": "",
                    "is_current": True,
                    "source_platform": "企业官网",
                    "source_url": source_url,
                    "confidence": 0.85,
                })
        return records

    def _extract_supplier_records(self, enterprise_name: str, text: str,
                                   source_url: str, structured_data: dict) -> List[dict]:
        """提取供应商关系记录"""
        records = []
        supplier_sentences = []
        for sentence in re.split(r'[。；\n]', text):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue
            for kw in self.SUPPLIER_CONTEXT:
                if re.search(kw, sentence):
                    supplier_sentences.append(sentence)
                    break

        for sentence in supplier_sentences:
            enterprises = self._extract_enterprises(sentence, enterprise_name)
            for name, industry in enterprises:
                records.append({
                    "record_type": "supplier",
                    "supplier_name": name,
                    "supplier_industry": industry,
                    "relationship_nature": "采购方",
                    "products_supplied": "",
                    "evidence_type": "官网提及",
                    "evidence_text": sentence[:100],
                    "source_platform": "企业官网",
                    "source_url": source_url,
                    "confidence": 0.82,
                })
        return records

    def _extract_partner_records(self, enterprise_name: str, text: str,
                                  source_url: str, structured_data: dict) -> List[dict]:
        """提取合作关系记录"""
        records = []
        partner_sentences = []
        for sentence in re.split(r'[。；\n]', text):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue
            for kw in self.COOPERATION_CONTEXT:
                if re.search(kw, sentence):
                    partner_sentences.append(sentence)
                    break

        for sentence in partner_sentences:
            enterprises = self._extract_enterprises(sentence, enterprise_name)
            for name, industry in enterprises:
                # 判断合作类型
                coop_type = "技术合作"
                if "产学研" in sentence:
                    coop_type = "产学研合作"
                elif "战略" in sentence:
                    coop_type = "战略合作"
                elif "联合研发" in sentence or "共同开发" in sentence:
                    coop_type = "联合研发"

                records.append({
                    "record_type": "partnership",
                    "partner_name": name,
                    "partner_industry": industry,
                    "partnership_type": coop_type,
                    "cooperation_content": sentence[:100],
                    "evidence_text": sentence[:100],
                    "start_date": "",
                    "source_platform": "企业官网",
                    "source_url": source_url,
                    "confidence": 0.88,
                })
        return records

    def _extract_investment_records(self, enterprise_name: str, text: str,
                                     source_url: str) -> List[dict]:
        """提取投资项目记录"""
        records = []
        invest_sentences = []
        for sentence in re.split(r'[。；\n]', text):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 15:
                continue
            has_invest = any(kw in sentence for kw in self.INVESTMENT_CONTEXT)
            has_money = bool(re.search(r'[\d,.]+\s*[亿万]元', sentence))
            if has_invest and has_money:
                invest_sentences.append(sentence)

        for sentence in invest_sentences:
            # 提取金额
            amount_info = {"amount": "", "amount_unit": "", "amount_raw": ""}
            m = re.search(r'([\d,.]+)\s*亿(元|人民币)', sentence)
            if m:
                amount_info = {"amount": m.group(1).replace(",", ""),
                               "amount_unit": "亿元", "amount_raw": m.group(0)}
            else:
                m = re.search(r'([\d,.]+)\s*万(元|人民币)', sentence)
                if m:
                    amount_info = {"amount": m.group(1).replace(",", ""),
                                   "amount_unit": "万元", "amount_raw": m.group(0)}

            # 提取日期
            date = ""
            m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月', sentence)
            if m:
                date = f"{m.group(1)}-{int(m.group(2)):02d}"
            else:
                m = re.search(r'(\d{4})\s*年', sentence)
                if m:
                    date = m.group(1)

            # 提取项目内容
            investment_type = "扩建"
            if "新增" in sentence:
                investment_type = "新建"
            elif "技改" in sentence:
                investment_type = "技改"
            elif "建设" in sentence:
                investment_type = "建设"

            # 提取产品
            products = ""
            for kw in ["轴承", "滚子", "保持架", "精密", "风电", "汽车"]:
                if kw in sentence:
                    products = kw
                    break

            records.append({
                "record_type": "investment",
                "project_name": sentence[:40],
                "investment_type": investment_type,
                **amount_info,
                "start_date": date,
                "completion_date": "",
                "project_content": sentence[:100],
                "products": products,
                "region": "",
                "source_platform": "企业官网",
                "source_url": source_url,
                "source_snippet": sentence[:150],
                "confidence": 0.90,
            })
        return records


# ========== 主提取器 ==========

class FactDataExtractor:
    """企业事实性商业关系数据结构化提取器"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir
        self.parsers = {
            "bidding_info": BiddingRecordParser(),
            "official_website": WebsiteRecordParser(),
            "business_info": BiddingRecordParser(),  # 工商信息中也可能有招投标
            "patent_info": None,  # 专利信息暂不提取商业关系
        }

    def extract(self, enterprise_name: str,
                raw_crawl_data: dict,
                structured_data: dict) -> dict:
        """主提取入口"""
        all_records = []

        # Step 1: 按来源分段原始文本
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

    def _segment_by_source(self, raw_crawl_data: dict) -> List[dict]:
        """按来源URL分段原始文本"""
        segments = []
        raw_content = raw_crawl_data.get("raw_content", {})

        for content_type in ["official_website", "business_info",
                             "bidding_info", "patent_info"]:
            text = raw_content.get(content_type, "")
            if not text:
                continue

            # 解析【来源: URL】标记，拆分为多个子段
            sub_segments = self._split_by_source_tags(text, content_type)
            segments.extend(sub_segments)

        return segments

    def _split_by_source_tags(self, text: str, content_type: str) -> List[dict]:
        """按【来源: xxx】标记拆分文本为子段"""
        segments = []
        # 按 【来源: xxx】 标记拆分
        parts = re.split(r'【来源[：:]\s*([^\]]*)】', text)

        i = 0
        while i < len(parts):
            source_url = ""
            content = ""

            if i + 1 < len(parts):
                source_url = parts[i].strip()
                content = parts[i + 1].strip() if i + 1 < len(parts) else ""
                i += 2
            else:
                content = parts[i].strip()
                i += 1

            if content and len(content) > 20:
                # 推断来源平台
                source_platform = self._infer_platform(source_url, content_type)
                segments.append({
                    "text": content,
                    "source_url": source_url,
                    "source_type": content_type,
                    "source_platform": source_platform,
                })

        # 如果没有拆分出任何段（没有来源标记），把整个文本作为一段
        if not segments and text and len(text) > 20:
            segments.append({
                "text": text,
                "source_url": "",
                "source_type": content_type,
                "source_platform": self._infer_platform("", content_type),
            })

        return segments

    def _infer_platform(self, url: str, content_type: str) -> str:
        """从URL或内容类型推断来源平台"""
        url_lower = url.lower()
        platform_map = {
            "tianyancha": "天眼查", "qcc": "企查查", "aiqicha": "爱企查",
            "gsxt": "国家企业信用公示", "ccgp": "中国政府采购网",
            "ggzy": "全国公共资源交易平台", "cebpubservice": "中国招标投标平台",
            "cnipa": "国家知识产权局", "cninfo": "巨潮资讯网",
        }
        for key, platform in platform_map.items():
            if key in url_lower:
                return platform

        type_map = {
            "official_website": "企业官网",
            "business_info": "工商查询平台",
            "bidding_info": "招投标平台",
            "patent_info": "专利查询平台",
        }
        return type_map.get(content_type, "综合平台")

    def _route_parser(self, segment: dict):
        """根据段落的来源类型路由到对应的解析器"""
        source_type = segment.get("source_type", "")
        return self.parsers.get(source_type)

    def _deduplicate_records(self, records: List[dict]) -> List[dict]:
        """跨来源去重"""
        seen = {}
        for record in records:
            rtype = record.get("record_type", "")
            if rtype == "bidding":
                key = (rtype, record.get("counterparty", ""),
                       record.get("project_name", "")[:30])
            elif rtype == "customer":
                key = (rtype, record.get("customer_name", ""))
            elif rtype == "supplier":
                key = (rtype, record.get("supplier_name", ""))
            elif rtype == "investment":
                key = (rtype, record.get("project_name", "")[:30])
            elif rtype == "partnership":
                key = (rtype, record.get("partner_name", ""))
            else:
                key = (rtype, record.get("counterparty", ""),
                       record.get("source_snippet", "")[:50])

            if key in seen:
                existing = seen[key]
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

    def _score_confidence(self, record: dict) -> float:
        """基于字段完整度和来源可信度计算置信度"""
        rtype = record.get("record_type", "")
        base = 0.60

        # 来源可信度加分
        source_platform = record.get("source_platform", "")
        platform_bonus = {
            "中国政府采购网": 0.15, "全国公共资源交易平台": 0.15,
            "全国公共资源交易": 0.15, "中国招标投标": 0.12,
            "中国招标投标平台": 0.12, "国家企业信用公示": 0.10,
            "天眼查": 0.08, "企查查": 0.08, "爱企查": 0.08,
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

    def _assign_ids(self, records: List[dict]):
        """为每条记录分配ID"""
        type_prefixes = {
            "bidding": "BID", "customer": "CUS", "supplier": "SUP",
            "investment": "INV", "partnership": "PTN", "product_supply": "PSR",
        }
        counters = {}
        for record in records:
            rtype = record.get("record_type", "")
            prefix = type_prefixes.get(rtype, "REC")
            counters[rtype] = counters.get(rtype, 0) + 1
            record["record_id"] = f"{prefix}-{counters[rtype]:03d}"

    def _build_output(self, enterprise_name: str, records: List[dict],
                      raw_crawl_data: dict) -> dict:
        """构建最终输出"""
        # 统计
        type_counts = {}
        for r in records:
            rtype = r.get("record_type", "")
            type_counts[rtype] = type_counts.get(rtype, 0) + 1

        # 来源覆盖
        raw_content = raw_crawl_data.get("raw_content", {})
        source_coverage = {
            "official_website": bool(raw_content.get("official_website")),
            "business_info": bool(raw_content.get("business_info")),
            "bidding_info": bool(raw_content.get("bidding_info")),
            "patent_info": bool(raw_content.get("patent_info")),
        }

        # 整体置信度
        if records:
            extraction_confidence = round(
                sum(r.get("confidence", 0) for r in records) / len(records), 2
            )
        else:
            extraction_confidence = 0.0

        return {
            "enterprise_name": enterprise_name,
            "extract_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_records": len(records),
                **{f"{k}_records": v for k, v in type_counts.items()},
            },
            "records": records,
            "source_coverage": source_coverage,
            "extraction_confidence": extraction_confidence,
        }

    def save_to_file(self, facts_result: dict, enterprise_name: str) -> str:
        """保存事实数据到独立JSON文件"""
        if not self.output_dir:
            return ""
        os.makedirs(self.output_dir, exist_ok=True)
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', enterprise_name)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}_facts.json"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(facts_result, f, ensure_ascii=False, indent=2)
        return filepath
