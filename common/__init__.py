"""
轴承行业企业数据项目 - 共享工具包

提供各子模块（模块0~4）共用的工具函数和基础类。
"""

from common.web_utils import (
    clean_html_to_text,
    extract_all_links,
    extract_domain,
    is_valid_url,
    extract_title,
)
from common.blacklist import BLACKLIST_DOMAINS, BLACKLIST_KEYWORDS, is_blacklisted
from common.output import resolve_output_dir
from common.logger import setup_logger
