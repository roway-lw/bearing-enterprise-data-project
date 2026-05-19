"""
统一日志配置

提供统一的logging配置，保留进度条友好输出。
各模块可通过 setup_logger(name) 获取Logger实例。
"""

import logging
import os
import sys


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """创建统一配置的Logger

    Args:
        name: Logger名称（通常为模块名）
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）

    特性:
        - INFO及以上：输出到console（简洁格式）
        - DEBUG：输出到 .cache/debug.log
        - WARNING以上：带 [!] 标记
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler - 简洁格式
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("  %(message)s"))
    console.setLevel(logging.INFO)
    logger.addHandler(console)

    # File handler - 详细格式（仅DEBUG级别以上）
    try:
        cache_dir = os.path.join(os.getcwd(), ".cache")
        os.makedirs(cache_dir, exist_ok=True)
        fh = logging.FileHandler(
            os.path.join(cache_dir, "debug.log"), encoding="utf-8"
        )
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
    except Exception:
        pass  # 无法创建文件handler时不影响主流程

    return logger
