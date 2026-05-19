"""FastAPI 应用入口"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import backend.config as config

# 确保项目根目录在 sys.path
if config.PROJECT_ROOT not in sys.path:
    sys.path.insert(0, config.PROJECT_ROOT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：尝试使用默认配置初始化数据库；密码为空也允许本地 MySQL 免密连接
    try:
        from backend.database.connection import init_db
        await init_db()
        print(f"[DB] 数据库已连接: {config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE}")
    except Exception as e:
        print(f"[DB] 数据库连接失败（可稍后通过前端配置）: {e}")

    yield

    # 关闭时：清理资源
    from backend.database.connection import close_db
    await close_db()
    print("[Server] 服务已停止")


app = FastAPI(
    title="轴承企业数据平台",
    description="企业数据采集→清洗→标签→关系 全流程可视化操作平台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from backend.api.pipeline import router as pipeline_router
from backend.api.enterprises import router as enterprises_router
from backend.api.db_config import router as db_config_router
from backend.api.llm_config import router as llm_config_router
from backend.api.ws import router as ws_router

app.include_router(pipeline_router)
app.include_router(enterprises_router)
app.include_router(db_config_router)
app.include_router(llm_config_router)
app.include_router(ws_router)

# 静态文件（前端构建后的产物）
frontend_dist = os.path.join(config.PROJECT_ROOT, "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )
