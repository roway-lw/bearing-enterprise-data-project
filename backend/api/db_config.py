"""数据库连接配置 API"""
import re
from fastapi import APIRouter, HTTPException
from backend.schemas.enterprise import DbConnectionTest, DbQueryNames, DbInitRequest
from backend.database.connection import init_db, close_db, is_initialized
import backend.config as config

router = APIRouter(prefix="/api/db", tags=["数据库配置"])

# 存储当前的动态数据库配置
_current_db_config = {}


def _validate_identifier(value: str, label: str) -> str:
    if not value or not re.match(r"^[\w\u4e00-\u9fa5]+$", value):
        raise HTTPException(400, f"{label}只能包含字母、数字、下划线或中文")
    return value


async def _connect(req: DbConnectionTest, database: str = None):
    import aiomysql
    kwargs = {
        "host": req.host,
        "port": req.port,
        "user": req.user,
        "password": req.password,
        "charset": "utf8mb4",
        "connect_timeout": 10,
        "autocommit": True,
    }
    if database:
        kwargs["db"] = database
    return await aiomysql.connect(**kwargs)


@router.post("/test-connection")
async def test_connection(req: DbConnectionTest):
    """测试 MySQL 连接；数据库不存在时自动创建并初始化系统表"""
    try:
        database = req.database or config.MYSQL_DATABASE
        _validate_identifier(database, "数据库名")

        # 先不指定 database 连接，避免数据库不存在导致测试失败
        conn = await _connect(req, None)
        async with conn.cursor() as cur:
            await cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.close()

        if is_initialized():
            await close_db()
        await init_db(
            host=req.host,
            port=req.port,
            user=req.user,
            password=req.password,
            database=database,
        )
        _current_db_config.update({**req.model_dump(), "database": database})

        conn = await _connect(req, database)
        async with conn.cursor() as cur:
            await cur.execute("SHOW TABLES")
            tables = [row[0] for row in await cur.fetchall()]
        conn.close()
        return {"connected": True, "tables": tables, "database": database, "message": "连接成功，数据库和系统表已自动初始化"}
    except Exception as e:
        return {"connected": False, "tables": [], "database": req.database, "message": str(e)}


@router.post("/init")
async def init_database(req: DbInitRequest):
    """初始化数据库连接并创建表"""
    try:
        database = req.database or config.MYSQL_DATABASE
        _validate_identifier(database, "数据库名")
        _validate_identifier(req.tag_table, "标签表名")
        _validate_identifier(req.fact_table, "事实表名")

        # 关闭旧连接
        if is_initialized():
            await close_db()
        await init_db(
            host=req.host, port=req.port,
            user=req.user, password=req.password,
            database=database,
        )
        _current_db_config.update({**req.model_dump(), "database": database})
        return {"message": "数据库初始化成功", "status": "ok"}
    except Exception as e:
        raise HTTPException(500, f"数据库初始化失败: {str(e)}")


@router.post("/tables")
async def list_tables(req: DbConnectionTest):
    """列出数据库表"""
    try:
        database = req.database or config.MYSQL_DATABASE
        _validate_identifier(database, "数据库名")
        conn = await _connect(req, database)
        async with conn.cursor() as cur:
            await cur.execute("SHOW TABLES")
            tables = [row[0] for row in await cur.fetchall()]
        conn.close()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(500, f"获取表失败: {str(e)}")


@router.post("/columns")
async def list_columns(req: DbQueryNames):
    """列出指定表字段"""
    if not is_initialized():
        raise HTTPException(400, "数据库未初始化")
    try:
        from backend.database.connection import async_session_factory
        from sqlalchemy import text

        table_name = _validate_identifier(req.table_name, "表名")
        async with async_session_factory() as session:
            result = await session.execute(text(f"SHOW COLUMNS FROM `{table_name}`"))
            columns = [row[0] for row in result.fetchall()]
        return {"columns": columns}
    except Exception as e:
        raise HTTPException(500, f"获取字段失败: {str(e)}")


@router.post("/query-names")
async def query_names(req: DbQueryNames):
    """从指定表获取企业名称列表"""
    if not is_initialized():
        raise HTTPException(400, "数据库未初始化")

    try:
        from backend.database.connection import async_session_factory
        from sqlalchemy import text

        table_name = _validate_identifier(req.table_name, "表名")
        name_column = _validate_identifier(req.name_column, "字段名")

        async with async_session_factory() as session:
            query = f"SELECT DISTINCT `{name_column}` FROM `{table_name}`"
            if req.where_clause:
                query += f" WHERE {req.where_clause}"
            if req.limit:
                query += f" LIMIT {req.limit}"

            result = await session.execute(text(query))
            names = [row[0] for row in result.fetchall() if row[0]]

        return {"names": names, "count": len(names)}
    except Exception as e:
        raise HTTPException(500, f"查询失败: {str(e)}")


@router.get("/config")
async def get_config():
    """获取当前数据库配置（脱敏）"""
    return {
        "configured": is_initialized(),
        "host": _current_db_config.get("host", config.MYSQL_HOST),
        "port": _current_db_config.get("port", config.MYSQL_PORT),
        "database": _current_db_config.get("database", config.MYSQL_DATABASE),
    }
