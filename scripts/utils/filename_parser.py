"""
文件名解析工具 - 支持多种视频文件命名格式

该模块提供强大的文件名解析功能，兼容各种视频文件命名格式：
- 纯数字: 1.mp4, 01.mp4, 001.mp4
- 带前缀: 精准-1.mp4, 机长姐姐-01.mp4
- EP前缀: ep01.mp4, EP1.mp4, e01.mp4
- 中文集数: 第1集.mp4, 第一集.mp4（需配合中文数字转换）
- 混合格式: 骨血灯_03_1080p.mp4
"""
import re
from typing import Optional
from pathlib import Path


def parse_episode_number(filename: str) -> Optional[int]:
    """
    从视频文件名中解析集数

    支持的格式：
    - 纯数字: 1.mp4, 01.mp4, 001.mp4
    - 带前缀: 精准-1.mp4, 机长姐姐-01.mp4
    - EP前缀: ep01.mp4, EP1.mp4, e01.mp4
    - 中文集数: 第1集.mp4（暂不支持中文数字"第一集"）
    - 混合格式: 骨血灯_03_1080p.mp4

    Args:
        filename: 视频文件名（可以是完整路径或仅文件名）

    Returns:
        集数（整数），如果无法解析则返回 None

    Examples:
        >>> parse_episode_number("1.mp4")
        1
        >>> parse_episode_number("精准-1.mp4")
        1
        >>> parse_episode_number("ep01.mp4")
        1
        >>> parse_episode_number("骨血灯_03_1080p.mp4")
        3
        >>> parse_episode_number("trailer.mp4")
        None
    """
    if not filename:
        return None

    # 从完整路径中提取文件名
    name = Path(filename).stem

    # 规则1：明确的"集"或"ep"关键字（优先级最高）
    explicit_patterns = [
        r'ep(\d+)',           # ep01, ep1
        r'EP(\d+)',           # EP01, EP1
        r'[eE](\d+)',         # e01, E01（边界匹配）
        r'第?(\d+)集',        # 第1集, 1集
    ]

    for pattern in explicit_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 200:  # 合理性检查
                return num

    # 规则2：文件名开头的2-3位数字（后面跟分隔符）
    # 例: "01 骨血灯", "02-", "001_"
    match = re.match(r'^(\d{2,3})[-_\s]', name)
    if match:
        num = int(match.group(1))
        if 1 <= num <= 200:
            return num

    # 规则3：文件名中间独立的2-3位数字（被分隔符包围）
    # 例: "骨血灯_03_1080p", "drama-04-final", "show_05_1080p"
    match = re.search(r'[-_\s](\d{2,3})[-_\s\.]', name)
    if match:
        num = int(match.group(1))
        if 1 <= num <= 200:
            return num

    # 规则4：带前缀的数字（前缀-数字或前缀_数字）
    # 例: "精准-1", "机长姐姐-01", "show_1"
    match = re.search(r'[-_](\d{1,3})$', name)
    if match:
        num = int(match.group(1))
        if 1 <= num <= 200:
            return num

    # 规则5：纯数字文件名
    # 例: "1", "01", "001"
    match = re.match(r'^(\d{1,3})$', name)
    if match:
        num = int(match.group(1))
        if 1 <= num <= 200:
            return num

    return None


def find_video_files(video_dir: str, episode_number: int) -> Optional[str]:
    """
    在指定目录中查找匹配集数的视频文件

    该函数会尝试多种方式查找视频文件：
    1. 首先尝试直接匹配：{episode_number}.mp4
    2. 然后遍历所有mp4文件，解析文件名进行匹配

    Args:
        video_dir: 视频目录路径
        episode_number: 目标集数

    Returns:
        视频文件的完整路径，如果未找到则返回 None

    Examples:
        >>> find_video_files("/path/to/videos", 1)
        '/path/to/videos/1.mp4'
        >>> find_video_files("/path/to/videos", 5)
        '/path/to/videos/精准-5.mp4'
    """
    video_path = Path(video_dir)
    if not video_path.exists():
        return None

    # 优先尝试直接匹配：{episode_number}.mp4
    direct_match = video_path / f"{episode_number}.mp4"
    if direct_match.exists():
        return str(direct_match)

    # 遍历所有mp4文件，尝试解析集数
    for video_file in video_path.glob("*.mp4"):
        parsed_episode = parse_episode_number(video_file.name)
        if parsed_episode == episode_number:
            return str(video_file)

    return None


def list_all_videos_with_episodes(video_dir: str) -> dict:
    """
    列出目录中所有视频文件及其对应的集数

    Args:
        video_dir: 视频目录路径

    Returns:
        字典 {集数: [文件路径列表]}
        如果无法解析集数，则存为 {None: [文件路径列表]}

    Examples:
        >>> list_all_videos_with_episodes("/path/to/videos")
        {1: ['/path/to/videos/1.mp4'], 2: ['/path/to/videos/ep02.mp4'], None: ['/path/to/videos/trailer.mp4']}
    """
    video_path = Path(video_dir)
    if not video_path.exists():
        return {}

    result = {}
    for video_file in video_path.glob("*.mp4"):
        episode = parse_episode_number(video_file.name)
        if episode not in result:
            result[episode] = []
        result[episode].append(str(video_file))

    return result


def validate_video_files(video_dir: str) -> dict:
    """
    验证视频文件的完整性和连续性

    Args:
        video_dir: 视频目录路径

    Returns:
        验证结果字典，包含：
        - total: 总文件数
        - parsed: 成功解析的文件数
        - failed: 解析失败的文件数
        - episodes: 已解析的集数列表（排序后）
        - missing: 缺失的集数（如果有）
        - duplicates: 重复的集数（如果有）
        - unparsed: 无法解析的文件列表
    """
    video_path = Path(video_dir)
    if not video_path.exists():
        return {"error": "目录不存在"}

    mp4_files = list(video_path.glob("*.mp4"))
    total = len(mp4_files)

    episodes_map = {}
    unparsed = []
    duplicates = {}

    for video_file in mp4_files:
        episode = parse_episode_number(video_file.name)
        if episode is None:
            unparsed.append(video_file.name)
        else:
            if episode not in episodes_map:
                episodes_map[episode] = []
            episodes_map[episode].append(video_file.name)

    # 检测重复
    for episode, files in episodes_map.items():
        if len(files) > 1:
            duplicates[episode] = files

    episodes = sorted(episodes_map.keys())

    # 检测缺失的集数
    missing = []
    if episodes:
        for i in range(1, max(episodes) + 1):
            if i not in episodes_map:
                missing.append(i)

    return {
        "total": total,
        "parsed": len(episodes_map),
        "failed": len(unparsed),
        "episodes": episodes,
        "missing": missing if missing else None,
        "duplicates": duplicates if duplicates else None,
        "unparsed": unparsed if unparsed else None,
    }


if __name__ == "__main__":
    # 简单测试
    test_files = [
        "1.mp4",
        "01.mp4",
        "精准-1.mp4",
        "机长姐姐-5.mp4",
        "ep03.mp4",
        "骨血灯_10_1080p.mp4",
        "trailer.mp4",
    ]

    print("=== 测试文件名解析 ===")
    for filename in test_files:
        episode = parse_episode_number(filename)
        print(f"{filename:30s} → {episode if episode else 'None'}")
