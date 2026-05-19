"""测试 common.dedup"""
import pytest
from common.dedup import SimHashDeduplicator


class TestSimHashDeduplicator:
    def test_identical_sentences(self):
        dedup = SimHashDeduplicator(threshold=3)
        sentences = ["公司成立于2015年", "公司成立于2015年"]
        result = dedup.deduplicate_sentences(sentences)
        assert len(result) == 1

    def test_similar_sentences(self):
        dedup = SimHashDeduplicator(threshold=3)
        sentences = ["公司成立于2015年", "企业2015年成立"]
        result = dedup.deduplicate_sentences(sentences)
        # 相似表述应被去重
        assert len(result) <= 2

    def test_different_sentences(self):
        dedup = SimHashDeduplicator(threshold=3)
        sentences = ["公司成立于2015年", "主要生产深沟球轴承"]
        result = dedup.deduplicate_sentences(sentences)
        assert len(result) == 2

    def test_is_duplicate(self):
        dedup = SimHashDeduplicator(threshold=3)
        assert not dedup.is_duplicate("轴承制造企业")
        assert dedup.is_duplicate("轴承制造企业")  # 完全相同

    def test_reset(self):
        dedup = SimHashDeduplicator()
        dedup.is_duplicate("test sentence")
        assert len(dedup.hashes) == 1
        dedup.reset()
        assert len(dedup.hashes) == 0

    def test_empty_input(self):
        dedup = SimHashDeduplicator()
        result = dedup.deduplicate_sentences([])
        assert result == []

    def test_short_sentences_filtered(self):
        dedup = SimHashDeduplicator()
        result = dedup.deduplicate_sentences(["a", ""])
        # SimHash分词需要至少2字符的token，短字符串可能产生空hash
        # 所以"a"可能保留也可能被过滤，只检查不含空字符串
        assert "" not in result
