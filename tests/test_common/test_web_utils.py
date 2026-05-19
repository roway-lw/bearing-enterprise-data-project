"""测试 common.web_utils"""
import pytest
from common.web_utils import (
    clean_html_to_text,
    extract_domain,
    is_valid_url,
    extract_all_links,
    extract_title,
)


class TestExtractDomain:
    def test_normal(self):
        assert extract_domain("https://www.example.com/page") == "example.com"

    def test_no_www(self):
        assert extract_domain("https://example.com/page") == "example.com"

    def test_subdomain(self):
        assert extract_domain("https://sub.example.com/page") == "sub.example.com"

    def test_invalid(self):
        assert extract_domain("") == ""


class TestIsValidUrl:
    def test_valid(self):
        assert is_valid_url("https://example.com/page")

    def test_blacklist_baidu(self):
        assert not is_valid_url("https://www.baidu.com/s?wd=test")

    def test_blacklist_zhihu(self):
        assert not is_valid_url("https://www.zhihu.com/question/123")

    def test_ftp_scheme(self):
        assert not is_valid_url("ftp://example.com/file")

    def test_empty(self):
        assert not is_valid_url("")


class TestCleanHtmlToText:
    def test_simple(self):
        html = "<p>Hello World</p>"
        result = clean_html_to_text(html, use_tag_lengths=False)
        assert "Hello World" in result

    def test_script_removal(self):
        html = "<script>alert('xss')</script><p>Content</p>"
        result = clean_html_to_text(html, use_tag_lengths=False)
        assert "alert" not in result
        assert "Content" in result

    def test_empty(self):
        assert clean_html_to_text("") == ""
        assert clean_html_to_text(None) == ""

    def test_tag_lengths_mode(self):
        html = "<p>Short paragraph with enough content to pass filter</p>"
        result = clean_html_to_text(html, use_tag_lengths=True)
        assert "Short paragraph" in result


class TestExtractTitle:
    def test_title_tag(self):
        html = "<html><head><title>Test Page</title></head></html>"
        assert extract_title(html) == "Test Page"

    def test_h1_fallback(self):
        html = "<html><body><h1>Heading</h1></body></html>"
        assert extract_title(html) == "Heading"

    def test_empty(self):
        assert extract_title("") == ""
