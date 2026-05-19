#!/usr/bin/env python3
"""
bearing-data-source-filter: 轴承行业企业信息数据源筛选与评价
功能：
  1. 全网搜索轴承行业企业信息相关网站
  2. 测试各网站的响应效率与数据质量
  3. 综合评价并遴选出TOP20优质数据源
"""

import asyncio
import json
import os
import re
import sys
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from urllib.parse import quote, urlparse, urljoin
import argparse

sys.stdout.reconfigure(encoding='utf-8')

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
except ImportError:
    print("请先安装 crawl4ai: pip install crawl4ai")
    exit(1)

# 导入共享模块
try:
    # 尝试从项目根目录导入
    _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
    from common.web_utils import clean_html_to_text, extract_all_links, extract_domain, is_valid_url, extract_title
    from common.search_engines import (
        SEARCH_ENGINES_PAGINATED, extract_search_result_links,
        build_search_url, get_engine_name,
    )
    from common.blacklist import BLACKLIST_DOMAINS as _COMMON_BLACKLIST
    from common.output import resolve_output_dir
    from common.logger import setup_logger
    from common.cache import ResponseCache
    _USE_COMMON = True
except ImportError:
    _USE_COMMON = False


# ===================== 配置区 =====================

# 搜索引擎配置
SEARCH_ENGINES = [
    ("百度", "https://www.baidu.com/s?wd={keyword}&pn={page}0"),
    ("必应", "https://cn.bing.com/search?q={keyword}&first={page}1"),
    ("搜狗", "https://www.sogou.com/web?query={keyword}&page={page}"),
    ("360搜索", "https://www.so.com/s?q={keyword}&pn={page}"),
]

# 轴承行业默认搜索关键词
DEFAULT_KEYWORDS = [
    # 企业名录类
    "轴承企业名录",
    "轴承零部件厂家名录",
    "滚动轴承制造商名录",
    "轴承企业数据库",
    "轴承制造企业名单",
    "轴承企业黄页",
    # 企业查询类
    "轴承企业信息查询",
    "轴承公司工商信息",
    "轴承零部件供应商查询",
    "轴承厂商信息查询",
    # 行业平台类
    "轴承行业B2B平台",
    "轴承零部件采购平台",
    "轴承产业信息平台",
    "轴承制造服务网站",
    # 招投标类
    "轴承行业招投标信息",
    "轴承采购招标",
    "轴承设备招标公告",
    # 专利资质类
    "轴承专利查询平台",
    "轴承技术专利检索",
    "轴承企业资质查询",
    # 产业研究类
    "轴承产业研究报告",
    "轴承行业数据库",
    "轴承行业资讯",
]

# 已知优质网站种子列表（作为初始候选）
KNOWN_SEED_SITES = [
    # ========== 工商查询平台 ==========
    ("天眼查", "https://www.tianyancha.com", "工商查询"),
    ("企查查", "https://www.qcc.com", "工商查询"),
    ("爱企查", "https://aiqicha.baidu.com", "工商查询"),
    ("启信宝", "https://www.qixin.com", "工商查询"),
    ("国家企业信用公示", "https://www.gsxt.gov.cn", "工商查询"),
    ("企洞察", "https://www.qidongcha.com", "工商查询"),

    # ========== 招投标平台 ==========
    ("中国政府采购网", "https://www.ccgp.gov.cn", "招投标平台"),
    ("全国公共资源交易", "https://www.ggzy.gov.cn", "招投标平台"),
    ("中国招标投标平台", "https://www.cebpubservice.com", "招投标平台"),
    ("采招网", "https://www.bidcenter.com.cn", "招投标平台"),
    ("中国采购与招标网", "https://www.chinabidding.cn", "招投标平台"),
    ("中国国际招标网", "https://www.chinabidding.com.cn", "招投标平台"),
    # 地方公共资源交易
    ("北京公共资源交易", "https://ggzyfw.beijing.gov.cn", "招投标平台"),
    ("上海公共资源交易", "https://www.shggzy.com", "招投标平台"),
    ("广东公共资源交易", "https://www.gdzbtb.gov.cn", "招投标平台"),
    ("深圳公共资源交易", "https://www.szggzy.com", "招投标平台"),
    ("江苏公共资源交易", "https://jsggzy.jiangsu.gov.cn", "招投标平台"),
    ("浙江公共资源交易", "https://ggzy.zj.gov.cn", "招投标平台"),

    # ========== 专利与知识产权平台 ==========
    ("国家知识产权局", "https://www.cnipa.gov.cn", "专利平台"),
    ("专利公布公告网", "https://patentimage.cnipa.gov.cn", "专利平台"),
    ("中国商标网", "https://sbj.cnipa.gov.cn", "专利平台"),
    ("soopat专利", "https://www.soopat.com", "专利平台"),
    ("专利之星", "https://www.cprs.patentstar.com", "专利平台"),

    # ========== B2B/轴承交易平台 ==========
    ("中国轴承网", "https://www.zcw168.com", "B2B平台"),
    ("轴承英才网", "https://www.zcjob88.com", "B2B平台"),
    ("中华轴承网", "https://www.zhoucheng.cn", "B2B平台"),
    ("轴承之家", "https://www.zcwz.com", "B2B平台"),
    ("中国机械网", "https://www.jx.cn", "B2B平台"),
    ("机电网", "https://www.jdzj.com", "B2B平台"),
    ("全球轴承网", "https://www.globalbearing.com", "B2B平台"),
    ("华轴网", "https://www.huazhou.com", "B2B平台"),
    ("中国制造网", "https://www.made-in-china.com", "B2B平台"),
    ("慧聪网", "https://www.hc360.com", "B2B平台"),
    ("马可波罗网", "https://www.makepolo.com", "B2B平台"),
    ("1688轴承", "https://www.1688.com", "B2B平台"),

    # ========== 行业媒体与资讯平台 ==========
    ("中国轴承行业网", "https://www.cbia.cn", "行业媒体"),
    ("轴承工业", "https://www.zcgy.cn", "行业媒体"),
    ("中国机械工业联合会", "https://www.cmia.cn", "行业媒体"),
    ("金属加工在线", "https://www.mw1950.com", "行业媒体"),
    ("中国工业报", "https://www.cinn.cn", "行业媒体"),
    ("机电商报", "https://www.jdscn.com", "行业媒体"),
    ("中国设备工程", "https://www.zgsb.com.cn", "行业媒体"),
    ("机械工程师", "https://www.mei.net.cn", "行业媒体"),
    ("中国通用机械工业协会", "https://www.cgmia.org.cn", "行业媒体"),
    ("OFweek工控网", "https://gk.ofweek.com", "行业媒体"),

    # ========== 产业研究与数据库平台 ==========
    ("赛迪顾问", "https://www.ccidconsulting.com", "产业研究"),

    # ========== 上市公司信息平台 ==========
    ("巨潮资讯网", "https://www.cninfo.com.cn", "上市公司"),
    ("上海证券交易所", "https://www.sse.com.cn", "上市公司"),
    ("深圳证券交易所", "https://www.szse.cn", "上市公司"),
    ("全国股转系统", "https://www.neeq.com.cn", "上市公司"),

    # ========== 企业名录/黄页类平台 ==========
    ("中国制造网", "https://www.made-in-china.com", "企业名录"),
    ("慧聪网", "https://www.hc360.com", "企业名录"),
    ("马可波罗网", "https://www.makepolo.com", "企业名录"),
    ("黄页88", "https://www.88.com", "企业名录"),
    ("顺企网", "https://www.11467.com", "企业名录"),
    ("淘金地", "https://www.taojindi.com", "企业名录"),
    ("一比多", "https://www.ebdoor.com", "企业名录"),

    # ========== 行业协会 ==========
    ("中国轴承工业协会CBIA", "https://www.cbia.cn", "行业协会"),
    ("中国机械工业联合会CMIF", "https://www.cmif.org.cn", "行业协会"),
    ("中国通用机械工业协会", "https://www.cgmia.org.cn", "行业协会"),
    ("中国机械工程学会", "https://www.cmes.org", "行业协会"),
    ("全国滚动轴承标准化技术委员会", "https://www.sac.org.cn", "行业协会"),
    ("洛阳轴承行业协会", "https://www.lybearing.com", "行业协会"),
    ("瓦房店轴承行业协会", "https://www.wfd-bearing.com", "行业协会"),
    ("浙江轴承工业协会", "https://www.zjbia.org", "行业协会"),

    # ========== 细分领域专业平台 ==========
    # 滚动轴承
    ("SKF中国", "https://www.skf.com.cn", "滚动轴承专业"),
    ("NSK中国", "https://www.nsk.com.cn", "滚动轴承专业"),
    ("NTN中国", "https://www.ntn.co.jp", "滚动轴承专业"),
    # 滑动轴承
    ("滑动轴承网", "https://www.hdzczw.com", "滑动轴承专业"),
    ("自润滑轴承网", "https://www.zrhwzc.com", "滑动轴承专业"),
    # 直线运动
    ("THK中国", "https://www.thk.com.cn", "直线运动专业"),
    ("HIWIN上银", "https://www.hiwin.cn", "直线运动专业"),
    # 轴承钢/材料
    ("特钢网", "https://www.tegang.com", "轴承钢材料"),
    ("中国特钢企业协会", "https://www.cstsa.org.cn", "轴承钢材料"),
    # 轴承装备
    ("机床商务网", "https://www.jc35.com", "轴承装备"),
    ("中国机床工具工业协会", "https://www.cmtba.org.cn", "轴承装备"),
    # 汽车轴承
    ("汽车轴承网", "https://www.qczcw.cn", "汽车轴承"),
    ("新能源汽车网", "https://www.nev.com.cn", "汽车轴承"),

    # ========== 新兴企业数据服务平台 ==========
    ("企名片", "https://www.qimingpian.com", "数据服务"),
    ("IT桔子", "https://www.itjuzi.com", "数据服务"),
    ("鲸准", "https://www.36kr.com", "数据服务"),
    ("萝卜投研", "https://robo.datayes.com", "数据服务"),
    ("清科研究中心", "https://www.pedata.cn", "数据服务"),

    # ========== 行业展会平台 ==========
    ("中国国际轴承及其专用装备展览会", "https://www.bearingexpo.com.cn", "行业展会"),
    ("上海国际轴承峰会", "https://www.bearingsummit.com", "行业展会"),
    ("中国国际机械工业博览会", "https://www.cmeexpo.com.cn", "行业展会"),
    ("PTC亚洲动力传动展", "https://www.ptc-asia.com", "行业展会"),
    ("中国国际工业博览会", "https://www.ciif-expo.com", "行业展会"),

    # ========== 招聘平台 ==========
    ("猎聘网", "https://www.liepin.com", "招聘平台"),
    ("BOSS直聘", "https://www.zhipin.com", "招聘平台"),
    ("拉勾网", "https://www.lagou.com", "招聘平台"),
    ("轴承英才网", "https://www.zcjob88.com", "招聘平台"),
    ("机械人才网", "https://www.jxjob.net", "招聘平台"),

    # ========== 投融资与企业征信平台 ==========
    ("央行征信中心", "https://www.pbccrc.org.cn", "征信平台"),
    ("中国裁判文书网", "https://wenshu.court.gov.cn", "司法信息"),
    ("中国执行信息公开网", "https://zxgk.court.gov.cn", "司法信息"),
    ("融360企业版", "https://www.rong360.com", "征信平台"),

    # ========== 诉讼与仲裁平台 ==========
    ("中国庭审公开网", "https://tingshen.court.gov.cn", "司法信息"),
    ("企查查司法", "https://www.qcc.com", "司法信息"),
    ("天眼查司法", "https://www.tianyancha.com", "司法信息"),

    # ========== 海关进出口数据平台 ==========
    ("海关进出口信用公示", "https://credit.customs.gov.cn", "海关数据"),
    ("环球慧思", "https://www.tradesns.com", "海关数据"),
    ("腾道数据", "https://www.tendata.cn", "海关数据"),

    # ========== 学术与标准平台 ==========
    ("中国知网CNKI", "https://www.cnki.net", "学术标准"),
    ("全国标准信息平台", "https://std.samr.gov.cn", "学术标准"),
    ("万方数据", "https://www.wanfangdata.com.cn", "学术标准"),
    ("维普网", "https://www.cqvip.com", "学术标准"),

    # ========== 行业研报与供应链分析平台 ==========
    ("IDC中国", "https://www.idc.com/cn", "产业研究"),
    ("TrendForce集邦", "https://www.trendforce.cn", "产业研究"),
    ("高工产业研究院", "https://www.gg-led.com", "产业研究"),
]

# 黑名单域名（排除）
BLACKLIST_DOMAINS = {
    'baidu.com', 'bing.com', 'google.com', 'sogou.com', 'so.com',
    'zhihu.com', 'weibo.com', 'douyin.com', 'bilibili.com',
    'taobao.com', 'tmall.com', 'jd.com', 'pinduoduo.com',
    '1688.com', 'alibaba.com',
    'csdn.net', 'jianshu.com', 'toutiao.com', '51cto.com',
    'youtube.com', 'facebook.com', 'twitter.com',
    'zhaopin.com', 'liepin.com', 'bosszhipin.com', '51job.com',
    'map.baidu.com', 'image.baidu.com', 'wenku.baidu.com',
    'baike.baidu.com', 'zhidao.baidu.com', 'tieba.baidu.com',
    'pan.baidu.com', 'haokan.baidu.com',
    'douban.com', 'mp.weixin.qq.com',
}

# 行业关键词（用于评价行业相关性）
INDUSTRY_KEYWORDS = {
    '企业', '公司', '厂家', '厂商', '制造商', '供应商',
    '轴承', '滚动轴承', '滑动轴承', '关节轴承', '直线轴承',
    '深沟球', '圆锥滚子', '调心滚子', '圆柱滚子', '角接触',
    '推力轴承', '球轴承', '滚子轴承', '轴承座',
    '保持架', '滚动体', '密封', '润滑',
    '轴承钢', 'GCr15', '陶瓷轴承', '不锈钢轴承',
    '内径', '外径', '精度等级', '额定载荷', '极限转速',
    '热处理', '磨削', '超精加工', '锻造', '车削',
    'AS9100', 'API', 'CRCC', 'IRIS', 'ISO/TS16949',
    '专利', '商标', '知识产权',
    '注册', '工商', '资本', '法人', '股东',
    '招标', '中标', '采购', '投标',
    '产品', '型号', '规格', '参数',
    '名录', '黄页', '数据库',
}

# 企业信息相关关键词（用于评价数据丰富度）
ENTERPRISE_INFO_KEYWORDS = {
    '企业名称', '公司名称', '厂商名称', '厂家名称',
    '地址', '所在地', '地区', '省市',
    '电话', '传真', '邮箱', '联系人',
    '主营', '产品', '业务', '经营范围',
    '注册资本', '成立时间', '员工', '规模',
    '简介', '介绍', '概况', '关于',
    '官网', '网站', '网址',
    '法人代表', '负责人', '经理',
    '认证', '资质', 'ISO', '专利',
}

# 商业关系关键词（用于评价商业关系丰富度）
COMMERCIAL_RELATION_KEYWORDS = {
    # 供应链关系
    '客户', '供应商', '下游', '上游', '供应链', '配套',
    '合作企业', '合作伙伴', '战略合作', '供应商名录', '客户名录',
    # 股权/投资关系
    '股东', '股权', '投资', '融资', '并购', '收购', '参股',
    '持股', '投资方', '被投资方', '注册资本变更', '股权变更',
    # 交易关系
    '中标', '中标单位', '中标金额', '中标公告', '中标结果',
    '采购', '招标', '合同', '订单', '成交金额', '交易额',
    '甲方', '乙方', '发包', '承包', '总包', '分包',
    # 合作关系
    '联合研发', '共建', '技术合作', '产学研', '联合实验室',
    '战略合作', '独家代理', '授权', '分销', '渠道',
    # 竞争关系
    '竞品', '竞争对手', '同行', '市场份额', '行业排名',
    # 人员关系
    '董事', '监事', '高管', '创始人', '实际控制人',
    '任职', '兼职', '关联', '一致行动人',
    # 司法/纠纷关系
    '诉讼', '判决', '仲裁', '执行', '被执行人', '失信',
    '合同纠纷', '知识产权纠纷', '不正当竞争',
}


# ===================== 工具函数 =====================
# 当 common 模块可用时使用共享实现，否则回退到本地实现

if not _USE_COMMON:
    def extract_domain(url: str) -> str:
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if netloc.startswith('www.'):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

    def is_valid_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return False
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            for bd in BLACKLIST_DOMAINS:
                if bd in domain or domain in bd:
                    return False
            return True
        except Exception:
            return False

    def clean_html_to_text(html: str) -> str:
        if not html:
            return ""
        for tag in ['script', 'style', 'noscript', 'nav', 'footer', 'header',
                    'aside', 'iframe', 'form', 'button', 'svg']:
            html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.I)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_all_links(html: str, base_url: str = "") -> List[str]:
        links = []
        for m in re.findall(r'href=["\'](https?://[^"\']+)["\']', html, re.I):
            links.append(m)
        for m in re.findall(r'href=["\'](/[^"\']*)["\']', html, re.I):
            if base_url:
                links.append(urljoin(base_url, m))
        seen = set()
        result = []
        for link in links:
            clean = link.split('#')[0].strip()
            if clean and clean not in seen and is_valid_url(clean):
                seen.add(clean)
                result.append(clean)
        return result

    def extract_search_result_links(html: str, engine: str) -> List[str]:
        links = []
        if engine == "百度":
            patterns = [r'href="(https?://www\.baidu\.com/link\?url=[^"]+)"', r'data-url="(https?://[^"]+)"', r'href="(https?://[^"]+)"[^>]*class="[^"]*c-showurl[^"]*"']
        elif engine == "必应":
            patterns = [r'<a[^>]+href="(https?://[^"]+)"[^>]*class="[^"]*b_algo[^"]*"', r'href="(https?://[^"]+)"[^>]*data-h="ID=SERP[^"]*"']
        elif engine == "搜狗":
            patterns = [r'href="(https?://[^"]+)"[^>]*class="[^"]*vr-title[^"]*"']
        elif engine == "360搜索":
            patterns = [r'href="(https?://[^"]+)"[^>]*class="[^"]*res-title[^"]*"']
        else:
            patterns = [r'href="(https?://[^"]+)"']
        for pattern in patterns:
            links.extend(re.findall(pattern, html, re.I | re.DOTALL))
        for cu in re.findall(r'<cite[^>]*>(.*?)</cite>', html, re.DOTALL | re.I):
            clean = re.sub(r'<[^>]+>', '', cu).strip()
            if re.match(r'https?://', clean):
                links.append(clean)
        if len(links) < 3:
            links = extract_all_links(html)
        seen = set()
        result = []
        for link in links:
            clean = link.split('?')[0].split('#')[0].strip()
            if clean and clean not in seen and is_valid_url(clean):
                seen.add(clean)
                result.append(clean)
        return result[:30]

    def extract_title(html: str) -> str:
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.DOTALL)
        if m:
            return re.sub(r'<[^>]+>', '', m.group(1)).strip()
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.DOTALL)
        if m:
            return re.sub(r'<[^>]+>', '', m.group(1)).strip()
        return ""


def calculate_industry_relevance(text: str) -> float:
    """计算文本与轴承行业的相关性得分 (0-1)"""
    if not text:
        return 0.0
    text_lower = text.lower()
    matched = 0
    for kw in INDUSTRY_KEYWORDS:
        if kw.lower() in text_lower:
            matched += 1
    # 也检查英文关键词
    en_keywords = ['bearing', 'ball bearing', 'roller bearing', 'thrust bearing',
                   'linear bearing', 'linear guide', 'ball screw', 'tapered roller',
                   'deep groove', 'angular contact', 'spherical', 'cylindrical roller',
                   'bearing steel', 'ceramic bearing', 'enterprise',
                   'manufacturer', 'supplier', 'directory']
    for kw in en_keywords:
        if kw in text_lower:
            matched += 0.5
    score = min(1.0, matched / 8.0)  # 匹配8个关键词视为满分
    return round(score, 2)


def calculate_enterprise_info_richness(text: str) -> float:
    """计算企业信息丰富度得分 (0-1)"""
    if not text:
        return 0.0
    text_lower = text.lower()
    matched = 0
    for kw in ENTERPRISE_INFO_KEYWORDS:
        if kw.lower() in text_lower:
            matched += 1
    # 检查是否有列表/表格结构（通常表示有多个企业信息）
    list_bonus = 0.0
    if re.search(r'<(table|ul|ol)[^>]*>', text, re.I):
        list_bonus = 0.15
    score = min(1.0, matched / 10.0 + list_bonus)
    return round(score, 2)


def calculate_commercial_relation_richness(text: str) -> float:
    """计算商业关系丰富度得分 (0-1)"""
    if not text:
        return 0.0
    text_lower = text.lower()
    matched = 0
    for kw in COMMERCIAL_RELATION_KEYWORDS:
        if kw.lower() in text_lower:
            matched += 1
    # 额外加分：同时包含"企业"+"关系"类上下文
    relation_bonus = 0.0
    if '客户' in text_lower and '供应商' in text_lower:
        relation_bonus += 0.1
    if '股东' in text_lower and '持股' in text_lower:
        relation_bonus += 0.1
    if '中标' in text_lower and '金额' in text_lower:
        relation_bonus += 0.1
    score = min(1.0, matched / 12.0 + relation_bonus)
    return round(score, 2)


def calculate_data_structuring(html: str) -> float:
    """计算数据结构化程度 (0-1)"""
    if not html:
        return 0.0
    score = 0.0
    # 表格
    tables = len(re.findall(r'<table[^>]*>', html, re.I))
    score += min(0.3, tables * 0.05)
    # 列表
    lists = len(re.findall(r'<(ul|ol)[^>]*>', html, re.I))
    score += min(0.2, lists * 0.03)
    # 结构化标签
    dls = len(re.findall(r'<dl[^>]*>', html, re.I))
    score += min(0.2, dls * 0.05)
    # div卡片布局
    cards = len(re.findall(r'<div[^>]*class="[^"]*(?:card|item|list|info|company|enterprise)[^"]*"', html, re.I))
    score += min(0.3, cards * 0.02)
    return min(1.0, score)


def check_data_freshness(text: str) -> float:
    """检查数据时效性 (0-1)"""
    if not text:
        return 0.0
    current_year = datetime.now().year
    # 查找近3年的年份
    years = re.findall(r'20(2[3-9]|3[0-9])', text)
    if years:
        recent_years = [int('20' + y) for y in years if int('20' + y) <= current_year]
        if recent_years:
            max_year = max(recent_years)
            if max_year >= current_year - 1:
                return 1.0
            elif max_year >= current_year - 2:
                return 0.7
            else:
                return 0.4
    # 查找月份日期格式
    if re.search(r'202[3-9]-\d{2}', text):
        return 0.8
    return 0.3


def check_page_quality(html: str) -> float:
    """检查页面质量 (0-1)"""
    if not html:
        return 0.0
    score = 0.5
    # 页面长度
    if len(html) > 50000:
        score += 0.2
    elif len(html) > 20000:
        score += 0.1
    # 是否有错误提示
    error_patterns = ['404', 'not found', '错误', '无法访问', ' Forbidden', '502', '503']
    text = html.lower()
    for ep in error_patterns:
        if ep.lower() in text[:500]:
            score -= 0.3
            break
    # 是否有丰富内容
    text_content = clean_html_to_text(html)
    if len(text_content) > 3000:
        score += 0.2
    elif len(text_content) > 1000:
        score += 0.1
    return max(0.0, min(1.0, score))


def check_crawl_friendly(html: str, response_time: float) -> float:
    """检查反爬友好度 (0-1)"""
    if not html:
        return 0.0
    score = 0.5
    # 是否有验证码
    captcha_patterns = ['验证码', 'captcha', '请验证', '安全验证', 'slide', '滑块']
    text = html.lower()
    for cp in captcha_patterns:
        if cp in text[:3000]:
            score -= 0.4
            break
    # 是否有访问限制
    limit_patterns = ['访问太频繁', '请求过多', 'too many requests', 'rate limit',
                      '请稍后', '稍后再试', 'access denied']
    for lp in limit_patterns:
        if lp in text[:3000]:
            score -= 0.3
            break
    # 响应时间惩罚
    if response_time > 8:
        score -= 0.2
    elif response_time > 5:
        score -= 0.1
    # 是否有丰富内容（说明返回了正常页面）
    if len(clean_html_to_text(html)) > 500:
        score += 0.2
    return max(0.0, min(1.0, score))


def check_authority(domain: str, text: str) -> float:
    """检查网站权威性 (0-1)"""
    score = 0.3
    domain_lower = domain.lower()
    # 政府/官方域名
    gov_patterns = ['.gov.cn', '.gov', 'cnipa', 'gsxt', 'miit', 'samr']
    for gp in gov_patterns:
        if gp in domain_lower:
            score += 0.4
            break
    # 知名平台
    known_patterns = ['tianyancha', 'qcc', 'qixin', 'aiqicha',
                      'alibaba', '1688', 'zcw168', 'zcjob88',
                      'chinabidding', 'ccgp', 'ggzy', 'cebpubservice',
                      'cbia', 'skf', 'nsk', 'ntn', 'thk']
    for kp in known_patterns:
        if kp in domain_lower:
            score += 0.2
            break
    # 行业关键词
    if text:
        text_lower = text.lower()
        authority_keywords = ['官方', '政府', '国家', ' ministry', 'bureau',
                              '协会', '学会', '联合会', 'industry association']
        for ak in authority_keywords:
            if ak in text_lower:
                score += 0.1
                break
    return min(1.0, score)


# ===================== 主类 =====================

class DataSourceFilter:
    """轴承行业企业信息数据源筛选器"""

    def __init__(self, keywords: List[str] = None, search_depth: int = 2,
                 eval_samples: int = 2, max_sites: int = 150,
                 output_dir: str = None, mode: str = "full",
                 config_output: str = None,
                 resume: bool = False, resume_from: str = None):
        self.keywords = keywords or DEFAULT_KEYWORDS
        self.search_depth = search_depth
        self.eval_samples = max(1, eval_samples)
        self.max_sites = max_sites
        self.mode = mode  # "seed-only" | "full"
        self.discovered_sites: Dict[str, Dict] = {}  # domain -> info
        self.evaluated_sites: List[Dict] = []
        self.crawled_domains: Set[str] = set()

        # 断点续跑
        self.resume = resume
        self.resume_from = resume_from

        # 输出目录（统一使用 common.output）
        if _USE_COMMON:
            self.output_dir = resolve_output_dir(output_dir)
        else:
            if output_dir:
                self.output_dir = output_dir
            elif os.environ.get("PROJECT_DIR"):
                self.output_dir = os.path.join(os.environ.get("PROJECT_DIR"), "output")
            else:
                self.output_dir = os.path.join(os.getcwd(), "output")

        # 进度文件路径
        self.progress_file = os.path.join(self.output_dir, "filter_progress.json")

        # 配置文件输出路径
        if config_output:
            self.config_output = config_output
        else:
            self.config_output = os.path.join(self.output_dir, "data_source_config.json")

    # ---------- 断点续跑 ----------

    def _load_progress(self) -> bool:
        """从 progress_file 加载已发现的网站和评价结果"""
        if not self.resume or not os.path.exists(self.progress_file):
            return False
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress = json.load(f)
            # 恢复已发现的网站
            for domain, info in progress.get("discovered_sites", {}).items():
                self.discovered_sites[domain] = info
            # 恢复已评价的网站
            for site in progress.get("evaluated_sites", []):
                self.evaluated_sites.append(site)
                self.crawled_domains.add(site.get("domain", ""))
            # 恢复已搜索的关键词
            self._searched_keywords = set(progress.get("searched_keywords", []))
            print(f"  [断点续跑] 已加载: {len(self.discovered_sites)} 个网站, "
                  f"{len(self.evaluated_sites)} 个已评价, "
                  f"{len(self._searched_keywords)} 个关键词已搜索")
            return True
        except Exception as e:
            print(f"  [断点续跑] 加载进度失败: {e}")
            return False

    def _save_progress(self, searched_keywords: list = None):
        """保存当前进度"""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            progress = {
                "discovered_sites": self.discovered_sites,
                "evaluated_sites": self.evaluated_sites,
                "searched_keywords": searched_keywords or list(getattr(self, '_searched_keywords', set())),
                "save_time": datetime.now().isoformat(),
            }
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [断点续跑] 保存进度失败: {e}")

    def _merge_existing_evaluation(self):
        """增量评价：加载上次评价结果，跳过已评价且未过期的网站"""
        report_path = self.resume_from
        if not report_path or not os.path.exists(report_path):
            return

        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                old_report = json.load(f)

            old_sites = old_report.get("all_sites", [])
            merged_count = 0
            for site in old_sites:
                domain = site.get("domain", "")
                if not domain or domain in self.crawled_domains:
                    continue
                # 检查是否过期（超过7天需重新评价）
                eval_time = site.get("evaluation_time", "")
                if eval_time and not self._is_expired(eval_time, days=7):
                    self.evaluated_sites.append(site)
                    self.crawled_domains.add(domain)
                    merged_count += 1

            print(f"  [增量评价] 合并 {merged_count} 个未过期网站（共 {len(old_sites)} 个历史记录）")
        except Exception as e:
            print(f"  [增量评价] 加载历史评价失败: {e}")

    @staticmethod
    def _is_expired(time_str: str, days: int = 7) -> bool:
        """检查时间戳是否超过指定天数"""
        try:
            from datetime import timedelta
            eval_time = datetime.fromisoformat(time_str)
            return (datetime.now() - eval_time) > timedelta(days=days)
        except Exception:
            return True

    # ---------- 阶段1: 网站发现 ----------

    async def discover_sites(self, crawler: AsyncWebCrawler) -> Dict[str, Dict]:
        """通过搜索引擎发现候选网站"""
        print(f"\n{'='*60}")
        print("[阶段1] 网站发现 - 通过多搜索引擎搜索候选网站")
        print(f"{'='*60}")
        print(f"搜索关键词数: {len(self.keywords)}")
        print(f"每个关键词搜索深度: {self.search_depth} 页")

        # 使用统一的搜索引擎配置
        engines = SEARCH_ENGINES_PAGINATED if _USE_COMMON else SEARCH_ENGINES
        print(f"搜索引擎: {[e[0] for e in engines]}")

        # 断点续跑：加载已有进度
        if self._load_progress():
            print(f"  从断点恢复，已有 {len(self.discovered_sites)} 个网站")

        searched_keywords = getattr(self, '_searched_keywords', set())

        # 先加入已知种子网站（断点续跑时可能已加入）
        if not self.discovered_sites:
            print(f"\n[种子网站] 加载 {len(KNOWN_SEED_SITES)} 个已知优质网站...")
        for name, url, category in KNOWN_SEED_SITES:
            domain = extract_domain(url)
            if domain and domain not in self.discovered_sites:
                self.discovered_sites[domain] = {
                    "url": url,
                    "domain": domain,
                    "title": name,
                    "category": category,
                    "source": "seed",
                    "discover_time": datetime.now().isoformat(),
                }

        # 通过搜索引擎搜索
        for kw_idx, keyword in enumerate(self.keywords):
            if len(self.discovered_sites) >= self.max_sites * 2:
                print(f"\n已达到最大发现数量 ({self.max_sites * 2})，停止搜索")
                break

            # 断点续跑：跳过已搜索的关键词
            if keyword in searched_keywords:
                continue

            print(f"\n[关键词 {kw_idx+1}/{len(self.keywords)}] {keyword}")

            for page in range(self.search_depth):
                engine_name, engine_url = engines[kw_idx % len(engines)]
                search_url = engine_url.format(keyword=quote(keyword), page=page)
                print(f"  搜索: {engine_name} 第{page+1}页 -> {keyword}")

                result = await self._crawl(crawler, search_url, wait_time=5, scroll=True)
                if result and result.get("success"):
                    links = extract_search_result_links(result["html"], engine_name)
                    new_count = 0
                    for link in links:
                        domain = extract_domain(link)
                        if domain and domain not in self.discovered_sites:
                            self.discovered_sites[domain] = {
                                "url": link,
                                "domain": domain,
                                "title": "",
                                "category": "未知",
                                "source": f"search:{engine_name}",
                                "discover_time": datetime.now().isoformat(),
                            }
                            new_count += 1
                    print(f"    发现 {new_count} 个新网站 (总计 {len(self.discovered_sites)})")
                else:
                    print(f"    搜索失败")

                await asyncio.sleep(random.uniform(1.5, 3.0))

            # 断点续跑：每完成一个关键词保存进度
            searched_keywords.add(keyword)
            self._searched_keywords = searched_keywords
            self._save_progress(list(searched_keywords))

        print(f"\n[网站发现完成] 共发现 {len(self.discovered_sites)} 个候选网站")
        return self.discovered_sites

    # ---------- 阶段2: 网站测试与评价 ----------

    async def evaluate_sites(self, crawler: AsyncWebCrawler) -> List[Dict]:
        """测试并评价候选网站"""
        print(f"\n{'='*60}")
        print("[阶段2] 网站测试与评价")
        print(f"{'='*60}")

        sites = list(self.discovered_sites.values())
        total = min(len(sites), self.max_sites)
        print(f"待评价网站: {total} 个 (从 {len(sites)} 个候选中选取)")
        print(f"每个网站测试次数: {self.eval_samples}")

        evaluated = []

        for idx, site in enumerate(sites[:total]):
            print(f"\n[{idx+1}/{total}] 评价: {site['domain']}")
            result = await self._evaluate_single_site(crawler, site)
            if result:
                evaluated.append(result)
                print(f"  综合得分: {result['overall_score']:.1f}")
            else:
                print(f"  评价失败，跳过")

            # 间隔
            await asyncio.sleep(random.uniform(1.0, 2.5))

        # 排序
        evaluated.sort(key=lambda x: x['overall_score'], reverse=True)

        # 添加排名
        for i, e in enumerate(evaluated, 1):
            e['rank'] = i

        self.evaluated_sites = evaluated
        print(f"\n[评价完成] 成功评价 {len(evaluated)} 个网站")
        return evaluated

    async def _evaluate_single_site(self, crawler: AsyncWebCrawler, site: Dict) -> Optional[Dict]:
        """评价单个网站"""
        url = site['url']
        domain = site['domain']

        if domain in self.crawled_domains:
            return None
        self.crawled_domains.add(domain)

        # 多次采样测试
        response_times = []
        success_count = 0
        html_contents = []
        titles = []

        for i in range(self.eval_samples):
            start = time.time()
            result = await self._crawl(crawler, url, wait_time=3)
            elapsed = (time.time() - start) * 1000  # ms

            if result and result.get("success") and result.get("html"):
                success_count += 1
                response_times.append(elapsed)
                html_contents.append(result["html"])
                titles.append(extract_title(result["html"]))
            else:
                response_times.append(elapsed if elapsed < 15000 else 15000)

            if i < self.eval_samples - 1:
                await asyncio.sleep(random.uniform(0.5, 1.5))

        if success_count == 0:
            return None

        # 使用最好的那次结果进行内容分析
        best_idx = 0
        best_len = 0
        for i, html in enumerate(html_contents):
            text_len = len(clean_html_to_text(html))
            if text_len > best_len:
                best_len = text_len
                best_idx = i

        best_html = html_contents[best_idx]
        best_text = clean_html_to_text(best_html)
        title = titles[best_idx] or site.get('title', '')

        # 计算响应效率指标
        avg_response_time = sum(response_times) / len(response_times)
        success_rate = success_count / self.eval_samples
        stability_score = 1.0 - (len([t for t in response_times if t > 5000]) / len(response_times))

        response_time_score = max(0, 100 - avg_response_time / 100)  # <1秒满分，>10秒0分
        response_efficiency_score = (
            response_time_score * 0.4 +
            success_rate * 100 * 0.4 +
            stability_score * 100 * 0.2
        )

        # 计算数据质量指标
        enterprise_richness = calculate_enterprise_info_richness(best_text)
        commercial_relation = calculate_commercial_relation_richness(best_text)
        industry_relevance = calculate_industry_relevance(best_text)
        structuring = calculate_data_structuring(best_html)
        freshness = check_data_freshness(best_text)

        # 数据质量得分：偏向商业关系（商业关系30%，企业信息20%，行业相关25%，结构化15%，时效性10%）
        data_quality_score = (
            commercial_relation * 100 * 0.30 +
            enterprise_richness * 100 * 0.20 +
            industry_relevance * 100 * 0.25 +
            structuring * 100 * 0.15 +
            freshness * 100 * 0.10
        )

        # 计算网站质量指标
        page_quality = check_page_quality(best_html)
        crawl_friendly = check_crawl_friendly(best_html, avg_response_time / 1000)
        authority = check_authority(domain, best_text)

        site_quality_score = (
            page_quality * 100 * 0.4 +
            crawl_friendly * 100 * 0.3 +
            authority * 100 * 0.3
        )

        # 综合得分
        overall_score = (
            response_efficiency_score * 0.30 +
            data_quality_score * 0.40 +
            site_quality_score * 0.30
        )

        # 推断分类
        category = site.get('category', '未知')
        if category == '未知':
            category = self._infer_category(domain, best_text)

        # 生成评价备注
        notes = []
        if commercial_relation > 0.6:
            notes.append("商业关系丰富")
        if enterprise_richness > 0.7:
            notes.append("企业信息丰富")
        if industry_relevance > 0.7:
            notes.append("行业相关性强")
        if avg_response_time < 2000:
            notes.append("响应速度快")
        if success_rate < 1.0:
            notes.append(f"成功率{success_rate:.0%}")
        if crawl_friendly < 0.5:
            notes.append("反爬严格")
        note = "，".join(notes) if notes else "常规网站"

        return {
            "url": url,
            "domain": domain,
            "title": title,
            "category": category,
            "response_efficiency": {
                "avg_response_time_ms": round(avg_response_time, 0),
                "success_rate": round(success_rate, 2),
                "stability_score": round(stability_score, 2),
                "score": round(response_efficiency_score, 1),
            },
            "data_quality": {
                "commercial_relation_richness": round(commercial_relation, 2),
                "enterprise_info_richness": round(enterprise_richness, 2),
                "industry_relevance": round(industry_relevance, 2),
                "data_structuring": round(structuring, 2),
                "data_freshness": round(freshness, 2),
                "score": round(data_quality_score, 1),
            },
            "site_quality": {
                "page_quality": round(page_quality, 2),
                "crawl_friendly": round(crawl_friendly, 2),
                "authority": round(authority, 2),
                "score": round(site_quality_score, 1),
            },
            "overall_score": round(overall_score, 1),
            "evaluation_notes": note,
            "content_sample": best_text[:300] + "..." if len(best_text) > 300 else best_text,
        }

    def _infer_category(self, domain: str, text: str) -> str:
        """根据域名和内容推断网站分类"""
        domain_lower = domain.lower()
        text_lower = text.lower() if text else ""

        # 工商查询
        if any(k in domain_lower for k in ['tianyancha', 'qcc', 'qixin', 'aiqicha', 'gsxt']):
            return "工商查询"
        # 招投标
        if any(k in domain_lower for k in ['bid', 'zhaobiao', 'tender', 'ccgp', 'ggzy', 'cebpubservice',
                                            'chinabidding', 'gonggao', 'purchase']):
            return "招投标平台"
        # 专利
        if any(k in domain_lower for k in ['patent', 'cnipa', 'zhuanli', 'soopat', 'trademark']):
            return "专利平台"
        # B2B/采购
        if any(k in domain_lower for k in ['1688', 'alibaba', 'hqew', 'lcsc', 'ickey', 'ichunt',
                                            'sekorm', 'dzsc', 'ic.net', 'b2b']):
            return "B2B平台"
        # 行业媒体
        if any(k in domain_lower for k in ['news', 'media', 'cbia', 'zcbearing', 'mw1950',
                                            'bearing', 'machine', 'mei.net', 'industry']):
            return "行业媒体"
        # 企业名录
        if any(k in text_lower for k in ['名录', '黄页', 'directory', '企业列表', '厂商列表']):
            return "企业名录"
        if any(k in text_lower for k in ['供应', '采购', '求购', 'b2b', '批发']):
            return "B2B平台"
        if any(k in text_lower for k in ['招标', '中标', '采购公告']):
            return "招投标平台"
        if any(k in text_lower for k in ['专利', '商标', '知识产权']):
            return "专利平台"
        # 司法/诉讼
        if any(k in domain_lower for k in ['wenshu', 'zxgk', 'tingshen', 'court']):
            return "司法信息"
        if any(k in text_lower for k in ['诉讼', '判决', '仲裁', '执行']):
            return "司法信息"
        # 海关
        if any(k in domain_lower for k in ['customs', 'tradesns', 'tendata']):
            return "海关数据"
        # 学术/标准
        if any(k in domain_lower for k in ['cnki', 'wanfang', 'cqvip', 'std.samr']):
            return "学术标准"

        return "综合平台"

    # ---------- 阶段3: 生成报告 ----------

    def generate_report(self) -> Dict[str, Any]:
        """生成评价报告"""
        print(f"\n{'='*60}")
        print("[阶段3] 生成评价报告并遴选TOP20")
        print(f"{'='*60}")

        evaluated = self.evaluated_sites
        top20 = evaluated[:20]

        # 统计分类分布
        category_dist = {}
        for site in evaluated:
            cat = site['category']
            category_dist[cat] = category_dist.get(cat, 0) + 1

        report = {
            "evaluation_summary": {
                "total_discovered": len(self.discovered_sites),
                "total_evaluated": len(evaluated),
                "top20_selected": len(top20) >= 20,
                "evaluation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "search_keywords": self.keywords,
                "search_depth": self.search_depth,
                "eval_samples": self.eval_samples,
            },
            "all_sites": evaluated,
            "top20_sites": top20,
            "category_distribution": category_dist,
        }

        # 打印TOP20
        print(f"\n{'='*60}")
        print("TOP 20 优质数据源网站")
        print(f"{'='*60}")
        print(f"{'排名':<4} {'综合得分':<8} {'响应':<6} {'数据':<6} {'网站':<6} {'分类':<10} {'域名':<30}")
        print("-" * 70)
        for site in top20:
            print(f"{site['rank']:<4} "
                  f"{site['overall_score']:<8} "
                  f"{site['response_efficiency']['score']:<6} "
                  f"{site['data_quality']['score']:<6} "
                  f"{site['site_quality']['score']:<6} "
                  f"{site['category']:<10} "
                  f"{site['domain']:<30}")

        print(f"\n{'='*60}")
        print("分类分布统计")
        print(f"{'='*60}")
        for cat, count in sorted(category_dist.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}个")

        print(f"\n{'='*60}")
        print("详细网站信息")
        print(f"{'='*60}")
        for site in top20:
            print(f"\n[{site['rank']}] {site['title'] or site['domain']}")
            print(f"  URL: {site['url']}")
            print(f"  分类: {site['category']}")
            print(f"  综合得分: {site['overall_score']}")
            print(f"  响应效率: {site['response_efficiency']['score']} "
                  f"(响应{site['response_efficiency']['avg_response_time_ms']:.0f}ms "
                  f"成功率{site['response_efficiency']['success_rate']:.0%})")
            print(f"  数据质量: {site['data_quality']['score']} "
                  f"(企业信息{site['data_quality']['enterprise_info_richness']:.0%} "
                  f"行业相关{site['data_quality']['industry_relevance']:.0%})")
            print(f"  网站质量: {site['site_quality']['score']} "
                  f"(页面{site['site_quality']['page_quality']:.0%} "
                  f"反爬友好{site['site_quality']['crawl_friendly']:.0%} "
                  f"权威{site['site_quality']['authority']:.0%})")
            print(f"  评价: {site['evaluation_notes']}")

        return report

    def save_report(self, report: Dict[str, Any]) -> str:
        """保存报告到文件"""
        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data_source_evaluation_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"报告已保存: {filepath}")
        print(f"{'='*60}")
        return filepath

    # ---------- 通用方法 ----------

    async def _crawl(self, crawler: AsyncWebCrawler, url: str,
                     wait_time: int = 5, scroll: bool = False) -> Optional[Dict]:
        """通用爬取方法"""
        try:
            js_code = None
            if scroll:
                js_code = """
                (async () => {
                    for (let i = 0; i < 2; i++) {
                        window.scrollTo(0, document.body.scrollHeight);
                        await new Promise(r => setTimeout(r, 800));
                    }
                })();
                """

            config = CrawlerRunConfig(
                page_timeout=15000,
                delay_before_return_html=wait_time,
            )
            if js_code:
                config = CrawlerRunConfig(
                    page_timeout=15000,
                    delay_before_return_html=wait_time,
                    js_code=js_code,
                )

            result = await crawler.arun(url=url, config=config)
            if result.success:
                return {"success": True, "html": result.html or "", "url": url}
            return None
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    # ---------- 主流程 ----------

    async def run(self) -> Dict[str, Any]:
        """执行完整流程"""
        print(f"\n{'#'*60}")
        print("# bearing-data-source-filter: 轴承行业企业信息数据源筛选")
        print(f"{'#'*60}")
        print(f"模式: {self.mode}")
        print(f"输出目录: {self.output_dir}")
        print(f"配置文件: {self.config_output}")

        if self.mode == "seed-only":
            print("\n[seed-only 模式] 跳过网络搜索，直接基于种子列表生成配置")
            config_path = self._generate_config_from_seed()
            return {
                "mode": "seed-only",
                "config_file": config_path,
                "message": "已基于种子列表生成默认配置",
            }

        print(f"搜索关键词: {len(self.keywords)} 个")
        print(f"搜索深度: {self.search_depth} 页/关键词")
        print(f"评价采样: {self.eval_samples} 次/网站")
        print(f"最大评价数: {self.max_sites}")

        browser_config = BrowserConfig(
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        start_time = time.time()

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # 阶段1: 网站发现
            await self.discover_sites(crawler)

            # 阶段2: 网站测试与评价
            await self.evaluate_sites(crawler)

        # 阶段3: 生成报告
        report = self.generate_report()

        elapsed = time.time() - start_time
        report["evaluation_summary"]["total_time_seconds"] = round(elapsed, 1)

        print(f"\n总耗时: {elapsed:.1f} 秒")

        # 保存评价报告
        report_filepath = self.save_report(report)
        report["output_file"] = report_filepath

        # 阶段4: 生成/更新配置文件（供 crawl skill 消费）
        config_path = self.generate_and_save_config()
        report["config_file"] = config_path

        return report

    def _generate_config_from_seed(self) -> str:
        """seed-only 模式：直接基于种子列表生成配置"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        seed_path = os.path.join(script_dir, "..", "references", "bearing_industry_sites.md")
        seed_path = os.path.normpath(seed_path)

        if not os.path.exists(seed_path):
            print(f"警告：找不到种子列表文件 {seed_path}，使用内置 KNOWN_SEED_SITES")
            return self._generate_config_from_builtin_seed()

        try:
            import generate_default_config as gdc
            config_path = gdc.generate_config(seed_path, self.output_dir)
            print(f"\n配置文件已生成: {config_path}")
            return config_path
        except Exception as e:
            print(f"调用 generate_default_config 失败: {e}，使用内置种子")
            return self._generate_config_from_builtin_seed()

    def _generate_config_from_builtin_seed(self) -> str:
        """使用内置 KNOWN_SEED_SITES 生成配置"""
        sources = []
        seen_ids = set()

        for name, url, category in KNOWN_SEED_SITES:
            sid = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', name).lower()[:30] or "source"
            counter = 1
            original_id = sid
            while sid in seen_ids:
                sid = f"{original_id}_{counter}"
                counter += 1
            seen_ids.add(sid)

            data_types = ["business_info", "commercial_relation"]
            if "专利" in category or "知识产权" in category:
                data_types = ["patent_info"]
            elif "招标" in category or "投标" in category or "采购" in category:
                data_types = ["bidding_info", "commercial_relation"]
            elif "行业媒体" in category or "展会" in category:
                data_types = ["commercial_relation"]

            sources.append({
                "id": sid,
                "name": name,
                "category": category,
                "base_url": url,
                "search_url_template": None,
                "search_keywords_template": [],
                "data_types": data_types,
                "priority": 1,
                "enabled": True,
                "authority_score": None,
                "crawl_friendly_score": None,
                "overall_score": None,
                "notes": "",
            })

        config = {
            "schema_version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "generated_by": "bearing-data-source-filter",
            "industry": "轴承",
            "description": "基于内置种子列表生成的默认配置",
            "update_policy": {
                "seed_list_source": "builtin",
                "evaluation_trigger": "manual_or_scheduled",
                "auto_promote_threshold": 70,
            },
            "sources": sources,
        }

        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.config_output, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"\n配置文件已生成: {self.config_output}")
        return self.config_output

    def generate_and_save_config(self) -> str:
        """基于评价结果生成/更新 data_source_config.json"""
        os.makedirs(self.output_dir, exist_ok=True)

        # 尝试加载已有配置（如果有）
        existing_sources = {}
        if os.path.exists(self.config_output):
            try:
                with open(self.config_output, 'r', encoding='utf-8') as f:
                    old = json.load(f)
                for s in old.get("sources", []):
                    existing_sources[s.get("id")] = s
            except Exception:
                pass

        sources = []
        seen_ids = set()

        # 以评价结果为基础生成配置
        for site in self.evaluated_sites:
            name = site.get("title") or site.get("domain", "")
            sid = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', name).lower()[:30] or "source"
            counter = 1
            original_id = sid
            while sid in seen_ids:
                sid = f"{original_id}_{counter}"
                counter += 1
            seen_ids.add(sid)

            # 推断 data_types
            category = site.get("category", "综合平台")
            data_types = ["business_info", "commercial_relation"]
            if "专利" in category or "知识产权" in category or "商标" in category:
                data_types = ["patent_info"]
            elif "招标" in category or "投标" in category or "采购" in category:
                data_types = ["bidding_info", "commercial_relation"]
            elif "工商" in category or "企业名录" in category or "黄页" in category:
                data_types = ["business_info", "commercial_relation"]
            elif "行业媒体" in category or "展会" in category or "研究" in category:
                data_types = ["commercial_relation"]

            # 生成搜索关键词模板
            keywords_set = set()
            for dt in data_types:
                for kw in ["{name} 工商信息", "{name} 注册资本", "{name} 法人代表", "{name} 经营范围", "{name} 股东信息",
                           "{name} 招标", "{name} 中标", "{name} 采购", "{name} 竞标",
                           "{name} 专利", "{name} 发明专利", "{name} 实用新型", "{name} 外观设计", "{name} 知识产权",
                           "{name} 供应链", "{name} 客户", "{name} 供应商", "{name} 股东", "{name} 投资", "{name} 合作"]:
                    if dt == "business_info" and "工商" in kw or "资本" in kw or "法人" in kw or "经营" in kw or "股东" in kw:
                        keywords_set.add(kw)
                    elif dt == "bidding_info" and ("招标" in kw or "中标" in kw or "采购" in kw or "竞标" in kw):
                        keywords_set.add(kw)
                    elif dt == "patent_info" and ("专利" in kw or "发明" in kw or "新型" in kw or "外观" in kw or "知识产权" in kw):
                        keywords_set.add(kw)
                    elif dt == "commercial_relation" and ("供应链" in kw or "客户" in kw or "供应商" in kw or "股东" in kw or "投资" in kw or "合作" in kw):
                        keywords_set.add(kw)
            keywords_template = list(keywords_set)

            # 合并已有配置中的搜索模板等
            existing = existing_sources.get(sid, {})
            search_template = existing.get("search_url_template")
            if existing.get("search_keywords_template") and not keywords_template:
                keywords_template = existing.get("search_keywords_template", [])
            priority = existing.get("priority", 1)

            # 根据评分调整 priority
            overall = site.get("overall_score", 0)
            if overall >= 85:
                priority = 1
            elif overall >= 70:
                priority = 2
            elif overall >= 55:
                priority = 3
            else:
                priority = 4

            sources.append({
                "id": sid,
                "name": name,
                "category": category,
                "base_url": site.get("url", ""),
                "search_url_template": search_template,
                "search_keywords_template": keywords_template,
                "data_types": data_types,
                "priority": priority,
                "enabled": overall >= 40,  # D级以下禁用
                "authority_score": site.get("site_quality", {}).get("authority"),
                "crawl_friendly_score": site.get("site_quality", {}).get("crawl_friendly"),
                "overall_score": overall,
                "notes": site.get("evaluation_notes", ""),
            })

        config = {
            "schema_version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "generated_by": "bearing-data-source-filter",
            "industry": "轴承",
            "description": "基于自动化评价生成的数据源配置，供 bearing-enterprise-data-crawl 消费",
            "update_policy": {
                "seed_list_source": "references/bearing_industry_sites.md",
                "evaluation_trigger": "manual_or_scheduled",
                "auto_promote_threshold": 70,
                "last_evaluation": datetime.now().isoformat(),
            },
            "sources": sources,
        }

        with open(self.config_output, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"\n配置文件已生成: {self.config_output}")
        print(f"共 {len(sources)} 个数据源，已按评分排序")
        return self.config_output


def main():
    parser = argparse.ArgumentParser(description="轴承行业企业信息数据源筛选与评价")
    parser.add_argument("--keywords", help="自定义搜索关键词，逗号分隔")
    parser.add_argument("--search-depth", type=int, default=2, help="每个关键词搜索页数 (默认2)")
    parser.add_argument("--eval-samples", type=int, default=2, help="每个网站测试次数 (默认2)")
    parser.add_argument("--max-sites", type=int, default=150, help="最大评价网站数 (默认150)")
    parser.add_argument("--output-dir", help="输出目录", default=None)
    parser.add_argument("--mode", choices=["seed-only", "full"], default="full",
                        help="运行模式: seed-only=仅基于种子列表生成配置(无网络请求), full=完整搜索+评价+生成配置 (默认full)")
    parser.add_argument("--config-output", help="配置文件输出路径 (默认: output_dir/data_source_config.json)", default=None)
    parser.add_argument("--resume", action="store_true", help="从断点恢复（使用上次进度）")
    parser.add_argument("--resume-from", help="基于上次评价结果增量更新（指定评价报告JSON路径）", default=None)
    args = parser.parse_args()

    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    filter_obj = DataSourceFilter(
        keywords=keywords,
        search_depth=args.search_depth,
        eval_samples=args.eval_samples,
        max_sites=args.max_sites,
        output_dir=args.output_dir,
        mode=args.mode,
        config_output=args.config_output,
        resume=args.resume,
        resume_from=args.resume_from,
    )

    result = asyncio.run(filter_obj.run())
    return result


if __name__ == "__main__":
    main()

