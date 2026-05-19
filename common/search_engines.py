"""
搜索引擎配置与搜索结果提取

统一管理4大搜索引擎的URL模板和结果页面解析逻辑。
"""

import re
from typing import Dict, List, Tuple
from urllib.parse import quote

from common.web_utils import extract_all_links, is_valid_url


# ========== 搜索引擎配置 ==========

# 模块0用的带分页模板
SEARCH_ENGINES_PAGINATED: List[Tuple[str, str]] = [
    ("百度", "https://www.baidu.com/s?wd={keyword}&pn={page}0"),
    ("必应", "https://cn.bing.com/search?q={keyword}&first={page}1"),
    ("搜狗", "https://www.sogou.com/web?query={keyword}&page={page}"),
    ("360搜索", "https://www.so.com/s?q={keyword}&pn={page}"),
]

# 模块1用的简单模板（无分页参数）
SEARCH_ENGINES_SIMPLE: List[Tuple[str, str]] = [
    ("百度", "https://www.baidu.com/s?wd={keyword}"),
    ("必应", "https://cn.bing.com/search?q={keyword}"),
    ("搜狗", "https://www.sogou.com/web?query={keyword}"),
    ("360搜索", "https://www.so.com/s?q={keyword}"),
]


# ========== 搜索引擎名称注册 ==========

ENGINE_NAMES: Dict[int, str] = {
    0: "百度",
    1: "必应",
    2: "搜狗",
    3: "360搜索",
}


def get_engine_name(index: int) -> str:
    """根据索引获取引擎名称"""
    return ENGINE_NAMES.get(index % len(ENGINE_NAMES), "百度")


def build_search_url(engine_name: str, keyword: str, page: int = 0,
                     use_pagination: bool = False) -> str:
    """构建搜索URL

    Args:
        engine_name: 引擎名称
        keyword: 搜索关键词（原始中文，函数内部编码）
        page: 页码（从0开始）
        use_pagination: 是否使用分页模板
    """
    encoded_kw = quote(keyword)
    engines = SEARCH_ENGINES_PAGINATED if use_pagination else SEARCH_ENGINES_SIMPLE

    for name, template in engines:
        if name == engine_name:
            if use_pagination:
                return template.format(keyword=encoded_kw, page=page)
            else:
                return template.format(keyword=encoded_kw)

    # 默认百度
    if use_pagination:
        return SEARCH_ENGINES_PAGINATED[0][1].format(keyword=encoded_kw, page=page)
    return SEARCH_ENGINES_SIMPLE[0][1].format(keyword=encoded_kw)


def extract_search_result_links(html: str, engine: str) -> List[str]:
    """从搜索结果页提取链接

    Args:
        html: 搜索结果页HTML
        engine: 搜索引擎名称
    """
    links = []

    # 各引擎专用提取模式
    engine_patterns = {
        "百度": [
            r'href="(https?://www\.baidu\.com/link\?url=[^"]+)"',
            r'data-url="(https?://[^"]+)"',
            r'href="(https?://[^"]+)"[^>]*class="[^"]*c-showurl[^"]*"',
        ],
        "必应": [
            r'<a[^>]+href="(https?://[^"]+)"[^>]*class="[^"]*b_algo[^"]*"',
            r'href="(https?://[^"]+)"[^>]*data-h="ID=SERP[^"]*"',
        ],
        "搜狗": [
            r'href="(https?://[^"]+)"[^>]*class="[^"]*vr-title[^"]*"',
        ],
        "360搜索": [
            r'href="(https?://[^"]+)"[^>]*class="[^"]*res-title[^"]*"',
        ],
    }

    patterns = engine_patterns.get(engine, [r'href="(https?://[^"]+)"'])

    for pattern in patterns:
        links.extend(re.findall(pattern, html, re.I | re.DOTALL))

    # cite标签提取
    for cu in re.findall(r'<cite[^>]*>(.*?)</cite>', html, re.DOTALL | re.I):
        clean = re.sub(r'<[^>]+>', '', cu).strip()
        if re.match(r'https?://', clean):
            links.append(clean)

    # 回退：提取不足3个则提取所有链接
    if len(links) < 3:
        all_links = extract_all_links(html)
        links.extend(all_links)

    seen = set()
    result = []
    for link in links:
        clean = link.split('?')[0].split('#')[0].strip()
        if clean and clean not in seen and is_valid_url(clean):
            seen.add(clean)
            result.append(clean)
    return result[:30]
