"""
SimHash语义去重

用于模块2文本预处理阶段的句子级语义去重，替换简单的seen集合。
"""

import hashlib
import re
from typing import List


class SimHashDeduplicator:
    """基于SimHash的语义去重

    相比完全匹配去重，SimHash能识别表述不同但语义相似的重复内容，
    例如"公司成立于2015年"和"企业2015年成立"。
    """

    def __init__(self, threshold: int = 3, hash_bits: int = 64):
        """
        Args:
            threshold: 海明距离阈值，越小越严格（默认3）
            hash_bits: hash位数（默认64）
        """
        self.threshold = threshold
        self.hash_bits = hash_bits
        self.hashes: List[int] = []

    def _simhash(self, text: str) -> int:
        """计算文本的SimHash值"""
        # 分词（中文按2-4字组合，英文按单词）
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
        """计算海明距离"""
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
        """对句子列表去重

        Args:
            sentences: 待去重的句子列表

        Returns:
            去重后的句子列表
        """
        self.hashes = []
        result = []
        for s in sentences:
            s = s.strip()
            if s and not self.is_duplicate(s):
                result.append(s)
        return result

    def reset(self):
        """重置去重状态"""
        self.hashes = []
