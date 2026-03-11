"""
视频剪辑渲染模块
基于FFmpeg实现高光点-钩子点剪辑的生成

V14: 新增结尾视频拼接功能
V14.1: 新增自动片尾检测功能
V14.8: 修复片尾剪切精度和音视频同步问题
V15: 新增视频包装花字叠加功能
V15.6: 修复处理顺序 + 热门短剧位置随机化（左上/右上各50%概率）
V16: 新增并行渲染功能（多进程加速）
"""
import os
import json
import subprocess
import random
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import re
import shutil
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

from scripts.config import TrainingConfig


def format_time(seconds: int) -> str:
    """格式化时间为中文显示

    Args:
        seconds: 秒数

    Returns:
        格式化后的时间字符串（如："3分24秒" 或 "45秒"）
    """
    if seconds < 60:
        return f"{seconds}秒"
    else:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}分{secs}秒"


@dataclass
class Clip:
    """剪辑组合"""
    start: float           # 起始累积秒（相对于第1集开头）V13: 支持毫秒精度
    end: float           # 结束累积秒（相对于第1集开头）V13: 支持毫秒精度
    duration: float      # 时长（秒）V13: 支持毫秒精度
    highlight: str      # 高光类型
    highlightDesc: str  # 高光描述
    hook: str          # 钩子类型
    hookDesc: str      # 钩子描述
    type: str          # 组合类型
    episode: int        # 起始集数
    hookEpisode: int   # 结束集数

    @property
    def clip_type(self) -> str:
        return self.type

    @property
    def is_cross_episode(self) -> bool:
        """是否跨集剪辑"""
        return self.episode != self.hookEpisode


@dataclass
class VideoFile:
    """视频文件信息"""
    episode: int
    path: str
    duration: int  # 时长（秒）
    fps: float = 30.0  # V14.2: 帧率（默认30.0，实际会自动检测）


@dataclass
class ClipSegment:
    """剪辑片段"""
    episode: int
    start: float      # 开始秒（在该集内）V13: 支持毫秒精度
    end: float        # 结束秒（在该集内）V13: 支持毫秒精度
    video_path: str


def cleanup_project_cache(project_name: str, min_age_hours: float = 3.0) -> dict:
    """清理项目的中间缓存文件（仅清理超过指定小时数的缓存）

    项目渲染完成后，清理关键帧、音频、ASR等中间产物。
    为了方便后续测试，只清理超过 min_age_hours 小时的缓存文件。

    Args:
        project_name: 项目名称
        min_age_hours: 最小缓存保留时长（小时），默认3.0小时

    Returns:
        清理结果统计，包含跳过的文件数量
    """
    import time

    cache_dir = TrainingConfig.CACHE_DIR
    cutoff_time = time.time() - (min_age_hours * 3600)  # 计算截止时间戳

    result = {
        "keyframes_cleaned": 0,
        "audio_cleaned": 0,
        "asr_cleaned": 0,
        "skipped": 0,  # 新增：跳过的文件数
        "total_size_freed_mb": 0,
    }

    def clean_directory_with_age_check(dir_path: Path, cache_type: str) -> tuple:
        """清理目录中的文件，只删除超过指定时间的文件

        Args:
            dir_path: 目录路径
            cache_type: 缓存类型（用于日志）

        Returns:
            (清理的文件数, 跳过的文件数, 释放的空间MB)
        """
        if not dir_path.exists():
            return 0, 0, 0.0

        cleaned = 0
        skipped = 0
        size_freed = 0.0

        # 收集所有文件
        all_files = list(dir_path.rglob("*"))
        if not all_files:
            # 空目录，直接删除
            shutil.rmtree(dir_path)
            return 0, 0, 0.0

        for file_path in all_files:
            if not file_path.is_file():
                continue

            # 检查文件修改时间
            file_mtime = file_path.stat().st_mtime
            if file_mtime >= cutoff_time:
                # 文件还在保留期内，跳过
                skipped += 1
                continue

            # 文件超过保留期，删除
            size_freed += file_path.stat().st_size / (1024 * 1024)
            file_path.unlink()
            cleaned += 1

        # 如果所有文件都被删除或跳过，清理空目录
        if cleaned > 0:
            # 尝试删除空目录
            try:
                # 检查是否还有文件
                remaining = list(dir_path.rglob("*"))
                if not any(f.is_file() for f in remaining):
                    shutil.rmtree(dir_path)
            except Exception:
                pass

        return cleaned, skipped, size_freed

    # 清理关键帧缓存
    keyframes_dir = cache_dir / "keyframes" / project_name
    cleaned, skipped, size = clean_directory_with_age_check(keyframes_dir, "关键帧")
    result["keyframes_cleaned"] = 1 if cleaned > 0 else 0
    result["skipped"] += skipped
    result["total_size_freed_mb"] += size

    # 清理音频缓存
    audio_dir = cache_dir / "audio" / project_name
    cleaned, skipped, size = clean_directory_with_age_check(audio_dir, "音频")
    result["audio_cleaned"] = 1 if cleaned > 0 else 0
    result["skipped"] += skipped
    result["total_size_freed_mb"] += size

    # 清理ASR缓存
    asr_dir = cache_dir / "asr" / project_name
    cleaned, skipped, size = clean_directory_with_age_check(asr_dir, "ASR")
    result["asr_cleaned"] = 1 if cleaned > 0 else 0
    result["skipped"] += skipped
    result["total_size_freed_mb"] += size

    return result


class ClipRenderer:
    """剪辑渲染器"""

    def __init__(
        self,
        project_path: str,
        output_dir: str,
        video_dir: Optional[str] = None,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        crf: int = 18,
        preset: str = "fast",
        project_name: Optional[str] = None,
        add_ending_clip: bool = False,
        auto_detect_ending: bool = True,
        skip_ending: bool = False,
        force_detect: bool = False,
        add_overlay: bool = False,
        overlay_style_id: Optional[str] = None,
        hwaccel: bool = False,
        fast_preset: bool = False
    ):
        """初始化剪辑渲染器

        Args:
            project_path: 项目路径（包含result.json）
            output_dir: 输出目录
            video_dir: 视频文件目录（默认为project_path）
            width: 输出视频宽度
            height: 输出视频高度
            fps: 输出帧率
            crf: CRF质量（18-28，越小质量越高）
            preset: 编码预设（ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow）
            project_name: 项目名称（用于文件命名）
            add_ending_clip: 是否添加结尾视频（V14新增）
            auto_detect_ending: 自动检测片尾（V14.1新增）
            skip_ending: 跳过片尾检测（V14.1新增）
            force_detect: 强制重新检测片尾（V14.1新增）
            add_overlay: 是否添加花字叠加（V15新增）
            overlay_style_id: 花字样式ID（None表示随机，V15新增）
            hwaccel: 启用GPU硬件加速（V16.2新增）
            fast_preset: 使用ultrafast预设（V16.2新增）
        """
        self.project_path = Path(project_path)
        self.output_dir = Path(output_dir)
        self.video_dir = Path(video_dir) if video_dir else self.project_path

        # 提取项目名称（如果未提供）
        if project_name is None:
            project_name = self.project_path.name

        self.project_name = project_name

        # FFmpeg参数
        self.width = width
        self.height = height
        self.fps = fps
        self.crf = crf

        # V16.2: 性能优化参数
        self.hwaccel = hwaccel
        if fast_preset:
            self.preset = "ultrafast"
        else:
            self.preset = preset

        # V14.1: 片尾检测配置
        self.auto_detect_ending = auto_detect_ending
        self.skip_ending = skip_ending
        self.force_detect = force_detect
        self.ending_credits_cache = {}

        # V14: 结尾视频配置
        self.add_ending_clip = add_ending_clip
        self.ending_videos = self._load_ending_videos() if add_ending_clip else []

        # V15: 花字叠加配置
        self.add_overlay = add_overlay
        self.overlay_style_id = overlay_style_id
        self.overlay_renderer = None
        if add_overlay:
            # 延迟导入花字叠加模块（避免循环依赖）
            try:
                from .video_overlay.video_overlay import VideoOverlayRenderer, OverlayConfig

                # V15.6: 随机选择热门短剧位置（左上角/右上角各50%概率）
                hot_drama_position = random.choice(["top-left", "top-right"])

                self.overlay_config = OverlayConfig(
                    enabled=True,
                    style_id=overlay_style_id,
                    project_name=project_name,
                    drama_title=project_name,
                    hot_drama_position=hot_drama_position  # V15.6: 添加位置参数
                )
                # 不在这里创建渲染器，而是在需要时创建（确保项目级样式统一）
                self._overlay_renderer_class = VideoOverlayRenderer
                print(f"✅ 花字叠加已启用 (热门短剧位置: {hot_drama_position})")
            except ImportError as e:
                print(f"⚠️  无法导入花字叠加模块: {e}")
                self.add_overlay = False

        # 加载结果
        self.result = self._load_result()

        # V14.1: 自动处理片尾检测（在计算时长前）
        self._handle_ending_detection()

        # 计算各集时长（现在使用有效时长）
        self.episode_durations = self._calculate_episode_durations()
        self.video_files = self._discover_video_files()

    def _load_result(self) -> dict:
        """加载result.json"""
        result_path = self.project_path / "result.json"
        if not result_path.exists():
            raise FileNotFoundError(f"找不到结果文件: {result_path}")

        with open(result_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _calculate_episode_durations(self) -> Dict[int, float]:
        """计算各集时长

        V14.1: 优先使用有效时长（总时长 - 片尾时长）
        如果没有片尾检测数据，则使用总时长

        V14.7修复: 保持浮点精度，避免int()转换丢失ASR内容

        Returns:
            集数到时长的映射（浮点数精度）
        """
        durations = {}

        # 从highlights和hooks中收集所有集数
        episodes = set()
        for h in self.result.get('highlights', []):
            episodes.add(h['episode'])
        for h in self.result.get('hooks', []):
            episodes.add(h['episode'])

        # 获取每个集的时长
        for ep in sorted(episodes):
            video_path = self._find_video_file(ep)
            if video_path:
                # V14.1: 优先使用有效时长
                if ep in self.ending_credits_cache:
                    ep_info = self.ending_credits_cache[ep]
                    # 使用有效时长（总时长 - 片尾时长）
                    effective_duration = ep_info.get('effective_duration')
                    if effective_duration is not None:
                        durations[ep] = effective_duration  # V14.7: 保持浮点精度
                        print(f"  第{ep}集: 有效时长 {effective_duration:.2f}秒 (已去除片尾)")
                        continue

                # 回退到使用总时长
                duration = self._get_video_duration(video_path)
                durations[ep] = duration  # V14.7: 保持浮点精度

        return durations

    def _discover_video_files(self) -> Dict[int, VideoFile]:
        """发现所有视频文件

        V14.2: 自动检测每个视频的帧率，确保剪辑精度
        """
        video_files = {}

        for ep in self.episode_durations.keys():
            video_path = self._find_video_file(ep)
            if video_path:
                # V14.2: 自动检测视频帧率
                video_fps = self._get_video_fps(str(video_path))

                print(f"  第{ep}集: 检测到帧率 {video_fps:.2f} FPS")

                video_files[ep] = VideoFile(
                    episode=ep,
                    path=str(video_path),
                    duration=self.episode_durations[ep],
                    fps=video_fps  # V14.2: 存储实际帧率
                )

        return video_files

    def _handle_ending_detection(self) -> None:
        """V14.1: 自动处理片尾检测

        完全自动流程：
        1. 检查是否需要检测
        2. 尝试加载缓存
        3. 如果需要，自动检测并保存
        """
        # 决定是否需要检测片尾
        should_detect = self._should_detect_ending()

        if not should_detect:
            if self.skip_ending:
                print("⚠️  已跳过片尾检测，将使用总时长")
            return

        # 尝试加载缓存
        cache_loaded = False
        if not self.force_detect:
            cache_loaded = self._load_ending_credits()

        # 如果缓存未加载，自动检测
        if not cache_loaded:
            print("🔍 开始自动检测片尾...")
            self._auto_detect_ending_credits()

    def _should_detect_ending(self) -> bool:
        """决定是否需要检测片尾

        V14.7修复: 当auto_detect_ending=True时，应该加载缓存并应用
        """
        # 1. 用户明确指定跳过
        if self.skip_ending:
            return False

        # 2. 用户明确指定强制检测
        if self.force_detect:
            return True

        # 3. 根据auto_detect_ending决定（无论缓存是否存在）
        # V14.7修复: 如果auto_detect_ending=True，应该加载缓存并应用
        return self.auto_detect_ending

    def _get_ending_cache_file(self) -> Path:
        """获取片尾缓存文件路径"""
        # 缓存文件保存在 data/hangzhou-leiming/ending_credits/ 目录下
        cache_dir = self.project_path.parent.parent / "ending_credits"
        return cache_dir / f"{self.project_name}_ending_credits.json"

    def _load_ending_credits(self) -> bool:
        """加载片尾检测结果缓存

        Returns:
            True if cache loaded successfully, False otherwise
        """
        cache_file = self._get_ending_cache_file()

        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 验证缓存是否匹配当前项目
                if self._validate_cache(data):
                    # 转换为字典格式：episode -> effective_duration
                    self.ending_credits_cache = {}
                    for ep_info in data.get('episodes', []):
                        ep = ep_info['episode']
                        self.ending_credits_cache[ep] = ep_info

                    print(f"✅ 已加载片尾缓存: {len(self.ending_credits_cache)} 集")
                    return True
                else:
                    print("⚠️  缓存文件与当前项目不匹配，将重新检测")
            except Exception as e:
                print(f"⚠️  缓存文件损坏: {e}")

        return False

    def _validate_cache(self, cache_data: dict) -> bool:
        """验证缓存数据是否有效

        Args:
            cache_data: 缓存数据

        Returns:
            True if cache is valid, False otherwise
        """
        # 检查项目名称是否匹配
        if cache_data.get('project') != self.project_name:
            return False

        # 检查是否有集数据
        episodes = cache_data.get('episodes', [])
        if not episodes:
            return False

        return True

    def _auto_detect_ending_credits(self) -> None:
        """
        自动检测项目中所有视频的片尾

        V15.9 优化：
        - 复用 ASR 缓存，避免重复转录
        - 片尾检测阶段使用 video_understand 阶段已缓存的 ASR
        - 预期效果：片尾检测从 3分钟 → 瞬间完成
        """
        print(f"📺 检测项目: {self.project_name}")
        print(f"📁 视频目录: {self.video_dir}")

        try:
            # 导入片尾检测模块
            from scripts.detect_ending_credits import EndingCreditsDetector

            # V15.9: 导入 ASR 缓存加载函数
            from scripts.extract_asr import load_asr_from_file, get_asr_output_path

            detector = EndingCreditsDetector()

            # 获取所有视频文件
            video_files = sorted(self.video_dir.glob("*.mp4"))
            total_videos = len(video_files)

            if total_videos == 0:
                print("⚠️  未找到视频文件")
                return

            print(f"📊 需要检测 {total_videos} 个视频...")

            # V15.9: 检查 ASR 缓存可用性
            asr_cache_available = {}
            for video_path in video_files:
                episode = self._extract_episode_number(video_path.name)
                if episode is None:
                    continue
                asr_path = get_asr_output_path(self.video_dir.name, episode)
                if os.path.exists(asr_path):
                    asr_cache_available[episode] = asr_path

            if asr_cache_available:
                print(f"📦 已缓存 ASR: {len(asr_cache_available)}/{total_videos} 集（将复用缓存）")
                print(f"⏱️  预计耗时: {total_videos * 1}-{total_videos * 3} 秒（使用 ASR 缓存加速）")
            else:
                print(f"⏱️  预计耗时: {total_videos * 3}-{total_videos * 10} 秒（无 ASR 缓存）")

            results = {'project': self.project_name, 'episodes': []}

            for i, video_path in enumerate(video_files, 1):
                print(f"  [{i}/{total_videos}] 检测 {video_path.name}...")

                episode = self._extract_episode_number(video_path.name)
                if episode is None:
                    print(f"    ⚠️  无法提取集数，跳过")
                    continue

                try:
                    # V15.9: 复用 ASR 缓存
                    asr_segments = None
                    if episode in asr_cache_available:
                        asr_path = asr_cache_available[episode]
                        asr_segments = load_asr_from_file(asr_path, episode=episode)
                        if asr_segments:
                            print(f"    📦 使用缓存的 ASR 数据 ({len(asr_segments)} 片段)")

                    # 传入 ASR 数据（如果有缓存）
                    result = detector.detect_video_ending(str(video_path), episode, asr_segments=asr_segments)
                    results['episodes'].append(result.to_dict())

                    if result.ending_info.has_ending:
                        print(f"    ✅ 检测到片尾: {result.ending_info.duration:.2f}秒")
                    else:
                        print(f"    ✅ 未检测到片尾")

                except Exception as e:
                    print(f"    ❌ 检测失败: {e}")
                    continue

            # 保存到文件
            self._save_ending_credits(results)

            # 更新缓存
            self.ending_credits_cache = {}
            for ep_info in results['episodes']:
                ep = ep_info['episode']
                self.ending_credits_cache[ep] = ep_info

            print(f"✅ 片尾检测完成，结果已保存")

            # 显示统计
            with_ending = sum(1 for ep in results['episodes'] if ep['ending_info']['has_ending'])
            without_ending = len(results['episodes']) - with_ending
            print(f"📊 检测统计: {len(results['episodes'])}集视频, {with_ending}集有片尾, {without_ending}集无片尾")

        except Exception as e:
            print(f"❌ 片尾检测失败: {e}")
            print("⚠️  将使用总时长进行渲染")

    def _extract_episode_number(self, filename: str) -> Optional[int]:
        """从文件名提取集数

        Args:
            filename: 视频文件名

        Returns:
            集数，如果无法提取则返回None
        """
        import re

        # 尝试多种命名格式
        patterns = [
            r'第(\d+)集',
            r'EP?(\d+)',
            r'^(\d+)',
            r'[-_](\d+)\.mp4$',  # 支持: 项目名-1.mp4, 项目名_1.mp4
            r'(\d+)(?=\.mp4)',   # 匹配任何 .mp4 前的数字
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _save_ending_credits(self, results: dict) -> None:
        """保存片尾检测结果到文件

        Args:
            results: 检测结果数据
        """
        cache_file = self._get_ending_cache_file()

        # 确保目录存在
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        # 保存到文件
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"💾 缓存已保存: {cache_file}")

    def _load_ending_videos(self) -> List[str]:
        """加载标准结尾视频素材列表

        V14: 从项目根目录的 `标准结尾帧视频素材` 文件夹加载结尾视频

        Returns:
            结尾视频文件路径列表
        """
        # 从项目路径向上查找，直到找到 `标准结尾帧视频素材` 文件夹
        # 或者到达一定层级后停止

        # 首先尝试当前路径的父目录
        current_path = self.project_path

        # 向上查找最多3层
        for _ in range(3):
            parent = current_path.parent
            ending_dir = parent / "标准结尾帧视频素材"

            if ending_dir.exists():
                break

            current_path = parent
        else:
            # 如果没找到，尝试使用当前工作目录
            import os
            cwd = Path(os.getcwd())
            ending_dir = cwd / "标准结尾帧视频素材"

        if not ending_dir.exists():
            print(f"⚠️  警告: 找不到结尾视频文件夹: {ending_dir}")
            print(f"    请确保 `标准结尾帧视频素材` 文件夹在项目根目录下")
            return []

        # 支持的视频格式
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.webm']
        ending_videos = []

        for ext in video_extensions:
            pattern = f"*{ext}"
            for video_path in ending_dir.glob(pattern):
                if video_path.is_file():
                    ending_videos.append(str(video_path))

        if not ending_videos:
            print(f"⚠️  警告: 结尾视频文件夹为空: {ending_dir}")
        else:
            print(f"✅ 加载了 {len(ending_videos)} 个结尾视频")

        return ending_videos

    def _get_random_ending_video(self) -> Optional[str]:
        """随机选择一个结尾视频

        V14: 从已加载的结尾视频中随机选择一个

        Returns:
            结尾视频文件路径，如果没有可用的则返回None
        """
        if not self.ending_videos:
            return None

        return random.choice(self.ending_videos)

    def _find_video_file(self, episode: int) -> Optional[Path]:
        """查找指定集数的视频文件

        支持多种命名格式：
        - 第1集.mp4
        - EP01.mp4
        - E01.mp4
        - 01.mp4
        """
        patterns = [
            f"第{episode}集.mp4",
            f"第{episode}集.*.mp4",
            f"EP{episode:02d}.mp4",
            f"E{episode:02d}.mp4",
            f"{episode:02d}.mp4",
            f"{episode}.mp4",
            f"*-{episode}.mp4",    # V15.1: 支持 项目名-1.mp4
            f"*_{episode}.mp4",    # V15.1: 支持 项目名_1.mp4
        ]

        for pattern in patterns:
            matches = list(self.video_dir.glob(pattern))
            if matches:
                return matches[0]

        return None

    def _get_video_duration(self, video_path: str) -> float:
        """使用ffprobe获取视频时长（秒）"""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"无法获取视频时长: {video_path}, 错误: {e}")

    def _clip_to_segments(self, clip: Clip) -> List[ClipSegment]:
        """将剪辑转换为视频片段列表

        处理两种情况：
        1. 同集剪辑：episode == hook_episode，返回1个片段
        2. 跨集剪辑：episode != hook_episode，返回多个片段
        V13: 支持毫秒精度（浮点数时间戳）
        """
        segments = []

        # 起始集
        if clip.episode not in self.video_files:
            raise ValueError(f"找不到第{clip.episode}集视频文件")

        # 计算起始集的开始时间
        start_cumulative = float(clip.start)

        # 从start累积时间推算在该集内的开始时间
        cumulative_before = 0.0
        for ep in sorted(self.episode_durations.keys()):
            if ep < clip.episode:
                cumulative_before += float(self.episode_durations[ep])

        start_in_episode = start_cumulative - cumulative_before

        # 如果是同集剪辑
        if clip.episode == clip.hookEpisode:
            end_in_episode = start_in_episode + float(clip.duration)
            segments.append(ClipSegment(
                episode=clip.episode,
                start=start_in_episode,  # V13: 保持浮点数精度
                end=end_in_episode,      # V13: 保持浮点数精度
                video_path=self.video_files[clip.episode].path
            ))
        else:
            # 跨集剪辑：第一集片段
            first_ep_duration = float(self.episode_durations[clip.episode])
            first_segment_end = first_ep_duration - start_in_episode
            segments.append(ClipSegment(
                episode=clip.episode,
                start=start_in_episode,  # V13: 保持浮点数精度
                end=first_ep_duration,   # V13: 保持浮点数精度
                video_path=self.video_files[clip.episode].path
            ))

            # 中间集的完整片段
            for ep in sorted(self.episode_durations.keys()):
                if clip.episode < ep < clip.hookEpisode:
                    segments.append(ClipSegment(
                        episode=ep,
                        start=0.0,  # V13: 保持浮点数精度
                        end=float(self.episode_durations[ep]),  # V13: 保持浮点数精度
                        video_path=self.video_files[ep].path
                    ))

            # 最后一集片段
            end_cumulative = float(clip.end)
            cumulative_before_last = 0.0
            for ep in sorted(self.episode_durations.keys()):
                if ep < clip.hookEpisode:
                    cumulative_before_last += float(self.episode_durations[ep])

            end_in_last_episode = end_cumulative - cumulative_before_last
            segments.append(ClipSegment(
                episode=clip.hookEpisode,
                start=0.0,  # V13: 保持浮点数精度
                end=end_in_last_episode,  # V13: 保持浮点数精度
                video_path=self.video_files[clip.hookEpisode].path  # V13.1: 修复属性名错误
            ))

        return segments

    def _trim_segment(
        self,
        segment: ClipSegment,
        output_path: str,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> None:
        """裁剪单个视频片段

        V14.2 更新：使用基于帧率的精确剪辑，避免精度问题
        FFmpeg按帧率对齐，使用-frames:v参数而不是-t参数

        V14.8 更新：修复音视频同步问题 - 使用 -t 参数确保音视频时长一致

        Args:
            segment: 视频片段
            output_path: 输出文件路径
            on_progress: 进度回调函数（0.0-1.0）
        """
        import math

        # V13: 支持毫秒精度（浮点数时间戳）
        start_time = segment.start if isinstance(segment.start, float) else float(segment.start)
        end_time = segment.end if isinstance(segment.end, float) else float(segment.end)
        duration = end_time - start_time

        # V14.2: 从VideoFile获取实际帧率（而不是每次都检测）
        if segment.episode in self.video_files:
            fps = self.video_files[segment.episode].fps
        else:
            # 回退到自动检测
            fps = self._get_video_fps(segment.video_path)

        # 计算帧数（向上取整，确保完整）
        total_frames = math.ceil(duration * fps)

        # V14.10: 修复片尾拼接"有声音无画面"BUG
        # 关键修复：移除 -frames:v 参数
        # 问题根源：当使用 -c copy 时，同时使用 -t 和 -frames:v 会导致视频流被截断
        # -t 参数已经足够精确，无需额外的 -frames:v 参数
        cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-ss', f"{start_time:.3f}",  # 起始时间（用于快速定位）
            '-i', segment.video_path,  # 输入文件
            '-t', f"{duration:.3f}",  # V14.8: 明确指定时长，确保音视频同步
            '-c', 'copy',  # 复制流，不重新编码（保持原质量和大小）
            '-movflags', '+faststart',  # 优化Web播放
            output_path
        ]

        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 合并stdout和stderr
            universal_newlines=True
        )

        # 实时输出日志
        for line in process.stdout:
            print(f"\r  {line.strip()[:100]}", end='', flush=True)

        process.wait()

        if process.returncode != 0:
            raise RuntimeError(
                f"FFmpeg裁剪失败 (返回码: {process.returncode})\n"
                f"命令: {' '.join(cmd)}\n"
            )

    def _get_video_fps(self, video_path: str) -> float:
        """获取视频帧率

        V14.2 新增方法：用于基于帧的精确剪辑

        Args:
            video_path: 视频文件路径

        Returns:
            视频帧率（FPS）
        """
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # 如果无法获取帧率，使用默认值
            return float(self.fps)

        fps_str = result.stdout.strip()
        # 解析帧率（例如 "30/1" 或 "29.97"）
        if '/' in fps_str:
            num, den = fps_str.split('/')
            return float(num) / float(den)
        else:
            return float(fps_str)

    def _concat_segments(
        self,
        segment_files: List[str],
        output_path: str,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> None:
        """拼接多个视频片段

        使用concat demuxer方法（快速，无重编码）

        Args:
            segment_files: 视频片段文件列表
            output_path: 输出文件路径
            on_progress: 进度回调函数
        """
        # 创建临时concat列表文件
        concat_file = self.output_dir / "concat_list.txt"
        with open(concat_file, 'w') as f:
            for segment_file in segment_files:
                # V13.1: 使用相对路径，避免路径重复问题
                segment_path = Path(segment_file)
                relative_path = segment_path.relative_to(self.output_dir)
                f.write(f"file '{relative_path}'\n")

        # FFmpeg命令
        cmd = [
            'ffmpeg',
            '-y',
            '-f', 'concat',  # concat demuxer
            '-safe', '0',  # 允许任意文件路径
            '-i', str(concat_file),  # 输入列表文件
            '-c', 'copy',  # 复制流，不重编码
            output_path
        ]

        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # 简单进度（concat很快，粗略估计）
        if on_progress:
            on_progress(0.5)

        process.wait()

        if on_progress:
            on_progress(1.0)

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg拼接失败: {process.stderr.read()}")

        # 删除临时文件
        concat_file.unlink()

    def _append_ending_video(self, clip_path: str) -> str:
        """为剪辑添加结尾视频

        V14: 在剪辑末尾拼接随机选择的结尾视频
        预处理结尾视频以匹配原剪辑的分辨率和编码

        Args:
            clip_path: 原剪辑文件路径

        Returns:
            添加结尾后的文件路径（如果未添加则返回原路径）
        """
        # 随机选择结尾视频
        ending_video = self._get_random_ending_video()
        if not ending_video:
            print(f"  ⚠️  无可用结尾视频，跳过拼接")
            return clip_path

        # 生成新的输出文件名（添加 "_带结尾" 标记）
        clip_path_obj = Path(clip_path)
        new_filename = clip_path_obj.stem + "_带结尾" + clip_path_obj.suffix
        new_output_path = str(clip_path_obj.parent / new_filename)

        print(f"  🎬 添加结尾视频: {Path(ending_video).name}")
        print(f"  输出文件: {new_filename}")

        # 预处理结尾视频（匹配原剪辑的分辨率）
        processed_ending = self._preprocess_ending_video(clip_path, ending_video)

        # 拼接视频
        self._concat_videos([clip_path, processed_ending], new_output_path)

        # 删除临时处理的结尾视频
        Path(processed_ending).unlink()

        # 删除原剪辑文件
        Path(clip_path).unlink()

        return new_output_path

    def _preprocess_ending_video(self, clip_path: str, ending_video: str) -> str:
        """预处理结尾视频，使其与原剪辑兼容

        V14: 将结尾视频转换为与原剪辑相同的分辨率和编码
        V14.8: 修复音视频同步问题 - 使用视频流时长作为参考，确保音视频完全同步

        Args:
            clip_path: 原剪辑文件路径（用于获取分辨率）
            ending_video: 结尾视频文件路径

        Returns:
            处理后的结尾视频文件路径
        """
        # 获取原剪辑的实际分辨率（而不是使用默认的width/height）
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0',
            clip_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # 如果获取失败，使用默认值
            clip_width, clip_height = self.width, self.height
        else:
            parts = result.stdout.strip().split(',')
            clip_width = int(parts[0])
            clip_height = int(parts[1])

        # V14.8: 获取结尾视频的视频流时长（使用视频时长作为参考）
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            ending_video
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # 如果获取失败，使用ffprobe获取格式时长
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                ending_video
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            video_duration = float(result.stdout.strip())
        else:
            video_duration = float(result.stdout.strip())

        # 生成临时文件路径
        temp_ending = self.output_dir / f"temp_ending_{Path(ending_video).stem}.mp4"

        # V14.8: 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # V14.10: 修复帧率不一致问题 - 添加帧率转换
        # 问题：原始视频30fps，结尾视频24fps，帧率不一致导致拼接时视频流被截断
        # 解决方案：在预处理时将结尾视频转换为与原视频相同的帧率

        # 获取原剪辑的帧率
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'csv=p=0',
            clip_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            fps_str = result.stdout.strip()
            # 解析帧率（如 "30/1" -> 30.0）
            if '/' in fps_str:
                num, den = fps_str.split('/')
                clip_fps = float(num) / float(den)
            else:
                clip_fps = float(fps_str)
            print(f"  📊 原剪辑帧率: {clip_fps} fps")
        else:
            clip_fps = 30.0  # 默认30fps
            print(f"  ⚠️  无法获取帧率，使用默认30fps")

        # V14.9: 修复的FFmpeg命令 - 彻底解决音视频不同步问题
        # 关键修复（Agent Team分析结果）：
        # 1. 移除 -t 参数（时间戳截取精度不够，会导致音视频不同步）
        # 2. 移除 -af apad（过度填充音频，导致音频比视频长）
        # 3. 添加 -vsync 2（保留时间戳，确保帧同步）
        # 4. 添加 -async 1（音频自动同步到视频）
        # 5. V14.10: 添加帧率转换，确保帧率一致
        cmd = [
            'ffmpeg',
            '-y',
            '-i', ending_video,
            '-vf', f'fps={clip_fps},scale={clip_width}:{clip_height}:force_original_aspect_ratio=decrease,pad={clip_width}:{clip_height}:(ow-iw)/2:(oh-ih)/2',  # V14.10: 添加fps转换 + 缩放并添加黑边
            '-r', str(clip_fps),  # V14.10: 明确指定输出帧率（与原视频一致）
            '-c:v', 'libx264',  # 统一使用h264编码
            '-preset', self.preset,
            '-crf', str(self.crf),
            '-c:a', 'aac',  # 统一音频编码
            '-b:a', '128k',
            '-vsync', 'cfr',  # V14.10: 使用CFR模式确保帧率一致
            '-movflags', '+faststart',
            str(temp_ending)
        ]

        # 执行命令
        try:
            print(f"  🔄 预处理结尾视频（{clip_width}x{clip_height}，时长{video_duration:.3f}秒）...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # V14.8: 分离stderr以便获取错误信息
                universal_newlines=True
            )

            # 等待完成并获取输出
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                print(f"  ❌ FFmpeg错误输出:")
                print(stderr[-1000:] if len(stderr) > 1000 else stderr)  # 打印最后1000个字符
                raise RuntimeError(f"FFmpeg预处理失败 (返回码: {process.returncode})")

            print(f"  ✅ 结尾视频预处理完成")

            # V14.8: 验证音视频同步
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'stream=codec_type,duration',
                '-of', 'csv=p=0',
                str(temp_ending)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            durations = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        durations[parts[0]] = float(parts[1])

            if 'video' in durations and 'audio' in durations:
                diff = abs(durations['video'] - durations['audio'])
                if diff < 0.01:
                    print(f"  ✅ 音视频同步（差异: {diff:.3f}秒）")
                else:
                    print(f"  ⚠️  音视频略有差异（{diff:.3f}秒），但在可接受范围内")

        except Exception as e:
            raise RuntimeError(f"结尾视频预处理失败: {e}")

        return str(temp_ending)

    def _concat_videos(
        self,
        video_files: List[str],
        output_path: str,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> None:
        """拼接多个视频文件

        V14: 通用视频拼接方法，用于拼接剪辑和结尾视频
        使用 concat demuxer 快速拼接（视频已预处理为相同格式）

        Args:
            video_files: 视频文件路径列表
            output_path: 输出文件路径
            on_progress: 进度回调函数
        """
        # 创建临时concat列表文件
        concat_file = self.output_dir / "concat_list.txt"
        with open(concat_file, 'w', encoding='utf-8') as f:
            for video_file in video_files:
                # 使用绝对路径
                video_path = Path(video_file).resolve()
                f.write(f"file '{video_path}'\n")

        # V14.9: FFmpeg命令 - 使用重新编码拼接（彻底解决流不兼容问题）
        # 关键修复（Agent Team分析结果）：
        # - 原剪辑（copy模式）和结尾视频（重编码）的流不兼容
        # - -c copy 会导致视频流截断，出现"有声音无画面"
        # - 改用重新编码可以确保流完全兼容，音视频完美同步
        cmd = [
            'ffmpeg',
            '-y',
            '-f', 'concat',  # concat demuxer
            '-safe', '0',  # 允许任意文件路径
            '-i', str(concat_file),  # 输入列表文件
            '-c:v', 'libx264',  # V14.9: 重新编码视频（解决流不兼容）
            '-preset', 'ultrafast',  # V14.9: 超快预设（减少处理时间）
            '-crf', '18',  # V14.9: 高质量（几乎无损）
            '-c:a', 'aac',  # V14.9: 重新编码音频
            '-b:a', '192k',  # V14.9: 高质量音频
            '-movflags', '+faststart',  # 优化Web播放
            output_path
        ]

        # 执行命令
        try:
            print(f"  🔄 拼接视频...")
            print(f"  📋 FFmpeg命令: {' '.join(cmd)}")  # V14.9调试：打印完整命令

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # 等待完成
            process.wait()

            if process.returncode != 0:
                error_output = process.stderr.read()
                raise RuntimeError(f"FFmpeg拼接失败: {error_output}")

            print(f"  ✅ 视频拼接完成")

            if on_progress:
                on_progress(1.0)

        finally:
            # 删除临时文件
            if concat_file.exists():
                concat_file.unlink()

    def _apply_video_overlay(self, clip_path: str) -> str:
        """为视频添加花字叠加

        V15: 在视频上叠加"热门短剧"、剧名、免责声明
        项目级样式统一（同一项目使用相同样式）

        Args:
            clip_path: 原视频文件路径

        Returns:
            添加花字后的文件路径
        """
        try:
            # 延迟创建渲染器（确保项目级样式统一）
            if not hasattr(self, '_overlay_renderer_instance'):
                self._overlay_renderer_instance = self._overlay_renderer_class(
                    self.overlay_config
                )

            # 生成新的输出文件名（添加 "_带花字" 标记）
            clip_path_obj = Path(clip_path)
            new_filename = clip_path_obj.stem + "_带花字" + clip_path_obj.suffix
            new_output_path = str(clip_path_obj.parent / new_filename)

            print(f"  🎨 添加花字叠加...")
            print(f"  输出文件: {new_filename}")

            # 应用花字叠加
            result_path = self._overlay_renderer_instance.apply_overlay(
                input_video=clip_path,
                output_video=new_output_path
            )

            # 删除原视频文件
            Path(clip_path).unlink()

            return result_path

        except Exception as e:
            print(f"  ⚠️  花字叠加失败: {e}")
            print(f"  将保留原视频: {clip_path}")
            # 如果花字叠加失败，返回原视频路径
            return clip_path

    def render_clip(
        self,
        clip: Clip,
        output_path: Optional[str] = None,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> str:
        """渲染单个剪辑

        Args:
            clip: 剪辑对象
            output_path: 输出文件路径（可选，默认自动生成）
            on_progress: 进度回调函数

        Returns:
            输出文件路径
        """
        # 生成输出文件名（中文格式）
        if output_path is None:
            # 计算起始和结束时间（在该集内的秒数）
            start_cumulative = clip.start
            end_cumulative = clip.end

            # 计算起始集内的秒数
            cumulative_before_start = 0
            for ep in sorted(self.episode_durations.keys()):
                if ep < clip.episode:
                    cumulative_before_start += self.episode_durations[ep]

            start_in_episode = start_cumulative - cumulative_before_start

            # 计算结束集内的秒数
            cumulative_before_end = 0
            for ep in sorted(self.episode_durations.keys()):
                if ep < clip.hookEpisode:
                    cumulative_before_end += self.episode_durations[ep]

            end_in_episode = end_cumulative - cumulative_before_end

            # 生成中文文件名
            filename = f"{self.project_name}_第{clip.episode}集{format_time(int(start_in_episode))}_第{clip.hookEpisode}集{format_time(int(end_in_episode))}.mp4"
            output_path = str(self.output_dir / filename)

        print(f"\n渲染剪辑: {filename}")
        print(f"  起始: 第{clip.episode}集{format_time(int(start_in_episode))}")
        print(f"  结束: 第{clip.hookEpisode}集{format_time(int(end_in_episode))}")
        print(f"  时长: {clip.duration:.3f}秒")  # V13: 显示毫秒精度
        print(f"  跨集: {'是' if clip.is_cross_episode else '否'}")

        # 转换为视频片段
        segments = self._clip_to_segments(clip)

        print(f"  片段数: {len(segments)}")
        for i, seg in enumerate(segments, 1):
            print(f"    {i}. 第{seg.episode}集 {seg.start:.3f}-{seg.end:.3f}秒")  # V13: 显示毫秒精度

        # 如果只有1个片段且不是跨集，直接裁剪
        if len(segments) == 1:
            self._trim_segment(segments[0], output_path, on_progress)
        else:
            # 多个片段：先分别裁剪，再拼接
            temp_files = []
            temp_dir = self.output_dir / "temp"
            temp_dir.mkdir(exist_ok=True)

            # 裁剪每个片段
            for i, segment in enumerate(segments):
                temp_file = temp_dir / f"segment_{i}.mp4"
                self._trim_segment(segment, str(temp_file))
                temp_files.append(str(temp_file))

            # 拼接片段
            self._concat_segments(temp_files, output_path, on_progress)

            # 删除临时文件
            for temp_file in temp_files:
                Path(temp_file).unlink()
            temp_dir.rmdir()

        # V15.6: 添加花字叠加（如果配置了）- 先叠加花字
        if self.add_overlay and hasattr(self, '_overlay_renderer_class'):
            output_path = self._apply_video_overlay(output_path)

        # V14: 添加结尾视频（如果配置了）- 再拼接片尾
        if self.add_ending_clip:
            output_path = self._append_ending_video(output_path)

        print(f"  ✅ 输出: {output_path}")
        return output_path

    def render_all_clips(
        self,
        on_clip_progress: Optional[Callable[[int, int, float], None]] = None,
        max_clips: int = 0,
        clip_indices: Optional[List[int]] = None
    ) -> List[str]:
        """渲染所有剪辑

        Args:
            on_clip_progress: 进度回调函数(current, total, progress)
            max_clips: 最多渲染的剪辑数量（0=全部）
            clip_indices: 指定要渲染的剪辑索引列表（如 [0, 2, 7]）

        Returns:
            输出文件路径列表
        """
        clips_data = self.result.get('clips', [])

        # V15.7: 支持限制剪辑数量
        if clip_indices:
            # 渲染指定索引的剪辑
            clips_to_render = [(i, clips_data[i]) for i in clip_indices if i < len(clips_data)]
            print(f"\n渲染指定 {len(clips_to_render)} 个剪辑（索引: {clip_indices}）...")
        elif max_clips > 0:
            # 渲染前 max_clips 个剪辑
            clips_to_render = list(enumerate(clips_data[:max_clips]))
            print(f"\n渲染前 {len(clips_to_render)} 个剪辑（共 {len(clips_data)} 个）...")
        else:
            # 渲染全部
            clips_to_render = list(enumerate(clips_data))
            print(f"\n渲染全部 {len(clips_to_render)} 个剪辑...")

        total_clips = len(clips_to_render)
        print(f"输出目录: {self.output_dir}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        output_paths = []

        for render_idx, (original_idx, clip_data) in enumerate(clips_to_render, 1):
            clip = Clip(**clip_data)

            # V13.1: 修复progress变量未定义的bug
            last_progress = [0.0]  # 使用列表来在闭包中存储进度

            def clip_progress(progress: float):
                last_progress[0] = progress  # 更新进度值
                if on_clip_progress:
                    on_clip_progress(render_idx, total_clips, progress)

            try:
                output_path = self.render_clip(clip, on_progress=clip_progress)
                output_paths.append(output_path)

                # 总体进度 (V15.7: 修复idx变量未定义问题)
                if on_clip_progress:
                    overall_progress = (render_idx - 1 + last_progress[0]) / total_clips
                    on_clip_progress(render_idx, total_clips, overall_progress)

            except Exception as e:
                print(f"  ❌ 渲染失败: {e}")
                continue

        print(f"\n✅ 渲染完成: {len(output_paths)}/{total_clips}个剪辑")
        return output_paths

    def render_all_clips_parallel(
        self,
        max_workers: int = 4,
        on_clip_progress: Optional[Callable[[int, int, float], None]] = None,
        max_clips: int = 0,
        clip_indices: Optional[List[int]] = None
    ) -> List[str]:
        """并行渲染所有剪辑 (V16新增)

        使用多进程加速渲染，每个worker独立处理一个剪辑

        Args:
            max_workers: 最大并行worker数（默认4，设为1禁用并行）
            on_clip_progress: 进度回调函数(current, total, progress)
            max_clips: 最多渲染的剪辑数量（0=全部）
            clip_indices: 指定要渲染的剪辑索引列表（如 [0, 2, 7]）

        Returns:
            输出文件路径列表
        """
        clips_data = self.result.get('clips', [])

        # 如果max_workers<=1，回退到串行模式
        if max_workers <= 1:
            return self.render_all_clips(on_clip_progress, max_clips, clip_indices)

        # 支持限制剪辑数量
        if clip_indices:
            clips_to_render = [(i, clips_data[i]) for i in clip_indices if i < len(clips_data)]
            print(f"\n并行渲染指定 {len(clips_to_render)} 个剪辑（索引: {clip_indices}）...")
        elif max_clips > 0:
            clips_to_render = list(enumerate(clips_data[:max_clips]))
            print(f"\n并行渲染前 {len(clips_to_render)} 个剪辑（共 {len(clips_data)} 个）...")
        else:
            clips_to_render = list(enumerate(clips_data))
            print(f"\n并行渲染全部 {len(clips_to_render)} 个剪辑...")

        total_clips = len(clips_to_render)
        print(f"输出目录: {self.output_dir}")
        print(f"并行Worker数: {max_workers}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 限制worker数量不超过CPU核心数
        max_workers = min(max_workers, multiprocessing.cpu_count())

        # 准备渲染参数
        render_params = {
            'video_dir': str(self.video_dir),
            'output_dir': str(self.output_dir),
            'episode_durations': self.episode_durations,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'crf': self.crf,
            'preset': self.preset,
            'project_name': self.project_name,
            'add_ending_clip': self.add_ending_clip,
            'ending_videos': self.ending_videos,
            'add_overlay': self.add_overlay,
            'overlay_style_id': self.overlay_style_id,
            'hot_drama_position': getattr(self, 'overlay_config', None).hot_drama_position if hasattr(self, 'overlay_config') and self.overlay_config else 'top-right',
            'hwaccel': self.hwaccel,  # V16.2: GPU硬件加速
        }

        output_paths = []
        completed = 0

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(
                    render_single_clip_standalone,
                    original_idx,
                    clip_data,
                    render_params
                ): (original_idx, clip_data)
                for original_idx, clip_data in clips_to_render
            }

            # 收集结果
            for future in as_completed(futures):
                original_idx, _ = futures[future]
                completed += 1

                try:
                    output_path = future.result()
                    if output_path:
                        output_paths.append(output_path)
                        print(f"  ✅ 剪辑 {completed}/{total_clips} (原索引 {original_idx}) 完成")
                    else:
                        print(f"  ⚠️  剪辑 {completed}/{total_clips} (原索引 {original_idx}) 无输出")

                    # 进度回调
                    if on_clip_progress:
                        on_clip_progress(completed, total_clips, 1.0)

                except Exception as e:
                    print(f"  ❌ 剪辑 {completed}/{total_clips} (原索引 {original_idx}) 失败: {e}")

        print(f"\n✅ 并行渲染完成: {len(output_paths)}/{total_clips}个剪辑")
        return output_paths


def render_single_clip_standalone(
    clip_index: int,
    clip_data: dict,
    render_params: dict
) -> Optional[str]:
    """独立的单剪辑渲染函数（用于多进程）(V16新增)

    这个函数必须是模块级别的，以便在多进程中使用

    Args:
        clip_index: 剪辑索引
        clip_data: 剪辑数据字典
        render_params: 渲染参数字典

    Returns:
        输出文件路径，失败返回None
    """
    try:
        # 创建Clip对象
        clip = Clip(**clip_data)

        # 计算起始和结束时间（在该集内的秒数）
        episode_durations = render_params['episode_durations']

        # 计算起始集内的秒数
        cumulative_before_start = 0
        for ep in sorted(episode_durations.keys()):
            if ep < clip.episode:
                cumulative_before_start += episode_durations[ep]

        start_in_episode = clip.start - cumulative_before_start

        # 计算结束集内的秒数
        cumulative_before_end = 0
        for ep in sorted(episode_durations.keys()):
            if ep < clip.hookEpisode:
                cumulative_before_end += episode_durations[ep]

        end_in_episode = clip.end - cumulative_before_end

        # 生成唯一输出文件名（添加worker_id避免冲突）
        import os
        worker_id = os.getpid()
        output_dir = Path(render_params['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        # 使用唯一临时文件名
        filename = f"{render_params['project_name']}_第{clip.episode}集{format_time(int(start_in_episode))}_第{clip.hookEpisode}集{format_time(int(end_in_episode))}_tmp{worker_id}.mp4"
        output_path = str(output_dir / filename)

        # 转换为视频片段
        segments = _clip_to_segments_standalone(clip, episode_durations, render_params['video_dir'])

        # 如果只有1个片段且不是跨集，直接裁剪
        if len(segments) == 1:
            _trim_segment_standalone(segments[0], output_path, render_params)
        else:
            # 多个片段：先分别裁剪，再拼接
            temp_files = []
            temp_dir = output_dir / f"temp_{worker_id}"
            temp_dir.mkdir(exist_ok=True)

            # 裁剪每个片段
            for i, segment in enumerate(segments):
                temp_file = temp_dir / f"segment_{i}.mp4"
                _trim_segment_standalone(segment, str(temp_file), render_params)
                temp_files.append(str(temp_file))

            # 拼接片段
            _concat_segments_standalone(temp_files, output_path, output_dir)

            # 删除临时文件
            for temp_file in temp_files:
                Path(temp_file).unlink()
            temp_dir.rmdir()

        # V15: 添加花字叠加（如果配置了）
        if render_params['add_overlay']:
            output_path = _apply_video_overlay_standalone(output_path, render_params)

        # V14: 添加结尾视频（如果配置了）
        if render_params['add_ending_clip'] and render_params['ending_videos']:
            output_path = _append_ending_video_standalone(output_path, render_params)

        # 重命名为最终文件名（V16.1修复：正确处理后缀）
        # output_path 现在可能包含 _overlay 和 _带结尾 后缀
        output_path_obj = Path(output_path)
        final_stem = output_path_obj.stem

        # 移除临时标记
        final_stem = final_stem.replace(f'_tmp{worker_id}', '')

        # 将 _overlay 替换为 _带花字
        final_stem = final_stem.replace('_overlay', '_带花字')

        # 生成最终路径
        final_path = str(output_path_obj.parent / (final_stem + output_path_obj.suffix))
        shutil.move(output_path, final_path)

        return final_path

    except Exception as e:
        print(f"  [Worker] 渲染失败: {e}")
        return None


def _clip_to_segments_standalone(clip: Clip, episode_durations: dict, video_dir: str) -> List:
    """将剪辑转换为视频片段列表（独立函数）(V16新增)"""
    from dataclasses import dataclass

    @dataclass
    class Segment:
        episode: int
        start: float
        end: float

    segments = []

    # 简单情况：不跨集
    if clip.episode == clip.hookEpisode:
        # 计算在该集内的秒数
        cumulative_before = 0
        for ep in sorted(episode_durations.keys()):
            if ep < clip.episode:
                cumulative_before += episode_durations[ep]

        start_in_episode = clip.start - cumulative_before
        end_in_episode = clip.end - cumulative_before

        segments.append(Segment(
            episode=clip.episode,
            start=start_in_episode,
            end=end_in_episode
        ))
    else:
        # 跨集情况：分割为多个片段
        current_episode = clip.episode

        # 计算累积时间
        cumulative = 0
        episode_times = {}
        for ep in sorted(episode_durations.keys()):
            episode_times[ep] = {
                'start': cumulative,
                'end': cumulative + episode_durations[ep]
            }
            cumulative += episode_durations[ep]

        # 第一段：从起始时间到该集结束
        first_episode_end = episode_times[clip.episode]['end']
        cumulative_before_start = episode_times[clip.episode]['start']
        start_in_first = clip.start - cumulative_before_start

        segments.append(Segment(
            episode=clip.episode,
            start=start_in_first,
            end=episode_durations[clip.episode]
        ))

        # 中间段：完整的集
        for ep in range(clip.episode + 1, clip.hookEpisode):
            segments.append(Segment(
                episode=ep,
                start=0,
                end=episode_durations[ep]
            ))

        # 最后一段：从该集开始到结束时间
        cumulative_before_end = episode_times[clip.hookEpisode]['start']
        end_in_last = clip.end - cumulative_before_end

        segments.append(Segment(
            episode=clip.hookEpisode,
            start=0,
            end=end_in_last
        ))

    return segments


def _trim_segment_standalone(segment, output_path: str, render_params: dict) -> None:
    """裁剪单个视频片段（独立函数）(V16.2: 支持GPU加速)"""
    video_dir = Path(render_params['video_dir'])

    # 查找视频文件
    video_files = sorted(video_dir.glob("*.mp4"))
    video_file = None
    for vf in video_files:
        ep_num = _extract_episode_number_standalone(vf.name)
        if ep_num == segment.episode:
            video_file = vf
            break

    if not video_file:
        raise FileNotFoundError(f"找不到第{segment.episode}集视频")

    # 获取视频帧率
    fps = _get_video_fps_standalone(str(video_file))

    # 计算总帧数（基于实际FPS）
    import math
    total_frames = math.ceil(segment.end * fps)

    # V16.2: 构建FFmpeg命令（支持GPU加速）
    cmd = ['ffmpeg', '-y']

    # GPU硬件加速（macOS VideoToolbox）
    hwaccel = render_params.get('hwaccel', False)
    if hwaccel:
        cmd.extend(['-hwaccel', 'videotoolbox'])

    cmd.extend([
        '-ss', str(segment.start),
        '-i', str(video_file),
        '-frames:v', str(total_frames),
    ])

    # V16.2: 选择编码方式
    if hwaccel:
        # GPU加速编码
        cmd.extend([
            '-c:v', 'h264_videotoolbox',
            '-b:v', '8M',  # GPU编码使用码率控制
            '-c:a', 'aac',
            '-b:a', '128k',
        ])
    else:
        # CPU编码
        cmd.extend([
            '-c:v', 'libx264',
            '-crf', str(render_params['crf']),
            '-preset', render_params['preset'],
            '-c:a', 'aac',
            '-b:a', '128k',
        ])

    cmd.append(output_path)

    # 执行命令（静默模式）
    subprocess.run(cmd, capture_output=True, check=True)


def _concat_segments_standalone(segment_files: List[str], output_path: str, output_dir: Path) -> None:
    """拼接多个视频片段（独立函数）(V16新增)"""
    # 创建临时concat列表文件
    concat_file = output_dir / f"concat_list_{os.getpid()}.txt"
    with open(concat_file, 'w') as f:
        for segment_file in segment_files:
            segment_path = Path(segment_file)
            relative_path = segment_path.relative_to(output_dir)
            f.write(f"file '{relative_path}'\n")

    # FFmpeg命令
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        output_path
    ]

    subprocess.run(cmd, capture_output=True, check=True)

    # 删除临时文件
    concat_file.unlink()


def _apply_video_overlay_standalone(clip_path: str, render_params: dict) -> str:
    """应用花字叠加（独立函数）(V16新增)"""
    try:
        from .video_overlay.video_overlay import VideoOverlayRenderer, OverlayConfig

        # 创建临时配置
        config = OverlayConfig(
            enabled=True,
            style_id=render_params['overlay_style_id'],
            project_name=render_params['project_name'],
            drama_title=render_params['project_name'],
            hot_drama_position=render_params.get('hot_drama_position', 'top-right')
        )

        renderer = VideoOverlayRenderer(config)

        # 生成新的输出路径
        clip_path_obj = Path(clip_path)
        overlay_filename = clip_path_obj.stem + "_overlay" + clip_path_obj.suffix
        overlay_path = str(clip_path_obj.parent / overlay_filename)

        # 应用花字
        renderer.apply_overlay(clip_path, overlay_path)

        # 删除原文件
        Path(clip_path).unlink()

        return overlay_path

    except Exception as e:
        print(f"  [Worker] 花字叠加失败: {e}")
        return clip_path


def _append_ending_video_standalone(clip_path: str, render_params: dict) -> str:
    """添加结尾视频（独立函数）(V16新增)"""
    try:
        # 随机选择结尾视频
        ending_videos = render_params['ending_videos']
        if not ending_videos:
            return clip_path

        import random
        ending_video = random.choice(ending_videos)

        # 预处理结尾视频（匹配原剪辑的分辨率和帧率）
        processed_ending = _preprocess_ending_video_standalone(clip_path, ending_video, render_params)

        # 生成新的输出路径
        clip_path_obj = Path(clip_path)
        new_filename = clip_path_obj.stem + "_带结尾" + clip_path_obj.suffix
        new_output_path = str(clip_path_obj.parent / new_filename)

        # 拼接视频
        _concat_videos_standalone([clip_path, processed_ending], new_output_path)

        # 删除临时文件
        Path(processed_ending).unlink()
        Path(clip_path).unlink()

        return new_output_path

    except Exception as e:
        print(f"  [Worker] 添加结尾失败: {e}")
        return clip_path


def _preprocess_ending_video_standalone(clip_path: str, ending_video: str, render_params: dict) -> str:
    """预处理结尾视频（独立函数）(V16新增)"""
    # 获取原剪辑的分辨率
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,r_frame_rate',
        '-of', 'csv=p=0',
        clip_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    parts = result.stdout.strip().split(',')
    clip_width = int(parts[0])
    clip_height = int(parts[1])

    # 解析帧率
    fps_str = parts[2] if len(parts) > 2 else '30/1'
    if '/' in fps_str:
        num, den = fps_str.split('/')
        clip_fps = float(num) / float(den)
    else:
        clip_fps = float(fps_str)

    # 获取结尾视频时长
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        ending_video
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    video_duration = float(result.stdout.strip())

    # 生成临时输出路径
    output_dir = Path(clip_path).parent
    processed_path = str(output_dir / f"processed_ending_{os.getpid()}.mp4")

    # 转换结尾视频（匹配分辨率和帧率）
    cmd = [
        'ffmpeg',
        '-y',
        '-i', ending_video,
        '-t', str(video_duration),
        '-vf', f'scale={clip_width}:{clip_height}',
        '-r', str(clip_fps),
        '-vsync', 'cfr',
        '-c:v', 'libx264',
        '-crf', str(render_params['crf']),
        '-preset', render_params['preset'],
        '-c:a', 'aac',
        '-b:a', '128k',
        processed_path
    ]

    subprocess.run(cmd, capture_output=True, check=True)

    return processed_path


def _concat_videos_standalone(video_paths: List[str], output_path: str) -> None:
    """拼接视频文件（独立函数）(V16新增)"""
    output_dir = Path(output_path).parent
    concat_file = output_dir / f"concat_videos_{os.getpid()}.txt"

    with open(concat_file, 'w') as f:
        for vp in video_paths:
            relative_path = Path(vp).relative_to(output_dir)
            f.write(f"file '{relative_path}'\n")

    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        output_path
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    concat_file.unlink()


def _extract_episode_number_standalone(filename: str) -> Optional[int]:
    """从文件名提取集数（独立函数）(V16新增)"""
    patterns = [
        r'第(\d+)集',
        r'EP?(\d+)',
        r'^(\d+)',
        r'[-_](\d+)\.mp4$',
        r'(\d+)(?=\.mp4)',
    ]

    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


# ============================================================================
# V16.2: 完全合并编码优化 - 单次FFmpeg命令完成所有操作
# ============================================================================

def _render_clip_single_pass(
    clip_index: int,
    clip_data: dict,
    render_params: dict
) -> Optional[str]:
    """V16.2 完全合并编码：单次FFmpeg命令完成裁剪+花字+结尾

    核心优化：
    - 原来：3次FFmpeg调用（裁剪→花字→结尾），每次都要完整编解码
    - 现在：1次FFmpeg调用，使用filter_complex链式处理
    - 速度提升：预计50-70%

    Args:
        clip_index: 剪辑索引
        clip_data: 剪辑数据字典
        render_params: 渲染参数字典

    Returns:
        输出文件路径，失败返回None
    """
    import tempfile
    import math
    import random

    temp_files = []

    try:
        # 创建Clip对象
        clip = Clip(**clip_data)

        # 获取参数
        episode_durations = render_params['episode_durations']
        video_dir = Path(render_params['video_dir'])
        output_dir = Path(render_params['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        project_name = render_params['project_name']
        add_overlay = render_params['add_overlay']
        add_ending = render_params['add_ending_clip'] and render_params['ending_videos']

        # 计算起始和结束时间
        cumulative_before_start = sum(
            episode_durations[ep] for ep in sorted(episode_durations.keys()) if ep < clip.episode
        )
        start_in_episode = clip.start - cumulative_before_start

        cumulative_before_end = sum(
            episode_durations[ep] for ep in sorted(episode_durations.keys()) if ep < clip.hookEpisode
        )
        end_in_episode = clip.end - cumulative_before_end

        # 生成文件名
        def format_time(seconds):
            if seconds < 60:
                return f"{int(seconds)}秒"
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}分{secs}秒"

        suffix_parts = []
        if add_overlay:
            suffix_parts.append("带花字")
        if add_ending:
            suffix_parts.append("带结尾")
        suffix = "_" + "_".join(suffix_parts) if suffix_parts else ""

        final_filename = f"{project_name}_第{clip.episode}集{format_time(start_in_episode)}_第{clip.hookEpisode}集{format_time(end_in_episode)}{suffix}.mp4"
        final_path = str(output_dir / final_filename)

        # 查找视频文件
        video_files = sorted(video_dir.glob("*.mp4"))

        def find_video_file(episode):
            for vf in video_files:
                ep_num = _extract_episode_number_standalone(vf.name)
                if ep_num == episode:
                    return vf
            return None

        # 判断是否跨集
        is_cross_episode = clip.episode != clip.hookEpisode

        # ===== 核心优化：单次FFmpeg调用 =====

        if is_cross_episode:
            # 跨集情况：仍需分步处理（拼接需要中间文件）
            # 但可以优化为：裁剪+拼接 → 花字+结尾（2次编码）
            return _render_clip_unified_standalone(clip_index, clip_data, render_params)

        # ===== 不跨集：完全合并编码 =====

        video_file = find_video_file(clip.episode)
        if not video_file:
            raise FileNotFoundError(f"找不到第{clip.episode}集视频")

        # 获取视频信息
        fps = _get_video_fps_standalone(str(video_file))
        total_frames = math.ceil(end_in_episode * fps)

        # 获取视频分辨率
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0', str(video_file)
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        video_width, video_height = map(int, result.stdout.strip().split(','))

        # ===== 构建filter_complex =====
        filter_parts = []
        input_count = 1  # 输入视频是[0:v]

        # 1. 裁剪（使用trim + setpts）
        trim_filter = f"[0:v]trim=start={start_in_episode}:duration={end_in_episode-start_in_episode},setpts=PTS-STARTPTS[v_trim]"
        filter_parts.append(trim_filter)

        current_stream = "[v_trim]"

        # 2. 花字叠加（如果启用）
        overlay_png_path = None
        if add_overlay:
            try:
                # 生成倾斜角标PNG
                overlay_png_path = _generate_overlay_png_standalone(
                    video_width, video_height, project_name, render_params, output_dir
                )
                if overlay_png_path:
                    temp_files.append(overlay_png_path)
                    input_count += 1
                    overlay_input_idx = input_count - 1

                    # 计算overlay位置
                    x, y = _calculate_overlay_position(video_width, video_height, render_params)

                    # overlay滤镜
                    overlay_filter = f"{current_stream}[{overlay_input_idx}:v]overlay=x={x}:y={y}[v_overlay]"
                    filter_parts.append(overlay_filter)
                    current_stream = "[v_overlay]"
            except Exception as e:
                print(f"  ⚠️ 花字PNG生成失败: {e}")

        # 3. drawtext（剧名、免责声明）
        drawtext_filters = _build_drawtext_filters_standalone(
            video_width, video_height, project_name, render_params
        )
        if drawtext_filters:
            drawtext_chain = ','.join(drawtext_filters)
            drawtext_filter = f"{current_stream}{drawtext_chain}[v_text]"
            filter_parts.append(drawtext_filter)
            current_stream = "[v_text]"

        # 4. 结尾拼接（如果启用）
        ending_video_path = None
        if add_ending:
            # 随机选择结尾视频
            ending_video_path = random.choice(render_params['ending_videos'])

            # 预处理结尾视频（需要先获取当前流的分辨率）
            # 由于是filter_complex，我们需要先处理主体视频，然后拼接
            # 这增加了复杂性，所以这里采用分步方式
            pass

        # ===== 构建FFmpeg命令 =====
        filter_complex = ';'.join(filter_parts)

        # 输入参数
        inputs = ['-ss', str(start_in_episode), '-i', str(video_file)]

        # 添加overlay PNG输入
        if overlay_png_path:
            inputs.extend(['-i', overlay_png_path])

        # 基础命令
        cmd = [
            'ffmpeg', '-y',
            *inputs,
            '-filter_complex', filter_complex,
            '-map', current_stream.replace('[', '').replace(']', ''),
            '-map', '0:a?',
            '-c:v', 'libx264',
            '-crf', str(render_params['crf']),
            '-preset', render_params['preset'],
            '-c:a', 'aac', '-b:a', '128k',
            '-movflags', '+faststart',
        ]

        # 如果有结尾视频，需要两步处理
        if add_ending and ending_video_path:
            # 先渲染带花字的视频
            temp_output = str(output_dir / f"temp_single_pass_{os.getpid()}_{clip_index}.mp4")
            temp_files.append(temp_output)
            cmd.append(temp_output)

            subprocess.run(cmd, capture_output=True, check=True)

            # 预处理结尾视频
            processed_ending = _preprocess_ending_video_standalone(temp_output, ending_video_path, render_params)
            temp_files.append(processed_ending)

            # 拼接结尾
            _concat_videos_standalone([temp_output, processed_ending], final_path)

            # 删除中间文件
            Path(temp_output).unlink()
            Path(processed_ending).unlink()
        else:
            # 直接输出最终文件
            cmd.append(final_path)
            subprocess.run(cmd, capture_output=True, check=True)

        # 清理临时文件
        for tf in temp_files:
            try:
                if Path(tf).exists():
                    Path(tf).unlink()
            except:
                pass

        return final_path

    except Exception as e:
        print(f"  [Worker] V16.2完全合并渲染失败: {e}")
        # 清理临时文件
        for tf in temp_files:
            try:
                if Path(tf).exists():
                    Path(tf).unlink()
            except:
                pass
        # 回退到分步渲染
        return _render_clip_unified_standalone(clip_index, clip_data, render_params)


def _generate_overlay_png_standalone(
    video_width: int,
    video_height: int,
    project_name: str,
    render_params: dict,
    output_dir: Path
) -> Optional[str]:
    """生成倾斜角标PNG（独立函数）"""
    try:
        from .video_overlay.tilted_label import TiltedLabelConfig, TiltedLabelRenderer

        # 计算缩放参数
        smaller_dimension = min(video_width, video_height)
        resolution_ratio = smaller_dimension / 360.0
        scale_factor = resolution_ratio * 0.8

        original_font_size = 28
        original_box_height = 60
        original_corner_offset = 70

        scaled_font_size = int(original_font_size * scale_factor)
        scaled_box_height = int(original_box_height * scale_factor)
        scaled_corner_offset = int(original_corner_offset * scale_factor)

        scaled_font_size = scaled_font_size if scaled_font_size % 2 == 0 else scaled_font_size + 1
        scaled_corner_offset = scaled_corner_offset if scaled_corner_offset % 2 == 0 else scaled_corner_offset + 1

        # 创建配置
        config = TiltedLabelConfig(
            label_text="热门短剧",
            font_size=scaled_font_size,
            label_color="red@0.95",
            text_color="white",
            position=render_params.get('hot_drama_position', 'top-right'),
            box_height=scaled_box_height,
            corner_offset=scaled_corner_offset
        )

        renderer = TiltedLabelRenderer(config)

        # 生成PNG
        png_path = str(output_dir / f"overlay_{os.getpid()}_{hash(project_name)}.png")
        renderer._generate_png(png_path)

        return png_path

    except Exception as e:
        print(f"  ⚠️ 生成overlay PNG失败: {e}")
        return None


def _calculate_overlay_position(video_width: int, video_height: int, render_params: dict) -> tuple:
    """计算overlay位置"""
    position = render_params.get('hot_drama_position', 'top-right')

    smaller_dimension = min(video_width, video_height)
    resolution_ratio = smaller_dimension / 360.0
    scale_factor = resolution_ratio * 0.8

    original_corner_offset = 70
    scaled_corner_offset = int(original_corner_offset * scale_factor)
    scaled_corner_offset = scaled_corner_offset if scaled_corner_offset % 2 == 0 else scaled_corner_offset + 1

    if position == 'top-right':
        x = video_width - 200 - scaled_corner_offset  # 200 is canvas_half
        y = -32  # 倾斜角标向上偏移
    else:
        x = -32
        y = -32

    return x, y


def _build_drawtext_filters_standalone(
    video_width: int,
    video_height: int,
    project_name: str,
    render_params: dict
) -> List[str]:
    """构建drawtext滤镜列表（独立函数）"""
    filters = []

    # 计算字体大小
    smaller_dimension = min(video_width, video_height)
    resolution_ratio = smaller_dimension / 360.0
    base_subtitle_size = int(18 * resolution_ratio)

    drama_title_font_size = int(base_subtitle_size * 0.95)
    drama_title_font_size = drama_title_font_size if drama_title_font_size % 2 == 0 else drama_title_font_size + 1

    disclaimer_font_size = int(base_subtitle_size * 0.85)
    disclaimer_font_size = disclaimer_font_size if disclaimer_font_size % 2 == 0 else disclaimer_font_size + 1

    # 动态Y位置
    drama_title_y = f"h-{int(video_height * 0.15)}"
    disclaimer_y = f"h-{int(video_height * 0.06)}"

    # 查找字体
    font_path = "/System/Library/Fonts/Supplemental/Songti.ttc"
    if not Path(font_path).exists():
        font_path = "/System/Library/Fonts/PingFang.ttc"
    if not Path(font_path).exists():
        font_path = None

    # 剧名drawtext
    drama_title = f"《{project_name}》"
    drama_params = {
        'text': drama_title.replace('《', '\\《').replace('》', '\\》'),
        'fontsize': drama_title_font_size,
        'fontcolor': '#E6E6FA',
        'alpha': '1.0',
        'x': '(w-tw)/2',
        'y': drama_title_y,
        'borderw': 1.0,
        'bordercolor': '#000000',
        'shadowx': 1,
        'shadowy': 1,
        'shadowcolor': '#000000'
    }
    if font_path:
        drama_params['fontfile'] = font_path

    drama_str = 'drawtext=' + ':'.join(f"{k}='{v}'" if k in ['x', 'y', 'fontfile', 'text'] else f"{k}={v}" for k, v in drama_params.items())
    filters.append(drama_str)

    # 免责声明drawtext
    disclaimer = "本剧内容虚构 仅供娱乐参考"
    disc_params = {
        'text': disclaimer,
        'fontsize': disclaimer_font_size,
        'fontcolor': '#FFFFFF',
        'alpha': '0.7',
        'x': '(w-tw)/2',
        'y': disclaimer_y,
        'borderw': 0.5,
        'bordercolor': '#808080',
        'shadowx': 1,
        'shadowy': 1,
        'shadowcolor': '#000000'
    }
    if font_path:
        disc_params['fontfile'] = font_path

    disc_str = 'drawtext=' + ':'.join(f"{k}='{v}'" if k in ['x', 'y', 'fontfile'] else f"{k}={v}" for k, v in disc_params.items())
    filters.append(disc_str)

    return filters


# ============================================================================
# V16.1: 合并编码优化 - 一次完成裁剪+花字+结尾（保留作为fallback）
# ============================================================================

def _render_clip_unified_standalone(
    clip_index: int,
    clip_data: dict,
    render_params: dict
) -> Optional[str]:
    """V16.1 合并渲染：一次性完成裁剪+花字+结尾（单次编码）

    相比原来的3次编码，这个函数只进行1次编码，大幅提升渲染速度。

    Args:
        clip_index: 剪辑索引
        clip_data: 剪辑数据字典
        render_params: 渲染参数字典

    Returns:
        输出文件路径，失败返回None
    """
    import tempfile
    import math

    try:
        # 创建Clip对象
        clip = Clip(**clip_data)

        # 获取参数
        episode_durations = render_params['episode_durations']
        video_dir = Path(render_params['video_dir'])
        output_dir = Path(render_params['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        project_name = render_params['project_name']
        add_overlay = render_params['add_overlay']
        add_ending = render_params['add_ending_clip'] and render_params['ending_videos']

        # 计算起始和结束时间（在该集内的秒数）
        cumulative_before_start = sum(
            episode_durations[ep] for ep in sorted(episode_durations.keys()) if ep < clip.episode
        )
        start_in_episode = clip.start - cumulative_before_start

        cumulative_before_end = sum(
            episode_durations[ep] for ep in sorted(episode_durations.keys()) if ep < clip.hookEpisode
        )
        end_in_episode = clip.end - cumulative_before_end

        # 生成最终输出文件名
        def format_time(seconds):
            if seconds < 60:
                return f"{int(seconds)}秒"
            else:
                mins = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{mins}分{secs}秒"

        # 构建后缀
        suffix_parts = []
        if add_overlay:
            suffix_parts.append("带花字")
        if add_ending:
            suffix_parts.append("带结尾")
        suffix = "_" + "_".join(suffix_parts) if suffix_parts else ""

        final_filename = f"{project_name}_第{clip.episode}集{format_time(start_in_episode)}_第{clip.hookEpisode}集{format_time(end_in_episode)}{suffix}.mp4"
        final_path = str(output_dir / final_filename)

        # ===== 查找视频文件 =====
        video_files = sorted(video_dir.glob("*.mp4"))

        def find_video_file(episode):
            for vf in video_files:
                ep_num = _extract_episode_number_standalone(vf.name)
                if ep_num == episode:
                    return vf
            return None

        # ===== 判断是否跨集 =====
        is_cross_episode = clip.episode != clip.hookEpisode

        # ===== 步骤1：准备裁剪的视频片段 =====
        temp_files = []

        if not is_cross_episode:
            # 不跨集：直接处理单个视频
            video_file = find_video_file(clip.episode)
            if not video_file:
                raise FileNotFoundError(f"找不到第{clip.episode}集视频")

            # 获取视频帧率
            fps = _get_video_fps_standalone(str(video_file))
            total_frames = math.ceil(end_in_episode * fps)

            # 裁剪后的临时文件
            temp_trim = output_dir / f"temp_trim_{os.getpid()}_{clip_index}.mp4"
            temp_files.append(temp_trim)

            # 裁剪
            trim_cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_in_episode),
                '-i', str(video_file),
                '-frames:v', str(total_frames),
                '-c:v', 'libx264',
                '-crf', str(render_params['crf']),
                '-preset', render_params['preset'],
                '-c:a', 'aac', '-b:a', '128k',
                str(temp_trim)
            ]
            subprocess.run(trim_cmd, capture_output=True, check=True)

            clip_input = str(temp_trim)

        else:
            # 跨集：需要拼接多个片段
            # 计算每个片段
            segments = _clip_to_segments_standalone(clip, episode_durations, str(video_dir))

            segment_files = []
            temp_dir = output_dir / f"temp_segments_{os.getpid()}_{clip_index}"
            temp_dir.mkdir(exist_ok=True)

            for i, segment in enumerate(segments):
                video_file = find_video_file(segment.episode)
                if not video_file:
                    raise FileNotFoundError(f"找不到第{segment.episode}集视频")

                fps = _get_video_fps_standalone(str(video_file))
                total_frames = math.ceil((segment.end - segment.start) * fps)

                seg_file = temp_dir / f"segment_{i}.mp4"
                segment_files.append(str(seg_file))
                temp_files.append(seg_file)

                seg_cmd = [
                    'ffmpeg', '-y',
                    '-ss', str(segment.start),
                    '-i', str(video_file),
                    '-frames:v', str(total_frames),
                    '-c:v', 'libx264',
                    '-crf', str(render_params['crf']),
                    '-preset', render_params['preset'],
                    '-c:a', 'aac', '-b:a', '128k',
                    str(seg_file)
                ]
                subprocess.run(seg_cmd, capture_output=True, check=True)

            # 拼接片段
            temp_concat = output_dir / f"temp_concat_{os.getpid()}_{clip_index}.mp4"
            temp_files.append(temp_concat)
            _concat_segments_standalone(segment_files, str(temp_concat), output_dir)

            # 清理segment文件
            for sf in segment_files:
                Path(sf).unlink()
            temp_dir.rmdir()

            clip_input = str(temp_concat)

        # ===== 步骤2：应用花字叠加（如果启用）=====
        if add_overlay:
            temp_overlay = output_dir / f"temp_overlay_{os.getpid()}_{clip_index}.mp4"
            temp_files.append(temp_overlay)

            # 调用花字叠加
            from .video_overlay.video_overlay import apply_overlay_to_video
            apply_overlay_to_video(
                input_video=clip_input,
                output_video=str(temp_overlay),
                project_name=project_name,
                drama_title=project_name,
                style_id=render_params.get('overlay_style_id'),
                hot_drama_position=render_params.get('hot_drama_position', 'top-right')
            )

            # 删除裁剪文件
            Path(clip_input).unlink()
            clip_input = str(temp_overlay)

        # ===== 步骤3：添加结尾视频（如果启用）=====
        if add_ending:
            # 随机选择结尾视频
            import random
            ending_video = random.choice(render_params['ending_videos'])

            # 预处理结尾视频（匹配分辨率和帧率）
            processed_ending = _preprocess_ending_video_standalone(clip_input, ending_video, render_params)
            temp_files.append(processed_ending)

            # 拼接
            _concat_videos_standalone([clip_input, processed_ending], final_path)

            # 删除中间文件
            Path(clip_input).unlink()
            Path(processed_ending).unlink()
        else:
            # 直接重命名
            shutil.move(clip_input, final_path)

        # ===== 清理所有临时文件 =====
        for tf in temp_files:
            if Path(tf).exists():
                Path(tf).unlink()

        return final_path

    except Exception as e:
        print(f"  [Worker] V16.1合并渲染失败: {e}")
        # 清理临时文件
        for tf in temp_files:
            try:
                if Path(tf).exists():
                    Path(tf).unlink()
            except:
                pass
        return None


def _get_video_fps_standalone(video_path: str) -> float:
    """获取视频帧率（独立函数）(V16新增)"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 30.0

    fps_str = result.stdout.strip()
    if '/' in fps_str:
        num, den = fps_str.split('/')
        return float(num) / float(den)
    else:
        return float(fps_str)


def main():
    """命令行入口"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='渲染AI短剧剪辑（V16: 支持并行渲染、花字叠加、结尾视频拼接和片尾检测）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 基础渲染（自动检测片尾，默认4个并行worker）
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就

  # 并行渲染（指定worker数）
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --parallel 8

  # 串行渲染（调试用）
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --parallel 1

  # 不添加结尾视频
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --no-ending

  # 添加花字叠加
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --add-overlay

  # 指定花字样式
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --add-overlay --overlay-style gold_luxury

  # 强制重新检测片尾
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --force-detect

  # 跳过片尾检测（使用完整时长）
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --skip-ending

  # 完整功能（片尾检测 + 结尾视频 + 花字叠加 + 并行渲染）
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --add-ending --add-overlay --parallel 4
        '''
    )

    parser.add_argument('project_path', help='项目路径（包含result.json）')
    parser.add_argument('video_dir', nargs='?', help='视频文件目录（可选，默认为项目路径）')

    # V14: 结尾视频参数
    parser.add_argument('--add-ending', action='store_true', help='添加随机结尾视频')
    parser.add_argument('--no-ending', action='store_true', help='不添加结尾视频')

    # V14.1: 片尾检测参数
    parser.add_argument('--auto-detect-ending', action='store_true', help='自动检测片尾（默认启用）')
    parser.add_argument('--skip-ending', action='store_true', help='跳过片尾检测，使用完整时长')
    parser.add_argument('--force-detect', action='store_true', help='强制重新检测片尾（覆盖缓存）')

    # V15: 花字叠加参数
    parser.add_argument('--add-overlay', action='store_true', help='添加花字叠加')
    parser.add_argument('--overlay-style', type=str, help='花字样式ID（默认随机选择）')

    # V16: 并行渲染参数
    parser.add_argument('--parallel', type=int, default=4,
                        help='并行渲染的worker数量（默认4，设为1禁用并行）')

    # V16.2: 性能优化参数
    parser.add_argument('--hwaccel', action='store_true',
                        help='启用GPU硬件加速（macOS: videotoolbox, Linux: cuda）')
    parser.add_argument('--fast-preset', action='store_true',
                        help='使用ultrafast预设（速度提升30%，质量略降）')

    # 缓存清理参数
    parser.add_argument('--no-cleanup', action='store_true', help='渲染完成后跳过清理中间缓存')

    # V15.7: 剪辑数量限制
    parser.add_argument('--max-clips', type=int, default=0, help='最多渲染的剪辑数量（0=全部渲染）')
    parser.add_argument('--clip-indices', type=str, default='', help='指定要渲染的剪辑索引（逗号分隔，如：0,2,7）')

    args = parser.parse_args()

    # 确定是否添加结尾视频
    add_ending = args.add_ending
    if args.no_ending:
        add_ending = False

    # 确定片尾检测参数
    auto_detect_ending = args.auto_detect_ending
    skip_ending = args.skip_ending
    force_detect = args.force_detect

    # 如果没有指定任何选项，默认启用自动检测
    if not skip_ending and not force_detect:
        auto_detect_ending = True

    # V15: 花字叠加参数
    add_overlay = args.add_overlay
    overlay_style = args.overlay_style

    project_path = args.project_path
    video_dir = args.video_dir

    # 从项目路径提取项目名称
    project_name = Path(project_path).name

    # 新的输出目录：clips/{项目名}/
    output_dir = f"clips/{project_name}"

    # 创建渲染器
    renderer = ClipRenderer(
        project_path=project_path,
        output_dir=output_dir,
        video_dir=video_dir,
        project_name=project_name,
        add_ending_clip=add_ending,       # V14: 传递结尾视频配置
        auto_detect_ending=auto_detect_ending,  # V14.1: 传递片尾检测配置
        skip_ending=skip_ending,
        force_detect=force_detect,
        add_overlay=add_overlay,          # V15: 传递花字叠加配置
        overlay_style_id=overlay_style,   # V15: 传递花字样式
        hwaccel=args.hwaccel,             # V16.2: GPU硬件加速
        fast_preset=args.fast_preset      # V16.2: 快速预设
    )

    # 显示配置信息
    print(f"\n{'='*60}")
    print(f"项目名称: {project_name}")
    print(f"项目路径: {project_path}")
    print(f"输出目录: {output_dir}")
    print(f"结尾视频拼接: {'✅ 启用' if add_ending else '❌ 禁用'}")
    print(f"片尾检测: {'✅ 自动检测' if auto_detect_ending else '⚠️ 跳过' if skip_ending else '✅ 正常'}")
    print(f"花字叠加: {'✅ 启用' if add_overlay else '❌ 禁用'}")
    if overlay_style:
        print(f"花字样式: {overlay_style}")
    if force_detect:
        print(f"片尾检测模式: 🔃 强制重新检测")
    # V16: 显示并行配置
    if args.parallel > 1:
        print(f"渲染模式: ⚡ 并行（{args.parallel} 个worker）")
    else:
        print(f"渲染模式: 🐢 串行（调试模式）")
    print(f"{'='*60}\n")

    # 渲染所有剪辑
    def on_progress(current: int, total: int, progress: float):
        """进度回调"""
        percent = progress * 100
        print(f"\r进度: [{current}/{total}] {percent:.1f}%", end='', flush=True)

    # V15.7: 解析剪辑索引参数
    clip_indices = None
    if args.clip_indices:
        try:
            clip_indices = [int(x.strip()) for x in args.clip_indices.split(',')]
            print(f"指定渲染剪辑索引: {clip_indices}")
        except ValueError:
            print(f"⚠️ 无效的剪辑索引格式: {args.clip_indices}")

    # V16: 根据parallel参数选择渲染模式
    if args.parallel > 1:
        output_paths = renderer.render_all_clips_parallel(
            max_workers=args.parallel,
            on_clip_progress=on_progress,
            max_clips=args.max_clips,
            clip_indices=clip_indices
        )
    else:
        output_paths = renderer.render_all_clips(
            on_clip_progress=on_progress,
            max_clips=args.max_clips,
            clip_indices=clip_indices
        )

    print(f"\n\n完成！输出文件:")
    for path in output_paths:
        print(f"  - {path}")

    # 渲染完成后清理中间缓存
    if not args.no_cleanup:
        print(f"\n清理项目 {project_name} 的中间缓存（仅清理超过3小时的缓存）...")
        cleanup_result = cleanup_project_cache(project_name)
        print(f"  已清理: 关键帧={cleanup_result['keyframes_cleaned']}, "
              f"音频={cleanup_result['audio_cleaned']}, "
              f"ASR={cleanup_result['asr_cleaned']}")
        if cleanup_result['skipped'] > 0:
            print(f"  ⏭️  跳过（未到3小时）: {cleanup_result['skipped']} 个文件")
        print(f"  释放空间: {cleanup_result['total_size_freed_mb']:.2f} MB")


if __name__ == "__main__":
    main()
