"""conftest.py - 将项目根目录和各模块加入 sys.path"""
import os
import sys

# 项目根目录
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 各子模块 scripts 目录
for module_dir in [
    "bearing-enterprise-data-crawl/scripts",
    "bearing-enterprise-data-clean/scripts",
    "bearing-enterprise-data-tag/scripts",
    "bearing-enterprise-data-pipeline/scripts",
    "bearing-data-source-filter/scripts",
]:
    p = os.path.join(project_root, module_dir)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
