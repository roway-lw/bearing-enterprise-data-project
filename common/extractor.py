"""
混合提取器（正则 + LLM 兜底）

正则优先、LLM兜底的两级字段提取策略。
未配置LLM时退化为纯正则模式，不影响现有功能。
"""

import re
from typing import Any, Callable, List, Optional, Tuple


class HybridExtractor:
    """正则优先 + LLM兜底的混合提取器

    使用方式:
        # 纯正则模式（默认，无需LLM）
        extractor = HybridExtractor()

        # LLM兜底模式
        extractor = HybridExtractor(llm_client=my_client)

        result, method = extractor.extract_field(
            field_name="registered_capital",
            text="注册资本5000万元",
            regex_patterns=[r'注册资本\\s*[:：]?\\s*([\\d,.]+)\\s*万'],
        )
    """

    def __init__(self, llm_client: Any = None):
        """
        Args:
            llm_client: 可选的LLM客户端，需有 chat/completions 接口
                        不传则纯正则模式，完全向后兼容
        """
        self.llm_client = llm_client

    def extract_field(
        self,
        field_name: str,
        text: str,
        regex_patterns: List[str],
        llm_prompt: str = None,
        validator: Callable[[str], bool] = None,
    ) -> Tuple[str, str]:
        """两级提取

        Args:
            field_name: 字段名（用于LLM prompt和日志）
            text: 待提取文本
            regex_patterns: 正则模式列表
            llm_prompt: LLM提取提示词（可选）
            validator: 值验证函数（可选）

        Returns:
            (value, method) - value为提取结果，method为 "regex"/"llm"/"miss"
        """
        # Level 1: 正则匹配
        for pattern in regex_patterns:
            try:
                m = re.search(pattern, text)
                if m:
                    value = m.group(1).strip() if m.lastindex else m.group(0).strip()
                    if validator and not validator(value):
                        continue
                    return value, "regex"
            except Exception:
                continue

        # Level 2: LLM兜底
        if self.llm_client and llm_prompt:
            value = self._llm_extract(field_name, text, llm_prompt)
            if value:
                return value, "llm"

        return "", "miss"

    def _llm_extract(self, field_name: str, text: str, prompt_template: str) -> str:
        """调用LLM提取字段值

        子类可覆写此方法以适配不同的LLM客户端。
        """
        if not self.llm_client:
            return ""

        try:
            # 通用LLM调用接口（适配OpenAI兼容格式）
            if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                # OpenAI兼容接口
                prompt = prompt_template.replace("{text}", text[:2000])
                response = self.llm_client.chat.completions.create(
                    model=getattr(self.llm_client, '_default_model', 'gpt-3.5-turbo'),
                    messages=[
                        {"role": "system", "content": "你是一个精确的信息提取助手，只返回提取结果，不要解释。"},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=100,
                    temperature=0,
                )
                return response.choices[0].message.content.strip()
        except Exception:
            pass

        return ""
