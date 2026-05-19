#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bearing-enterprise-data-tag: 轴承行业企业基础静态属性标签生成

本脚本承接 bearing-enterprise-data-clean 输出的结构化数据，
聚焦产品、服务、能力三大核心维度，自动生成标准化标签。

使用方式:
  python tag_enterprise.py <cleaned_json_path>
  python tag_enterprise.py output/企业名称_xxx_cleaned.json
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding='utf-8')


# ============================================================
# 术语标准化映射
# ============================================================
TERM_NORMALIZE = {
    # 轴承类型相关
    "滚动轴承": "滚动轴承", "球轴承": "球轴承", "滚子轴承": "滚子轴承",
    "深沟球轴承": "深沟球轴承", "向心球轴承": "深沟球轴承",
    "圆锥滚子轴承": "圆锥滚子轴承", "圆锥滚子": "圆锥滚子轴承",
    "调心球轴承": "调心球轴承", "调心滚子轴承": "调心滚子轴承",
    "圆柱滚子轴承": "圆柱滚子轴承", "圆柱滚子": "圆柱滚子轴承",
    "角接触球轴承": "角接触球轴承", "角接触轴承": "角接触球轴承",
    "推力球轴承": "推力球轴承", "推力滚子轴承": "推力滚子轴承",
    "推力轴承": "推力轴承", "关节轴承": "关节轴承",
    "杆端关节轴承": "杆端关节轴承",
    "直线轴承": "直线轴承", "直线导轨": "直线导轨", "导轨": "直线导轨",
    "滚珠丝杠": "滚珠丝杠", "丝杠": "滚珠丝杠",
    "外球面轴承": "外球面轴承", "带座轴承": "外球面轴承",
    "轴承座": "轴承座", "轴承单元": "轴承单元",
    # 材料相关
    "陶瓷轴承": "陶瓷轴承", "混合陶瓷轴承": "混合陶瓷轴承",
    "不锈钢轴承": "不锈钢轴承", "塑料轴承": "塑料轴承",
    "轴承钢": "轴承钢", "高碳铬轴承钢": "GCr15轴承钢",
    "GCr15": "GCr15轴承钢",
    # 零部件相关
    "保持架": "保持架", "轴承保持架": "保持架",
    "滚动体": "滚动体", "钢球": "钢球", "陶瓷球": "陶瓷球",
    "密封件": "密封件", "防尘盖": "防尘盖",
    "套圈": "套圈", "内圈": "内圈", "外圈": "外圈",
    # 精度等级
    "P0级": "P0级(普通级)", "P6级": "P6级(较高级)",
    "P5级": "P5级(高级)", "P4级": "P4级(精密级)",
    "P2级": "P2级(超精密级)",
    "ABEC-1": "P0级(普通级)", "ABEC-3": "P6级(较高级)",
    "ABEC-5": "P5级(高级)", "ABEC-7": "P4级(精密级)",
    "ABEC-9": "P2级(超精密级)",
    # 工艺相关
    "锻造": "锻造", "车削": "车削", "磨削": "磨削",
    "超精加工": "超精加工", "热处理": "热处理",
    "表面处理": "表面处理", "装配": "装配",
    # 认证标准化
    "ISO9001质量管理体系认证": "ISO9001认证",
    "ISO9001质量体系": "ISO9001认证",
    "ISO14001环境管理体系认证": "ISO14001认证",
    "IATF16949质量管理体系认证": "IATF16949认证",
    "AS9100质量管理体系认证": "AS9100认证",
    "API认证": "API认证",
    "CRCC铁路产品认证": "CRCC认证",
    "RoHS指令": "RoHS合规", "RoHS认证": "RoHS合规",
    "CE认证": "CE认证",
}

# 产品类型关键词 → 标准标签
PRODUCT_TYPE_MAP = {
    "深沟球轴承": "深沟球轴承", "圆锥滚子轴承": "圆锥滚子轴承",
    "调心球轴承": "调心球轴承", "调心滚子轴承": "调心滚子轴承",
    "圆柱滚子轴承": "圆柱滚子轴承", "角接触球轴承": "角接触球轴承",
    "推力球轴承": "推力球轴承", "推力滚子轴承": "推力滚子轴承",
    "关节轴承": "关节轴承", "杆端关节轴承": "杆端关节轴承",
    "直线轴承": "直线轴承", "直线导轨": "直线导轨",
    "滚珠丝杠": "滚珠丝杠", "外球面轴承": "外球面轴承",
    "轴承座": "轴承座", "轴承单元": "轴承单元",
    "陶瓷轴承": "陶瓷轴承", "混合陶瓷轴承": "混合陶瓷轴承",
    "不锈钢轴承": "不锈钢轴承", "精密轴承": "精密轴承",
    "高温轴承": "高温轴承", "高速轴承": "高速轴承",
    "绝缘轴承": "绝缘轴承", "微型轴承": "微型轴承",
    "薄壁轴承": "薄壁轴承", "满装滚子轴承": "满装滚子轴承",
    "交叉滚子轴承": "交叉滚子轴承", "转盘轴承": "转盘轴承",
    "保持架": "保持架", "钢球": "钢球", "陶瓷球": "陶瓷球",
    "滚子": "滚子", "密封件": "密封件",
    "轴承钢": "轴承钢", "GCr15": "GCr15轴承钢",
    "滚动体": "滚动体", "套圈": "套圈",
    "滚针轴承": "滚针轴承", "滚针": "滚针轴承",
}

# 应用场景关键词 → 标签
APPLICATION_SCENE_MAP = {
    "汽车": "汽车", "轿车": "汽车", "商用车": "汽车", "变速箱": "汽车", "轮毂": "汽车",
    "风电": "风电", "风力发电": "风电", "主轴": "风电", "偏航": "风电", "变桨": "风电",
    "航空": "航空航天", "航天": "航空航天", "飞机": "航空航天", "发动机": "航空航天",
    "铁路": "铁路", "高铁": "铁路", "机车": "铁路", "地铁": "铁路", "轮对": "铁路",
    "矿山": "矿山机械", "采煤": "矿山机械", "掘进": "矿山机械",
    "机床": "机床", "数控": "机床", "加工中心": "机床", "主轴": "机床",
    "工业机器人": "工业机器人", "机器人": "工业机器人", "减速器": "工业机器人",
    "冶金": "冶金设备", "轧机": "冶金设备", "连铸": "冶金设备",
    "石油": "石油装备", "钻井": "石油装备", "钻机": "石油装备",
    "农机": "农业机械", "拖拉机": "农业机械", "收割机": "农业机械",
    "工程机械": "工程机械", "挖掘机": "工程机械", "起重机": "工程机械",
    "电梯": "电梯", "扶梯": "电梯",
    "家电": "家用电器", "空调": "家用电器", "洗衣机": "家用电器",
    "电机": "电机", "电动机": "电机", "发电机": "电机",
    "泵": "泵阀", "阀门": "泵阀", "压缩机": "泵阀",
    "船舶": "船舶", "海洋": "海洋装备",
}

# 服务类型关键词 → 标签
SERVICE_TYPE_MAP = {
    "设计服务": "轴承设计服务", "轴承设计": "轴承设计服务",
    "定制": "轴承定制服务", "非标": "轴承定制服务",
    "加工": "轴承加工服务", "机械加工": "轴承加工服务",
    "热处理": "热处理服务", "淬火": "热处理服务",
    "检测": "轴承检测服务", "测试": "轴承检测服务", "测量": "轴承检测服务",
    "润滑": "润滑服务", "润滑脂": "润滑服务",
    "选型": "轴承选型服务",
    "代工": "OEM代工", "OEM": "OEM代工",
    "ODM": "ODM设计制造",
    "技术支持": "技术支持服务", "售后": "售后维护服务",
    "咨询": "技术咨询", "培训": "技术培训",
    "检测认证": "检测认证服务", "认证": "检测认证服务",
    "维修": "售后维护服务",
}

# 合作模式关键词
COOP_MODE_MAP = {
    "配套": "供应链配套", "供应商": "供应链配套", "供货": "批量供货",
    "中标": "招投标合作", "采购": "批量供货", "定制化": "定制化服务",
    "战略": "战略合作", "长期": "长期合作",
}

# 知名企业 → 应用领域推断
FAMOUS_ENTERPRISE_SCENE = {
    "一汽": ["汽车工业"], "东风": ["汽车工业"], "上汽": ["汽车工业"],
    "长安": ["汽车工业"], "广汽": ["汽车工业"], "吉利": ["汽车工业"],
    "比亚迪": ["汽车工业"], "蔚来": ["汽车工业"], "理想": ["汽车工业"],
    "中车": ["轨道交通"], "中国中车": ["轨道交通"],
    "金风科技": ["风力发电"], "明阳智能": ["风力发电"],
    "SKF": ["高端制造"], "NSK": ["高端制造"], "NTN": ["高端制造"],
    "铁姆肯": ["高端制造"], "舍弗勒": ["高端制造"],
    "人本集团": ["轴承"], "瓦轴": ["轴承"], "洛轴": ["轴承"], "哈轴": ["轴承"],
    "西门子": ["电力设备"], "ABB": ["电力设备"],
    "徐工": ["工程机械"], "三一": ["工程机械"], "中联": ["工程机械"],
    "格力": ["家电"], "美的": ["家电"], "海尔": ["家电"],
    "宝钢": ["冶金设备"], "鞍钢": ["冶金设备"],
    "中国商飞": ["航空航天"], "中航": ["航空航天"],
}


# ============================================================
# 标签生成器
# ============================================================
class EnterpriseTagger:
    """轴承行业企业基础静态属性标签生成器"""

    def __init__(self, progress_callback=None, output_dir: str = None, llm_client=None):
        self.uncertain_tags = []
        self.progress_callback = progress_callback  # 进度回调函数
        self._llm_client = llm_client  # 可选的 LLM 客户端
        # 输出目录：优先使用指定目录，否则使用当前工作目录下的 output
        # 输出目录优先级: --output-dir 参数 > PROJECT_DIR 环境变量 > 当前工作目录
        if output_dir:
            self.output_dir = output_dir
        elif os.environ.get("PROJECT_DIR"):
            self.output_dir = os.path.join(os.environ.get("PROJECT_DIR"), "output")
        else:
            self.output_dir = os.path.join(os.getcwd(), "output")

    def _report_progress(self, progress: int, step: str, detail: str = ""):
        """报告标签生成进度"""
        if self.progress_callback:
            self.progress_callback(progress, "模块3打标", step, detail)

    def _normalize_term(self, text: str) -> str:
        """术语标准化"""
        if not text or text in ("未提取到", "未明确", ""):
            return text
        for old, new in TERM_NORMALIZE.items():
            if old in text:
                text = text.replace(old, new)
        return text

    def _extract_keywords(self, text: str, keyword_map: dict) -> List[str]:
        """从文本中提取匹配关键词，返回标准化标签列表"""
        if not text or text in ("未提取到", "未明确"):
            return []
        tags = []
        text_lower = text.lower()
        for keyword, label in keyword_map.items():
            if keyword.lower() in text_lower:
                if label not in tags:
                    tags.append(label)
        return tags

    def _calc_confidence(self, source_value: str, base_confidence: float = 0.90) -> float:
        """根据源字段状态计算置信度"""
        if not source_value or source_value in ("未提取到", "未明确", ""):
            return 0.0
        # 内容越详细置信度越高
        length_bonus = min(len(source_value) / 100, 0.05)
        return round(min(base_confidence + length_bonus, 0.99), 2)

    # ----------------------------------------------------------
    # 产品标签
    # ----------------------------------------------------------
    def _gen_product_type_tags(self, data: dict) -> List[dict]:
        """核心产品类型标签"""
        core_products = data.get("core_products", "")
        industry_segment = data.get("industry_segment", "")
        main_business = data.get("main_business", "")

        combined = f"{core_products} {industry_segment} {main_business}"
        tags = self._extract_keywords(combined, PRODUCT_TYPE_MAP)

        if not tags and core_products and core_products not in ("未提取到", "未明确"):
            # 如果关键词未匹配，直接按逗号/顿号分割
            for item in re.split(r'[,，、；;/\s]+', core_products):
                item = item.strip()
                if item and len(item) <= 20:
                    tags.append(self._normalize_term(item))

        if not tags:
            self.uncertain_tags.append({"tag_category": "产品标签", "sub_category": "核心产品类型", "reason": "core_products字段为空或未提取到"})
            return [{"tag": "核心产品类型-未明确", "source_field": "core_products", "confidence": 0.0}]

        conf = self._calc_confidence(core_products, 0.90)
        return [{"tag": t, "source_field": "core_products", "confidence": conf} for t in tags[:8]]

    def _gen_product_spec_tags(self, data: dict) -> List[dict]:
        """产品规格标签"""
        product_spec = data.get("product_spec", "")
        if not product_spec or product_spec in ("未提取到", "未明确"):
            self.uncertain_tags.append({"tag_category": "产品标签", "sub_category": "产品规格标签", "reason": "product_spec字段为空"})
            return [{"tag": "产品规格-未明确", "source_field": "product_spec", "confidence": 0.0}]

        tags = []
        # 解析规格信息，如 "内径：20-200mm；精度等级：P5、P4"
        spec_parts = re.split(r'[;；\n]+', product_spec)
        for part in spec_parts:
            part = part.strip()
            if not part:
                continue
            # 提取 "类别：规格" 格式
            m = re.match(r'([^:：]+)[：:]\s*(.+)', part)
            if m:
                category = self._normalize_term(m.group(1).strip())
                specs = m.group(2).strip()
                # 按逗号/顿号分割规格
                for s in re.split(r'[,，、]+', specs):
                    s = s.strip()
                    if s:
                        tags.append(f"{category}-{s}")
            else:
                tags.append(self._normalize_term(part))

        if not tags:
            tags = [self._normalize_term(product_spec)]

        conf = self._calc_confidence(product_spec, 0.88)
        return [{"tag": t, "source_field": "product_spec", "confidence": conf} for t in tags[:10]]

    def _gen_application_scene_tags(self, data: dict) -> List[dict]:
        """产品应用场景标签"""
        coop = data.get("cooperative_enterprise", "")
        main_biz = data.get("main_business", "")
        bidding = data.get("bidding_projects", "")
        business_scope = data.get("business_scope", "")

        tags = set()

        # 从合作企业推断
        if coop and coop not in ("未提取到", "未明确"):
            for ent in re.split(r'[,，、；;/\s]+', coop):
                ent = ent.strip()
                if ent in FAMOUS_ENTERPRISE_SCENE:
                    for scene in FAMOUS_ENTERPRISE_SCENE[ent]:
                        tags.add(scene)

        # 从业务描述推断
        combined = f"{main_biz} {bidding} {business_scope}"
        for tag in self._extract_keywords(combined, APPLICATION_SCENE_MAP):
            tags.add(tag)

        if not tags:
            self.uncertain_tags.append({"tag_category": "产品标签", "sub_category": "产品应用场景", "reason": "无法从合作企业或业务描述推断应用场景"})
            return [{"tag": "应用场景-未明确", "source_field": "cooperative_enterprise", "confidence": 0.0}]

        conf = 0.88 if tags else 0.0
        return [{"tag": t, "source_field": "cooperative_enterprise", "confidence": conf} for t in sorted(tags)[:8]]

    def _gen_compliance_tags(self, data: dict) -> List[dict]:
        """产品合规标签"""
        cert = data.get("industry_cert", "")
        if not cert or cert in ("未提取到", "未明确"):
            self.uncertain_tags.append({"tag_category": "产品标签", "sub_category": "产品合规标签", "reason": "industry_cert字段为空"})
            return [{"tag": "合规认证-未明确", "source_field": "industry_cert", "confidence": 0.0}]

        tags = []
        for item in re.split(r'[,，、；;]+', cert):
            item = item.strip()
            if not item:
                continue
            normalized = self._normalize_term(item)
            # 清理冗余表述
            normalized = re.sub(r'取得|获得|通过|持有|具备|已获', '', normalized).strip()
            if normalized:
                tags.append(normalized)

        if not tags:
            tags = [self._normalize_term(cert)]

        conf = self._calc_confidence(cert, 0.92)
        return [{"tag": t, "source_field": "industry_cert", "confidence": conf} for t in tags[:10]]

    # ----------------------------------------------------------
    # 服务标签
    # ----------------------------------------------------------
    def _gen_service_type_tags(self, data: dict) -> List[dict]:
        """核心服务类型标签"""
        scope = data.get("business_scope", "")
        main_biz = data.get("main_business", "")

        combined = f"{scope} {main_biz}"
        tags = self._extract_keywords(combined, SERVICE_TYPE_MAP)

        # 额外从经营模式推断
        if "研发" in combined and "生产" in combined and "销售" in combined:
            if "研产销一体化" not in tags:
                tags.append("研产销一体化")

        if not tags:
            self.uncertain_tags.append({"tag_category": "服务标签", "sub_category": "核心服务类型", "reason": "business_scope字段无法提取服务类型"})
            return [{"tag": "服务类型-未明确", "source_field": "business_scope", "confidence": 0.0}]

        conf = self._calc_confidence(scope, 0.88)
        return [{"tag": t, "source_field": "business_scope", "confidence": conf} for t in tags[:8]]

    def _gen_coop_mode_tags(self, data: dict) -> List[dict]:
        """合作模式标签"""
        coop = data.get("cooperative_enterprise", "")
        bidding = data.get("bidding_projects", "")

        combined = f"{coop} {bidding}"
        tags = self._extract_keywords(combined, COOP_MODE_MAP)

        # 根据招投标信息推断
        if bidding and bidding not in ("未提取到", "未明确"):
            if "中标" in bidding and "招投标合作" not in tags:
                tags.append("招投标合作")
            if "采购" in bidding and "批量供货" not in tags:
                tags.append("批量供货")

        # 根据合作企业推断
        if coop and coop not in ("未提取到", "未明确"):
            if "供应链配套" not in tags:
                tags.append("供应链配套")

        if not tags:
            self.uncertain_tags.append({"tag_category": "服务标签", "sub_category": "合作模式标签", "reason": "cooperative_enterprise/bidding_projects字段无法推断合作模式"})
            return [{"tag": "合作模式-未明确", "source_field": "cooperative_enterprise", "confidence": 0.0}]

        conf = 0.88
        return [{"tag": t, "source_field": "cooperative_enterprise", "confidence": conf} for t in tags[:6]]

    def _gen_service_coverage_tags(self, data: dict) -> List[dict]:
        """服务覆盖范围标签"""
        coop = data.get("cooperative_enterprise", "")
        address = data.get("register_address", "")

        tags = []

        # 从合作企业推断覆盖范围
        if coop and coop not in ("未提取到", "未明确"):
            coop_list = [e.strip() for e in re.split(r'[,，、；;]+', coop) if e.strip()]
            if len(coop_list) >= 3:
                tags.append("全国")
            elif coop_list:
                # 检查是否为头部企业
                has_famous = any(e in FAMOUS_ENTERPRISE_SCENE for e in coop_list)
                if has_famous:
                    tags.append("头部轴承企业配套")
                else:
                    tags.append("区域市场")

        # 从地址推断
        if address and address not in ("未提取到", "未明确"):
            if any(p in address for p in ["洛阳", "瓦房店", "哈尔滨", "新昌", "慈溪", "聊城"]):
                if "轴承产业集群地" not in tags:
                    tags.append("轴承产业集群地")

        if not tags:
            self.uncertain_tags.append({"tag_category": "服务标签", "sub_category": "服务覆盖范围", "reason": "无法推断服务覆盖范围"})
            return [{"tag": "覆盖范围-未明确", "source_field": "cooperative_enterprise", "confidence": 0.0}]

        conf = 0.85
        return [{"tag": t, "source_field": "cooperative_enterprise", "confidence": conf} for t in tags[:6]]

    def _gen_value_added_tags(self, data: dict) -> List[dict]:
        """增值服务标签"""
        scope = data.get("business_scope", "")
        tags = []

        value_keywords = {
            "技术咨询": "技术咨询", "技术支持": "技术支持服务",
            "售后": "售后维护服务", "维修": "轴承维修服务",
            "培训": "技术培训", "升级": "产品升级迭代",
            "检测": "轴承检测服务", "认证": "检测认证服务",
            "方案": "整体解决方案", "解决方案": "整体解决方案",
            "咨询": "技术咨询", "轴承设计": "轴承设计服务",
            "润滑": "润滑咨询", "选型": "轴承选型服务",
        }

        for kw, label in value_keywords.items():
            if kw in scope and label not in tags:
                tags.append(label)

        if not tags:
            self.uncertain_tags.append({"tag_category": "服务标签", "sub_category": "增值服务标签", "reason": "business_scope字段无法提取增值服务"})
            return [{"tag": "增值服务-未明确", "source_field": "business_scope", "confidence": 0.0}]

        conf = 0.82
        return [{"tag": t, "source_field": "business_scope", "confidence": conf} for t in tags[:6]]

    # ----------------------------------------------------------
    # 能力标签
    # ----------------------------------------------------------
    def _gen_tech_ability_tags(self, data: dict) -> List[dict]:
        """技术能力标签"""
        tags = []
        high_tech = data.get("high_tech_enterprise", "")
        patent = data.get("patent_count", "")
        main_biz = data.get("main_business", "")
        core_products = data.get("core_products", "")

        # 高新技术企业
        if high_tech == "是":
            tags.append("高新技术企业")
        elif high_tech == "未明确":
            pass
        else:
            self.uncertain_tags.append({"tag_category": "能力标签", "sub_category": "技术能力标签", "reason": "high_tech_enterprise字段为否或未明确"})

        # 专利分析
        if patent and patent not in ("未提取到", "未明确"):
            # 提取专利数量
            num_match = re.search(r'(\d+)', patent)
            if num_match:
                num = int(num_match.group(1))
                if num >= 50:
                    tags.append("专利密集型")
                elif num >= 20:
                    tags.append("专利较多型")

            # 提取专利技术方向
            tech_directions = {
                "轴承": "轴承设计技术", "滚子": "滚子加工技术",
                "保持架": "保持架制造技术", "密封": "密封技术",
                "润滑": "润滑技术", "热处理": "热处理技术",
                "磨削": "精密磨削技术", "超精": "超精加工技术",
                "锻造": "锻造技术", "材料": "材料技术",
                "陶瓷": "陶瓷轴承技术", "仿真": "有限元分析技术",
                "振动": "振动噪声分析", "寿命": "寿命预测技术",
            }
            for kw, label in tech_directions.items():
                if kw in patent and label not in tags:
                    tags.append(label)
        else:
            self.uncertain_tags.append({"tag_category": "能力标签", "sub_category": "技术能力标签", "reason": "patent_count字段为空"})

        # 从主营业务推断技术方向
        combined = f"{main_biz} {core_products}"
        tech_keywords = {
            "深沟球": "深沟球轴承技术", "圆锥滚子": "圆锥滚子轴承技术",
            "调心": "调心轴承技术", "角接触": "角接触轴承技术",
            "推力": "推力轴承技术", "直线": "直线运动技术",
            "陶瓷": "陶瓷轴承技术", "精密": "精密加工技术",
            "高速": "高速轴承技术", "高温": "高温轴承技术",
            "密封": "密封技术", "润滑": "润滑技术",
            "保持架": "保持架技术", "热处理": "热处理技术",
        }
        for kw, label in tech_keywords.items():
            if kw in combined and label not in tags:
                tags.append(label)

        if not tags:
            self.uncertain_tags.append({"tag_category": "能力标签", "sub_category": "技术能力标签", "reason": "无法提取技术能力标签"})
            return [{"tag": "技术能力-未明确", "source_field": "patent_count", "confidence": 0.0}]

        conf = 0.90
        return [{"tag": t, "source_field": "high_tech_enterprise", "confidence": conf} for t in tags[:8]]

    def _gen_production_ability_tags(self, data: dict) -> List[dict]:
        """生产能力标签"""
        tags = []
        employee = data.get("employee_scale", "")
        investment = data.get("investment_projects", "")

        # 员工规模
        if employee and employee not in ("未提取到", "未明确"):
            emp_match = re.search(r'(\d+)', employee.replace(",", ""))
            if emp_match:
                emp_num = int(emp_match.group(1))
                if emp_num >= 1000:
                    tags.append("大型生产企业")
                elif emp_num >= 500:
                    tags.append("中大型生产企业")
                elif emp_num >= 100:
                    tags.append("中型生产企业")
                else:
                    tags.append("小型生产企业")
            else:
                # 按档位关键词
                if "大型" in employee:
                    tags.append("大型生产企业")
                elif "中型" in employee:
                    tags.append("中型生产企业")

        # 投资项目
        if investment and investment not in ("未提取到", "未明确"):
            # 提取产线信息
            if "生产线" in investment or "产线" in investment:
                line_match = re.search(r'(\d+)\s*条', investment)
                if line_match and int(line_match.group(1)) >= 3:
                    tags.append("多条产线")
                else:
                    tags.append("产线扩建")

            # 提取投资额
            inv_match = re.search(r'(\d+(?:\.\d+)?)\s*亿', investment)
            if inv_match:
                inv_val = float(inv_match.group(1))
                if inv_val >= 5:
                    tags.append("重资产投资")
                elif inv_val >= 1:
                    tags.append("产能升级能力")

            # 产能关键词
            prod_keywords = {
                "锻造": "锻造产线", "车削": "车削产线",
                "磨削": "磨削产线", "热处理": "热处理产线",
                "装配": "装配产线", "超精": "超精加工产线",
            }
            for kw, label in prod_keywords.items():
                if kw in investment and label not in tags:
                    tags.append(label)

        if not tags:
            self.uncertain_tags.append({"tag_category": "能力标签", "sub_category": "生产能力标签", "reason": "employee_scale/investment_projects字段为空"})
            return [{"tag": "生产能力-未明确", "source_field": "employee_scale", "confidence": 0.0}]

        conf = 0.88
        return [{"tag": t, "source_field": "employee_scale", "confidence": conf} for t in tags[:8]]

    def _gen_cert_ability_tags(self, data: dict) -> List[dict]:
        """资质能力标签"""
        tags = []
        specialized = data.get("specialized_enterprise", "")
        cert = data.get("industry_cert", "")

        if specialized == "是":
            tags.append("专精特新企业")
        elif specialized not in ("否", "未明确", ""):
            tags.append("专精特新企业")

        # 从认证提取资质标签
        if cert and cert not in ("未提取到", "未明确"):
            cert_keywords = {
                "ISO9001": "ISO9001认证", "ISO14001": "ISO14001认证",
                "IATF16949": "IATF16949认证", "AS9100": "AS9100认证",
                "API": "API认证", "CRCC": "CRCC认证",
                "IRIS": "IRIS认证", "RoHS": "RoHS合规",
                "CE": "CE认证", "TS16949": "IATF16949认证",
                "ISO/TS22163": "IRIS认证",
            }
            for kw, label in cert_keywords.items():
                if kw in cert and label not in tags:
                    tags.append(label)

        if not tags:
            self.uncertain_tags.append({"tag_category": "能力标签", "sub_category": "资质能力标签", "reason": "specialized_enterprise/industry_cert字段为空"})
            return [{"tag": "资质能力-未明确", "source_field": "specialized_enterprise", "confidence": 0.0}]

        conf = 0.92
        return [{"tag": t, "source_field": "specialized_enterprise", "confidence": conf} for t in tags[:8]]

    def _gen_financial_ability_tags(self, data: dict) -> List[dict]:
        """资金实力标签"""
        tags = []
        capital = data.get("registered_capital", "")
        investment = data.get("investment_projects", "")

        # 注册资本分析
        if capital and capital not in ("未提取到", "未明确"):
            # 提取金额
            cap_wan = re.search(r'(\d+(?:\.\d+)?)\s*万', capital)
            cap_yi = re.search(r'(\d+(?:\.\d+)?)\s*亿', capital)

            cap_value = 0
            if cap_yi:
                cap_value = float(cap_yi.group(1)) * 10000
            elif cap_wan:
                cap_value = float(cap_wan.group(1))

            if cap_value >= 10000:
                tags.append("高注册资本（≥1亿）")
            elif cap_value >= 5000:
                tags.append("高注册资本（≥5000万）")
            elif cap_value >= 1000:
                tags.append("中等注册资本")
            else:
                tags.append("中小规模注册资本")

        # 投资项目分析
        if investment and investment not in ("未提取到", "未明确"):
            inv_yi = re.search(r'(\d+(?:\.\d+)?)\s*亿', investment)
            if inv_yi:
                inv_val = float(inv_yi.group(1))
                if inv_val >= 5:
                    if "重资产投资" not in tags:
                        tags.append("重资产投资")
                elif inv_val >= 1:
                    if "产能升级能力" not in tags:
                        tags.append("产能升级能力")

        if not tags:
            self.uncertain_tags.append({"tag_category": "能力标签", "sub_category": "资金实力标签", "reason": "registered_capital/investment_projects字段为空"})
            return [{"tag": "资金实力-未明确", "source_field": "registered_capital", "confidence": 0.0}]

        conf = 0.90
        return [{"tag": t, "source_field": "registered_capital", "confidence": conf} for t in tags[:6]]

    # ----------------------------------------------------------
    # 主流程
    # ----------------------------------------------------------
    def generate_tags(self, data: dict) -> dict:
        """生成完整标签体系"""
        self.uncertain_tags = []

        self._report_progress(82, "产品标签生成", "提取核心产品类型/规格/应用场景/合规标签")

        # 产品标签
        product_tags = {
            "核心产品类型": self._gen_product_type_tags(data),
            "产品规格标签": self._gen_product_spec_tags(data),
            "产品应用场景": self._gen_application_scene_tags(data),
            "产品合规标签": self._gen_compliance_tags(data),
        }

        self._report_progress(86, "服务标签生成", "提取服务类型/合作模式/覆盖范围/增值服务标签")

        # 服务标签
        service_tags = {
            "核心服务类型": self._gen_service_type_tags(data),
            "合作模式标签": self._gen_coop_mode_tags(data),
            "服务覆盖范围": self._gen_service_coverage_tags(data),
            "增值服务标签": self._gen_value_added_tags(data),
        }

        self._report_progress(90, "能力标签生成", "提取技术能力/生产能力/资质/资金实力标签")

        # 能力标签
        ability_tags = {
            "技术能力标签": self._gen_tech_ability_tags(data),
            "生产能力标签": self._gen_production_ability_tags(data),
            "资质能力标签": self._gen_cert_ability_tags(data),
            "资金实力标签": self._gen_financial_ability_tags(data),
        }

        self._report_progress(93, "置信度计算", "汇总标签置信度与异常标注")

        # LLM 增强打标：当存在 "未明确" 标签时，使用大模型补充
        if self._llm_client and self.uncertain_tags:
            product_tags, service_tags, ability_tags = self._llm_enhance_tags(
                data, product_tags, service_tags, ability_tags
            )

        # 计算标签置信度
        all_tags = []
        for category in [product_tags, service_tags, ability_tags]:
            for sub_tags in category.values():
                all_tags.extend(sub_tags)
        valid_confidences = [t["confidence"] for t in all_tags if t["confidence"] > 0]
        tag_confidence = round(sum(valid_confidences) / len(valid_confidences), 2) if valid_confidences else 0.0

        result = {
            "enterprise_info": {
                "enterprise_name": data.get("enterprise_name", "未提取到"),
                "enterprise_short_name": data.get("enterprise_short_name", ""),
                "industry_segment": data.get("industry_segment", "未明确"),
                "data_source": data.get("data_source", "未提取到"),
                "tag_confidence": tag_confidence,
                "tag_generate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "tag_system": {
                "产品标签": product_tags,
                "服务标签": service_tags,
                "能力标签": ability_tags,
            },
            "uncertain_tags": self.uncertain_tags,
            "note": self._generate_note(data, tag_confidence),
        }

        return result

    # ----------------------------------------------------------
    # LLM 增强打标
    # ----------------------------------------------------------
    def _llm_enhance_tags(self, data: dict, product_tags: dict, service_tags: dict, ability_tags: dict):
        """使用 LLM 补充规则未能生成的标签"""
        # 收集所有 "未明确" 标签的类别
        uncertain_categories = [t.get("sub_category", "") for t in self.uncertain_tags]
        if not uncertain_categories:
            return product_tags, service_tags, ability_tags

        # 收集企业关键信息供 LLM 分析
        enterprise_info = {
            "enterprise_name": data.get("enterprise_name", ""),
            "main_business": data.get("main_business", ""),
            "core_products": data.get("core_products", ""),
            "business_scope": data.get("business_scope", ""),
            "product_spec": data.get("product_spec", ""),
            "cooperative_enterprise": data.get("cooperative_enterprise", ""),
            "bidding_projects": data.get("bidding_projects", ""),
            "industry_cert": data.get("industry_cert", ""),
            "registered_capital": data.get("registered_capital", ""),
            "employee_scale": data.get("employee_scale", ""),
            "patent_count": data.get("patent_count", ""),
            "industry_segment": data.get("industry_segment", ""),
        }

        self._report_progress(91, "LLM 增强打标", f"使用大模型补充 {len(uncertain_categories)} 个未明确标签类别")

        system_prompt = (
            "你是轴承行业企业标签分析专家。请根据企业信息，为指定类别生成准确的标准标签。"
            "只返回 JSON 格式。每个标签需包含 tag（标签名）和 confidence（置信度 0-1）。"
        )
        user_prompt = (
            f"企业信息：\n{json.dumps(enterprise_info, ensure_ascii=False, indent=2)}\n\n"
            f"以下标签类别未被规则方法识别，请分析企业信息后生成标签：\n"
            + "\n".join(f"- {c}" for c in uncertain_categories)
            + "\n\n请返回 JSON，key 为标签类别，value 为标签数组。示例：\n"
            + '{"核心产品类型": [{"tag": "深沟球轴承", "confidence": 0.85}]}'
        )

        try:
            from backend.services.llm_client import llm_chat_json
            llm_result = llm_chat_json(self._llm_client, system_prompt, user_prompt)
            if not llm_result or not isinstance(llm_result, dict):
                return product_tags, service_tags, ability_tags

            # 将 LLM 生成的标签合并到对应类别
            all_tag_groups = {
                "产品标签": product_tags,
                "服务标签": service_tags,
                "能力标签": ability_tags,
            }
            for tag_group in all_tag_groups.values():
                for sub_key, tag_list in tag_group.items():
                    # 检查当前类别是否是 "未明确"
                    has_uncertain = any(
                        t.get("confidence", 0) == 0.0 and "未明确" in t.get("tag", "")
                        for t in tag_list
                    )
                    if has_uncertain and sub_key in llm_result:
                        llm_tags = llm_result[sub_key]
                        if isinstance(llm_tags, list) and llm_tags:
                            # 替换 "未明确" 标签为 LLM 生成的标签
                            new_tags = []
                            for t in llm_tags:
                                if isinstance(t, dict) and t.get("tag"):
                                    new_tags.append({
                                        "tag": t["tag"],
                                        "source_field": "llm_enhanced",
                                        "confidence": min(float(t.get("confidence", 0.8)), 0.95),
                                    })
                            if new_tags:
                                tag_group[sub_key] = new_tags
                                # 从 uncertain_tags 中移除
                                self.uncertain_tags = [
                                    ut for ut in self.uncertain_tags
                                    if ut.get("sub_category") != sub_key
                                ]

        except Exception as e:
            print(f"[LLM增强] 打标阶段补充失败: {e}")

        return product_tags, service_tags, ability_tags

    def _generate_note(self, data: dict, confidence: float) -> str:
        """生成备注说明"""
        notes = []
        if confidence >= 0.90:
            notes.append("标签生成正常，核心标签基于模块2结构化字段")
        elif confidence >= 0.70:
            notes.append("标签生成部分完成，部分字段缺失影响标签覆盖")
        else:
            notes.append("标签生成受限，多数字段缺失")

        uncertain = [f["reason"] for f in self.uncertain_tags]
        if uncertain:
            notes.append(f"未明确标签{len(uncertain)}项：{'; '.join(uncertain[:3])}")

        return "；".join(notes)

    def save_to_file(self, data: dict, enterprise_name: str) -> str:
        """将标签结果写入项目的 output 目录"""
        output_dir = self.output_dir
        os.makedirs(output_dir, exist_ok=True)

        safe_name = re.sub(r'[\\/:*?"<>|]', '_', enterprise_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}_tag.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath


# ============================================================
# CLI 入口
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="轴承行业企业基础静态属性标签生成")
    parser.add_argument("input_file", help="清洗输出JSON文件路径")
    parser.add_argument("--output-dir", help="输出目录（默认为当前工作目录下的 output）", default=None)
    args = parser.parse_args()

    input_path = args.input_file

    if not os.path.exists(input_path):
        print(f"错误: 文件不存在 - {input_path}")
        sys.exit(1)

    # 读取模块2输出的结构化数据
    with open(input_path, 'r', encoding='utf-8') as f:
        cleaned_data = json.load(f)

    enterprise_name = cleaned_data.get("enterprise_name", "未知企业")
    print(f"正在生成标签: {enterprise_name}")

    # 生成标签
    tagger = EnterpriseTagger(output_dir=args.output_dir)
    result = tagger.generate_tags(cleaned_data)

    # 保存结果
    output_path = tagger.save_to_file(result, enterprise_name)

    # 输出摘要
    print(f"\n{'='*60}")
    print(f"企业: {enterprise_name}")
    print(f"标签置信度: {result['enterprise_info']['tag_confidence']}")
    print(f"\n--- 产品标签 ---")
    for sub, tags in result["tag_system"]["产品标签"].items():
        tag_names = [t["tag"] for t in tags]
        print(f"  {sub}: {', '.join(tag_names)}")
    print(f"\n--- 服务标签 ---")
    for sub, tags in result["tag_system"]["服务标签"].items():
        tag_names = [t["tag"] for t in tags]
        print(f"  {sub}: {', '.join(tag_names)}")
    print(f"\n--- 能力标签 ---")
    for sub, tags in result["tag_system"]["能力标签"].items():
        tag_names = [t["tag"] for t in tags]
        print(f"  {sub}: {', '.join(tag_names)}")

    if result["uncertain_tags"]:
        print(f"\n未明确标签: {len(result['uncertain_tags'])} 项")
        for ut in result["uncertain_tags"][:5]:
            print(f"  - [{ut['tag_category']}/{ut['sub_category']}] {ut['reason']}")

    print(f"\n备注: {result['note']}")
    print(f"\n结果已保存到: {output_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

