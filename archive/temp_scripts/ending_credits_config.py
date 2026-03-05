"""
项目片尾配置管理模块

负责读取和管理项目级别的片尾检测配置
"""

import json
from pathlib import Path
from typing import Dict, Any


# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "data/hangzhou-leiming/project_config.json"


def load_project_config(project_name: str) -> Dict[str, Any]:
    """
    加载项目的片尾配置

    Args:
        project_name: 项目名称

    Returns:
        项目配置字典，如果项目不存在则返回默认配置
    """
    # 读取配置文件
    if not CONFIG_FILE.exists():
        # 配置文件不存在，返回默认配置
        return get_default_config()

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    # 获取项目配置
    projects = config_data.get('projects', {})
    project_config = projects.get(project_name)

    # 如果项目没有配置，返回默认配置
    if project_config is None:
        default_config = config_data.get('default_config', {})
        return {
            **default_config,
            'project_name': project_name,
            'notes': '使用默认配置'
        }

    return project_config


def get_default_config() -> Dict[str, Any]:
    """
    获取默认配置

    Returns:
        默认配置字典
    """
    return {
        "has_ending_credits": True,
        "auto_detect": True,
        "ending_type": "unknown",
        "verified": False,
        "notes": "默认配置：启用片尾检测"
    }


def should_detect_ending(project_name: str) -> bool:
    """
    判断项目是否需要检测片尾

    Args:
        project_name: 项目名称

    Returns:
        True 表示需要检测，False 表示跳过检测
    """
    config = load_project_config(project_name)
    return config.get("has_ending_credits", True)


def update_project_config(project_name: str, updates: Dict[str, Any]) -> None:
    """
    更新项目配置

    Args:
        project_name: 项目名称
        updates: 要更新的配置字段
    """
    # 读取现有配置
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    else:
        config_data = {
            "projects": {},
            "default_config": get_default_config(),
            "metadata": {
                "version": "1.0",
                "last_updated": "2026-03-04"
            }
        }

    # 更新项目配置
    if project_name not in config_data["projects"]:
        config_data["projects"][project_name] = {}

    config_data["projects"][project_name].update(updates)

    # 保存配置
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 项目配置已更新: {project_name}")


def list_all_projects() -> Dict[str, Dict[str, Any]]:
    """
    列出所有项目的配置

    Returns:
        所有项目配置字典
    """
    if not CONFIG_FILE.exists():
        return {}

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    return config_data.get('projects', {})


def get_project_summary() -> str:
    """
    获取项目配置摘要

    Returns:
        摘要字符串
    """
    projects = list_all_projects()

    total = len(projects)
    has_ending = sum(1 for p in projects.values() if p.get('has_ending_credits', False))
    no_ending = total - has_ending
    verified = sum(1 for p in projects.values() if p.get('verified', False))

    summary = f"""
项目配置摘要
{'=' * 60}
总项目数: {total}
需要检测片尾: {has_ending} 个
不需要检测片尾: {no_ending} 个
已人工验证: {verified} 个

{'=' * 60}
"""

    return summary


# 便捷函数
def is_project_configured(project_name: str) -> bool:
    """检查项目是否有配置"""
    if not CONFIG_FILE.exists():
        return False

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    return project_name in config_data.get('projects', {})


if __name__ == "__main__":
    # 测试代码
    print(get_project_summary())

    print("\n各项目配置:")
    for name, config in list_all_projects().items():
        status = "✅ 检测" if config.get('has_ending_credits') else "❌ 跳过"
        verified = "✅" if config.get('verified') else "❌"
        print(f"  {name}: {status} (验证:{verified})")
