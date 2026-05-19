"""LLM 客户端管理 — 可插拔式大模型集成

配置持久化到 llm_config.json，通过前端界面管理。
未启用时所有方法安全回退，不影响纯规则流程。
"""
import json
import os
from typing import Any, Optional

import backend.config as config


def load_llm_config() -> dict:
    """从 llm_config.json 加载配置，不存在则返回默认值"""
    defaults = {
        "enabled": config.LLM_ENABLED,
        "base_url": config.LLM_BASE_URL,
        "api_key": config.LLM_API_KEY,
        "model": config.LLM_MODEL,
    }
    cfg_file = config.LLM_CONFIG_FILE
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_llm_config(cfg: dict) -> dict:
    """保存配置到 llm_config.json，返回更新后的配置"""
    # 过滤只保留合法字段
    allowed = {"enabled", "base_url", "api_key", "model"}
    clean = {k: v for k, v in cfg.items() if k in allowed}
    clean.setdefault("enabled", False)
    clean.setdefault("base_url", "")
    clean.setdefault("api_key", "")
    clean.setdefault("model", "")

    cfg_file = config.LLM_CONFIG_FILE
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

    # 同步到运行时 config 模块属性
    config.LLM_ENABLED = clean["enabled"]
    config.LLM_BASE_URL = clean["base_url"]
    config.LLM_API_KEY = clean["api_key"]
    config.LLM_MODEL = clean["model"]

    return clean


def get_llm_client() -> Optional[Any]:
    """获取 LLM 客户端实例（OpenAI 兼容格式）

    未启用或配置不完整时返回 None。
    """
    cfg = load_llm_config()
    if not cfg.get("enabled"):
        return None
    if not cfg.get("base_url") or not cfg.get("api_key") or not cfg.get("model"):
        return None

    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
        )
        client._default_model = cfg["model"]
        return client
    except ImportError:
        print("[LLM] openai 库未安装，请运行: pip install openai")
        return None
    except Exception as e:
        print(f"[LLM] 客户端创建失败: {e}")
        return None


def llm_chat(
    client: Any,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2000,
    temperature: float = 0.0,
) -> Optional[str]:
    """通用 LLM 调用，返回文本或 None"""
    if client is None:
        return None
    try:
        model = getattr(client, "_default_model", "gpt-3.5-turbo")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content.strip()
        if content:
            return content
    except Exception as e:
        print(f"[LLM] 调用失败: {e}")
    return None


def llm_chat_json(
    client: Any,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4000,
) -> Optional[dict]:
    """调用 LLM 并解析 JSON 返回，失败返回 None"""
    text = llm_chat(client, system_prompt, user_prompt, max_tokens)
    if not text:
        return None
    # 尝试提取 JSON 块
    import re
    # 去掉 markdown 代码块包裹
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    print(f"[LLM] JSON 解析失败: {text[:200]}")
    return None


async def test_llm_connection(cfg: dict) -> dict:
    """测试 LLM 连接是否可用"""
    if not cfg.get("base_url") or not cfg.get("api_key") or not cfg.get("model"):
        return {"ok": False, "error": "配置不完整，请填写 base_url、api_key 和 model"}

    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
        )
        model = cfg["model"]
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "请回复：连接测试成功"},
            ],
            max_tokens=20,
            temperature=0,
        )
        reply = response.choices[0].message.content.strip()
        return {"ok": True, "reply": reply}
    except ImportError:
        return {"ok": False, "error": "openai 库未安装，请运行: pip install openai"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
