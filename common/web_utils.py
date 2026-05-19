"""
Web工具函数

提供HTML清洗、链接提取、域名提取、URL校验等通用功能。
合并自 filter_data_sources.py 和 crawl_enterprise.py 中的重复函数。
"""

import re
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse


def extract_domain(url: str) -> str:
    """提取域名，去掉 www. 前缀"""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def is_valid_url(url: str, blacklist: Set[str] = None, check_path: bool = False) -> bool:
    """检查URL是否有效

    Args:
        url: 待检查URL
        blacklist: 自定义黑名单域名集合（None则使用默认）
        check_path: 是否检查路径中的黑名单关键词
    """
    from common.blacklist import is_blacklisted
    return not is_blacklisted(url, extra_domains=blacklist, check_path=check_path)


def clean_html_to_text(html: str, use_tag_lengths: bool = True) -> str:
    """将HTML清洗为纯文本

    Args:
        html: HTML源码
        use_tag_lengths: 使用模块1的按标签最小长度过滤策略（更精确但更慢）
    """
    if not html:
        return ""

    # 移除script/style等标签
    for tag in ['script', 'style', 'noscript', 'nav', 'footer', 'header',
                'aside', 'iframe', 'form', 'button', 'svg', 'img']:
        html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.I)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    if not use_tag_lengths:
        # 简单模式（模块0用）：直接去标签
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    # 精确模式（模块1用）：按标签类型+最小长度过滤
    parts = []
    tag_min_lengths = [
        ('p', 10), ('h1', 3), ('h2', 3), ('h3', 3),
        ('h4', 3), ('h5', 3), ('li', 6), ('td', 6),
        ('span', 15), ('div', 30), ('article', 15),
        ('section', 15), ('blockquote', 8),
        ('dt', 3), ('dd', 5), ('th', 3), ('tr', 5),
    ]
    for tag, min_len in tag_min_lengths:
        texts = re.findall(f'<{tag}[^>]*>(.*?)</{tag}>', html, re.DOTALL | re.I)
        for t in texts:
            clean = re.sub(r'<[^>]+>', '', t).strip()
            if len(clean) > min_len and not re.match(r'^[\d\s\.,;:!?\-+/()]+$', clean):
                parts.append(clean)

    content = ' '.join(parts)
    return re.sub(r'\s+', ' ', content).strip()


def extract_all_links(html: str, base_url: str = "") -> List[str]:
    """从HTML中提取所有链接

    Args:
        html: HTML源码
        base_url: 基础URL（用于解析相对路径）
    """
    links = []

    # href属性提取
    for m in re.findall(r'href=["\'](https?://[^"\']+)["\']', html, re.I):
        links.append(m)

    # data-url/data-href属性
    for m in re.findall(r'data-(?:url|href)=["\'](https?://[^"\']+)["\']', html, re.I):
        links.append(m)

    # 相对路径
    if base_url:
        for m in re.findall(r'href=["\'](/[^"\']*)["\']', html, re.I):
            links.append(urljoin(base_url, m))

    # cite标签
    for cu in re.findall(r'<cite[^>]*>(.*?)</cite>', html, re.DOTALL | re.I):
        clean = re.sub(r'<[^>]+>', '', cu).strip()
        if re.match(r'https?://', clean):
            links.append(clean)

    seen = set()
    result = []
    for link in links:
        clean = link.split('#')[0].strip()
        if clean and clean not in seen and len(clean) > 10:
            if is_valid_url(clean):
                seen.add(clean)
                result.append(clean)
    return result


def extract_title(html: str) -> str:
    """从HTML中提取页面标题"""
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.DOTALL)
    if m:
        title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        return title
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.DOTALL)
    if m:
        return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    return ""
