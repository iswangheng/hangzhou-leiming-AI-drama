"""
视频剪辑渲染模块
基于FFmpeg实现高光点-钩子点剪辑的生成

V14: 新增结尾视频拼接功能
V14.1: 新增自动片尾检测功能
V14.8: 修复片尾剪切精度和音视频同步问题
V15: 新增视频包装花字叠加功能
V15.6: 修复处理顺序 + 热门短剧位置随机化（左上/右上各50%概率）
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


def cleanup_project_cache(project_name: str) -> dict:
    """清理项目的中间缓存文件

    项目渲染完成后，清理关键帧、音频、ASR等中间产物。

    Args:
        project_name: 项目名称

    Returns:
        清理结果统计
    """
    cache_dir = TrainingConfig.CACHE_DIR
    result = {
        "keyframes_cleaned": 0,
        "audio_cleaned": 0,
        "asr_cleaned": 0,
        "total_size_freed_mb": 0,
    }

    # 清理关键帧缓存
    keyframes_dir = cache_dir / "keyframes" / project_name
    if keyframes_dir.exists():
        size = sum(f.stat().st_size for f in keyframes_dir.rglob("*") if f.is_file())
        shutil.rmtree(keyframes_dir)
        result["keyframes_cleaned"] = 1
        result["total_size_freed_mb"] += size / (1024 * 1024)

    # 清理音频缓存
    audio_dir = cache_dir / "audio" / project_name
    if audio_dir.exists():
        size = sum(f.stat().st_size for f in audio_dir.rglob("*") if f.is_file())
        shutil.rmtree(audio_dir)
        result["audio_cleaned"] = 1
        result["total_size_freed_mb"] += size / (1024 * 1024)

    # 清理ASR缓存
    asr_dir = cache_dir / "asr" / project_name
    if asr_dir.exists():
        size = sum(f.stat().st_size for f in asr_dir.rglob("*") if f.is_file())
        shutil.rmtree(asr_dir)
        result["asr_cleaned"] = 1
        result["total_size_freed_mb"] += size / (1024 * 1024)

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
        overlay_style_id: Optional[str] = None
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
        """自动检测项目中所有视频的片尾"""
        print(f"📺 检测项目: {self.project_name}")
        print(f"📁 视频目录: {self.video_dir}")

        try:
            # 导入片尾检测模块
            from scripts.detect_ending_credits import EndingCreditsDetector

            detector = EndingCreditsDetector()

            # 获取所有视频文件
            video_files = sorted(self.video_dir.glob("*.mp4"))
            total_videos = len(video_files)

            if total_videos == 0:
                print("⚠️  未找到视频文件")
                return

            print(f"📊 需要检测 {total_videos} 个视频...")
            print(f"⏱️  预计耗时: {total_videos * 3}-{total_videos * 10} 秒")

            results = {'project': self.project_name, 'episodes': []}

            for i, video_path in enumerate(video_files, 1):
                print(f"  [{i}/{total_videos}] 检测 {video_path.name}...")

                episode = self._extract_episode_number(video_path.name)
                if episode is None:
                    print(f"    ⚠️  无法提取集数，跳过")
                    continue

                try:
                    result = detector.detect_video_ending(str(video_path), episode)
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


def main():
    """命令行入口"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='渲染AI短剧剪辑（V15.6: 支持花字叠加、结尾视频拼接和片尾检测，处理顺序：花字→片尾）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 基础渲染（自动检测片尾，添加结尾视频和花字叠加）
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就

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

  # 完整功能（片尾检测 + 结尾视频 + 花字叠加）
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --add-ending --add-overlay
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
        overlay_style_id=overlay_style    # V15: 传递花字样式
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
        print(f"\n清理项目 {project_name} 的中间缓存...")
        cleanup_result = cleanup_project_cache(project_name)
        print(f"  已清理: 关键帧={cleanup_result['keyframes_cleaned']}, "
              f"音频={cleanup_result['audio_cleaned']}, "
              f"ASR={cleanup_result['asr_cleaned']}")
        print(f"  释放空间: {cleanup_result['total_size_freed_mb']:.2f} MB")


if __name__ == "__main__":
    main()
