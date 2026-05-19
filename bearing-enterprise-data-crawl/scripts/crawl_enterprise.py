#!/usr/bin/env python3
"""
企业信息采集脚本 - 基于 Crawl4AI（聚焦增强版）
重点采集：官网 / 工商 / 招投标 / 专利 四大核心数据
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import quote, urlparse
import random
import sys
import traceback

sys.stdout.reconfigure(encoding='utf-8')

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
except ImportError:
    print("请先安装 crawl4ai: pip install crawl4ai")
    exit(1)

# 导入共享模块
try:
    _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
    from common.web_utils import clean_html_to_text, extract_all_links, extract_domain, is_valid_url, extract_title
    from common.search_engines import (
        SEARCH_ENGINES_SIMPLE, extract_search_result_links,
        build_search_url, get_engine_name,
    )
    from common.blacklist import BLACKLIST_KEYWORDS
    from common.output import resolve_output_dir
    from common.cache import ResponseCache
    _USE_COMMON = True
except ImportError:
    _USE_COMMON = False


# ===================== 配置区 =====================

# 搜索引擎
SEARCH_ENGINES = [
    ("百度", "https://www.baidu.com/s?wd={keyword}"),
    ("必应", "https://cn.bing.com/search?q={keyword}"),
    ("搜狗", "https://www.sogou.com/web?query={keyword}"),
    ("360搜索", "https://www.so.com/s?q={keyword}"),
]

# ========== 四大核心维度的搜索策略 ==========

# 官网搜索关键词（多角度定位真实官网）
OFFICIAL_WEBSITE_KEYWORDS = [
    "{name} 官网",
    "{name} 官方网站",
    "{short} 官网",
    "{name} 公司简介",
    "{name} 关于我们",
    "{name} 联系方式",
]

# 工商搜索关键词
BUSINESS_KEYWORDS = [
    "{name} 工商信息",
    "{name} 注册资本",
    "{name} 法人代表",
    "{name} 经营范围",
    "{name} 股东信息",
    "{name} site:gsxt.gov.cn",
]

# 招投标搜索关键词
BIDDING_KEYWORDS = [
    "{name} 招标",
    "{name} 中标",
    "{name} 采购",
    "{name} 竞标",
    "{name} site:ccgp.gov.cn",
    "{name} site:ggzy.gov.cn",
    "{name} site:cebpubservice.com",
]

# 专利搜索关键词
PATENT_KEYWORDS = [
    "{name} 专利",
    "{name} 发明专利",
    "{name} 实用新型",
    "{name} 外观设计",
    "{name} 知识产权",
    "{name} site:cnipa.gov.cn",
]

# ========== 直接平台 URL ==========

# 工商平台
BUSINESS_PLATFORMS = [
    ("天眼查", "https://www.tianyancha.com/search?key={name}"),
    ("企查查", "https://www.qcc.com/web/search?key={name}"),
    ("爱企查", "https://aiqicha.baidu.com/s?wd={name}"),
    ("启信宝", "https://www.qixin.com/search?key={name}"),
    ("国家企业信用公示", "https://www.gsxt.gov.cn/index.html"),
]

# 招投标平台
BIDDING_PLATFORMS = [
    ("中国政府采购网", "http://search.ccgp.gov.cn/bxsearch?searchtype=1&bidSort=0&pinMu=0&bidType=1&dbselect=bidx&kw={name}"),
    ("全国公共资源交易", "https://deal.ggzy.gov.cn/ds/deal/dealList.jsp?search={name}"),
    ("中国招标投标平台", "http://www.cebpubservice.com/search?keyword={name}"),
    ("采招网", "https://search.bidcenter.com.cn/search?keywords={name}"),
    ("中国采购与招标网", "https://www.chinabidding.cn/search/searchzbgg?keyword={name}"),
]

# 专利平台
PATENT_PLATFORMS = [
    ("国家知识产权局-专利检索", "https://pss-system.cponline.cnipa.gov.cn/conventionalSearch?searchType=patent&keyword={name}"),
    ("中国商标网", "https://wcjs.sbj.cnipa.gov.cn/?word={name}"),
    ("专利之星", "https://www.cprs.patentstar.com/search?kw={name}"),
    ("soopat专利检索", "https://www.soopat.com/Home/Result?SearchWord={name}"),
]

# 官网站内深度采集的重要页面关键词
OFFICIAL_SITE_IMPORTANT_PATHS = [
    'about', 'intro', 'profile', 'company', 'overview',     # 关于我们
    'product', 'solution', 'service', 'technology',          # 产品/方案
    'news', 'article', 'press', 'media', 'xinwen',          # 新闻
    'contact', 'connect', 'reach',                           # 联系方式
    'team', 'leader', 'management',                          # 团队
    'honor', 'certif', 'qualification', 'aptitude',          # 资质荣誉
    'partner', 'cooperation', 'client',                      # 合作伙伴
    'recruit', 'career', 'job', 'join',                      # 招聘
    'guanyu', 'chanpin', 'jianjie', 'zizhi', 'hezuo',       # 中文拼音
]

# 黑名单
BLACKLIST_DOMAINS = {
    'baidu.com', 'bing.com', 'google.com', 'sogou.com', 'so.com',
    'taobao.com', 'jd.com', 'tmall.com', 'pinduoduo.com',
    'douyin.com', 'kuaishou.com', 'bilibili.com',
    'weibo.com', 'zhihu.com', 'douban.com',
    'csdn.net', 'jianshu.com', 'toutiao.com', '51cto.com',
    'ad.com', 'doubleclick.net', 'googlesyndication.com',
    '58.com', 'ganji.com', 'zhipin.com', 'liepin.com',   # 招聘/分类
    '1688.com', 'made-in-china.com', 'alibaba.com',       # B2B
}

BLACKLIST_KEYWORDS = {
    'login', 'signin', 'register', 'signup', 'password',
    'member', 'vip', 'pay', 'payment', 'cart', 'shop',
    'download', 'app', 'plugin', 'ad.', 'ads.',
    'video.', 'play.', 'music.', 'game.',
    'zhaopin', 'job', 'career', 'recruit',               # 排除招聘页面
}


# ===================== 工具函数 =====================
# 当 common 模块可用时使用共享实现，否则回退到本地实现

if not _USE_COMMON:
    def is_valid_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return False
            domain = parsed.netloc.lower()
            for bd in BLACKLIST_DOMAINS:
                if bd in domain:
                    return False
            path_query = (parsed.path + parsed.query).lower()
            for bk in BLACKLIST_KEYWORDS:
                if bk in path_query:
                    return False
            return True
        except Exception:
            return False

    def extract_domain(url: str) -> str:
        try:
            return urlparse(url).netloc
        except Exception:
            return ""

    def clean_html_to_text(html: str) -> str:
        for tag in ['script', 'style', 'noscript', 'nav', 'footer', 'header',
                    'aside', 'iframe', 'form', 'button', 'svg', 'img']:
            html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.I)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        parts = []
        for tag, min_len in [('p', 10), ('h1', 3), ('h2', 3), ('h3', 3),
                             ('h4', 3), ('h5', 3), ('li', 6), ('td', 6),
                             ('span', 15), ('div', 30), ('article', 15),
                             ('section', 15), ('blockquote', 8),
                             ('dt', 3), ('dd', 5), ('th', 3), ('tr', 5)]:
            texts = re.findall(f'<{tag}[^>]*>(.*?)</{tag}>', html, re.DOTALL | re.I)
            for t in texts:
                clean = re.sub(r'<[^>]+>', '', t).strip()
                if len(clean) > min_len and not re.match(r'^[\d\s\.,;:!?\-+/()]+$', clean):
                    parts.append(clean)
        content = ' '.join(parts)
        return re.sub(r'\s+', ' ', content).strip()

    def extract_all_links(html: str) -> List[str]:
        links = []
        for m in re.findall(r'href=["\'](https?://[^"\']+)["\']', html, re.I):
            links.append(m)
        for m in re.findall(r'data-(?:url|href)=["\'](https?://[^"\']+)["\']', html, re.I):
            links.append(m)
        for m in re.findall(r'<cite[^>]*>(.*?)</cite>', html, re.DOTALL | re.I):
            clean = re.sub(r'<[^>]+>', '', m).strip()
            if re.match(r'https?://', clean):
                links.append(clean)
        seen = set()
        result = []
        for link in links:
            clean = link.split('#')[0].strip()
            if clean and clean not in seen and len(clean) > 10:
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


# ===================== 主采集器 =====================

class EnterpriseDataCrawler:
    """企业信息采集器（聚焦版：官网/工商/招投标/专利）"""

    def __init__(self, max_pages: int = 20, progress_callback=None, output_dir: str = None,
                 source_config: str = None):
        self.results = {
            "enterprise_name": "",
            "source_urls": [],
            "raw_content": {},
            "crawl_status": "failed",
            "confidence": 0.0,
            "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "note": ""
        }
        self.max_pages = max_pages
        self.crawled_urls: Set[str] = set()
        self.official_website_url: Optional[str] = None  # 已确认的官网URL
        self.progress_callback = progress_callback  # 进度回调函数
        # 输出目录：优先使用指定目录，否则使用当前工作目录下的 output
        # 输出目录优先级: --output-dir 参数 > PROJECT_DIR 环境变量 > 当前工作目录
        if _USE_COMMON:
            self.output_dir = resolve_output_dir(output_dir)
        else:
            if output_dir:
                self.output_dir = output_dir
            elif os.environ.get("PROJECT_DIR"):
                self.output_dir = os.path.join(os.environ.get("PROJECT_DIR"), "output")
            else:
                self.output_dir = os.path.join(os.getcwd(), "output")

        # 平台列表（可被配置文件覆盖）
        self.business_platforms = list(BUSINESS_PLATFORMS)
        self.bidding_platforms = list(BIDDING_PLATFORMS)
        self.patent_platforms = list(PATENT_PLATFORMS)

        # 搜索关键词（可被配置文件覆盖）
        self.business_keywords = list(BUSINESS_KEYWORDS)
        self.bidding_keywords = list(BIDDING_KEYWORDS)
        self.patent_keywords = list(PATENT_KEYWORDS)

        # 域名分类映射（可被配置文件覆盖）
        self.domain_type_map: Dict[str, str] = {}

        # 加载外部配置（未指定时自动寻找默认配置）
        config_path = source_config or self._find_default_config()
        if config_path:
            self._load_source_config(config_path)

    @staticmethod
    def _search_upwards(start_dir: str, target_relative: str, max_depth: int = 5) -> Optional[str]:
        """从 start_dir 向上递归查找目标文件（最多 max_depth 层）"""
        current = os.path.abspath(start_dir)
        for _ in range(max_depth):
            candidate = os.path.join(current, target_relative)
            if os.path.exists(candidate):
                return candidate
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return None

    @staticmethod
    def _find_default_config() -> Optional[str]:
        """自动寻找 bearing-data-source-filter 生成的默认配置文件"""
        target = os.path.join("bearing-data-source-filter", "scripts", "output", "data_source_config.json")

        # 候选路径（按优先级）
        candidates = [
            # 1. 相对于本脚本所在目录直接向上两级
            os.path.join(os.path.dirname(__file__), "..", "..", target),
            # 2. 相对于当前工作目录
            os.path.join(os.getcwd(), target),
            # 3. 相对于项目根目录（通过环境变量）
            os.path.join(os.environ.get("PROJECT_DIR", ""), target),
        ]
        for path in candidates:
            path = os.path.abspath(path)
            if os.path.exists(path):
                print(f"[自动配置] 发现默认数据源配置: {path}")
                return path

        # 4. 从脚本所在目录向上递归搜索（应对 skill 被复制到临时目录的情况）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        found = EnterpriseDataCrawler._search_upwards(script_dir, target, max_depth=5)
        if found:
            print(f"[自动配置] 发现默认数据源配置: {found}")
            return found

        # 5. 从当前工作目录向上递归搜索
        found = EnterpriseDataCrawler._search_upwards(os.getcwd(), target, max_depth=5)
        if found:
            print(f"[自动配置] 发现默认数据源配置: {found}")
            return found

        return None

    def _load_source_config(self, config_path: str):
        """从 data_source_config.json 加载平台配置"""
        if not os.path.exists(config_path):
            print(f"[警告] 配置文件不存在: {config_path}，使用内置平台列表")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            sources = config.get("sources", [])
            if not sources:
                print("[警告] 配置文件中无数据源，使用内置平台列表")
                return

            business = []
            bidding = []
            patent = []
            domain_map: Dict[str, str] = {}
            biz_keywords: set = set()
            bid_keywords: set = set()
            pat_keywords: set = set()

            for src in sources:
                if not src.get("enabled", True):
                    continue
                template = src.get("search_url_template")
                name = src.get("name", src.get("id", "未知"))
                data_types = src.get("data_types", [])
                base_url = src.get("base_url", "")

                # 提取域名用于分类映射（按优先级取最高优先级的 data_type）
                if base_url:
                    try:
                        domain = urlparse(base_url).netloc.lower()
                        if domain.startswith("www."):
                            domain = domain[4:]
                        for dt in data_types:
                            # 优先级：business_info(1) > bidding_info(2) > patent_info(3) > commercial_relation(4)
                            priority = {"business_info": 1, "bidding_info": 2, "patent_info": 3, "commercial_relation": 4}
                            existing = domain_map.get(domain)
                            existing_p = priority.get(existing, 99)
                            new_p = priority.get(dt, 99)
                            if new_p < existing_p:
                                domain_map[domain] = dt
                    except Exception:
                        pass

                # 聚合搜索关键词
                for kw in src.get("search_keywords_template", []):
                    if "business_info" in data_types:
                        biz_keywords.add(kw)
                    if "bidding_info" in data_types:
                        bid_keywords.add(kw)
                    if "patent_info" in data_types:
                        pat_keywords.add(kw)

                if not template:
                    continue

                if "business_info" in data_types:
                    business.append((name, template))
                if "bidding_info" in data_types:
                    bidding.append((name, template))
                if "patent_info" in data_types:
                    patent.append((name, template))

            # 覆盖平台列表
            if business:
                self.business_platforms = business
                print(f"[配置加载] 工商平台: {len(business)} 个")
            if bidding:
                self.bidding_platforms = bidding
                print(f"[配置加载] 招投标平台: {len(bidding)} 个")
            if patent:
                self.patent_platforms = patent
                print(f"[配置加载] 专利平台: {len(patent)} 个")

            # 覆盖搜索关键词（如果配置中有）
            if biz_keywords:
                self.business_keywords = sorted(biz_keywords)
                print(f"[配置加载] 工商搜索关键词: {len(self.business_keywords)} 条")
            if bid_keywords:
                self.bidding_keywords = sorted(bid_keywords)
                print(f"[配置加载] 招投标搜索关键词: {len(self.bidding_keywords)} 条")
            if pat_keywords:
                self.patent_keywords = sorted(pat_keywords)
                print(f"[配置加载] 专利搜索关键词: {len(self.patent_keywords)} 条")

            # 覆盖域名分类映射
            if domain_map:
                self.domain_type_map = domain_map
                print(f"[配置加载] 域名分类映射: {len(domain_map)} 条")

            print(f"[配置加载] 已从 {config_path} 加载数据源配置")
        except Exception as e:
            print(f"[警告] 加载配置文件失败: {e}，使用内置平台列表")

    def classify_url(self, url: str) -> str:
        """四大分类：official_website / business_info / bidding_info / patent_info
        优先使用配置中的域名映射，回退到硬编码模式"""
        url_lower = url.lower()

        # 优先匹配配置中的域名映射
        try:
            domain = urlparse(url_lower).netloc
            if domain.startswith("www."):
                domain = domain[4:]
            mapped = self.domain_type_map.get(domain)
            if mapped:
                return mapped
            # 尝试子串匹配（域名包含关系）
            for mapped_domain, data_type in self.domain_type_map.items():
                if mapped_domain in domain or domain in mapped_domain:
                    return data_type
        except Exception:
            pass

        # 回退到硬编码模式
        business_patterns = [
            'tianyancha', 'qcc.com', 'qixin.com', 'aiqicha',
            'gsxt.gov', 'gov.cn', 'ndrc', 'miit', 'mee', 'samr',
            'cninfo', 'sse.com', 'szse', 'neeq', 'samr',
        ]
        if any(p in url_lower for p in business_patterns):
            return 'business_info'

        bid_patterns = [
            'bid', 'zhaobiao', 'tender', 'ccgp', 'ctbp', 'ggzy',
            'cebpubservice', 'gonggao', 'purchase', 'procurement',
            'bidcenter', 'chinabidding', 'public-resource', 'jyxx',
        ]
        if any(p in url_lower for p in bid_patterns):
            return 'bidding_info'

        patent_patterns = [
            'patent', 'cnipa', 'cponline', 'trademark', 'sbj.cnipa',
            'ipr', 'zhuanli', 'soopat', 'patentstar', 'cprs',
        ]
        if any(p in url_lower for p in patent_patterns):
            return 'patent_info'

        return 'official_website'

    def _report_progress(self, progress: int, step: str, detail: str = ""):
        """报告采集进度"""
        if self.progress_callback:
            self.progress_callback(progress, "模块1采集", step, detail)

    # ---------- 并发平台爬取（优化方案1.3） ----------

    async def _crawl_platforms_concurrent(self, crawler: AsyncWebCrawler,
                                           platform_tasks: List[Tuple[str, str]],
                                           category: str,
                                           name: str,
                                           max_concurrent: int = 3,
                                           min_results: int = 2) -> List[Dict]:
        """并发爬取多个平台（Semaphore控制并发数）

        Args:
            crawler: 爬虫实例
            platform_tasks: [(平台名, URL), ...]
            category: 内容分类（business_info/bidding_info/patent_info）
            name: 企业名
            max_concurrent: 最大并发数
            min_results: 最少结果数（达到后停止）
        """
        crawled = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _crawl_one(pname: str, url: str) -> Optional[Dict]:
            async with semaphore:
                result = await self._crawl(crawler, url, wait_time=3, scroll=True)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                if result and result.get("success"):
                    content = clean_html_to_text(result["html"])
                    if len(content) > 80:
                        return {
                            "platform": pname,
                            "url": url,
                            "content": content,
                            "html": result["html"],
                        }
                return None

        tasks = [_crawl_one(pname, url) for pname, url in platform_tasks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                print(f"    平台爬取异常: {r}")
                continue
            if r is None:
                continue

            pname = r["platform"]
            url = r["url"]
            content = r["content"]

            if url not in self.crawled_urls:
                self.crawled_urls.add(url)
                self.results["source_urls"].append(url)
                crawled.append({
                    "url": url,
                    "content": content,
                    "category": category,
                })
                print(f"    ✓ {pname} ({len(content)} 字)")

                # 提取详情页链接并爬取
                links = extract_all_links(r["html"])
                detail_links = [l for l in links
                                if self.classify_url(l) == category
                                and l not in self.crawled_urls]
                for dl in detail_links[:2]:
                    dr = await self._crawl(crawler, dl, wait_time=2)
                    if dr and dr.get("success"):
                        dc = clean_html_to_text(dr["html"])
                        if len(dc) > 80:
                            self.crawled_urls.add(dl)
                            self.results["source_urls"].append(dl)
                            crawled.append({
                                "url": dl,
                                "content": dc,
                                "category": category,
                            })
                            print(f"      详情: {dl[:50]}... ({len(dc)} 字)")
                    await asyncio.sleep(random.uniform(0.5, 1.5))

            if len(crawled) >= min_results:
                break

        return crawled

    # ---------- 官网识别评分器（优化方案3.3） ----------

    @staticmethod
    def _score_official_website(url: str, html_content: str, enterprise_name: str) -> float:
        """多维度官网置信度评分 (0-1, >=0.6视为官网)"""
        score = 0.0
        short_name = enterprise_name
        for suffix in ["股份有限公司", "有限公司", "有限责任公司"]:
            if short_name.endswith(suffix):
                short_name = short_name[:-len(suffix)]
                break

        # 维度1: 页面Title匹配（25%权重）
        title = extract_title(html_content) if _USE_COMMON else ""
        if not title:
            m = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.I | re.DOTALL)
            if m:
                title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if enterprise_name in title:
            score += 0.25
        elif short_name in title and len(short_name) >= 3:
            score += 0.20

        # 维度2: 页面内容匹配（30%权重）
        text = clean_html_to_text(html_content)
        if enterprise_name in text:
            density = text.count(enterprise_name) / max(len(text), 1) * 1000
            score += min(0.30, density * 0.03)
        elif short_name in text and len(short_name) >= 3:
            score += 0.15

        # 维度3: 页面结构匹配（15%权重）
        structure_keywords = ['关于我们', '产品中心', '联系我们', '公司简介', '新闻动态']
        structure_hits = sum(1 for kw in structure_keywords if kw in html_content)
        score += min(0.15, structure_hits * 0.03)

        # 维度4: 域名匹配（15%权重）
        domain = extract_domain(url).lower()
        name_keywords = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', short_name))
        name_keywords = {kw.lower() for kw in name_keywords if len(kw) >= 2}
        if any(nk in domain for nk in name_keywords):
            score += 0.15

        # 维度5: 反面信号扣分（15%权重）
        negative_signals = ['天眼查', '企查查', '百度百科', '微博', '知乎']
        if any(ns in title for ns in negative_signals):
            score -= 0.15

        return max(0.0, min(1.0, score))

    # ---------- 内容相关性校验（优化方案3.2） ----------

    @staticmethod
    def _check_content_relevance(enterprise_name: str, content: dict) -> float:
        """检查内容与目标企业的相关性 (0-1)"""
        if not enterprise_name:
            return 0.5

        short_name = enterprise_name
        for suffix in ["股份有限公司", "有限公司", "有限责任公司"]:
            if short_name.endswith(suffix):
                short_name = short_name[:-len(suffix)]
                break

        all_text = content.get("all_content", "")
        if not all_text:
            return 0.0

        full_count = all_text.count(enterprise_name)
        short_count = all_text.count(short_name) if len(short_name) >= 2 else 0

        # 核心关键词共现
        industry_cooccur = 0
        for kw in ["轴承", "滚子", "保持架", "密封", "热处理", "磨削"]:
            for sentence in all_text.split("。"):
                if (enterprise_name in sentence or short_name in sentence) and kw in sentence:
                    industry_cooccur += 1

        score = min(1.0, (full_count * 0.05 + short_count * 0.03 + industry_cooccur * 0.1))
        return round(max(score, 0.1), 2)

    # ---------- 阶段1: 官网发现与深度采集 ----------

    async def phase1_official_website(self, crawler: AsyncWebCrawler, name: str) -> List[Dict]:
        """阶段1: 发现并深度采集企业官网"""
        crawled = []
        short_name = name.replace("股份有限公司", "").replace("有限公司", "").replace("（", "").replace("）", "").strip()
        
        print(f"\n[阶段1] 官网发现与深度采集...")
        
        # 1.1 多关键词搜索定位官网
        all_links = set()
        keywords = [kw.format(name=name, short=short_name) for kw in OFFICIAL_WEBSITE_KEYWORDS[:3]]
        
        for i, keyword in enumerate(keywords):
            engine_name, engine_url = SEARCH_ENGINES[i % len(SEARCH_ENGINES)]
            search_url = engine_url.format(keyword=quote(keyword))
            print(f"  搜索: {engine_name} -> {keyword}")
            
            result = await self._crawl(crawler, search_url, wait_time=4, scroll=True)
            if result and result.get("success"):
                links = extract_search_result_links(result["html"], engine_name)
                all_links.update(links)
            
            await asyncio.sleep(random.uniform(1, 2))
        
        # 1.2 识别官网候选（优先选含企业名称关键字的域名）
        name_keywords = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', short_name))
        name_keywords = {kw.lower() for kw in name_keywords if len(kw) >= 2}
        
        official_candidates = []
        other_candidates = []
        
        for url in all_links:
            domain = extract_domain(url).lower()
            # 检查域名是否包含企业名称关键字
            domain_words = re.findall(r'[a-z0-9]+', domain)
            if any(nk in domain for nk in name_keywords) or \
               any(nk in ''.join(domain_words) for nk in name_keywords):
                official_candidates.append(url)
            else:
                other_candidates.append(url)
        
        # 优先爬官网候选，再补充其他
        crawl_targets = official_candidates[:5] + other_candidates[:3]
        
        print(f"  发现 {len(official_candidates)} 个官网候选, {len(other_candidates)} 个其他链接")
        
        # 1.3 爬取并验证官网
        for url in crawl_targets[:5]:
            if url in self.crawled_urls:
                continue
            
            print(f"  爬取: {url[:60]}...")
            result = await self._crawl(crawler, url, wait_time=3)
            
            if result and result.get("success"):
                content = clean_html_to_text(result["html"])
                # 验证是否为官网：内容包含企业名称
                if len(content) > 100 and (name in content or short_name in content):
                    self.crawled_urls.add(url)
                    self.official_website_url = url
                    self.results["source_urls"].append(url)
                    crawled.append({
                        "url": url,
                        "content": content,
                        "category": "official_website"
                    })
                    print(f"    ✓ 确认为官网 ({len(content)} 字)")
                    break  # 找到官网就停止
                else:
                    print(f"    ✗ 内容不匹配")
            
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # 1.4 官网站内深度爬取
        if self.official_website_url:
            deep = await self._deep_crawl_official_site(crawler, self.official_website_url, name)
            crawled.extend(deep)
        
        return crawled

    async def _deep_crawl_official_site(self, crawler: AsyncWebCrawler, base_url: str, name: str) -> List[Dict]:
        """官网站内深度爬取"""
        crawled = []
        domain = extract_domain(base_url)
        if not domain:
            return crawled
        
        print(f"\n  官网深度采集: {domain}")
        
        # 爬首页提取站内链接
        result = await self._crawl(crawler, base_url, wait_time=3)
        if not result or not result.get("success"):
            return crawled
        
        all_links = extract_all_links(result["html"])
        internal_links = [l for l in all_links if domain in l and l != base_url]
        
        # 按重要程度分类
        priority_links = []
        normal_links = []
        
        for link in internal_links:
            link_lower = link.lower()
            if any(kw in link_lower for kw in OFFICIAL_SITE_IMPORTANT_PATHS):
                priority_links.append(link)
            else:
                normal_links.append(link)
        
        # 去重
        seen = {base_url}
        deep_targets = priority_links[:6] + normal_links[:2]
        
        print(f"    站内链接: {len(internal_links)} 个，优先 {len(priority_links)} 个，爬取 {len(deep_targets)} 个")
        
        for url in deep_targets[:8]:
            if url in self.crawled_urls or url in seen:
                continue
            seen.add(url)
            
            result = await self._crawl(crawler, url, wait_time=1.5)
            if result and result.get("success"):
                content = clean_html_to_text(result["html"])
                if len(content) > 80:
                    self.crawled_urls.add(url)
                    self.results["source_urls"].append(url)
                    crawled.append({
                        "url": url,
                        "content": content,
                        "category": "official_website"
                    })
                    print(f"    -> {url[:50]}... ({len(content)} 字)")
            
            await asyncio.sleep(random.uniform(0.5, 1))
        
        return crawled

    # ---------- 阶段2: 工商信息采集 ----------

    async def phase2_business_info(self, crawler: AsyncWebCrawler, name: str) -> List[Dict]:
        """阶段2: 工商信息采集"""
        crawled = []
        encoded = quote(name)
        
        print(f"\n[阶段2] 工商信息采集...")
        
        # 2.1 直接平台采集（只取前3个高效平台）
        platform_tasks = [
            (pname, url_tpl.format(name=encoded))
            for pname, url_tpl in self.business_platforms[:3]
        ]
        
        for pname, url in platform_tasks:
            print(f"  平台: {pname}")
            result = await self._crawl(crawler, url, wait_time=3, scroll=True)
            
            if result and result.get("success"):
                # 平台页面提取链接
                links = extract_all_links(result["html"])
                # 筛选企业详情页链接
                detail_links = [l for l in links if self._is_enterprise_detail_page(l, name)]
                
                # 也提取当前页面内容
                content = clean_html_to_text(result["html"])
                if len(content) > 100 and (name in content or name[:4] in content):
                    self.crawled_urls.add(url)
                    self.results["source_urls"].append(url)
                    crawled.append({
                        "url": url,
                        "content": content,
                        "category": "business_info"
                    })
                    print(f"    ✓ 页面内容 ({len(content)} 字)")
                
                # 爬取详情页
                for detail_url in detail_links[:2]:
                    if detail_url in self.crawled_urls:
                        continue
                    print(f"    详情: {detail_url[:50]}...")
                    dr = await self._crawl(crawler, detail_url, wait_time=2)
                    if dr and dr.get("success"):
                        dc = clean_html_to_text(dr["html"])
                        if len(dc) > 100:
                            self.crawled_urls.add(detail_url)
                            self.results["source_urls"].append(detail_url)
                            crawled.append({
                                "url": detail_url,
                                "content": dc,
                                "category": "business_info"
                            })
                            print(f"      ✓ ({len(dc)} 字)")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
            else:
                print(f"    ✗ 失败")
            
            # 已获取足够工商数据则跳过后续平台
            if len(crawled) >= 2:
                print(f"  已获取足够工商数据，跳过剩余平台")
                break
            
            await asyncio.sleep(random.uniform(1.5, 3))
        
        # 2.2 搜索引擎补充（仅平台数据不足时执行）
        if len(crawled) < 2:
            short_name = name.replace("股份有限公司", "").replace("有限公司", "").strip()
            search_keywords = [kw.format(name=name) for kw in self.business_keywords[:2]]
            
            for i, keyword in enumerate(search_keywords):
                engine_name, engine_url = SEARCH_ENGINES[(i + 1) % len(SEARCH_ENGINES)]
                search_url = engine_url.format(keyword=quote(keyword))
                print(f"  搜索: {engine_name} -> {keyword}")
                
                result = await self._crawl(crawler, search_url, wait_time=3, scroll=True)
                if result and result.get("success"):
                    links = extract_search_result_links(result["html"], engine_name)
                    # 筛选工商相关链接
                    business_links = [l for l in links if self.classify_url(l) == 'business_info']
                    for link in business_links[:2]:
                        if link in self.crawled_urls:
                            continue
                        lr = await self._crawl(crawler, link, wait_time=2)
                        if lr and lr.get("success"):
                            lc = clean_html_to_text(lr["html"])
                            if len(lc) > 100:
                                self.crawled_urls.add(link)
                                self.results["source_urls"].append(link)
                                crawled.append({
                                    "url": link,
                                    "content": lc,
                                    "category": "business_info"
                                })
                                print(f"    ✓ {link[:50]}... ({len(lc)} 字)")
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                
                await asyncio.sleep(random.uniform(1.5, 2.5))
        else:
            print(f"  工商数据充足，跳过搜索引擎补充")
        
        return crawled

    def _is_enterprise_detail_page(self, url: str, name: str) -> bool:
        """判断是否为企业详情页链接"""
        url_lower = url.lower()
        detail_patterns = [
            'company', 'firm', 'enterprise', 'detail',
            '/c/', '/p/', '/com/', '/corp/',
        ]
        return any(p in url_lower for p in detail_patterns)

    # ---------- 阶段3: 招投标信息采集 ----------

    async def phase3_bidding_info(self, crawler: AsyncWebCrawler, name: str) -> List[Dict]:
        """阶段3: 招投标信息采集"""
        crawled = []
        encoded = quote(name)
        
        print(f"\n[阶段3] 招投标信息采集...")
        
        # 3.1 直接平台采集（只取前3个高效平台）
        platform_tasks = [
            (pname, url_tpl.format(name=encoded))
            for pname, url_tpl in self.bidding_platforms[:3]
        ]
        
        for pname, url in platform_tasks:
            print(f"  平台: {pname}")
            result = await self._crawl(crawler, url, wait_time=3, scroll=True)
            
            if result and result.get("success"):
                content = clean_html_to_text(result["html"])
                if len(content) > 80:
                    self.crawled_urls.add(url)
                    self.results["source_urls"].append(url)
                    crawled.append({
                        "url": url,
                        "content": content,
                        "category": "bidding_info"
                    })
                    print(f"    ✓ ({len(content)} 字)")
                    
                    # 提取结果中的详情链接
                    links = extract_all_links(result["html"])
                    bid_detail_links = [l for l in links if self.classify_url(l) == 'bidding_info' and l not in self.crawled_urls]
                    for dl in bid_detail_links[:2]:
                        dr = await self._crawl(crawler, dl, wait_time=2)
                        if dr and dr.get("success"):
                            dc = clean_html_to_text(dr["html"])
                            if len(dc) > 80:
                                self.crawled_urls.add(dl)
                                self.results["source_urls"].append(dl)
                                crawled.append({
                                    "url": dl,
                                    "content": dc,
                                    "category": "bidding_info"
                                })
                                print(f"    详情: {dl[:50]}... ({len(dc)} 字)")
                        await asyncio.sleep(random.uniform(0.5, 1.5))
            else:
                print(f"    ✗ 失败")
            
            # 已获取足够招投标数据则跳过后续平台
            if len(crawled) >= 2:
                print(f"  已获取足够招投标数据，跳过剩余平台")
                break
            
            await asyncio.sleep(random.uniform(1.5, 3))
        
        # 3.2 搜索引擎补充（仅平台数据不足时执行）
        if len(crawled) < 2:
            search_keywords = [kw.format(name=name) for kw in self.bidding_keywords[:2]]
            
            for i, keyword in enumerate(search_keywords):
                engine_name, engine_url = SEARCH_ENGINES[(i + 2) % len(SEARCH_ENGINES)]
                search_url = engine_url.format(keyword=quote(keyword))
                print(f"  搜索: {engine_name} -> {keyword}")
                
                result = await self._crawl(crawler, search_url, wait_time=3, scroll=True)
                if result and result.get("success"):
                    links = extract_search_result_links(result["html"], engine_name)
                    bid_links = [l for l in links if self.classify_url(l) == 'bidding_info']
                    for link in bid_links[:2]:
                        if link in self.crawled_urls:
                            continue
                        lr = await self._crawl(crawler, link, wait_time=2)
                        if lr and lr.get("success"):
                            lc = clean_html_to_text(lr["html"])
                            if len(lc) > 80:
                                self.crawled_urls.add(link)
                                self.results["source_urls"].append(link)
                                crawled.append({
                                    "url": link,
                                    "content": lc,
                                    "category": "bidding_info"
                                })
                                print(f"    ✓ {link[:50]}... ({len(lc)} 字)")
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                
                await asyncio.sleep(random.uniform(1.5, 2.5))
        else:
            print(f"  招投标数据充足，跳过搜索引擎补充")
        
        return crawled

    # ---------- 阶段4: 专利信息采集 ----------

    async def phase4_patent_info(self, crawler: AsyncWebCrawler, name: str) -> List[Dict]:
        """阶段4: 专利信息采集"""
        crawled = []
        encoded = quote(name)
        
        print(f"\n[阶段4] 专利信息采集...")
        
        # 4.1 直接平台采集（只取前3个高效平台）
        platform_tasks = [
            (pname, url_tpl.format(name=encoded))
            for pname, url_tpl in self.patent_platforms[:3]
        ]
        
        for pname, url in platform_tasks:
            print(f"  平台: {pname}")
            result = await self._crawl(crawler, url, wait_time=3, scroll=True)
            
            if result and result.get("success"):
                content = clean_html_to_text(result["html"])
                if len(content) > 80:
                    self.crawled_urls.add(url)
                    self.results["source_urls"].append(url)
                    crawled.append({
                        "url": url,
                        "content": content,
                        "category": "patent_info"
                    })
                    print(f"    ✓ ({len(content)} 字)")
                    
                    # 提取专利详情链接
                    links = extract_all_links(result["html"])
                    patent_detail_links = [l for l in links if self.classify_url(l) == 'patent_info' and l not in self.crawled_urls]
                    for dl in patent_detail_links[:2]:
                        dr = await self._crawl(crawler, dl, wait_time=2)
                        if dr and dr.get("success"):
                            dc = clean_html_to_text(dr["html"])
                            if len(dc) > 80:
                                self.crawled_urls.add(dl)
                                self.results["source_urls"].append(dl)
                                crawled.append({
                                    "url": dl,
                                    "content": dc,
                                    "category": "patent_info"
                                })
                                print(f"    详情: {dl[:50]}... ({len(dc)} 字)")
                        await asyncio.sleep(random.uniform(0.5, 1.5))
            else:
                print(f"    ✗ 失败")
            
            # 已获取足够专利数据则跳过后续平台
            if len(crawled) >= 2:
                print(f"  已获取足够专利数据，跳过剩余平台")
                break
            
            await asyncio.sleep(random.uniform(1.5, 3))
        
        # 4.2 搜索引擎补充（仅平台数据不足时执行）
        if len(crawled) < 2:
            search_keywords = [kw.format(name=name) for kw in self.patent_keywords[:2]]
            
            for i, keyword in enumerate(search_keywords):
                engine_name, engine_url = SEARCH_ENGINES[(i + 3) % len(SEARCH_ENGINES)]
                search_url = engine_url.format(keyword=quote(keyword))
                print(f"  搜索: {engine_name} -> {keyword}")
                
                result = await self._crawl(crawler, search_url, wait_time=3, scroll=True)
                if result and result.get("success"):
                    links = extract_search_result_links(result["html"], engine_name)
                    patent_links = [l for l in links if self.classify_url(l) == 'patent_info']
                    for link in patent_links[:2]:
                        if link in self.crawled_urls:
                            continue
                        lr = await self._crawl(crawler, link, wait_time=2)
                        if lr and lr.get("success"):
                            lc = clean_html_to_text(lr["html"])
                            if len(lc) > 80:
                                self.crawled_urls.add(link)
                                self.results["source_urls"].append(link)
                                crawled.append({
                                    "url": link,
                                    "content": lc,
                                    "category": "patent_info"
                                })
                                print(f"    ✓ {link[:50]}... ({len(lc)} 字)")
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                
                await asyncio.sleep(random.uniform(1.5, 2.5))
        else:
            print(f"  专利数据充足，跳过搜索引擎补充")
        
        return crawled

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
                page_timeout=30000,
                delay_before_return_html=wait_time,
            )
            if js_code:
                config = CrawlerRunConfig(
                    page_timeout=30000,
                    delay_before_return_html=wait_time,
                    js_code=js_code,
                )
            
            result = await crawler.arun(url=url, config=config)
            if result.success:
                return {"success": True, "html": result.html or "", "url": url}
            return None
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    def build_result(self, all_crawled: List[Dict]) -> Dict[str, Any]:
        """整理分类结果（仅四大核心分类）+ 内容相关性校验"""
        categorized = {
            "official_website": "",
            "business_info": "",
            "bidding_info": "",
            "patent_info": "",
            "all_content": ""
        }

        seen = set()
        for item in all_crawled:
            preview = item["content"][:80]
            if preview not in seen and len(item["content"]) > 80:
                seen.add(preview)
                cat = item.get("category", "official_website")
                src = item['url'][:80]
                categorized[cat] += f"【来源: {src}】\n{item['content'][:5000]}\n\n"

        # 合并
        categorized["all_content"] = "\n\n".join([v.strip() for v in categorized.values() if v.strip()])
        self.results["raw_content"] = categorized

        # 置信度
        filled = sum(1 for k, v in categorized.items() if v.strip() and k != "all_content")
        total_len = sum(len(v) for v in categorized.values() if v.strip())

        self.results["confidence"] = min(0.95, 0.2 + filled * 0.18 + min(total_len / 15000, 0.15))
        self.results["confidence"] = round(self.results["confidence"], 2)

        # 内容相关性校验
        relevance_score = self._check_content_relevance(
            self.results["enterprise_name"], categorized
        )
        if relevance_score < 0.3:
            self.results["crawl_status"] = "partial"
            self.results["note"] += f"；内容相关性较低({relevance_score:.0%})，可能采集到同名企业"
            self.results["confidence"] *= 0.6
        self.results["content_relevance"] = relevance_score

        if filled >= 4:
            self.results["crawl_status"] = "success"
            self.results["note"] = f"采集成功，覆盖全部 {filled} 个核心渠道，共 {len(self.results['source_urls'])} 个页面"
        elif filled >= 2:
            self.results["crawl_status"] = "partial"
            self.results["note"] = f"部分采集成功，覆盖 {filled} 个核心渠道，共 {len(self.results['source_urls'])} 个页面"
        elif filled >= 1:
            self.results["crawl_status"] = "partial"
            self.results["note"] = f"少量采集，仅覆盖 {filled} 个渠道"
        else:
            self.results["crawl_status"] = "failed"
            self.results["note"] = "未获取到有效内容"

        return self.results

    async def search_and_crawl(self, enterprise_name: str) -> Dict[str, Any]:
        """主流程：四阶段聚焦采集"""
        self.results["enterprise_name"] = enterprise_name
        
        browser_config = BrowserConfig(
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        all_crawled = []
        
        self._report_progress(2, "初始化", "启动浏览器，准备采集")
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # 阶段1: 官网发现与深度采集（串行，后续阶段依赖官网URL）
            self._report_progress(5, "官网发现", "多关键词搜索定位企业官网")
            official_data = await self.phase1_official_website(crawler, enterprise_name)
            all_crawled.extend(official_data)
            self._report_progress(20, "官网采集完成", f"获取 {len(official_data)} 个页面")
            
            # 阶段2/3/4: 工商/招投标/专利 并行采集（三者互不依赖）
            self._report_progress(25, "工商/招投标/专利并行采集", "三维度数据并行采集启动")
            results = await asyncio.gather(
                self.phase2_business_info(crawler, enterprise_name),
                self.phase3_bidding_info(crawler, enterprise_name),
                self.phase4_patent_info(crawler, enterprise_name),
                return_exceptions=True,  # 单个失败不阻断整体
            )
            # 逐个检查结果
            labels = ["工商", "招投标", "专利"]
            business_data, bidding_data, patent_data = [], [], []
            for label, data in zip(labels, results):
                if isinstance(data, Exception):
                    print(f"  [!] {label}采集异常: {data}")
                    self._report_progress(55, f"{label}采集", f"异常: {data}")
                else:
                    if label == "工商":
                        business_data = data
                    elif label == "招投标":
                        bidding_data = data
                    else:
                        patent_data = data
            all_crawled.extend(business_data)
            all_crawled.extend(bidding_data)
            all_crawled.extend(patent_data)
            self._report_progress(55, "并行采集完成",
                                 f"工商{len(business_data)}页 + 招投标{len(bidding_data)}页 + 专利{len(patent_data)}页")
        
        self._report_progress(58, "数据整合", "清洗分类并整合采集内容")
        return self.build_result(all_crawled)

    def save_to_file(self, data: Dict[str, Any], enterprise_name: str) -> str:
        output_dir = self.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', enterprise_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}_crawl.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath

    def run(self, name: str) -> str:
        result = asyncio.run(self.search_and_crawl(name))
        output_path = self.save_to_file(result, name)
        print(f"\n结果已保存到: {output_path}")
        return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="企业信息采集脚本")
    parser.add_argument("enterprise_name", help="企业名称")
    parser.add_argument("--output-dir", help="输出目录（默认为当前工作目录下的 output）", default=None)
    parser.add_argument("--source-config", help="数据源配置文件路径（由 bearing-data-source-filter 生成的 data_source_config.json）", default=None)
    args = parser.parse_args()
    
    name = args.enterprise_name
    
    print(f"{'='*60}")
    print(f"企业信息采集（聚焦版） - {name}")
    print(f"重点采集: 官网 / 工商 / 招投标 / 专利")
    if args.source_config:
        print(f"数据源配置: {args.source_config}")
    print(f"{'='*60}")
    
    crawler = EnterpriseDataCrawler(output_dir=args.output_dir, source_config=args.source_config)
    print(crawler.run(name))

