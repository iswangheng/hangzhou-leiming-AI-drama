"""
Excel读取模块 - 读取项目标记数据
"""
import pandas as pd
import os
from typing import List
from pathlib import Path

from .data_models import Marking
from .config import ProjectConfig


def load_project_markings(config: ProjectConfig) -> List[Marking]:
    """读取项目的标记数据

    Args:
        config: 项目配置

    Returns:
        标记数据列表

    Raises:
        FileNotFoundError: Excel文件不存在
        ValueError: Excel格式错误
    """
    excel_path = config.get_absolute_excel_path()

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel文件不存在: {excel_path}")

    try:
        # 读取 Excel
        df = pd.read_excel(excel_path)
    except Exception as e:
        raise ValueError(f"读取Excel文件失败: {e}")

    # 验证必要的列是否存在
    required_columns = ['集数', '时间点', '标记类型']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Excel缺少必要的列: {missing_columns}")

    # 中文数字到阿拉伯数字的映射（支持11-99）
    chinese_numerals = {
        '十': 10,
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9
    }

    def parse_chinese_episode(episode_str: str) -> int:
        """
        解析集数字符串，支持阿拉伯数字和中文数字

        Args:
            episode_str: 如 "第1集", "第十集", "第12集", "第二十集"

        Returns:
            集数编号（整数）
        """
        # 去掉"第"和"集"
        core = episode_str.replace('第', '').replace('集', '').strip()

        # 尝试直接转换为阿拉伯数字
        try:
            return int(core)
        except ValueError:
            pass

        # 处理中文数字
        if len(core) == 1:
            # 个位：一、二、三...九
            return chinese_numerals.get(core, 0)
        elif len(core) == 2:
            if core[0] == '十':
                # 10-19：十一、十二...十九
                return 10 + chinese_numerals.get(core[1], 0)
            else:
                # 20-99：二十、二十一...九十九
                # 二十 = 2 * 10, 二十一 = 2 * 10 + 1
                tens = chinese_numerals.get(core[0], 0)
                units = chinese_numerals.get(core[1], 0) if core[1] != '十' else 0
                return tens * 10 + units
        elif len(core) == 3:
            # 20-99 的完整表达：二十、二十一...九十九
            # "二十" = 2 * 10 + 0, "二十一" = 2 * 10 + 1
            tens = chinese_numerals.get(core[0], 0)
            units = chinese_numerals.get(core[2], 0) if len(core) > 2 else 0
            return tens * 10 + units

        return 0

    markings = []
    for idx, row in df.iterrows():
        try:
            # 解析集数（支持阿拉伯数字和中文数字）
            episode = str(row['集数']).strip()
            episode_number = parse_chinese_episode(episode)

            # 解析时间点
            # Excel里的格式是 MM:SS:毫秒 (如 00:25:00 = 25秒)
            timestamp_raw = row['时间点']
            
            # 处理不同格式的时间点
            if isinstance(timestamp_raw, str):
                timestamp = timestamp_raw.strip()
            elif hasattr(timestamp_raw, 'strftime'):  # datetime.time 对象
                timestamp = timestamp_raw.strftime('%H:%M:%S')
            else:
                timestamp = str(timestamp_raw)
            
            if ':' not in timestamp:
                print(f"警告: 跳过无效时间点格式: {timestamp} (行 {idx + 2})")
                continue

            parts = timestamp.split(':')
            # 格式是 MM:SS:毫秒 (如 00:25:00 = 25秒)
            # parts[0] = 分钟, parts[1] = 秒
            try:
                if len(parts) == 3:
                    # MM:SS:ms 格式 (如 00:25:00 = 25秒)
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    seconds_val = minutes * 60 + seconds
                elif len(parts) == 2:
                    # MM:SS 格式
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    seconds_val = minutes * 60 + seconds
                else:
                    print(f"警告: 跳过无效时间点格式: {timestamp} (行 {idx + 2})")
                    continue
            except ValueError:
                print(f"警告: 跳过无效时间点格式: {timestamp} (行 {idx + 2})")
                continue

            # 创建标记对象
            marking = Marking(
                id=idx,
                episode=episode,
                episode_number=episode_number,
                timestamp=timestamp,
                seconds=seconds_val,
                type=str(row['标记类型']).strip(),
                sub_type=str(row['子类型']).strip() if pd.notna(row.get('子类型')) else None,
                description=str(row['描述']).strip() if pd.notna(row.get('描述')) else None,
                score=int(row['得分']) if pd.notna(row.get('得分')) else None
            )
            markings.append(marking)

        except (ValueError, IndexError) as e:
            print(f"警告: 跳过无效数据行 {idx + 2}: {e}")
            continue

    print(f"从 {config.name} 读取了 {len(markings)} 个标记")
    return markings


def get_unique_episodes(markings: List[Marking]) -> set:
    """获取有标记的唯一集数"""
    return set(marking.episode_number for marking in markings)


def filter_markings_by_type(markings: List[Marking], marking_type: str) -> List[Marking]:
    """按类型过滤标记"""
    return [m for m in markings if m.type == marking_type]


def validate_markings(markings: List[Marking], config: ProjectConfig) -> List[Marking]:
    """验证标记数据，过滤掉无效的视频文件

    Args:
        markings: 标记数据列表
        config: 项目配置

    Returns:
        有效的标记数据列表
    """
    valid_markings = []
    invalid_episodes = set()

    for marking in markings:
        try:
            # 尝试获取视频文件路径
            config.get_video_path(marking.episode_number)
            valid_markings.append(marking)
        except FileNotFoundError:
            invalid_episodes.add(marking.episode_number)

    if invalid_episodes:
        print(f"警告: 项目 {config.name} 中以下集数的视频文件不存在，已跳过: {sorted(invalid_episodes)}")

    return valid_markings


if __name__ == "__main__":
    # 测试代码
    from .config import PROJECTS

    # 创建目录
    from .config import create_directories
    create_directories()

    # 测试读取第一个项目
    if PROJECTS:
        print(f"测试读取项目: {PROJECTS[0].name}")
        try:
            markings = load_project_markings(PROJECTS[0])
            valid_markings = validate_markings(markings, PROJECTS[0])

            print(f"总标记数: {len(markings)}")
            print(f"有效标记数: {len(valid_markings)}")
            print(f"唯一集数: {sorted(get_unique_episodes(valid_markings))}")

            # 显示前几个标记
            for marking in valid_markings[:3]:
                print(f"  {marking.episode} @ {marking.timestamp} - {marking.type}")

        except Exception as e:
            print(f"错误: {e}")