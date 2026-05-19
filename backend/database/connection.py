"""数据库连接池管理"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import backend.config as config


engine = None
async_session_factory = None


class Base(DeclarativeBase):
    pass


async def init_db(
    host: str = None, port: int = None, user: str = None,
    password: str = None, database: str = None,
    create_database: bool = True,
):
    """初始化数据库连接池；数据库不存在时自动创建"""
    global engine, async_session_factory

    # 先清理旧连接
    if engine:
        try:
            await engine.dispose()
        except Exception:
            pass
    engine = None
    async_session_factory = None

    _host = host or config.MYSQL_HOST
    _port = port or config.MYSQL_PORT
    _user = user or config.MYSQL_USER
    _password = password if password is not None else config.MYSQL_PASSWORD
    _database = database or config.MYSQL_DATABASE

    if create_database:
        bootstrap_url = f"mysql+aiomysql://{_user}:{_password}@{_host}:{_port}/mysql?charset=utf8mb4"
        bootstrap_engine = create_async_engine(bootstrap_url, pool_recycle=3600)
        try:
            async with bootstrap_engine.begin() as conn:
                await conn.exec_driver_sql(
                    f"CREATE DATABASE IF NOT EXISTS `{_database}` "
                    "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        finally:
            await bootstrap_engine.dispose()

    url = f"mysql+aiomysql://{_user}:{_password}@{_host}:{_port}/{_database}?charset=utf8mb4"
    engine = create_async_engine(url, pool_size=10, max_overflow=20, pool_recycle=3600)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 创建表（如果不存在）
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        # 建表失败时回滚 engine 和 session_factory
        try:
            await engine.dispose()
        except Exception:
            pass
        engine = None
        async_session_factory = None
        raise


async def get_session() -> AsyncSession:
    """获取数据库会话"""
    if async_session_factory is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")
    async with async_session_factory() as session:
        yield session


async def close_db():
    """关闭数据库连接池"""
    global engine
    if engine:
        await engine.dispose()
        engine = None


async def create_tables_for_models(models: list[type[Base]]):
    """为动态表模型创建数据表"""
    if engine is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")
    async with engine.begin() as conn:
        for model in models:
            await conn.run_sync(model.__table__.create, checkfirst=True)


def is_initialized() -> bool:
    return engine is not None
