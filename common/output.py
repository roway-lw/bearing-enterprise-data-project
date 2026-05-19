"""
统一输出目录逻辑

三级优先级: 显式参数 > PROJECT_DIR 环境变量 > 当前工作目录/output
"""

import os


def resolve_output_dir(explicit_dir: str = None) -> str:
    """解析输出目录

    Args:
        explicit_dir: 显式指定的输出目录

    Returns:
        最终的输出目录绝对路径
    """
    if explicit_dir:
        return explicit_dir
    if os.environ.get("PROJECT_DIR"):
        return os.path.join(os.environ.get("PROJECT_DIR"), "output")
    return os.path.join(os.getcwd(), "output")
