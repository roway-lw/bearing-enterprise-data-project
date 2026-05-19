#!/usr/bin/env python3
"""
从种子列表生成默认数据源配置文件 data_source_config.json
功能：
  1. 解析 references/bearing_industry_sites.md 中的网站列表
  2. 为每个网站推断 data_types、搜索模板等元数据
  3. 输出标准化的 data_source_config.json
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding='utf-8')

# 分类到 data_types 的映射
CATEGORY_DATA_TYPES: Dict[str, List[str]] = {
    "工商查询平台": ["business_info", "commercial_relation"],
    "招投标平台": ["bidding_info", "commercial_relation"],
    "专利与知识产权平台": ["patent_info"],
    "B2B/轴承交易平台": ["business_info", "commercial_relation"],
    "行业媒体与资讯平台": ["commercial_relation"],
    "产业研究与数据库平台": ["commercial_relation"],
    "上市公司信息平台": ["business_info", "commercial_relation"],
    "企业名录/黄页类平台": ["business_info"],
    "地方公共资源交易平台（重点省市）": ["bidding_info", "commercial_relation"],
    "地方公共资源交易平台": ["bidding_info", "commercial_relation"],
    "国家级与地方轴承行业协会": ["commercial_relation"],
    "细分领域专业平台": ["business_info", "commercial_relation"],
    "新兴企业数据服务平台": ["commercial_relation", "business_info"],
    "行业展会与活动平台": ["commercial_relation"],
    "招聘平台（轴承行业板块）": ["commercial_relation"],
    "招聘平台": ["commercial_relation"],
    "投融资与企业征信平台": ["commercial_relation", "business_info"],
    "诉讼与仲裁平台": ["commercial_relation"],
    "海关进出口数据平台": ["commercial_relation"],
    "学术与标准平台": ["commercial_relation"],
    "行业研报与供应链分析平台": ["commercial_relation"],
}

# 已知平台的搜索 URL 模板
SEARCH_URL_TEMPLATES: Dict[str, str] = {
    "天眼查": "https://www.tianyancha.com/search?key={name}",
    "企查查": "https://www.qcc.com/web/search?key={name}",
    "爱企查": "https://aiqicha.baidu.com/s?wd={name}",
    "启信宝": "https://www.qixin.com/search?key={name}",
    "国家企业信用信息公示系统": "https://www.gsxt.gov.cn/index.html",
    "中国政府采购网": "http://search.ccgp.gov.cn/bxsearch?searchtype=1&bidSort=0&pinMu=0&bidType=1&dbselect=bidx&kw={name}",
    "全国公共资源交易平台": "https://deal.ggzy.gov.cn/ds/deal/dealList.jsp?search={name}",
    "中国招标投标公共服务平台": "http://www.cebpubservice.com/search?keyword={name}",
    "采招网": "https://search.bidcenter.com.cn/search?keywords={name}",
    "中国采购与招标网": "https://www.chinabidding.cn/search/searchzbgg?keyword={name}",
    "中国国际招标网": "https://www.chinabidding.com.cn/search?keyword={name}",
    "国家知识产权局": "https://pss-system.cponline.cnipa.gov.cn/conventionalSearch?searchType=patent&keyword={name}",
    "中国商标网": "https://wcjs.sbj.cnipa.gov.cn/?word={name}",
    "专利之星": "https://www.cprs.patentstar.com/search?kw={name}",
    "soopat专利检索": "https://www.soopat.com/Home/Result?SearchWord={name}",
    "专利公布公告网": "https://patentimage.cnipa.gov.cn/advancedSearch",
    "中国轴承网": "https://www.zcw168.com/search?keyword={name}",
    "中华轴承网": "https://www.zhoucheng.cn/search?keyword={name}",
    "中国制造网": "https://www.made-in-china.com/search?keyword={name}",
    "慧聪网": "https://www.hc360.com/search?keyword={name}",
    "顺企网": "https://www.11467.com/search?keyword={name}",
    "巨潮资讯网": "http://www.cninfo.com.cn/new/information/topSearch/query?keyWord={name}",
}

# 搜索关键词模板（按 data_type）
SEARCH_KEYWORDS_BY_TYPE: Dict[str, List[str]] = {
    "business_info": [
        "{name} 工商信息",
        "{name} 注册资本",
        "{name} 法人代表",
        "{name} 经营范围",
        "{name} 股东信息",
    ],
    "bidding_info": [
        "{name} 招标",
        "{name} 中标",
        "{name} 采购",
        "{name} 竞标",
    ],
    "patent_info": [
        "{name} 专利",
        "{name} 发明专利",
        "{name} 实用新型",
        "{name} 外观设计",
        "{name} 知识产权",
    ],
    "commercial_relation": [
        "{name} 供应链",
        "{name} 客户",
        "{name} 供应商",
        "{name} 股东",
        "{name} 投资",
        "{name} 合作",
    ],
}


def parse_markdown_tables(filepath: str) -> List[Tuple[str, List[Dict[str, str]]]]:
    """
    解析 markdown 文件中的表格
    返回: [(分类标题, [{序号, 平台名称, 网址, 说明}]), ...]
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    results: List[Tuple[str, List[Dict[str, str]]]] = []

    # 按二级标题分割
    sections = re.split(r'\n##\s+', content)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # 提取标题（第一行）
        lines = section.split('\n')
        title = lines[0].strip()

        # 跳过维护说明等非数据章节
        if not title or '维护说明' in title or '说明' in title and len(title) < 8:
            continue

        # 查找表格
        table_lines = []
        in_table = False
        for line in lines:
            if line.strip().startswith('|'):
                in_table = True
                table_lines.append(line)
            elif in_table and line.strip() == '':
                in_table = False
            elif in_table:
                in_table = False

        if len(table_lines) < 3:
            continue

        # 解析表头
        header_line = table_lines[0]
        headers = [h.strip().lower() for h in header_line.split('|') if h.strip()]
        # 标准化表头
        header_map = {}
        for i, h in enumerate(headers):
            if '序号' in h or '编号' in h:
                header_map['seq'] = i
            elif '平台' in h or '名称' in h:
                header_map['name'] = i
            elif '网址' in h or 'url' in h or '链接' in h:
                header_map['url'] = i
            elif '说明' in h or '描述' in h or '备注' in h:
                header_map['desc'] = i

        if 'name' not in header_map or 'url' not in header_map:
            continue

        # 跳过表头分隔行（包含---的行）
        data_lines = [l for l in table_lines[1:] if not re.match(r'^\|\s*[-:]+\s*\|', l)]

        entries = []
        for line in data_lines:
            cols = [c.strip() for c in line.split('|') if c.strip() != '']
            if len(cols) < max(header_map.values()) + 1:
                continue

            name_idx = header_map['name']
            url_idx = header_map['url']

            name = cols[name_idx] if name_idx < len(cols) else ''
            url = cols[url_idx] if url_idx < len(cols) else ''
            desc = cols[header_map.get('desc', -1)] if 'desc' in header_map and header_map['desc'] < len(cols) else ''

            # 清洗 URL（去除 markdown 链接格式）
            url_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', url)
            if url_match:
                url = url_match.group(2)
            url = url.strip()

            # 过滤无效 URL
            if not url or url == '-' or not url.startswith('http'):
                continue

            if name:
                entries.append({
                    'name': name,
                    'url': url,
                    'description': desc,
                })

        if entries:
            results.append((title, entries))

    return results


def infer_data_types(category: str) -> List[str]:
    """根据分类推断数据类型"""
    for key, types in CATEGORY_DATA_TYPES.items():
        if key in category or category in key:
            return list(types)
    # 默认
    if '招标' in category or '投标' in category or '采购' in category:
        return ["bidding_info", "commercial_relation"]
    if '专利' in category or '商标' in category or '知识产权' in category:
        return ["patent_info"]
    if '工商' in category or '企业' in category or '名录' in category or '黄页' in category:
        return ["business_info", "commercial_relation"]
    return ["commercial_relation"]


def get_search_url_template(name: str, base_url: str) -> Optional[str]:
    """获取已知平台的搜索模板"""
    if name in SEARCH_URL_TEMPLATES:
        return SEARCH_URL_TEMPLATES[name]
    # 尝试子串匹配
    for known_name, template in SEARCH_URL_TEMPLATES.items():
        if known_name in name or name in known_name:
            return template
    return None


def get_search_keywords(data_types: List[str]) -> List[str]:
    """根据数据类型获取搜索关键词模板"""
    keywords = []
    seen = set()
    for dt in data_types:
        for kw in SEARCH_KEYWORDS_BY_TYPE.get(dt, []):
            if kw not in seen:
                seen.add(kw)
                keywords.append(kw)
    return keywords


def generate_source_id(name: str) -> str:
    """生成 source_id"""
    # 移除特殊字符，保留中文、英文、数字
    sid = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', name)
    sid = sid.lower()
    # 限制长度
    if len(sid) > 30:
        sid = sid[:30]
    return sid or "source"


def generate_config(seed_markdown_path: str, output_dir: Optional[str] = None) -> str:
    """生成默认配置文件"""
    sections = parse_markdown_tables(seed_markdown_path)

    sources: List[Dict[str, Any]] = []
    seen_ids: set = set()

    for category, entries in sections:
        data_types = infer_data_types(category)
        keywords = get_search_keywords(data_types)

        for entry in entries:
            name = entry['name']
            base_url = entry['url']
            desc = entry['description']

            source_id = generate_source_id(name)
            # 去重 id
            original_id = source_id
            counter = 1
            while source_id in seen_ids:
                source_id = f"{original_id}_{counter}"
                counter += 1
            seen_ids.add(source_id)

            # 提取域名作为 base_url
            # 如果 URL 已经是域名形式，直接使用
            search_template = get_search_url_template(name, base_url)

            source = {
                "id": source_id,
                "name": name,
                "category": category.replace("## ", "").strip(),
                "base_url": base_url,
                "search_url_template": search_template,
                "search_keywords_template": keywords,
                "data_types": data_types,
                "priority": 1,
                "enabled": True,
                "authority_score": None,
                "crawl_friendly_score": None,
                "overall_score": None,
                "notes": desc,
            }
            sources.append(source)

    config = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now().isoformat(),
        "generated_by": "bearing-data-source-filter/generate_default_config.py",
        "industry": "轴承",
        "description": "轴承行业企业信息数据源配置文件，基于种子列表生成，供 bearing-enterprise-data-crawl 消费",
        "update_policy": {
            "seed_list_source": "references/bearing_industry_sites.md",
            "evaluation_trigger": "manual_or_scheduled",
            "auto_promote_threshold": 70,
            "max_concurrent_sources": 20,
        },
        "sources": sources,
    }

    # 确定输出目录
    if output_dir:
        out_dir = output_dir
    elif os.environ.get("PROJECT_DIR"):
        out_dir = os.path.join(os.environ.get("PROJECT_DIR"), "output")
    else:
        out_dir = os.path.join(os.getcwd(), "output")

    os.makedirs(out_dir, exist_ok=True)
    output_path = os.path.join(out_dir, "data_source_config.json")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="从种子列表生成默认数据源配置")
    parser.add_argument(
        "--seed-file",
        default=None,
        help="种子列表 markdown 文件路径（默认：../references/bearing_industry_sites.md）",
    )
    parser.add_argument("--output-dir", default=None, help="输出目录")
    args = parser.parse_args()

    # 默认种子文件路径
    if args.seed_file:
        seed_path = args.seed_file
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        seed_path = os.path.join(script_dir, "..", "references", "bearing_industry_sites.md")
        seed_path = os.path.normpath(seed_path)

    if not os.path.exists(seed_path):
        print(f"错误：找不到种子列表文件 {seed_path}")
        sys.exit(1)

    print(f"解析种子列表: {seed_path}")
    sections = parse_markdown_tables(seed_path)
    total = sum(len(entries) for _, entries in sections)
    print(f"共发现 {len(sections)} 个分类，{total} 个网站")

    output_path = generate_config(seed_path, args.output_dir)
    print(f"\n配置文件已生成: {output_path}")
    print(f"包含 {total} 个数据源")


if __name__ == "__main__":
    main()

