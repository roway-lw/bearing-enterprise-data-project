"""后端配置管理"""
import os

# 项目根目录（指向 bearing-enterprise-data-project）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# FastAPI 服务配置
HOST = os.getenv("API_HOST", "0.0.0.0")
PORT = int(os.getenv("API_PORT", "8000"))

# MySQL 默认配置（可通过环境变量覆盖）
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "meritcloud")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "BigData.2018v6")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "dataprocess")

# 输出目录
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(PROJECT_ROOT, "output"))

# LLM 大模型配置（可通过前端界面修改并持久化到 llm_config.json）
LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_CONFIG_FILE = os.path.join(PROJECT_ROOT, "llm_config.json")

# CORS 允许的前端地址
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
