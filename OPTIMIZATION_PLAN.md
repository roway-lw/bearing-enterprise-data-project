# 轴承企业数据项目优化方案

## 一、性能优化方案

### 1.1 共享工具模块抽取

**问题**：模块0和模块1有大量重复代码（HTML清洗、链接提取、搜索引擎配置、黑名单等），修改一处容易遗漏另一处。

**方案**：抽取 `common/` 共享工具包

```
bearing-enterprise-data-project/
├── common/
│   ├── __init__.py
│   ├── web_utils.py        # HTML清洗、链接提取、URL校验
│   ├── search_engines.py   # 搜索引擎配置与搜索结果提取
│   ├── blacklist.py        # 统一黑名单管理
│   ├── output.py           # 统一输出目录逻辑
│   └── cache.py            # URL缓存管理
└── bearing-xxx/            # 各子模块保持不变
```

核心接口设计：

```python
# common/web_utils.py
def clean_html_to_text(html: str, min_tag_len: dict = None) -> str: ...
def extract_all_links(html: str, base_url: str = "") -> List[str]: ...
def extract_domain(url: str) -> str: ...
def is_valid_url(url: str, blacklist: set = None) -> bool: ...

# common/search_engines.py
ENGINE_REGISTRY = {
    "百度": BaiduEngine(),
    "必应": BingEngine(),
    ...
}
async def search(engine: str, keyword: str, page: int) -> List[str]: ...

# common/output.py
def resolve_output_dir(explicit_dir: str = None) -> str:
    """统一三级优先级: 参数 > PROJECT_DIR > cwd/output"""

# common/cache.py
class ResponseCache:
    """基于文件的URL响应缓存，支持TTL"""
    def __init__(self, cache_dir: str, ttl: int = 3600): ...
    async def get_or_fetch(self, crawler, url: str, **kwargs) -> Optional[Dict]: ...
```

**改动范围**：模块0和模块1删除各自重复函数，改为 `from common.xxx import ...`。模块2/3/4的输出目录逻辑也统一。

---

### 1.2 URL响应缓存

**问题**：同一URL可能被多次爬取（如天眼查搜索页在模块0评价和模块1采集时重复访问），无缓存导致重复等待。

**方案**：基于SQLite的轻量级响应缓存

```python
# common/cache.py
class ResponseCache:
    """
    基于SQLite的URL响应缓存
    - 以 URL+参数 组合为key
    - 支持TTL过期（默认1小时）
    - 自动清理过期记录
    - 缓存命中率统计
    """
    def __init__(self, cache_dir: str = None, ttl: int = 3600):
        self.ttl = ttl
        cache_dir = cache_dir or os.path.join(os.getcwd(), ".cache")
        self.db_path = os.path.join(cache_dir, "response_cache.db")
        self._init_db()

    def _init_db(self):
        """建表: url, html, status, fetched_at, etag"""

    async def get(self, url: str) -> Optional[Dict]:
        """查缓存，过期返回None"""

    async def set(self, url: str, result: Dict):
        """写入缓存"""

    async def get_or_fetch(self, crawler, url: str, **crawl_kwargs) -> Optional[Dict]:
        """优先读缓存，未命中则爬取并缓存"""

    def stats(self) -> dict:
        """返回命中/未命中/过期统计"""
```

**预期效果**：对同一企业的重复查询（如调试、批量模式中跨模块共享），缓存命中率预计40-60%，整体耗时减少20-30%。

---

### 1.3 平台级并发爬取

**问题**：模块1中工商/招投标/专利各取前3个平台，但每个阶段内是串行爬取（平台1完成才爬平台2），浪费等待时间。

**方案**：使用 `asyncio.Semaphore` 控制并发数

```python
# 当前代码（串行）
for pname, url in platform_tasks:
    result = await self._crawl(crawler, url, ...)

# 改进后（并发，最多3个同时）
async def _crawl_platforms_concurrent(self, crawler, platform_tasks, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _crawl_one(pname, url):
        async with semaphore:
            result = await self._crawl(crawler, url, ...)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            return pname, result

    tasks = [_crawl_one(name, url) for name, url in platform_tasks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理结果，单个失败不影响其他
    success_results = []
    for r in results:
        if isinstance(r, Exception):
            print(f"  平台爬取异常: {r}")
            continue
        success_results.append(r)
    return success_results
```

**注意**：
- 需要配合缓存机制，避免并发请求同一域名被反爬
- `Semaphore` 数量建议3，平衡速度和礼貌访问
- `return_exceptions=True` 确保单平台失败不阻断

**预期效果**：每个采集阶段从串行3次（约9-15秒）降至并发（约3-5秒），整体单企业采集时间减少40%。

---

### 1.4 模块0增量评价与断点续跑

**问题**：full模式22个关键词×4搜索引擎+150个网站评价，全量执行约30-60分钟，中断后需从头开始。

**方案**：进度持久化 + 增量评价

```python
class DataSourceFilter:
    def __init__(self, ..., resume_from: str = None):
        # 新增：进度文件
        self.progress_file = os.path.join(self.output_dir, "filter_progress.json")
        # 新增：增量评价模式
        self.resume_from = resume_from  # 上次评价报告路径

    async def discover_sites(self, crawler):
        # 尝试加载上次进度
        if self._load_progress():
            print(f"从断点恢复，已发现 {len(self.discovered_sites)} 个网站")
            # 跳过已搜索的关键词
        # ... 正常搜索，每完成一个关键词保存进度
        self._save_progress()

    def _load_progress(self) -> bool:
        """从 progress_file 加载已发现的网站"""

    def _save_progress(self):
        """保存当前进度到 progress_file"""

    def _merge_existing_evaluation(self):
        """增量评价：加载上次评价结果，跳过已评价且未过期的网站"""
        if self.resume_from and os.path.exists(self.resume_from):
            old_report = json.load(open(self.resume_from))
            # 只评价新增网站 + 过期网站（超过7天）
            for site in old_report.get("all_sites", []):
                evaluated_time = site.get("evaluation_time", "")
                if not self._is_expired(evaluated_time, days=7):
                    self.evaluated_sites.append(site)
                    self.crawled_domains.add(site["domain"])
```

**新增CLI参数**：
```bash
# 从断点恢复
python scripts/filter_data_sources.py --mode full --resume

# 基于上次评价结果增量更新
python scripts/filter_data_sources.py --mode full --resume-from output/data_source_evaluation_20260510.json
```

---

### 1.5 性能优化汇总

| 优化项 | 改动范围 | 预期效果 |
|--------|---------|---------|
| 共享工具模块 | 模块0+1重构 | 减少~500行重复代码，维护成本降50% |
| URL响应缓存 | 新增common/cache.py，模块0+1+4集成 | 重复URL零等待，批量模式减少20-30%耗时 |
| 平台并发爬取 | 模块1三个phase内 | 单企业采集减少40%耗时 |
| 断点续跑 | 模块0新增进度持久化 | full模式可中断恢复，不浪费已完成工作 |
| 增量评价 | 模块0新增评价合并 | 日常更新只评价变化部分，从30分钟降至5分钟 |

---

## 二、工程规范方案

### 2.1 依赖管理

**问题**：无 requirements.txt，依赖散落在各SKILL.md中，运行时才发现缺失。

**方案**：项目根目录统一管理

```
bearing-enterprise-data-project/
├── requirements.txt          # 生产依赖
├── requirements-dev.txt      # 开发/测试依赖
└── common/                   # 共享模块（模块1-4都依赖）
```

`requirements.txt`：
```
crawl4ai>=0.3.0
openpyxl>=3.1.0
```

`requirements-dev.txt`：
```
-r requirements.txt
pytest>=7.0
pytest-asyncio>=0.21
```

---

### 2.2 日志系统替换

**问题**：全部用 `print()` 输出，无法控制级别、无法重定向、生产环境不可管理。

**方案**：统一使用 `logging` 模块，保留进度条友好输出

```python
# common/logger.py
import logging
import sys

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """统一日志配置

    - INFO及以上：输出到console（带进度格式）
    - DEBUG：输出到 .cache/debug.log
    - WARNING以上：带颜色标记
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Console handler - 保留进度友好的简洁格式
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("  %(message)s"))
    logger.addHandler(console)

    # File handler - 详细格式，用于调试
    fh = logging.FileHandler(".cache/debug.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    return logger
```

**迁移策略**：渐进式替换，先在新增代码和 `common/` 中使用 `logging`，各模块的 `print()` 保持不变，后续逐步替换。模块4的 `ProgressReporter` 特殊处理——保持 `print` 用于里程碑输出，日志记录用 `logging.debug`。

---

### 2.3 单元测试

**问题**：零测试覆盖，正则提取逻辑脆弱，改一处容易全盘崩溃。

**方案**：优先覆盖核心提取逻辑和工具函数

```
tests/
├── test_common/
│   ├── test_web_utils.py      # HTML清洗、链接提取
│   └── test_cache.py          # 缓存逻辑
├── test_clean/
│   ├── test_extract_name.py       # 企业名提取
│   ├── test_extract_address.py    # 地址提取
│   ├── test_extract_capital.py    # 注册资本提取
│   ├── test_extract_patent.py     # 专利提取
│   ├── test_extract_products.py   # 产品提取
│   ├── test_preprocess.py         # 文本预处理
│   └── test_confidence.py         # 置信度计算
├── test_tag/
│   ├── test_product_tags.py       # 产品标签
│   ├── test_service_tags.py       # 服务标签
│   └── test_ability_tags.py       # 能力标签
└── test_pipeline/
    ├── test_tag_extractor.py      # 扁平化标签
    └── test_fact_extractor.py     # 事实关系提取
```

**示例测试**：

```python
# tests/test_clean/test_extract_capital.py
import pytest
from bearing_enterprise_data_clean.scripts.clean_enterprise_data import BearingDataCleaner

@pytest.fixture
def cleaner():
    c = BearingDataCleaner()
    c.raw_text = ""
    c.filtered_text = ""
    return c

class TestExtractCapital:
    def test_万元(self, cleaner):
        cleaner.filtered_text = "注册资本：5000万元人民币"
        result = cleaner.extract_registered_capital()
        assert result == "5000万元人民币"

    def test_亿元(self, cleaner):
        cleaner.filtered_text = "注册资本：1.5亿元人民币"
        result = cleaner.extract_registered_capital()
        assert result == "1.5亿元人民币"

    def test_带逗号(self, cleaner):
        cleaner.filtered_text = "注册资本: 10,000万元"
        result = cleaner.extract_registered_capital()
        assert result == "10000万元人民币"

    def test_缺失(self, cleaner):
        cleaner.filtered_text = "这是一段不包含资本信息的文本"
        result = cleaner.extract_registered_capital()
        assert result == ""
        assert "registered_capital" in cleaner.uncertain_fields
```

**优先级**：模块2（清洗）> 模块3（标签）> common > 模块4

---

### 2.4 类型标注规范化

**问题**：部分函数有 type hints，部分没有，不一致。

**方案**：对公共接口和核心类添加完整标注

```python
# 改前
def extract_search_result_links(html, engine):
    links = []

# 改后
def extract_search_result_links(html: str, engine: str) -> List[str]:
    links: List[str] = []
```

**范围**：优先处理 `common/` 和各模块的公共类（`DataSourceFilter`、`EnterpriseDataCrawler`、`BearingDataCleaner`、`EnterpriseTagger`），内部方法标注参数类型即可。

---

### 2.5 错误处理增强

**问题**：
- 模块1 `asyncio.gather` 未用 `return_exceptions=True`，一个平台失败全部中断
- 模块2正则匹配失败无详细诊断信息
- 模块4异常只记录 message，缺少 traceback

**方案**：

```python
# 1. asyncio.gather 容错
business_data, bidding_data, patent_data = await asyncio.gather(
    self.phase2_business_info(crawler, name),
    self.phase3_bidding_info(crawler, name),
    self.phase4_patent_info(crawler, name),
    return_exceptions=True,  # 关键修改
)
# 逐个检查结果
for label, data in [("工商", business_data), ("招投标", bidding_data), ("专利", patent_data)]:
    if isinstance(data, Exception):
        logger.warning(f"{label}采集异常: {data}")
        # 降级处理，不阻断整体

# 2. 清洗失败诊断
def extract_registered_capital(self) -> str:
    ...
    if not result:
        self.uncertain_fields.append("registered_capital")
        self._diagnostic_info["registered_capital"] = {
            "reason": "正则未匹配",
            "text_sample": self._get_search_text()[:200],
            "tried_patterns": [p.pattern for p in patterns],
        }
    return result

# 3. Pipeline异常增强
except Exception as e:
    import traceback
    error_info = f"采集异常: {str(e)}"
    self._log("采集", f"采集异常: {str(e)}\n{traceback.format_exc()}", "error")
```

---

### 2.6 工程规范汇总

| 规范项 | 改动范围 | 优先级 |
|--------|---------|--------|
| requirements.txt | 项目根目录新增 | P0 |
| logging替换 | common/新增，各模块渐进替换 | P1 |
| 单元测试 | tests/新增，优先模块2 | P1 |
| 类型标注 | 公共接口优先 | P2 |
| 错误处理增强 | 模块1+2+4 | P1 |

---

## 三、数据质量提升方案

### 3.1 正则 + LLM 混合提取策略

**问题**：模块2完全依赖正则匹配，对于格式不规范的网页（动态渲染、非标准排版），关键字段提取失败率高。

**方案**：正则优先、LLM兜底的两级提取

```python
# common/extractor.py
class HybridExtractor:
    """正则优先 + LLM兜底的混合提取器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client  # 可选，不传则纯正则模式

    def extract_field(self, field_name: str, text: str,
                      regex_patterns: List[str],
                      llm_prompt: str = None,
                      validator=None) -> str:
        """
        两级提取：
        1. 正则匹配 → 如果命中且通过validator，直接返回
        2. LLM提取 → 如果正则未命中且llm_client可用，调用LLM
        """
        # Level 1: 正则
        for pattern in regex_patterns:
            m = re.search(pattern, text)
            if m:
                value = m.group(1).strip() if m.lastindex else m.group(0).strip()
                if validator and not validator(value):
                    continue
                return value, "regex"

        # Level 2: LLM
        if self.llm_client and llm_prompt:
            value = self._llm_extract(field_name, text, llm_prompt)
            if value:
                return value, "llm"

        return "", "miss"
```

**集成方式**：在 `BearingDataCleaner` 中可选注入

```python
class BearingDataCleaner:
    def __init__(self, ..., extractor: HybridExtractor = None):
        self.extractor = extractor or HybridExtractor()  # 默认纯正则

    def extract_registered_capital(self) -> str:
        result, method = self.extractor.extract_field(
            field_name="registered_capital",
            text=self._get_search_text(),
            regex_patterns=[...],  # 现有正则
            llm_prompt="从以下文本中提取该企业的注册资本，格式为'XXX万元人民币'或'XXX亿元人民币'。仅返回金额，不要解释。",
            validator=lambda v: bool(re.search(r'\d+', v)),
        )
        if method == "llm":
            self.uncertain_fields.append("registered_capital")
            self._diagnostic_info["registered_capital"] = {"method": "llm_fallback"}
        self.result["registered_capital"] = result
        return result
```

**LLM选择建议**：
- 开发/测试：使用便宜模型（如 DeepSeek-V3、Qwen-Plus）
- 生产：根据字段重要度选择，核心字段用强模型，非核心字段用便宜模型
- 成本控制：每个企业约需2-5次LLM调用（仅正则未命中的字段），按DeepSeek-V3价格约0.01元/企业

---

### 3.2 采集内容与企业相关性校验

**问题**：当前置信度只看"有效分类数"和"内容长度"，不检查内容是否真的属于目标企业。可能爬到同名/近似名企业的信息。

**方案**：在 `build_result` 阶段增加相关性校验

```python
class EnterpriseDataCrawler:
    def build_result(self, all_crawled: List[Dict]) -> Dict[str, Any]:
        # ... 现有逻辑 ...

        # 新增：内容相关性校验
        relevance_score = self._check_content_relevance(
            self.results["enterprise_name"],
            categorized
        )

        # 相关性过低时降级
        if relevance_score < 0.3:
            self.results["crawl_status"] = "partial"
            self.results["note"] += f"；内容相关性较低({relevance_score:.0%})，可能采集到同名企业"
            self.results["confidence"] *= 0.6  # 大幅降低置信度

        self.results["content_relevance"] = relevance_score
        return self.results

    def _check_content_relevance(self, enterprise_name: str, content: dict) -> float:
        """检查内容与目标企业的相关性"""
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

        # 策略1: 企业全称出现次数
        full_count = all_text.count(enterprise_name)
        # 策略2: 企业简称出现次数
        short_count = all_text.count(short_name) if len(short_name) >= 2 else 0
        # 策略3: 核心关键词共现（企业名+行业关键词在同一句话中）
        industry_cooccur = 0
        for kw in ["轴承", "滚子", "保持架", "密封", "热处理", "磨削"]:
            for sentence in all_text.split("。"):
                if (enterprise_name in sentence or short_name in sentence) and kw in sentence:
                    industry_cooccur += 1

        # 综合评分
        score = min(1.0, (full_count * 0.05 + short_count * 0.03 + industry_cooccur * 0.1))
        return round(max(score, 0.1), 2)
```

---

### 3.3 官网识别策略增强

**问题**：当前通过"域名包含企业名称关键字"识别官网，对中文企业名效果差（域名多为拼音/英文缩写）。

**方案**：多维度官网置信度评分

```python
class OfficialWebsiteScorer:
    """官网识别评分器"""

    @staticmethod
    def score(url: str, html_content: str, enterprise_name: str) -> float:
        """综合评分 0-1，>=0.6 视为官网"""
        score = 0.0
        short_name = _extract_short_name(enterprise_name)

        # 维度1: 域名匹配（15%权重）
        domain = extract_domain(url)
        # 域名中包含企业名拼音
        pinyin_name = _to_pinyin(short_name)
        if pinyin_name and pinyin_name in domain:
            score += 0.15
        # 域名中包含英文关键字
        en_keywords = _extract_english_keywords(enterprise_name)
        if any(ek in domain for ek in en_keywords):
            score += 0.10

        # 维度2: 页面Title匹配（25%权重）
        title = extract_title(html_content)
        if enterprise_name in title:
            score += 0.25
        elif short_name in title:
            score += 0.20

        # 维度3: 页面内容匹配（30%权重）—— 最关键
        text = clean_html_to_text(html_content)
        if enterprise_name in text:
            # 企业名在页面中出现的密度
            density = text.count(enterprise_name) / max(len(text), 1) * 1000
            score += min(0.30, density * 0.03)
        elif short_name in text and len(short_name) >= 3:
            score += 0.15

        # 维度4: 页面结构匹配（15%权重）
        # "关于我们"/"产品中心"等板块暗示是企业官网
        structure_keywords = ['关于我们', '产品中心', '联系我们', '公司简介', '新闻动态']
        structure_hits = sum(1 for kw in structure_keywords if kw in html_content)
        score += min(0.15, structure_hits * 0.03)

        # 维度5: 反面信号扣分（15%权重）
        negative_signals = ['天眼查', '企查查', '百度百科', '微博', '知乎']
        if any(ns in title for ns in negative_signals):
            score -= 0.15

        return max(0.0, min(1.0, score))

    @staticmethod
    def _to_pinyin(text: str) -> str:
        """中文转拼音（首字母缩写）"""
        try:
            from pypinyin import lazy_pinyin
            return ''.join(lazy_pinyin(text))
        except ImportError:
            return ""
```

---

### 3.4 语义去重

**问题**：模块2的句子级去重基于完全匹配，对语义相同但表述不同的重复内容无效（如"公司成立于2015年"和"企业2015年成立"）。

**方案**：SimHash 语义去重

```python
# common/dedup.py
import hashlib

class SimHashDeduplicator:
    """基于 SimHash 的语义去重"""

    def __init__(self, threshold: int = 3, hash_bits: int = 64):
        self.threshold = threshold  # 海明距离阈值，越小越严格
        self.hash_bits = hash_bits
        self.hashes: List[int] = []

    def _simhash(self, text: str) -> int:
        """计算文本的SimHash值"""
        # 分词（简单按字符/标点分割）
        tokens = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{2,}', text)
        if not tokens:
            return 0

        v = [0] * self.hash_bits
        for token in tokens:
            token_hash = int(hashlib.md5(token.encode()).hexdigest(), 16)
            for i in range(self.hash_bits):
                if token_hash & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1

        fingerprint = 0
        for i in range(self.hash_bits):
            if v[i] >= 0:
                fingerprint |= (1 << i)
        return fingerprint

    def _hamming_distance(self, h1: int, h2: int) -> int:
        return bin(h1 ^ h2).count('1')

    def is_duplicate(self, text: str) -> bool:
        """检查文本是否与已有内容重复"""
        h = self._simhash(text)
        for existing in self.hashes:
            if self._hamming_distance(h, existing) <= self.threshold:
                return True
        self.hashes.append(h)
        return False

    def deduplicate_sentences(self, sentences: List[str]) -> List[str]:
        """对句子列表去重"""
        self.hashes = []
        result = []
        for s in sentences:
            s = s.strip()
            if s and not self.is_duplicate(s):
                result.append(s)
        return result
```

**集成**：替换 `BearingDataCleaner.preprocess_text()` 中的简单 `seen` 集合去重

---

### 3.5 数据质量汇总

| 提升项 | 改动范围 | 预期效果 |
|--------|---------|---------|
| 正则+LLM混合提取 | 模块2新增HybridExtractor | 关键字段提取成功率从~70%提升至~90% |
| 内容相关性校验 | 模块1新增相关性检查 | 避免同名企业误采，误采率降至<5% |
| 官网识别增强 | 模块1新增评分器 | 官网识别准确率从~60%提升至~85% |
| 语义去重 | 模块2集成SimHash | 去重召回率提升30%，冗余内容减少 |
