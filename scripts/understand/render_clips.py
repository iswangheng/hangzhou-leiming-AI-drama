"""
视频剪辑渲染模块
基于FFmpeg实现高光点-钩子点剪辑的生成

V14: 新增结尾视频拼接功能
"""
import os
import json
import subprocess
import random
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import re


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


@dataclass
class ClipSegment:
    """剪辑片段"""
    episode: int
    start: float      # 开始秒（在该集内）V13: 支持毫秒精度
    end: float        # 结束秒（在该集内）V13: 支持毫秒精度
    video_path: str


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
        add_ending_clip: bool = False
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

        # V14: 结尾视频配置
        self.add_ending_clip = add_ending_clip
        self.ending_videos = self._load_ending_videos() if add_ending_clip else []

        # 加载结果
        self.result = self._load_result()
        self.episode_durations = self._calculate_episode_durations()
        self.video_files = self._discover_video_files()

    def _load_result(self) -> dict:
        """加载result.json"""
        result_path = self.project_path / "result.json"
        if not result_path.exists():
            raise FileNotFoundError(f"找不到结果文件: {result_path}")

        with open(result_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _calculate_episode_durations(self) -> Dict[int, int]:
        """计算各集时长

        从clips中推断各集时长
        """
        durations = {}

        # 从highlights和hooks中收集所有集数
        episodes = set()
        for h in self.result.get('highlights', []):
            episodes.add(h['episode'])
        for h in self.result.get('hooks', []):
            episodes.add(h['episode'])

        # 临时方案：使用ffprobe获取实际时长
        for ep in sorted(episodes):
            video_path = self._find_video_file(ep)
            if video_path:
                duration = self._get_video_duration(video_path)
                durations[ep] = int(duration)

        return durations

    def _discover_video_files(self) -> Dict[int, VideoFile]:
        """发现所有视频文件"""
        video_files = {}

        for ep in self.episode_durations.keys():
            video_path = self._find_video_file(ep)
            if video_path:
                video_files[ep] = VideoFile(
                    episode=ep,
                    path=str(video_path),
                    duration=self.episode_durations[ep]
                )

        return video_files

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

        Args:
            segment: 视频片段
            output_path: 输出文件路径
            on_progress: 进度回调函数（0.0-1.0）
        """
        # V13: 支持毫秒精度（浮点数时间戳）
        start_time = segment.start if isinstance(segment.start, float) else float(segment.start)
        duration = segment.end - segment.start

        # FFmpeg命令（V13.1优化：使用流复制，保持原质量）
        # 使用 -c copy 直接复制流，不重新编码，保持原视频质量和大小
        cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-ss', f"{start_time:.3f}",  # V13: 毫秒精度开始时间
            '-i', segment.video_path,  # 输入文件
            '-t', f"{duration:.3f}",  # V13: 毫秒精度持续时间
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

        # 生成临时文件路径
        temp_ending = self.output_dir / f"temp_ending_{Path(ending_video).stem}.mp4"

        # FFmpeg命令：转换分辨率和编码
        cmd = [
            'ffmpeg',
            '-y',
            '-i', ending_video,
            '-vf', f'scale={clip_width}:{clip_height}:force_original_aspect_ratio=decrease,pad={clip_width}:{clip_height}:(ow-iw)/2:(oh-ih)/2',  # 缩放并添加黑边
            '-c:v', 'libx264',  # 统一使用h264编码
            '-preset', self.preset,
            '-crf', str(self.crf),
            '-c:a', 'aac',  # 统一音频编码
            '-b:a', '128k',
            '-movflags', '+faststart',
            str(temp_ending)
        ]

        # 执行命令
        try:
            print(f"  🔄 预处理结尾视频（{clip_width}x{clip_height}）...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            # 等待完成
            process.wait()

            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg预处理失败 (返回码: {process.returncode})")

            print(f"  ✅ 结尾视频预处理完成")

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

        # FFmpeg命令 - 使用 concat demuxer 快速拼接
        cmd = [
            'ffmpeg',
            '-y',
            '-f', 'concat',  # concat demuxer
            '-safe', '0',  # 允许任意文件路径
            '-i', str(concat_file),  # 输入列表文件
            '-c', 'copy',  # 复制流，不重编码（因为已经预处理为相同格式）
            '-movflags', '+faststart',  # 优化Web播放
            output_path
        ]

        # 执行命令
        try:
            print(f"  🔄 拼接视频...")

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

        # V14: 添加结尾视频（如果配置了）
        if self.add_ending_clip:
            output_path = self._append_ending_video(output_path)

        print(f"  ✅ 输出: {output_path}")
        return output_path

    def render_all_clips(
        self,
        on_clip_progress: Optional[Callable[[int, int, float], None]] = None
    ) -> List[str]:
        """渲染所有剪辑

        Args:
            on_clip_progress: 进度回调函数(current, total, progress)

        Returns:
            输出文件路径列表
        """
        clips_data = self.result.get('clips', [])
        total_clips = len(clips_data)

        print(f"\n开始渲染 {total_clips} 个剪辑...")
        print(f"输出目录: {self.output_dir}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        output_paths = []

        for idx, clip_data in enumerate(clips_data, 1):
            clip = Clip(**clip_data)

            # V13.1: 修复progress变量未定义的bug
            last_progress = [0.0]  # 使用列表来在闭包中存储进度

            def clip_progress(progress: float):
                last_progress[0] = progress  # 更新进度值
                if on_clip_progress:
                    on_clip_progress(idx, total_clips, progress)

            try:
                output_path = self.render_clip(clip, on_progress=clip_progress)
                output_paths.append(output_path)

                # 总体进度 (V13.1: 修复progress变量作用域问题)
                if on_clip_progress:
                    overall_progress = (idx - 1 + last_progress[0]) / total_clips
                    on_clip_progress(idx, total_clips, overall_progress)

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
        description='渲染AI短剧剪辑（V14: 支持结尾视频拼接）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 基础渲染（不加结尾）
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就

  # 添加结尾视频
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --add-ending

  # 不添加结尾视频（显式指定）
  python -m scripts.understand.render_clips data/hangzhou-leiming/analysis/百里将就 漫剧素材/百里将就 --no-ending
        '''
    )

    parser.add_argument('project_path', help='项目路径（包含result.json）')
    parser.add_argument('video_dir', nargs='?', help='视频文件目录（可选，默认为项目路径）')
    parser.add_argument('--add-ending', action='store_true', help='添加随机结尾视频')
    parser.add_argument('--no-ending', action='store_true', help='不添加结尾视频')

    args = parser.parse_args()

    # 确定是否添加结尾
    add_ending = args.add_ending
    if args.no_ending:
        add_ending = False

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
        add_ending_clip=add_ending  # V14: 传递结尾视频配置
    )

    # 显示配置信息
    print(f"\n{'='*60}")
    print(f"项目名称: {project_name}")
    print(f"项目路径: {project_path}")
    print(f"输出目录: {output_dir}")
    print(f"结尾视频: {'✅ 启用' if add_ending else '❌ 禁用'}")
    print(f"{'='*60}\n")

    # 渲染所有剪辑
    def on_progress(current: int, total: int, progress: float):
        """进度回调"""
        percent = progress * 100
        print(f"\r进度: [{current}/{total}] {percent:.1f}%", end='', flush=True)

    output_paths = renderer.render_all_clips(on_clip_progress=on_progress)

    print(f"\n\n完成！输出文件:")
    for path in output_paths:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
