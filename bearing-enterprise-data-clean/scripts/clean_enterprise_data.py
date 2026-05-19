#!/usr/bin/env python3
"""
轴承行业数据结构化清洗脚本
承接 bearing-enterprise-data-crawl 输出的原始数据，完成清洗、结构化提取
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

sys.stdout.reconfigure(encoding='utf-8')


# ===================== 轴承行业专属词典 =====================

# 细分领域关键词
INDUSTRY_SEGMENTS = {
    "滚动轴承制造": ["滚动轴承", "球轴承", "滚子轴承", "深沟球轴承", "圆锥滚子轴承",
                    "调心球轴承", "调心滚子轴承", "圆柱滚子轴承", "角接触球轴承",
                    "推力球轴承", "推力滚子轴承", "轴承单元"],
    "滑动轴承制造": ["滑动轴承", "滑动轴套", "自润滑轴承", "含油轴承", "无油轴承",
                    "衬套", "轴瓦", "滑动轴承合金", "巴氏合金"],
    "关节轴承制造": ["关节轴承", "杆端关节轴承", "向心关节轴承", "推力关节轴承"],
    "直线运动轴承": ["直线轴承", "直线导轨", "滚珠丝杠", "直线运动系统",
                    "滚柱导轨", "交叉滚子导轨", "直线电机"],
    "轴承零部件制造": ["轴承保持架", "保持架", "滚动体", "钢球", "陶瓷球",
                      "滚子", "密封件", "防尘盖", "轴承套圈", "内圈", "外圈"],
    "轴承钢材料": ["轴承钢", "高碳铬轴承钢", "渗碳轴承钢", "GCr15", "SUJ2",
                  "不锈钢轴承", "陶瓷轴承", "混合陶瓷轴承"],
    "轴承装备制造": ["轴承磨床", "轴承车床", "超精加工机", "轴承装配线",
                    "轴承检测设备", "清洗机", "热处理设备"],
}

# 行业资质认证
CERTIFICATION_KEYWORDS = {
    "ISO9001": ["ISO9001", "ISO 9001", "质量管理体系"],
    "ISO14001": ["ISO14001", "ISO 14001", "环境管理体系"],
    "IATF16949": ["IATF16949", "IATF 16949", "TS16949", "汽车质量体系"],
    "AS9100": ["AS9100", "AS9100D", "航空航天质量体系"],
    "API": ["API认证", "API标准", "美国石油学会认证"],
    "CRCC": ["CRCC认证", "铁路产品认证", "中铁认证"],
    "IRIS": ["IRIS认证", "ISO/TS 22163", "铁路行业质量体系"],
    "RoHS": ["RoHS", "ROHS", "有害物质限制"],
    "CE": ["CE认证", "CE标识", "欧盟认证"],
    "ISO45001": ["ISO45001", "ISO 45001", "职业健康安全"],
}

# 经营状态映射
OPERATING_STATUS_MAP = {
    "存续": ["存续", "在营", "开业", "在业", "正常", "在册"],
    "注销": ["注销", "吊销", "撤销"],
    "迁出": ["迁出", "迁入"],
    "停业": ["停业", "歇业", "清算"],
}

# 企业类型映射
ENTERPRISE_TYPE_MAP = {
    "有限责任公司（自然人投资或控股）": ["有限责任公司", "有限公司", "自然人投资或控股"],
    "股份有限公司": ["股份有限公司", "股份公司"],
    "外商投资企业": ["外商投资", "外资", "合资", "中外合资", "外商独资"],
    "国有企业": ["国有", "国有独资", "全民所有制"],
    "私营企业": ["私营", "民营"],
}

# 核心产品规格正则
PRODUCT_SPEC_PATTERNS = [
    # 轴承内径
    r'内径\s*[:：]?\s*([\d.]+)\s*mm',
    r'内径d\s*[:：]?\s*([\d.]+)\s*mm',
    # 轴承外径
    r'外径\s*[:：]?\s*([\d.]+)\s*mm',
    r'外径D\s*[:：]?\s*([\d.]+)\s*mm',
    # 轴承宽度
    r'宽度\s*[:：]?\s*([\d.]+)\s*mm',
    r'宽度B\s*[:：]?\s*([\d.]+)\s*mm',
    # 精度等级
    r'(?:精度等级|精度)\s*[:：]?\s*(P[0-6]|ABEC[-\d]+)',
    # 额定载荷
    r'额定动载荷\s*[:：]?\s*([\d.]+)\s*k?N',
    r'额定静载荷\s*[:：]?\s*([\d.]+)\s*k?N',
    # 极限转速
    r'极限转速\s*[:：]?\s*([\d,]+)\s*r(?:/min|pm)?',
    # 轴承型号
    r'(?:轴承型号|型号)\s*[:：]?\s*([A-Z0-9/-]+)',
]

# 日期正则
DATE_PATTERNS = [
    r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
    r'(\d{4})\s*[-/年]\s*(\d{1,2})\s*[-/月]\s*(\d{1,2})',
    r'(\d{4})\s*年\s*(\d{1,2})\s*月',
    r'成立于?\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
]

# 地址正则
ADDRESS_PATTERNS = [
    r'(?:注册地址|地址|住所|经营地址|位于|供应商地址)\s*[:：]?\s*([\u4e00-\u9fa5\d\-省市县区路街道号室栋楼层]+)',
    r'((?:北京|上海|天津|重庆|广东|浙江|江苏|山东|福建|四川|陕西|湖北|湖南|安徽|河北|河南|辽宁|江西|广西|云南|贵州|甘肃|海南|宁夏|青海|新疆|西藏|内蒙古)[\u4e00-\u9fa5\d\-省市县区路街道号室栋楼层]+)',
]

# 专利正则
PATENT_PATTERNS = [
    r'(?:拥有|持有|获批|授权)\s*(\d+)\s*项\s*(?:发明)?专利',
    r'(?:发明)?专利\s*(\d+)\s*项',
    r'(\d+)\s*项\s*(?:发明)?专利',
    r'(?:实用新型|外观设计)\s*(\d+)\s*项',
]

# ===================== 噪声过滤规则 =====================

# 网站导航/页脚噪声关键词（出现这些则整行/整段删除）
NOISE_LINE_KEYWORDS = [
    # 天眼查/企查查导航
    "查公司", "查老板", "查关系", "天眼一下", "打开天眼查APP",
    "开通会员", "个人VIP", "SVIP", "企业套餐", "登录/注册",
    "风险监控", "尽职调查", "舆情管理", "营销拓客",
    "数据API", "专业版", "风险管理解决方案", "商务合作", "企业门户",
    "知识产权", "查商标", "查专利", "查著作权", "查网站",
    "查招聘", "查榜单", "查公告", "产业链", "千寻地图",
    "新增企业", "招标查查", "建筑查查", "网络核查", "企业核名",
    "空壳扫描", "工商接口", "人员名录", "失信被执行人",
    "受益所有人", "企业产品中心", "企查查移动版", "企业税号查询",
    "全球企业查询", "企查查MCP",
    # 用户协议/隐私政策
    "隐私政策", "用户协议", "版权政策", "免责声明", "投诉指引",
    "意见反馈", "已收集个人信息清单", "第三方信息共享清单",
    "限制民事行为能力人", "未经天眼查事先明示同意",
    "加粗方式显著标示", "您应立即停止注册",
    # 备案/版权
    "ICP备", "增值电信业务经营许可证", "京公网安备",
    "苏ICP备", "苏公网安备", "版权所有",
    # 人名列表（企查查人员名录页）
    "贝文彪", "茅健", "乌兰", "钭正刚", "韶铁山",
    # 登录/注册相关
    "验证码登录", "密码登录", "扫码成功", "二维码已失效",
    "已阅读并同意", "《用户协议》", "《隐私政策》",
    # 客服
    "客服电话", "工作时间", "客服邮箱",
]

# 连续噪声行阈值：如果一段内连续3行以上匹配噪声关键词，则丢弃整段
NOISE_LINE_THRESHOLD = 2

# 网站纯导航段模式（匹配整段内容全是导航的）
NOISE_BLOCK_PATTERNS = [
    # 纯导航菜单
    r'^(?:综合查询|高级搜索|批量查询|找关系|全球企业|企业风控|司法大数据|信用大数据|专项数据|场景应用|经营状况查询|专项查询|专业版)(?:\s+|$)',
    # 纯备案号行
    r'^[粤京沪苏浙]\w*ICP备\d+号',
    # 人员名录页
    r'^(?:贝|茅|乌|钭|韶|蓟|索|贡|劳|堵|宰|璩|寿|通|郏|充|宦|庾|暨|弘|殴|沃|夔|厍|那|空|毋|乜|养|後|益|公)',
]

# 高价值数据源关键词（出现在【来源: xxx】之后的段落中）
HIGH_VALUE_SOURCE_KEYWORDS = {
    "ccgp.gov.cn": "政府采购",      # 招投标
    "cnipa": "知识产权局",           # 专利
    "gov.cn": "政府公示",            # 工商
    "aiqicha.baidu.com": "爱企查",   # 工商
}


# ===================== 核心清洗类 =====================

class BearingDataCleaner:
    """轴承行业数据结构化清洗器"""

    def __init__(self, progress_callback=None, output_dir: str = None, llm_client=None):
        self.result = {}
        self.uncertain_fields = []
        self.progress_callback = progress_callback
        self.raw_text = ""
        self.source_info = {}
        self.filtered_text = ""  # 噪声过滤后的文本
        self._high_value_sections = []  # 高价值段落
        self._diagnostic_info = {}  # 诊断信息（错误处理增强）
        self._llm_client = llm_client  # 可选的 LLM 客户端
        # 输出目录：优先使用指定目录，否则使用当前工作目录下的 output
        # 输出目录优先级: --output-dir 参数 > PROJECT_DIR 环境变量 > 当前工作目录
        if output_dir:
            self.output_dir = output_dir
        elif os.environ.get("PROJECT_DIR"):
            self.output_dir = os.path.join(os.environ.get("PROJECT_DIR"), "output")
        else:
            self.output_dir = os.path.join(os.getcwd(), "output")

        # 尝试加载SimHash去重器（可选增强）
        self._use_simhash = False
        try:
            _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if _project_root not in sys.path:
                sys.path.insert(0, _project_root)
            from common.dedup import SimHashDeduplicator
            self._simhash_dedup = SimHashDeduplicator(threshold=3)
            self._use_simhash = True
        except ImportError:
            pass

    def _report_progress(self, progress: int, step: str, detail: str = ""):
        """报告清洗进度"""
        if self.progress_callback:
            self.progress_callback(progress, "模块2清洗", step, detail)

    def load_input(self, input_data: Dict[str, Any]) -> bool:
        """加载 bearing-enterprise-data-crawl 输出的原始数据"""
        if isinstance(input_data, dict):
            self.source_info = input_data
        else:
            return False

        # 合并所有原始文本
        raw_content = self.source_info.get("raw_content", {})
        parts = []
        for key, value in raw_content.items():
            if value and key != "all_content":
                parts.append(value)

        # 优先使用 all_content，如果为空则拼接
        self.raw_text = raw_content.get("all_content", "") or "\n".join(parts)

        if not self.raw_text.strip():
            return False
        return True

    # ---------- 1. 文本预处理 + 噪声深度过滤 ----------

    def preprocess_text(self) -> str:
        """文本预处理：深度噪声过滤 + 清洗无效字符"""
        text = self.raw_text

        # 1.1 按【来源:】分段处理，保留来源信息
        sections = re.split(r'(【来源[：:][^】]*】)', text)

        # 重组：把来源标注和其内容配对
        source_sections = []
        current_source = ""
        i = 0
        while i < len(sections):
            s = sections[i].strip()
            if re.match(r'【来源[：:]', s):
                current_source = s
                # 下一个元素是该来源的内容
                if i + 1 < len(sections):
                    content = sections[i + 1].strip()
                    source_sections.append((current_source, content))
                    i += 2
                    continue
            elif s:
                source_sections.append(("", s))
            i += 1

        filtered_sections = []
        for source_tag, section in source_sections:
            if not section:
                continue

            # 判断是否为高价值来源
            is_high_value = False
            for domain, label in HIGH_VALUE_SOURCE_KEYWORDS.items():
                if domain in source_tag:
                    is_high_value = True
                    break
            # 政府采购/招投标来源一定保留
            if 'ccgp' in source_tag or 'ggzy' in source_tag:
                is_high_value = True

            # 按行过滤噪声（逐行判断，只跳过纯噪声行）
            lines = section.split('\n')
            clean_lines = []

            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    continue

                # 检测是否为噪声行
                is_noise = False

                # 规则1: 一行包含3个以上导航关键词 = 导航行
                noise_keyword_count = sum(1 for kw in NOISE_LINE_KEYWORDS if kw in line_stripped)
                if noise_keyword_count >= 3:
                    is_noise = True

                # 规则2: 匹配纯噪声模式
                for pattern in NOISE_BLOCK_PATTERNS:
                    if re.match(pattern, line_stripped):
                        is_noise = True
                        break

                # 规则3: 纯备案号行
                if re.search(r'ICP[备证]\d+', line_stripped) and len(line_stripped) < 50:
                    is_noise = True

                # 规则4: 纯英文+符号的短行（页面元素残留）
                if len(line_stripped) < 30 and re.match(r'^[a-zA-Z\s&;,.>/\-=_()]+$', line_stripped):
                    is_noise = True

                # 高价值来源：即使有少量噪声关键词也不丢弃
                if is_high_value and noise_keyword_count < 5:
                    is_noise = False

                if not is_noise:
                    clean_lines.append(line_stripped)

            # 只要还有有效内容就保留
            if clean_lines:
                filtered_text = ' '.join(clean_lines)
                if is_high_value:
                    # 高价值来源内容加权（重复一次，增加被匹配概率）
                    filtered_sections.append(filtered_text)
                    filtered_sections.append(filtered_text)
                else:
                    filtered_sections.append(filtered_text)

        text = '\n'.join(filtered_sections)

        # 1.2 移除来源标注
        text = re.sub(r'【来源[：:].*?】', '', text)
        text = re.sub(r'【企业官网内容】|【政府公示内容】|【招投标内容】|【专利信息】|【新闻信息】|【合并全部内容】', '', text)

        # 1.3 移除 HTML 残留
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        text = re.sub(r'&nbsp;', ' ', text)

        # 1.4 移除特殊字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # 1.5 统一空白
        text = re.sub(r'[ \t]+', ' ', text).strip()

        # 1.6 去除重复句子（按句号分段）
        sentences = re.split(r'[。；\n]', text)
        if self._use_simhash:
            # SimHash语义去重（识别表述不同但语义相似的重复）
            unique = self._simhash_dedup.deduplicate_sentences(sentences)
        else:
            # 回退：简单归一化去重
            seen = set()
            unique = []
            for s in sentences:
                s = s.strip()
                if not s or len(s) < 5:
                    continue
                s_norm = re.sub(r'\s+', '', s)
                if s_norm not in seen and len(s_norm) > 4:
                    seen.add(s_norm)
                    unique.append(s)
        text = '。'.join(unique)

        # 1.7 去除超长重复片段（API描述等整段重复）
        if len(text) > 300:
            paragraphs = text.split('。')
            from collections import Counter
            para_norms = [re.sub(r'\s+', '', p) for p in paragraphs if len(re.sub(r'\s+', '', p)) > 20]
            para_counts = Counter(para_norms)
            repeated_paras = {p for p, cnt in para_counts.items() if cnt >= 2}
            if repeated_paras:
                clean_paragraphs = []
                for p in paragraphs:
                    p = p.strip()
                    if not p:
                        continue
                    p_norm = re.sub(r'\s+', '', p)
                    if p_norm not in repeated_paras:
                        clean_paragraphs.append(p)
                text = '。'.join(clean_paragraphs)

        self.filtered_text = text
        return text

    def _get_search_text(self) -> str:
        """获取用于正则匹配的文本（过滤后文本 + 原始文本合并，确保信息不丢失）"""
        # 优先使用过滤后文本，但始终拼接原始文本作为回退
        if self.filtered_text.strip():
            return self.filtered_text + "\n" + self.raw_text
        return self.raw_text

    def _search(self, pattern: str, text: str = None, flags: int = 0) -> Optional[re.Match]:
        """多级文本搜索：先在过滤后文本匹配，失败则回退到原始文本"""
        if text is not None:
            return re.search(pattern, text, flags)
        # 先搜过滤后文本
        if self.filtered_text.strip():
            m = re.search(pattern, self.filtered_text, flags)
            if m:
                return m
        # 回退到原始文本
        if self.raw_text.strip():
            m = re.search(pattern, self.raw_text, flags)
            if m:
                return m
        return None

    def _find_all(self, pattern: str, text: str = None, flags: int = 0) -> List[re.Match]:
        """多级文本搜索：findall 版本"""
        if text is not None:
            return re.findall(pattern, text, flags)
        results = []
        if self.filtered_text.strip():
            results = re.findall(pattern, self.filtered_text, flags)
        if not results and self.raw_text.strip():
            results = re.findall(pattern, self.raw_text, flags)
        return results

    # ---------- 2. 企业基础信息提取 ----------

    def extract_enterprise_name(self) -> str:
        """提取标准化企业全称"""
        name = self.source_info.get("enterprise_name", "")
        text = self._get_search_text()

        if not name or name in ("未提取到", "未明确"):
            # 正则提取
            patterns = [
                r'([\u4e00-\u9fa5]+(?:股份有限公司|有限责任公司|有限公司))',
                r'([\u4e00-\u9fa5]+(?:轴承|精密|机械|传动|冶金|装备|机电|五金|钢铁)+有限公司)',
            ]
            for p in patterns:
                m = re.search(p, text)
                if m and len(m.group(1)) >= 4:
                    name = m.group(1)
                    break
        self.result["enterprise_name"] = name if name else ""
        return name

    def extract_short_name(self) -> str:
        """提取企业简称"""
        name = self.result.get("enterprise_name", "")
        short = name
        for suffix in ["股份有限公司", "有限公司", "有限责任公司", "公司"]:
            if short.endswith(suffix):
                short = short[:-len(suffix)]
                break
        self.result["enterprise_short_name"] = short
        return short

    def extract_establish_time(self) -> str:
        """提取成立时间"""
        # 策略1: 带上下文关键词的日期
        for pattern in DATE_PATTERNS:
            m = self._search(pattern)
            if m:
                groups = m.groups()
                if len(groups) >= 3:
                    time_str = f"{groups[0]}-{int(groups[1]):02d}-{int(groups[2]):02d}"
                elif len(groups) >= 2:
                    time_str = f"{groups[0]}-{int(groups[1]):02d}"
                else:
                    time_str = groups[0]
                context_start = max(0, m.start() - 30)
                context = m.string[context_start:m.start()]
                if any(kw in context for kw in ['成立', '设立', '创建', '创办', '注册于', '登记于']):
                    self.result["establish_time"] = time_str
                    return time_str

        # 策略2: "成立" + 日期组合
        for pattern in [r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日.*?成立',
                        r'成立.*?(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日']:
            m = self._search(pattern)
            if m:
                g = m.groups()
                time_str = f"{g[0]}-{int(g[1]):02d}-{int(g[2]):02d}"
                self.result["establish_time"] = time_str
                self.uncertain_fields.append("establish_time")
                return time_str

        # 策略3: 只要有日期就尝试
        for pattern in [r'(\d{4})\s*[-/年]\s*(\d{1,2})\s*[-/月]\s*(\d{1,2})']:
            m = self._search(pattern)
            if m:
                g = m.groups()
                year = int(g[0])
                if 1990 <= year <= 2023:
                    time_str = f"{g[0]}-{int(g[1]):02d}-{int(g[2]):02d}"
                    self.result["establish_time"] = time_str
                    self.uncertain_fields.append("establish_time")
                    return time_str

        self.result["establish_time"] = ""
        self.uncertain_fields.append("establish_time")
        return ""

    def extract_address(self) -> Tuple[str, str]:
        """提取注册地址和实际经营地址"""
        register_addr = ""
        actual_addr = ""

        # 策略1: 按正则提取（两级搜索）
        for pattern in ADDRESS_PATTERNS:
            # 在两个文本源中搜索
            for text in [self.filtered_text, self.raw_text]:
                if not text.strip():
                    continue
                for m in re.finditer(pattern, text):
                    addr = m.group(1).strip()
                    if len(addr) < 6:
                        continue
                    context_start = max(0, m.start() - 20)
                    context = text[context_start:m.start()]
                    if '实际' in context or '经营' in context:
                        if not actual_addr:
                            actual_addr = addr
                    else:
                        if not register_addr:
                            register_addr = addr

        # 策略2: 从招投标公告提取供应商地址
        if not register_addr:
            m = self._search(r'(?:供应商|中标).*?地址\s*[:：]?\s*([\u4e00-\u9fa5\d\-省市县区路街道号室栋楼层]+)')
            if m and len(m.group(1)) > 5:
                register_addr = m.group(1).strip()

        # 策略3: 省市区开头地址
        if not register_addr:
            m = self._search(r'((?:陕西省西安市|北京市海淀区|北京市朝阳区|深圳市南山区|上海市浦东新区)[\u4e00-\u9fa5\d\-高新区新城路街道号室栋楼层]+)')
            if m and len(m.group(1)) > 8:
                register_addr = m.group(1).strip()

        self.result["register_address"] = register_addr
        self.result["actual_address"] = actual_addr
        if not register_addr:
            self.uncertain_fields.append("register_address")
        return register_addr, actual_addr

    def extract_legal_person(self) -> str:
        """提取法定代表人"""
        patterns = [
            r'法定代表人\s*[:：]?\s*([\u4e00-\u9fa5]{2,4})',
            r'法人代表\s*[:：]?\s*([\u4e00-\u9fa5]{2,4})',
            r'法人\s*[:：]?\s*([\u4e00-\u9fa5]{2,4})',
            r'(?:负责人|执行事务合伙人)\s*[:：]?\s*([\u4e00-\u9fa5]{2,4})',
        ]
        for p in patterns:
            m = self._search(p)
            if m:
                name = m.group(1)
                if name not in ("企业", "公司", "有限", "股份", "集团", "自然"):
                    self.result["legal_person"] = name
                    return name
        self.result["legal_person"] = ""
        self.uncertain_fields.append("legal_person")
        return ""

    def extract_registered_capital(self) -> str:
        """提取注册资本"""
        patterns = [
            r'注册资本\s*[:：]?\s*([\d,.]+)\s*万(元|人民币)',
            r'注册资本\s*[:：]?\s*([\d,.]+)\s*亿(元|人民币)',
            r'注册资本\s*[:：]?\s*([\d,.]+)\s*亿',
            r'注册资本\s*[:：]?\s*([\d,.]+)\s*万',
            r'资金\s*[:：]?\s*([\d,.]+)\s*万(元|人民币)',
            r'(?:投资|总额)\s*([\d,.]+)\s*万元',
        ]
        for p in patterns:
            m = self._search(p)
            if m:
                value = m.group(1).replace(',', '')
                if '亿' in p:
                    capital = f"{value}亿元人民币"
                else:
                    capital = f"{value}万元人民币"
                self.result["registered_capital"] = capital
                return capital
        self.result["registered_capital"] = ""
        self.uncertain_fields.append("registered_capital")
        # 错误诊断信息
        self._diagnostic_info["registered_capital"] = {
            "reason": "正则未匹配",
            "text_sample": self._get_search_text()[:200],
            "tried_patterns": [p for p in patterns],
        }
        return ""

    def extract_enterprise_type(self) -> str:
        """提取企业类型"""
        text = self._get_search_text()
        for std_type, keywords in ENTERPRISE_TYPE_MAP.items():
            for kw in keywords:
                if kw in text:
                    self.result["enterprise_type"] = std_type
                    return std_type
        self.result["enterprise_type"] = ""
        self.uncertain_fields.append("enterprise_type")
        return ""

    def extract_operating_status(self) -> str:
        """提取经营状态"""
        text = self._get_search_text()
        for std_status, keywords in OPERATING_STATUS_MAP.items():
            for kw in keywords:
                if kw in text:
                    self.result["operating_status"] = std_status
                    return std_status
        self.result["operating_status"] = ""
        return ""

    # ---------- 3. 轴承行业专属字段提取 ----------

    def extract_business_scope(self) -> str:
        """提取经营范围（精简，突出行业特性）"""
        patterns = [
            r'经营范围\s*[:：]?\s*([\u4e00-\u9fa5，、；;,\s]+?)(?:。|$)',
            r'主营\s*[:：]?\s*([\u4e00-\u9fa5，、；;,\s]+?)(?:。|$)',
            r'从事\s*[:：]?\s*([\u4e00-\u9fa5，、；;,\s]+?)(?:。|$)',
            r'业务范围\s*[:：]?\s*([\u4e00-\u9fa5，、；;,\s]+?)(?:。|$)',
        ]
        for p in patterns:
            m = self._search(p)
            if m:
                scope = m.group(1).strip()
                scope = re.sub(r'\s+', '', scope)
                scope = re.sub(r'[;；]', '；', scope)
                if len(scope) > 5:
                    self.result["business_scope"] = scope
                    return scope
        self.result["business_scope"] = ""
        return ""

    def extract_main_business(self) -> str:
        """提取主营业务（轴承细分领域）"""
        text = self._get_search_text()
        found_segments = []
        for segment, keywords in INDUSTRY_SEGMENTS.items():
            for kw in keywords:
                if kw in text:
                    if segment not in found_segments:
                        found_segments.append(segment)
                    break

        # 回退：从经营范围推断
        if not found_segments:
            scope = self.result.get("business_scope", "")
            biz_text = f"{scope} {text}"
            for segment, keywords in INDUSTRY_SEGMENTS.items():
                for kw in keywords:
                    if kw in biz_text:
                        if segment not in found_segments:
                            found_segments.append(segment)
                        break

        result = "、".join(found_segments) if found_segments else ""
        self.result["main_business"] = result
        if not result:
            self.uncertain_fields.append("main_business")
        return result

    def extract_core_products(self) -> str:
        """提取核心产品"""
        text = self._get_search_text()
        product_keywords = [
            "深沟球轴承", "圆锥滚子轴承", "调心球轴承", "调心滚子轴承",
            "圆柱滚子轴承", "角接触球轴承", "推力球轴承", "推力滚子轴承",
            "关节轴承", "杆端关节轴承", "直线轴承", "直线导轨", "滚珠丝杠",
            "外球面轴承", "轴承座", "轴承单元", "陶瓷轴承", "不锈钢轴承",
            "精密轴承", "高温轴承", "高速轴承", "绝缘轴承", "微型轴承",
            "薄壁轴承", "满装滚子轴承", "交叉滚子轴承", "转盘轴承",
            "轴承保持架", "钢球", "陶瓷球", "滚子", "密封件",
            "轴承钢", "GCr15", "轴承套圈",
        ]

        found = []
        for kw in product_keywords:
            if kw in text and kw not in found:
                found.append(kw)

        # 合并同类
        if "深沟球轴承" in found and "球轴承" in found:
            found = [x for x in found if x != "球轴承"]
        if "直线导轨" in found and "导轨" in found:
            found = [x for x in found if x != "导轨"]

        result = "、".join(found) if found else ""
        self.result["core_products"] = result
        if not result:
            self.uncertain_fields.append("core_products")
        return result

    def extract_product_spec(self) -> str:
        """提取核心产品规格"""
        text = self._get_search_text()
        specs = []

        for pattern in PRODUCT_SPEC_PATTERNS:
            m = re.search(pattern, text)
            if m:
                specs.append(m.group(0).strip())

        result = "；".join(specs) if specs else ""
        self.result["product_spec"] = result
        if not result:
            self.uncertain_fields.append("product_spec")
        return result

    def extract_employee_scale(self) -> str:
        """提取用工规模"""
        text = self._get_search_text()
        patterns = [
            r'(\d+)\s*[-~至]\s*(\d+)\s*人',
            r'员工\s*[:：]?\s*(\d+)\s*人',
            r'现有.*?(\d+)\s*人',
            r'人员\s*(\d+)\s*人',
            r'(\d+)\s*人以上',
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                groups = m.groups()
                if len(groups) >= 2:
                    low, high = int(groups[0]), int(groups[1])
                    scale = self._categorize_employee_count(low, high)
                else:
                    count = int(groups[0])
                    scale = self._categorize_employee_count(count, count)
                self.result["employee_scale"] = scale
                return scale
        self.result["employee_scale"] = ""
        return ""

    def _categorize_employee_count(self, low: int, high: int) -> str:
        """用工规模分档"""
        mid = (low + high) // 2
        if mid < 50:
            return "50人以下"
        elif mid < 150:
            return "50-150人"
        elif mid < 500:
            return "150-500人"
        elif mid < 1000:
            return "500-1000人"
        elif mid < 5000:
            return "1000-5000人"
        else:
            return "5000人以上"

    # ---------- 4. 资质信息提取 ----------

    def extract_qualifications(self) -> None:
        """提取资质信息"""
        text = self._get_search_text()

        # 高新技术企业
        if any(kw in text for kw in ['高新技术企业', '高新企业', '高新技', '科技型企业']):
            self.result["high_tech_enterprise"] = "是"
        elif any(kw in text for kw in ['非高新技术企业']):
            self.result["high_tech_enterprise"] = "否"
        else:
            self.result["high_tech_enterprise"] = "未明确"
            self.uncertain_fields.append("high_tech_enterprise")

        # 专精特新
        if any(kw in text for kw in ['专精特新', '小巨人', '专精特新中小企业']):
            self.result["specialized_enterprise"] = "是"
        elif any(kw in text for kw in ['非专精特新']):
            self.result["specialized_enterprise"] = "否"
        else:
            self.result["specialized_enterprise"] = "未明确"
            self.uncertain_fields.append("specialized_enterprise")

        # 专利数量
        patent_info = self._extract_patent_count()
        self.result["patent_count"] = patent_info

        # 行业资质
        certs = []
        for cert_name, keywords in CERTIFICATION_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    if cert_name not in certs:
                        certs.append(cert_name)
                    break
        self.result["industry_cert"] = "、".join(certs) if certs else ""

    def _extract_patent_count(self) -> str:
        """提取专利数量"""
        text = self._get_search_text()
        total = 0
        invention = 0
        has_detail = False

        for p in PATENT_PATTERNS:
            m = re.search(p, text)
            if m:
                count = int(m.group(1))
                context_start = max(0, m.start() - 10)
                context = text[context_start:m.start()]
                if '发明' in context:
                    invention = count
                    has_detail = True
                else:
                    total = max(total, count)

        # 检查是否有轴承相关专利
        bearing_patent_keywords = ['轴承', '滚子', '保持架', '密封', '润滑', '热处理', '磨削', '精密', '滚动体', '套圈']
        bearing_related = []
        for kw in bearing_patent_keywords:
            if '专利' in text and kw in text:
                bearing_related.append(kw)

        if has_detail and total == 0:
            total = invention

        if total > 0:
            parts = [f"{total}项"]
            if invention > 0:
                parts.append(f"发明专利{invention}项")
            if bearing_related:
                parts.append(f"含{'、'.join(bearing_related[:3])}相关")
            return "（".join(parts) + "）" if len(parts) > 1 else parts[0]

        return ""

    # ---------- 5. 项目与招投标提取 ----------

    def extract_projects(self) -> None:
        """提取项目与招投标信息"""
        text = self._get_search_text()
        enterprise_name = self.source_info.get("enterprise_name", "") or self.result.get("enterprise_name", "")

        # 招投标项目 — 放宽匹配条件
        bidding = []
        bid_patterns = [
            # 标准格式
            r'(\d{4})\s*年.*?中标.*?(?:项目|采购).*?(?:金额|总额)?\s*([\d,.]+)\s*万?元?',
            # 简化格式
            r'中标.*?(?:项目|采购).*?([\d,.]+)\s*万?元',
            # 供应商名称出现在中标信息中
            r'中标.*?供应商.*?([\d,.]+)\s*元',
            # 采购项目
            r'(\w+项目).*?成交.*?([\d,.]+)\s*万?元?',
        ]
        for p in bid_patterns:
            m = re.search(p, text)
            if m:
                bidding.append(m.group(0).strip())

        # 回退：提取任何包含企业名+招投标关键词的句子
        if not bidding:
            for sentence in re.split(r'[。；\n]', text):
                sentence = sentence.strip()
                if not sentence or len(sentence) < 10:
                    continue
                has_bid = any(kw in sentence for kw in ['中标', '成交', '招标', '采购'])
                has_money = bool(re.search(r'[\d,.]+\s*万?元', sentence))
                has_enterprise = enterprise_name and enterprise_name in sentence
                if has_bid and (has_money or has_enterprise):
                    bidding.append(sentence)
                    if len(bidding) >= 3:
                        break

        # 再回退：只看包含"采购/项目"且金额的句子
        if not bidding:
            for sentence in re.split(r'[。；\n]', text):
                sentence = sentence.strip()
                if not sentence or len(sentence) < 10:
                    continue
                if ('项目' in sentence or '采购' in sentence) and re.search(r'[\d,.]+\s*万?元', sentence):
                    bidding.append(sentence)
                    if len(bidding) >= 2:
                        break

        self.result["bidding_projects"] = bidding[0] if bidding else ""
        if not bidding:
            self.uncertain_fields.append("bidding_projects")

        # 投资项目
        invest = []
        invest_patterns = [
            r'(\d{4})\s*年.*?(?:新增|建设|投资).*?项目.*?(?:投资|总额)?\s*([\d.]+)\s*亿?万?元',
            r'(?:新增|投资).*?项目.*?([\d.]+)\s*亿?万?元',
        ]
        for p in invest_patterns:
            m = re.search(p, text)
            if m:
                invest.append(m.group(0).strip())

        self.result["investment_projects"] = invest[0] if invest else ""

        # 合作企业
        partners = self._extract_partners()
        self.result["cooperative_enterprise"] = "、".join(partners) if partners else ""

    def _extract_partners(self) -> List[str]:
        """提取核心合作企业 - 正则+字典混合提取"""
        text = self._get_search_text()
        
        # 策略1: 从文本中正则提取企业名（覆盖面最广）
        found_companies = set()
        company_patterns = [
            # 带行业关键词的公司名
            r'([\u4e00-\u9fa5]+(?:集团|股份|科技|技术|工业|装备|机械|电子|电气|汽车|轴承|精密|传动|冶金|重工|动力|机电|五金|钢铁|新材料|新能源)(?:有限)?(?:责任)?(?:公司|厂))',
            # "XX有限公司" 简写
            r'([\u4e00-\u9fa5]{2,8}有限公司)',
            # "XX集团"
            r'([\u4e00-\u9fa5]{2,6}集团)',
        ]
        for pattern in company_patterns:
            for m in re.finditer(pattern, text):
                name = m.group(1).strip()
                if name and len(name) >= 4 and name not in found_companies:
                    found_companies.add(name)
        
        # 策略2: 从已知企业字典匹配（覆盖缩写/简称）
        known_partners = [
            "SKF", "NSK", "NTN", "铁姆肯", "Timken", "舍弗勒", "Schaeffler",
            "FAG", "INA", "KOYO", "NMB", "Nachi", "不二越",
            "人本集团", "万向钱潮", "洛阳LYC", "瓦轴ZWZ", "哈尔滨轴承HRB",
            "天马轴承", "五洲新春", "襄阳轴承", "南方轴承", "龙溪股份",
            "宝塔实业", "大连冶金轴承", "西北轴承", "苏州轴承",
            "一汽", "东风", "中车", "金风科技", "中航工业",
            "三一重工", "徐工", "潍柴动力", "中国商飞",
            "上汽", "广汽", "长安", "吉利", "比亚迪", "北汽",
            "远景能源", "明阳智能", "东方电气", "上海电气",
            "西门子", "ABB", "格力", "美的", "海尔",
            "宝钢", "鞍钢", "首钢",
            "中国中车", "中联重科", "柳工", "山推",
        ]
        for partner in known_partners:
            if partner in text and partner not in found_companies:
                found_companies.add(partner)
        
        # 过滤：排除自身企业名和噪声
        enterprise_name = self.source_info.get("enterprise_name", "") or self.result.get("enterprise_name", "")
        exclude_names = {
            "公司", "有限公司", "集团", "有限责任公司", "股份有限公司",
            "未提取到", "未明确", "暂无", "无",
        }
        filtered = []
        for name in found_companies:
            if name in exclude_names:
                continue
            if enterprise_name and (name == enterprise_name or name in enterprise_name or enterprise_name in name):
                continue
            filtered.append(name)
        
        return filtered[:8]

    # ---------- 6. 行业分类 ----------

    def classify_industry(self) -> None:
        """行业分类"""
        text = self._get_search_text()

        # 确定细分领域
        segments = []
        for segment, keywords in INDUSTRY_SEGMENTS.items():
            for kw in keywords:
                if kw in text:
                    if segment not in segments:
                        segments.append(segment)
                    break

        self.result["industry_segment"] = segments[0] if segments else ""
        if len(segments) > 1:
            self.result["industry_segment"] = "/".join(segments[:3])

        # 如果没找到行业细分，从经营范围推断
        if not segments:
            scope = self.result.get("business_scope", "")
            biz_text = f"{scope} {self.result.get('main_business', '')}"
            # IT/软件类
            if any(kw in biz_text for kw in ['软件开发', '信息技术咨询', '信息系统集成']):
                self.result["industry_segment"] = "信息技术服务"
            elif any(kw in biz_text for kw in ['轴承', '滚子', '保持架', '密封', '润滑', '热处理', '磨削']):
                self.result["industry_segment"] = "轴承制造"

        # 行业大类
        self.result["industry_category"] = "制造业-通用设备制造业-轴承制造"

        # 数据来源
        source_urls = self.source_info.get("source_urls", [])
        sources = []
        for url in source_urls:
            domain = ""
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
            except Exception:
                pass
            if 'tianyancha' in domain:
                sources.append("天眼查")
            elif 'qcc' in domain:
                sources.append("企查查")
            elif 'aiqicha' in domain:
                sources.append("爱企查")
            elif 'gov.cn' in domain:
                sources.append("政府公示平台")
            elif 'ccgp' in domain:
                sources.append("中国政府采购网")
            elif 'ggzy' in domain:
                sources.append("公共资源交易平台")
            elif 'cnipa' in domain:
                sources.append("国家知识产权局")
            elif 'cninfo' in domain:
                sources.append("巨潮资讯网")
            else:
                sources.append("企业官网")

        self.result["data_source"] = "、".join(list(set(sources))) if sources else ""

    # ---------- 7. LLM 增强提取 ----------

    def _llm_enhance_extraction(self):
        """使用 LLM 补充正则未能提取的字段"""
        # 只针对缺失的关键字段
        target_fields = [
            "registered_capital", "establish_time", "legal_person",
            "register_address", "main_business", "core_products",
            "business_scope", "employee_scale",
        ]
        missing = [f for f in target_fields if f in self.uncertain_fields and not self.result.get(f)]
        if not missing:
            return

        field_names_cn = {
            "registered_capital": "注册资本",
            "establish_time": "成立时间",
            "legal_person": "法定代表人",
            "register_address": "注册地址",
            "main_business": "主营业务/细分领域",
            "core_products": "核心产品",
            "business_scope": "经营范围",
            "employee_scale": "员工规模",
        }

        fields_desc = "\n".join(f"- {field_names_cn.get(f, f)}（字段名: {f}）" for f in missing)
        text_sample = self._get_search_text()[:6000]

        self._report_progress(79, "LLM 增强提取", f"使用大模型补充 {len(missing)} 个缺失字段")

        system_prompt = (
            "你是一个精确的企业信息提取助手。请从给定文本中提取指定字段。"
            "只返回 JSON 格式，不要任何解释。"
            "如果某个字段确实无法从文本中提取，值设为空字符串。"
        )
        user_prompt = (
            f"请从以下企业文本中提取这些缺失字段：\n{fields_desc}\n\n"
            f"企业文本：\n{text_sample}\n\n"
            f"请返回 JSON，key 为字段名，value 为提取结果。示例：\n"
            f'{{"registered_capital": "5000万元人民币", "legal_person": "张三"}}'
        )

        try:
            from backend.services.llm_client import llm_chat_json
            result = llm_chat_json(self._llm_client, system_prompt, user_prompt)
            if result and isinstance(result, dict):
                for field in missing:
                    value = result.get(field, "")
                    if value and value not in ("未提取到", "未明确", "无", "null", "None"):
                        self.result[field] = str(value).strip()
                        if field in self.uncertain_fields:
                            self.uncertain_fields.remove(field)
        except Exception as e:
            print(f"[LLM增强] 清洗阶段提取失败: {e}")

    # ---------- 7. 置信度计算 ----------

    def calculate_confidence(self) -> float:
        """计算整体置信度"""
        core_fields = [
            "enterprise_name", "establish_time", "register_address",
            "legal_person", "registered_capital", "main_business",
            "core_products", "industry_segment"
        ]

        filled = sum(1 for f in core_fields if self.result.get(f))
        confidence = min(0.98, 0.3 + filled * 0.085)

        # 加分项
        if self.result.get("patent_count"):
            confidence += 0.03
        if self.result.get("industry_cert"):
            confidence += 0.02
        if self.result.get("bidding_projects"):
            confidence += 0.02
        if self.result.get("business_scope"):
            confidence += 0.02
        if self.result.get("cooperative_enterprise"):
            confidence += 0.01

        confidence = min(0.98, confidence)
        self.result["confidence"] = round(confidence, 2)
        return confidence

    # ---------- 8. 主流程 ----------

    def clean(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行完整清洗流程"""
        # 加载数据
        if not self.load_input(input_data):
            return {
                "clean_status": "failed",
                "note": "输入数据为空或格式错误",
                "clean_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        self._report_progress(62, "文本预处理", "深度噪声过滤+清洗无效字符")
        self.preprocess_text()

        self._report_progress(65, "企业基础信息提取", "提取企业名称/地址/法人/资本等")
        self.extract_enterprise_name()
        self.extract_short_name()
        self.extract_establish_time()
        self.extract_address()
        self.extract_legal_person()
        self.extract_registered_capital()
        self.extract_enterprise_type()
        self.extract_operating_status()

        self._report_progress(70, "经营信息提取", "提取经营范围/核心产品/产品规格等")
        self.extract_business_scope()
        self.extract_main_business()
        self.extract_core_products()
        self.extract_product_spec()
        self.extract_employee_scale()

        self._report_progress(74, "资质信息提取", "提取高新技术/专精特新/认证/专利等")
        self.extract_qualifications()

        self._report_progress(77, "项目信息提取", "提取招投标/投资项目/合作企业等")
        self.extract_projects()

        self._report_progress(78, "行业分类与去重", "确定细分领域、标准化字段、去重")
        self.classify_industry()

        self._report_progress(79, "置信度计算", "评估字段完整度")
        self.calculate_confidence()

        # LLM 增强提取：当关键字段缺失时，使用大模型补充
        if self._llm_client and self.uncertain_fields:
            self._llm_enhance_extraction()

        # 完成状态
        filled_core = sum(1 for f in ["enterprise_name", "establish_time", "main_business", "core_products"]
                         if self.result.get(f))

        if filled_core >= 4:
            self.result["clean_status"] = "success"
            self.result["note"] = "所有核心字段提取完整"
        elif filled_core >= 2:
            self.result["clean_status"] = "partial"
            self.result["note"] = f"部分字段提取成功，{len(self.uncertain_fields)} 个字段不确定"
        elif filled_core >= 1:
            self.result["clean_status"] = "partial"
            self.result["note"] = f"核心字段提取不充分，仅{filled_core}个字段有值，{len(self.uncertain_fields)} 个字段不确定"
        else:
            self.result["clean_status"] = "partial"
            self.result["note"] = "核心字段提取不足，但已尽力提取可用信息"

        self.result["uncertain_fields"] = self.uncertain_fields
        self.result["clean_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self._diagnostic_info:
            self.result["_diagnostic_info"] = self._diagnostic_info

        return self.result

    def save_to_file(self, data: Dict[str, Any], enterprise_name: str) -> str:
        """将结果写入项目 output 目录"""
        output_dir = self.output_dir
        os.makedirs(output_dir, exist_ok=True)

        safe_name = re.sub(r'[\\/:*?"<>|]', '_', enterprise_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}_clean.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath


def main():
    import argparse
    parser = argparse.ArgumentParser(description="轴承行业数据结构化清洗脚本")
    parser.add_argument("input_file", help="爬虫输出JSON文件路径")
    parser.add_argument("--output-dir", help="输出目录（默认为当前工作目录下的 output）", default=None)
    args = parser.parse_args()

    input_path = args.input_file

    # 读取输入文件
    if not os.path.exists(input_path):
        print(f"文件不存在: {input_path}")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    enterprise_name = input_data.get("enterprise_name", "未知企业")

    print(f"{'='*60}")
    print(f"轴承行业数据清洗 - {enterprise_name}")
    print(f"{'='*60}\n")

    cleaner = BearingDataCleaner(output_dir=args.output_dir)
    result = cleaner.clean(input_data)

    # 保存
    output_path = cleaner.save_to_file(result, enterprise_name)

    print(f"\n{'='*60}")
    print("清洗结果:")
    print(f"{'='*60}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n结果已保存到: {output_path}")


if __name__ == "__main__":
    main()

