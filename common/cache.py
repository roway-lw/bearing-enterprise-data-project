"""
URL响应缓存

基于SQLite的轻量级URL响应缓存，支持TTL过期、自动清理、命中率统计。
"""

import asyncio
import hashlib
import json
import os
import sqlite3
import time
from typing import Any, Dict, Optional


class ResponseCache:
    """基于SQLite的URL响应缓存

    - 以 URL+参数 组合为key
    - 支持TTL过期（默认1小时）
    - 自动清理过期记录
    - 缓存命中率统计
    """

    def __init__(self, cache_dir: str = None, ttl: int = 3600):
        self.ttl = ttl
        cache_dir = cache_dir or os.path.join(os.getcwd(), ".cache")
        os.makedirs(cache_dir, exist_ok=True)
        self.db_path = os.path.join(cache_dir, "response_cache.db")
        self._hits = 0
        self._misses = 0
        self._expired = 0
        self._init_db()

    def _init_db(self):
        """建表"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS url_cache (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                result_json TEXT NOT NULL,
                fetched_at REAL NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fetched_at ON url_cache(fetched_at)")
        conn.commit()
        conn.close()

    def _make_key(self, url: str) -> str:
        """生成URL的hash key"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    async def get(self, url: str) -> Optional[Dict]:
        """查缓存，过期返回None"""
        key = self._make_key(url)
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT result_json, fetched_at FROM url_cache WHERE url_hash = ?",
                (key,)
            ).fetchone()
            if row:
                result_json, fetched_at = row
                if time.time() - fetched_at > self.ttl:
                    # 过期，删除
                    conn.execute("DELETE FROM url_cache WHERE url_hash = ?", (key,))
                    conn.commit()
                    self._expired += 1
                    return None
                self._hits += 1
                return json.loads(result_json)
            self._misses += 1
            return None
        finally:
            conn.close()

    async def set(self, url: str, result: Dict):
        """写入缓存"""
        key = self._make_key(url)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO url_cache (url_hash, url, result_json, fetched_at) VALUES (?, ?, ?, ?)",
                (key, url, json.dumps(result, ensure_ascii=False), time.time())
            )
            conn.commit()
        finally:
            conn.close()

    async def get_or_fetch(self, crawler, url: str, **crawl_kwargs) -> Optional[Dict]:
        """优先读缓存，未命中则爬取并缓存

        Args:
            crawler: 爬虫实例（需要有 _crawl 方法或 arun 方法）
            url: 目标URL
            **crawl_kwargs: 传给爬虫的额外参数
        """
        # 先查缓存
        cached = await self.get(url)
        if cached is not None:
            return cached

        # 爬取
        result = None
        if hasattr(crawler, '_crawl'):
            result = await crawler._crawl(crawler, url, **crawl_kwargs)
        elif hasattr(crawler, 'arun'):
            try:
                from crawl4ai import CrawlerRunConfig
                config = CrawlerRunConfig(
                    page_timeout=crawl_kwargs.get('page_timeout', 15000),
                    delay_before_return_html=crawl_kwargs.get('wait_time', 3),
                )
                r = await crawler.arun(url=url, config=config)
                if r.success:
                    result = {"success": True, "html": r.html or "", "url": url}
            except Exception:
                pass

        # 缓存结果
        if result and result.get("success"):
            await self.set(url, result)
        return result

    def cleanup(self):
        """清理过期缓存"""
        cutoff = time.time() - self.ttl
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM url_cache WHERE fetched_at < ?", (cutoff,))
        conn.commit()
        conn.close()

    def stats(self) -> dict:
        """返回命中/未命中/过期统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "expired": self._expired,
            "hit_rate": round(hit_rate, 2),
        }
