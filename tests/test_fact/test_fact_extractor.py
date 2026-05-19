"""测试 common.fact_extractor 事实数据提取"""
import os
import sys
import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from common.fact_extractor import (
    BiddingRecordParser,
    WebsiteRecordParser,
    FactDataExtractor,
)


class TestBiddingRecordParser:
    @pytest.fixture
    def parser(self):
        return BiddingRecordParser()

    def test_简单中标句子(self, parser):
        segment = {
            "text": "2024年3月洛阳LYC轴承有限公司中标金风科技股份有限公司风电主轴轴承采购项目，金额3,200万元",
            "source_url": "http://search.ccgp.gov.cn/xxx",
            "source_platform": "中国政府采购网",
        }
        records = parser.parse("洛阳LYC轴承有限公司", segment, {})
        assert len(records) == 1
        r = records[0]
        assert r["record_type"] == "bidding"
        assert r["amount"] == "3200"
        assert r["amount_unit"] == "万元"
        assert r["bid_type"] == "中标"
        # counterparty应包含金风
        assert "金风" in r["counterparty"]
        assert r["role"] == "中标方"

    def test_多句子招投标(self, parser):
        text = ("2024年3月中标XX公司轴承采购项目，金额500万元。"
                "2024年5月中标YY公司滚子采购项目，金额800万元。")
        segment = {"text": text, "source_url": "", "source_platform": ""}
        records = parser.parse("测试公司", segment, {})
        assert len(records) == 2

    def test_无关键词不提取(self, parser):
        segment = {
            "text": "公司主营深沟球轴承，产品质量优秀",
            "source_url": "",
            "source_platform": "",
        }
        records = parser.parse("测试公司", segment, {})
        assert len(records) == 0

    def test_金额提取_亿元(self, parser):
        segment = {
            "text": "2024年中标重大项目，金额1.5亿元",
            "source_url": "",
            "source_platform": "",
        }
        records = parser.parse("测试公司", segment, {})
        assert len(records) == 1
        assert records[0]["amount"] == "1.5"
        assert records[0]["amount_unit"] == "亿元"

    def test_日期提取(self, parser):
        segment = {
            "text": "2024年3月15日中标XX项目，金额100万元",
            "source_url": "",
            "source_platform": "",
        }
        records = parser.parse("测试公司", segment, {})
        assert len(records) == 1
        assert records[0]["bid_date"] == "2024-03-15"


class TestWebsiteRecordParser:
    @pytest.fixture
    def parser(self):
        return WebsiteRecordParser()

    def test_客户关系提取(self, parser):
        segment = {
            "text": "公司长期为一汽解放提供配套轴承产品，同时与中车合作供应铁路轴承。",
            "source_url": "https://www.example.com/partners",
            "source_platform": "企业官网",
        }
        structured = {"core_products": "深沟球轴承", "cooperative_enterprise": ""}
        records = parser.parse("测试轴承公司", segment, structured)
        # 应提取到客户关系
        customer_records = [r for r in records if r["record_type"] == "customer"]
        assert len(customer_records) >= 1

    def test_投资项目提取(self, parser):
        segment = {
            "text": "2023年新增精密轴承生产线项目，总投资1.5亿元",
            "source_url": "https://www.example.com/news",
            "source_platform": "企业官网",
        }
        records = parser.parse("测试公司", segment, {})
        invest_records = [r for r in records if r["record_type"] == "investment"]
        assert len(invest_records) >= 1
        assert invest_records[0]["amount"] == "1.5"
        assert invest_records[0]["amount_unit"] == "亿元"

    def test_合作关系提取(self, parser):
        segment = {
            "text": "与洛阳轴承研究所有限公司联合开展高铁轴承技术攻关合作",
            "source_url": "https://www.example.com/about",
            "source_platform": "企业官网",
        }
        records = parser.parse("测试公司", segment, {})
        partner_records = [r for r in records if r["record_type"] == "partnership"]
        assert len(partner_records) >= 1


class TestFactDataExtractor:
    @pytest.fixture
    def extractor(self):
        return FactDataExtractor(output_dir=None)

    def test_完整提取流程(self, extractor):
        raw_crawl_data = {
            "raw_content": {
                "official_website": (
                    "【来源: www.example.com】\n"
                    "公司长期为一汽提供配套轴承。\n"
                    "2023年新增产线，投资5000万元。\n"
                ),
                "bidding_info": (
                    "【来源: ccgp.gov.cn】\n"
                    "2024年3月中标XX风电设备厂轴承采购项目，金额3,200万元。\n"
                ),
                "business_info": "",
                "patent_info": "",
            }
        }
        structured_data = {
            "core_products": "深沟球轴承",
            "cooperative_enterprise": "",
        }

        result = extractor.extract("测试轴承公司", raw_crawl_data, structured_data)
        assert "records" in result
        assert "summary" in result
        assert result["summary"]["total_records"] > 0

    def test_空数据(self, extractor):
        result = extractor.extract("测试公司", {"raw_content": {}}, {})
        assert result["summary"]["total_records"] == 0
        assert result["records"] == []

    def test_去重(self, extractor):
        raw_crawl_data = {
            "raw_content": {
                "bidding_info": (
                    "2024年3月中标XX公司轴承采购项目，金额3,200万元。\n"
                    "2024年3月中标XX公司轴承采购项目，金额3,200万元。\n"
                ),
                "official_website": "",
                "business_info": "",
                "patent_info": "",
            }
        }
        result = extractor.extract("测试公司", raw_crawl_data, {})
        # 重复的记录应被去重
        bidding_records = [r for r in result["records"] if r["record_type"] == "bidding"]
        assert len(bidding_records) <= 1
