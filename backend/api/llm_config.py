"""LLM 大模型配置 API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from backend.services.llm_client import (
    load_llm_config,
    save_llm_config,
    test_llm_connection,
)

router = APIRouter(prefix="/api/llm", tags=["LLM 配置"])


class LlmConfigRequest(BaseModel):
    enabled: bool = False
    base_url: str = ""
    api_key: str = ""
    model: str = ""


class LlmTestRequest(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""


@router.get("/config")
async def get_llm_config():
    """获取 LLM 配置（api_key 脱敏）"""
    cfg = load_llm_config()
    # 脱敏 api_key
    safe_cfg = {
        "enabled": cfg.get("enabled", False),
        "base_url": cfg.get("base_url", ""),
        "api_key": _mask_key(cfg.get("api_key", "")),
        "model": cfg.get("model", ""),
        "is_configured": bool(cfg.get("base_url") and cfg.get("api_key") and cfg.get("model")),
    }
    return safe_cfg


@router.put("/config")
async def update_llm_config(req: LlmConfigRequest):
    """更新 LLM 配置"""
    data = {
        "enabled": req.enabled,
        "base_url": req.base_url,
        "model": req.model,
    }
    # 如果 api_key 是脱敏格式（***...），保留原值
    if req.api_key and not req.api_key.startswith("***"):
        data["api_key"] = req.api_key
    else:
        # 保留原有 api_key
        existing = load_llm_config()
        data["api_key"] = existing.get("api_key", "")

    saved = save_llm_config(data)
    return {
        "ok": True,
        "config": {
            "enabled": saved["enabled"],
            "base_url": saved["base_url"],
            "api_key": _mask_key(saved["api_key"]),
            "model": saved["model"],
        },
    }


@router.post("/test-connection")
async def test_llm(req: LlmTestRequest):
    """测试 LLM 连接"""
    # 如果传了脱敏 key，用已保存的
    test_cfg = {
        "base_url": req.base_url,
        "api_key": req.api_key,
        "model": req.model,
    }
    if req.api_key and req.api_key.startswith("***"):
        existing = load_llm_config()
        test_cfg["api_key"] = existing.get("api_key", "")

    result = await test_llm_connection(test_cfg)
    return result


def _mask_key(key: str) -> str:
    """API Key 脱敏"""
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    return key[:4] + "***" + key[-4:]
