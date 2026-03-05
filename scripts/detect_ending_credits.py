"""
片尾结束帧智能检测模块

用于自动识别和标记每集视频的片尾结束帧时长
支持视觉（画面）+ 听觉（音频）综合分析

使用场景：
1. 预处理阶段：批量检测所有视频的片尾
2. 渲染阶段：自动跳过片尾，保证剪辑连贯性

双层防护架构：
- 第一层：项目级配置（快速开关）
- 第二层：智能检测算法（画面相似度）

作者：V14
创建时间：2026-03-04
更新时间：2026-03-04（添加项目配置支持）
"""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib

# 导入项目配置模块
try:
    from scripts.ending_credits_config import load_project_config, should_detect_ending
except ImportError:
    # 如果导入失败，提供降级方案
    def load_project_config(project_name):
        return {"has_ending_credits": True}

    def should_detect_ending(project_name):
        return True

# 导入ASR分析模块
try:
    from scripts.asr_transcriber import ASRTranscriber
    from scripts.asr_analyzer import ASRContentAnalyzer
    ASR_AVAILABLE = True
except ImportError:
    ASR_AVAILABLE = False
    print("⚠️  ASR模块未安装，将跳过ASR增强检测")


# ========== 数据结构 ==========

@dataclass
class EndingCreditsInfo:
    """片尾信息"""
    has_ending: bool          # 是否有片尾
    duration: float           # 片尾时长（秒）
    confidence: float         # 置信度 (0-1)
    method: str              # 主要检测方法
    features: Dict           # 检测到的特征详情

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VideoEndingResult:
    """单集视频的片尾检测结果"""
    video_path: str           # 视频路径
    episode: int              # 集数
    total_duration: float     # 总时长（秒）
    ending_info: EndingCreditsInfo  # 片尾信息
    effective_duration: float # 有效时长（总时长 - 片尾时长）

    def to_dict(self) -> dict:
        return {
            'video_path': self.video_path,
            'episode': self.episode,
            'total_duration': self.total_duration,
            'ending_info': self.ending_info.to_dict(),
            'effective_duration': self.effective_duration
        }


@dataclass
class ProjectEndingResult:
    """项目的片尾检测结果"""
    project_name: str                    # 项目名称
    project_path: str                    # 项目路径
    episodes: List[VideoEndingResult]    # 各集检测结果
    summary: Dict                         # 汇总信息

    def to_dict(self) -> dict:
        return {
            'project_name': self.project_name,
            'project_path': self.project_path,
            'episodes': [ep.to_dict() for ep in self.episodes],
            'summary': self.summary
        }

    def save_to_file(self, output_path: str):
        """保存结果到JSON文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"✅ 结果已保存到: {output_path}")


# ========== 核心检测功能 ==========

class EndingCreditsDetector:
    """片尾结束帧检测器"""

    def __init__(self, cache_dir: Optional[str] = None):
        """
        初始化检测器

        Args:
            cache_dir: 缓存目录（用于存储临时帧文件）
        """
        if cache_dir is None:
            cache_dir = "/tmp/ending_detection_cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 配置参数
        self.CHECK_LAST_SECONDS = 3.5         # 只分析最后3.5秒
        self.SIMILARITY_THRESHOLD = 0.92      # 相似度阈值
        self.MIN_CONTINUOUS_FRAMES = 5        # 最小连续高相似度帧数（0.1秒 @ 50fps）
        self.SAFE_MARGIN = 0.1                # 安全边界（秒），避免剪太多
        self.BRIGHTNESS_THRESHOLD = 0.3       # 亮度阈值（黑屏判定）
        self.MIN_ENDING_DURATION = 0.2        # 最小片尾时长（秒）

    def detect_video_ending(
        self,
        video_path: str,
        episode: int,
        asr_segments: Optional[List] = None
    ) -> VideoEndingResult:
        """
        检测单个视频的片尾

        Args:
            video_path: 视频文件路径
            episode: 集数编号
            asr_segments: ASR数据（可选，用于对白密度分析）

        Returns:
            VideoEndingResult
        """
        print(f"\n{'=' * 70}")
        print(f"🔍 检测第{episode}集片尾")
        print(f"{'=' * 70}")
        print(f"视频: {os.path.basename(video_path)}")

        # 1. 获取视频总时长
        total_duration = self._get_video_duration(video_path)
        print(f"总时长: {total_duration:.1f}秒")

        # 1.5. 【第一层防护】检查项目配置
        # 从视频路径提取项目名称
        project_name = self._extract_project_name(video_path)

        # 检查项目配置
        if not should_detect_ending(project_name):
            config = load_project_config(project_name)
            print(f"\n[项目配置] 该项目配置为无需检测片尾")
            print(f"  原因: {config.get('notes', '项目配置为无片尾')}")
            print(f"  有效时长: {total_duration:.2f}秒（使用总时长）")

            return VideoEndingResult(
                video_path=video_path,
                episode=episode,
                total_duration=total_duration,
                ending_info=EndingCreditsInfo(
                    has_ending=False,
                    duration=0.0,
                    confidence=1.0,
                    method="project_config",
                    features={
                        "reason": "项目配置为无片尾",
                        "config": config
                    }
                ),
                effective_duration=total_duration
            )

        print(f"\n[项目配置] 该项目需要检测片尾，运行智能检测算法")

        # 2. 【第二层防护】ASR增强检测
        asr_analysis = None
        if ASR_AVAILABLE:
            print(f"\n[第二层防护] ASR增强检测...")
            asr_analysis = self._asr_enhanced_detection(video_path, total_duration)
        else:
            print(f"\n[第二层防护] ASR模块未安装，使用传统检测算法")

        # 3. 综合检测
        features_found = []
        durations = []

        # 方法1: 画面相似度检测
        print(f"\n[方法1/4] 画面相似度检测（慢动作）...")
        sim_duration, sim_conf = self._detect_by_similarity(video_path, total_duration)
        if sim_duration > self.MIN_ENDING_DURATION:
            print(f"  ✅ 检测到慢动作片尾: {sim_duration:.1f}秒 (置信度: {sim_conf:.0%})")
            durations.append(('similarity', sim_duration, sim_conf, '慢动作'))
            features_found.append('慢动作')
        else:
            print(f"  ❌ 未检测到明显的慢动作片尾")

        # 方法2: 画面亮度/渐变检测
        print(f"\n[方法2/4] 画面亮度/渐变检测（黑屏/淡出）...")
        bright_duration, bright_conf = self._detect_by_brightness(video_path, total_duration)
        if bright_duration > self.MIN_ENDING_DURATION:
            print(f"  ✅ 检测到渐变/黑屏片尾: {bright_duration:.1f}秒 (置信度: {bright_conf:.0%})")
            durations.append(('brightness', bright_duration, bright_conf, '渐变/黑屏'))
            features_found.append('渐变/黑屏')
        else:
            print(f"  ❌ 未检测到明显的渐变/黑屏")

        # 方法3: 音频特征分析
        print(f"\n[方法3/4] 音频特征分析（背景音乐）...")
        audio_result = self._detect_by_audio(video_path, total_duration)
        if audio_result['has_music']:
            audio_duration = audio_result['duration']
            audio_conf = audio_result['confidence']
            print(f"  ✅ 检测到背景音乐片尾: {audio_duration:.1f}秒 (置信度: {audio_conf:.0%})")
            durations.append(('audio', audio_duration, audio_conf, '背景音乐'))
            features_found.append('背景音乐')
        else:
            print(f"  ❌ 未检测到明显的背景音乐特征")

        # 方法4: ASR对白密度分析
        if asr_segments:
            print(f"\n[方法4/4] ASR对白密度分析（无对白）...")
            asr_duration, asr_conf = self._detect_by_asr_density(asr_segments, total_duration)
            if asr_duration > self.MIN_ENDING_DURATION:
                print(f"  ✅ 检测到对白缺失片尾: {asr_duration:.1f}秒 (置信度: {asr_conf:.0%})")
                durations.append(('asr', asr_duration, asr_conf, '无对白'))
                features_found.append('无对白')
            else:
                print(f"  ❌ 对白密度正常")
        else:
            print(f"\n[方法4/4] ASR对白密度分析...（无ASR数据，跳过）")

        # 3. 综合判断（应用ASR修正）
        print(f"\n{'=' * 70}")
        print(f"📊 检测结果汇总")
        print(f"{'=' * 70}")

        if not durations:
            # 所有传统检测方法都失败，检查ASR增强检测结果
            if asr_analysis and asr_analysis.get('has_speech', False):
                # 有ASR内容，检查ASR分析的判断
                asr_has_ending = asr_analysis.get('has_ending', False)
                if asr_has_ending:
                    # ASR分析认为这是片尾
                    print(f"✅ 传统检测方法未检测到，但ASR分析认为有片尾")
                    print(f"  ASR文本: \"{asr_analysis.get('full_text', '')[:30]}...\"")
                    print(f"  原因: {asr_analysis.get('reason', 'N/A')}")

                    # 计算片尾时长
                    if asr_analysis.get('is_ending_narration'):
                        # 片尾旁白 → 使用ASR结束时间
                        ending_start = asr_analysis.get('last_asr_end', 0)
                        ending_duration = total_duration - ending_start
                    else:
                        # 短ASR声效 → 使用默认时长
                        ending_duration = 2.0

                    ending_info = EndingCreditsInfo(
                        has_ending=True,
                        duration=ending_duration,
                        confidence=0.90,
                        method='asr_only',
                        features={
                            'methods_used': [],
                            'features_found': ['ASR验证'],
                            'asr_analysis': asr_analysis
                        }
                    )
                else:
                    # ASR分析认为不是片尾
                    print(f"❌ 传统检测方法未检测到，ASR分析也认为无片尾")
                    ending_info = EndingCreditsInfo(
                        has_ending=False,
                        duration=0.0,
                        confidence=0.0,
                        method='none',
                        features={'methods_used': [], 'features_found': [], 'asr_analysis': asr_analysis}
                    )
            else:
                # 无ASR内容或ASR分析失败
                print(f"❌ 未检测到明显的片尾特征")
                ending_info = EndingCreditsInfo(
                    has_ending=False,
                    duration=0.0,
                    confidence=0.0,
                    method='none',
                    features={'methods_used': [], 'features_found': []}
                )
        else:
            # 选择最可靠的检测结果
            # 优先级: similarity > brightness > audio > asr
            priority = {'similarity': 4, 'brightness': 3, 'audio': 2, 'asr': 1}

            best_method, best_duration, best_conf, best_feature = max(
                durations,
                key=lambda x: (priority.get(x[0], 0), x[2])
            )

            # 【关键】应用ASR修正逻辑
            similarity_duration = sim_duration if 'similarity' in [d[0] for d in durations] else 0.0
            similarity_conf = sim_conf if 'similarity' in [d[0] for d in durations] else 0.0

            has_ending, final_duration, final_conf, final_method = self._apply_asr_correction(
                similarity_result=(similarity_duration, similarity_conf),
                asr_analysis=asr_analysis,
                total_duration=total_duration
            )

            # 计算综合置信度
            if has_ending:
                confidence = min(0.98, final_conf)
                print(f"检测方法: {final_method}")
                if asr_analysis:
                    print(f"ASR修正: 已应用ASR增强检测")
                    print(f"修正原因: {asr_analysis.get('reason', 'N/A')}")
                print(f"检测特征: {', '.join(features_found)}")
                print(f"片尾时长: {final_duration:.2f}秒")
                print(f"综合置信度: {confidence:.1%}")

                ending_info = EndingCreditsInfo(
                    has_ending=True,
                    duration=final_duration,
                    confidence=confidence,
                    method=final_method,
                    features={
                        'methods_used': [d[0] for d in durations],
                        'features_found': features_found,
                        'all_durations': [(d[0], d[1]) for d in durations],
                        'asr_analysis': asr_analysis if asr_analysis else None
                    }
                )
            else:
                # ASR判断为误判，返回无片尾
                print(f"检测方法: {final_method}")
                print(f"❌ 修正结果: 无片尾（ASR检测到正常剧情内容）")

                ending_info = EndingCreditsInfo(
                    has_ending=False,
                    duration=0.0,
                    confidence=1.0,
                    method=final_method,
                    features={
                        'reason': 'ASR增强检测修正误判',
                        'asr_analysis': asr_analysis,
                        'original_similarity_detection': {
                            'duration': similarity_duration,
                            'confidence': similarity_conf
                        }
                    }
                )

        # 4. 计算有效时长
        effective_duration = total_duration - ending_info.duration

        print(f"\n📏 时长统计:")
        print(f"  原始时长: {total_duration:.2f}秒 ({total_duration/60:.2f}分钟)")
        print(f"  片尾时长: {ending_info.duration:.2f}秒")
        print(f"  有效时长: {effective_duration:.2f}秒 ({effective_duration/60:.2f}分钟)")

        return VideoEndingResult(
            video_path=video_path,
            episode=episode,
            total_duration=total_duration,
            ending_info=ending_info,
            effective_duration=effective_duration
        )

    # =================== 私有辅助方法 ===================

    def _asr_enhanced_detection(self, video_path: str, total_duration: float) -> Optional[Dict]:
        """
        【第二层防护】ASR增强检测

        转录视频最后3.5秒的音频，分析内容判断是否是真实片尾

        Args:
            video_path: 视频路径
            total_duration: 视频总时长

        Returns:
            ASR分析结果字典，包含：
            - has_speech: 是否检测到语音
            - is_ending_narration: 是否是片尾旁白
            - last_asr_end: 最后一条ASR的结束时间
            - full_text: 转录文本
            - reason: 判断原因
        """
        if not ASR_AVAILABLE:
            return None

        try:
            # 初始化ASR转录器
            transcriber = ASRTranscriber(model_size="base")

            # 转录最后3.5秒
            print(f"  🎙️  转录最后3.5秒音频...")
            asr_segments = transcriber.transcribe_last_seconds(video_path, seconds=3.5)

            if not asr_segments:
                print(f"  ℹ️  未检测到语音（无ASR片段）")
                return {
                    "has_speech": False,
                    "is_ending_narration": False,
                    "last_asr_end": 0,
                    "full_text": "",
                    "reason": "无语音"
                }

            # 初始化ASR分析器
            analyzer = ASRContentAnalyzer()

            # 分析ASR内容
            print(f"  📝 分析ASR内容...")
            analysis = analyzer.analyze_with_similarity(
                asr_segments=asr_segments,
                video_end_time=total_duration,
                similarity_has_ending=True,  # 这里先假设有片尾，让analyzer判断
                similarity_duration=3.5
            )

            # 提取asr_analysis中的详细信息
            detailed_analysis = analysis.get('asr_analysis', {})

            # 构建返回结果，同时保留兼容性
            asr_analysis = {
                'has_ending': analysis.get('has_ending', False),
                'method': analysis.get('method', ''),
                'reason': analysis.get('reason', ''),
                # 详细信息
                'has_speech': detailed_analysis.get('has_speech', False),
                'is_ending_narration': detailed_analysis.get('is_ending_narration', False),
                'last_asr_end': detailed_analysis.get('last_asr_end', 0),
                'full_text': detailed_analysis.get('full_text', ''),
            }

            # 输出分析结果
            print(f"  检测到语音: {'是' if asr_analysis['has_speech'] else '否'}")
            if asr_analysis['has_speech']:
                print(f"  片尾旁白: {'是' if asr_analysis['is_ending_narration'] else '否'}")
                print(f"  ASR文本: \"{asr_analysis['full_text'][:50]}...\"")
                print(f"  判断原因: {asr_analysis['reason']}")

            return asr_analysis

        except Exception as e:
            print(f"  ⚠️  ASR检测失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _apply_asr_correction(
        self,
        similarity_result: Tuple[float, float],
        asr_analysis: Optional[Dict],
        total_duration: float
    ) -> Tuple[bool, float, float, str]:
        """
        应用ASR分析结果修正画面相似度检测的误判

        Args:
            similarity_result: (相似度检测时长, 置信度)
            asr_analysis: ASR分析结果
            total_duration: 视频总时长

        Returns:
            (是否有片尾, 片尾时长, 置信度, 检测方法)
        """
        sim_duration, sim_conf = similarity_result

        # 如果没有ASR分析，使用相似度结果
        if asr_analysis is None:
            return (sim_duration > self.MIN_ENDING_DURATION, sim_duration, sim_conf, "similarity")

        # 情况1: 无语音 + 画面相似 → 真实片尾
        if not asr_analysis['has_speech']:
            if sim_duration > self.MIN_ENDING_DURATION:
                print(f"\n[ASR修正] 无语音 + 画面相似 → 真实片尾")
                return (True, sim_duration, min(0.95, sim_conf + 0.1), "asr_verified")
            else:
                return (False, 0.0, 0.0, "none")

        # 情况2: 有语音 + ASR分析认为是片尾 → 真实片尾
        # 检查has_ending字段（从ASR分析结果中提取）
        asr_has_ending = asr_analysis.get('has_ending', False)

        if asr_has_ending:
            # ASR分析确认这是片尾（包括：片尾旁白、短ASR无明确剧情等）
            if asr_analysis['is_ending_narration']:
                # 片尾旁白 → 使用ASR结束时间
                ending_start = asr_analysis['last_asr_end']
                ending_duration = total_duration - ending_start

                if ending_duration >= self.MIN_ENDING_DURATION:
                    print(f"\n[ASR修正] 检测到片尾旁白 → 真实片尾")
                    print(f"  片尾旁白结束时间: {ending_start:.2f}秒")
                    print(f"  片尾时长: {ending_duration:.2f}秒")
                    return (True, ending_duration, 0.95, "asr_ending_narration")
            else:
                # 短ASR无明确剧情特征 → 保留相似度检测结果，如果相似度失败则使用默认时长
                print(f"\n[ASR修正] ASR验证通过（短ASR，无明确剧情特征）")
                print(f"  ASR文本: \"{asr_analysis['full_text'][:30]}...\"")
                print(f"  原因: {asr_analysis['reason']}")

                # 如果画面相似度检测失败，使用ASR计算的时长或默认时长
                if sim_duration < self.MIN_ENDING_DURATION:
                    # 画面相似度检测失败，使用ASR停止位置后的时长
                    ending_start = asr_analysis.get('last_asr_end', 0)
                    ending_duration = total_duration - ending_start
                    if ending_duration < self.MIN_ENDING_DURATION:
                        # ASR计算的时长也不够，使用默认时长
                        ending_duration = 2.0
                    return (True, ending_duration, 0.90, "asr_only")
                else:
                    # 画面相似度检测成功，使用相似度时长
                    return (True, sim_duration, min(0.95, sim_conf + 0.1), "asr_verified")

        # 情况3: 有语音 + ASR分析认为不是片尾 → 误判
        if asr_analysis['has_speech'] and not asr_has_ending:
            print(f"\n[ASR修正] 检测到正常剧情对白 → 画面相似是误判！")
            print(f"  ASR文本: \"{asr_analysis['full_text']}\"")
            print(f"  原因: {asr_analysis['reason']}")
            print(f"  ✅ 修正结果: 无片尾（保留全部内容）")
            return (False, 0.0, 1.0, "asr_false_positive_fix")

        # 默认情况：使用相似度结果
        return (sim_duration > self.MIN_ENDING_DURATION, sim_duration, sim_conf, "similarity")

    def _extract_project_name(self, video_path: str) -> str:
        """
        从视频路径提取项目名称

        Args:
            video_path: 视频文件路径

        Returns:
            项目名称
        """
        path = Path(video_path)

        # 从路径中提取项目名称
        # 路径示例: .../晓红姐-3.4剧目/多子多福，开局就送绝美老婆/1.mp4
        #          .../新的漫剧素材/不晚忘忧/1.mp4

        # 获取项目目录（视频文件的父目录）
        project_dir = path.parent

        # 如果目录名为数字（集数），再往上一层
        if project_dir.name.isdigit():
            project_dir = project_dir.parent

        project_name = project_dir.name
        return project_name

    def _get_video_duration(self, video_path: str) -> float:
        """获取视频总时长"""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())

    def _detect_by_similarity(self, video_path: str, total_duration: float) -> Tuple[float, float]:
        """
        方法1: 通过画面相似度检测慢动作片尾

        采样策略：最后3.5秒全部密集采样（每帧都抽）

        边界判定：
- 找最长的连续高相似度段
        - 至少5帧（0.1秒）连续高相似度才判定为片尾
        - 添加安全边界0.1秒，避免剪太多

        Returns:
            (片尾时长, 置信度)
        """
        try:
            from PIL import Image
            import imagehash
            import cv2

            # 获取视频帧率
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()

            start_time = max(0, total_duration - self.CHECK_LAST_SECONDS)

            # 全部密集采样（每帧都抽）
            frames = []  # (timestamp, hash)
            frame_count = int((total_duration - start_time) * fps)

            for i in range(frame_count):
                timestamp = start_time + (i / fps)
                # 更保守的边界检查：确保timestamp < total_duration - 0.05
                if timestamp >= total_duration - 0.05:  # 留50ms边界
                    break

                frame_file = self.cache_dir / f"frame_{i}.jpg"

                cmd = [
                    'ffmpeg',
                    '-ss', str(timestamp),
                    '-i', video_path,
                    '-vframes', '1',
                    '-q:v', '2',
                    '-y',
                    str(frame_file)
                ]
                subprocess.run(cmd, capture_output=True, check=True)

                if frame_file.exists():
                    img = Image.open(frame_file)
                    hash_val = imagehash.phash(img)
                    frames.append((timestamp, hash_val))

            if len(frames) < 2:
                return (0.0, 0.0)

            # 按时间排序
            frames.sort(key=lambda x: x[0])

            # 计算相邻帧的相似度
            similarities = []  # (timestamp, similarity)
            for i in range(len(frames) - 1):
                timestamp, hash1 = frames[i]
                _, hash2 = frames[i + 1]

                distance = hash1 - hash2
                max_distance = hash1.hash.size
                similarity = 1 - (distance / max_distance)
                similarities.append((timestamp, similarity))

            # 找到最后N秒内最长的连续高相似度段
            max_continuous_count = 0
            max_continuous_start = None
            current_count = 0
            current_start = None

            for timestamp, sim in similarities:
                if sim >= self.SIMILARITY_THRESHOLD:
                    if current_count == 0:
                        current_start = timestamp
                    current_count += 1
                else:
                    # 连续段结束
                    if current_count > max_continuous_count:
                        max_continuous_count = current_count
                        max_continuous_start = current_start
                    current_count = 0
                    current_start = None

            # 检查最后一段
            if current_count > max_continuous_count:
                max_continuous_count = current_count
                max_continuous_start = current_start

            # 如果找到了足够长的连续高相似度段
            if max_continuous_count >= self.MIN_CONTINUOUS_FRAMES:
                # 使用最长的连续段
                ending_start = max_continuous_start - self.SAFE_MARGIN
            else:
                ending_start = total_duration

            # 计算片尾时长
            ending_duration = total_duration - ending_start

            if ending_duration >= self.MIN_ENDING_DURATION:
                # 根据连续帧数计算置信度
                confidence = min(0.95, 0.70 + (max_continuous_count * 0.05))
                return (ending_duration, confidence)
            else:
                return (0.0, 0.0)

        except Exception as e:
            print(f"    ⚠️  画面相似度检测失败: {e}")
            import traceback
            traceback.print_exc()
            return (0.0, 0.0)

    def _detect_by_brightness(self, video_path: str, total_duration: float) -> Tuple[float, float]:
        """
        方法2: 通过画面亮度检测渐变/黑屏片尾

        采样策略：最后3.5秒全部密集采样（每帧都抽）

        Returns:
            (片尾时长, 置信度)
        """
        try:
            import cv2
            import numpy as np

            # 获取视频帧率
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()

            start_time = max(0, total_duration - self.CHECK_LAST_SECONDS)

            # 全部密集采样（每帧都抽）
            brightness_values = []  # (timestamp, brightness)
            frame_count = int((total_duration - start_time) * fps)

            for i in range(frame_count):
                timestamp = start_time + (i / fps)
                # 确保不超出视频长度
                if timestamp >= total_duration - 0.01:  # 留10ms边界
                    break

                cap = cv2.VideoCapture(video_path)
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                ret, frame = cap.read()

                if ret:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    brightness = np.mean(gray) / 255.0
                    brightness_values.append((timestamp, brightness))

                cap.release()

            if len(brightness_values) < 2:
                return (0.0, 0.0)

            # 按时间排序
            brightness_values.sort(key=lambda x: x[0])

            # 检测1: 最后几秒是否很暗
            timestamps, brights = zip(*brightness_values)
            last_n = min(10, len(brights))  # 最后几个采样点
            avg_brightness_last = sum(brights[-last_n:]) / last_n

            if avg_brightness_last < self.BRIGHTNESS_THRESHOLD:
                # 最后几秒很暗，可能是片尾
                # 找到亮度开始变暗的时刻
                for i, (timestamp, bright) in enumerate(brightness_values):
                    if bright < self.BRIGHTNESS_THRESHOLD:
                        ending_start = timestamp - self.SAFE_MARGIN
                        ending_duration = total_duration - ending_start
                        if ending_duration >= self.MIN_ENDING_DURATION:
                            return (ending_duration, 0.75)
                        break

            # 检测2: 亮度是否单调递减（渐变）
            is_decreasing = True
            for i in range(len(brightness_values) - 1):
                if brightness_values[i][1] < brightness_values[i + 1][1]:
                    is_decreasing = False
                    break

            if is_decreasing and avg_brightness_last < 0.5:
                # 亮度递减，可能是渐变片尾
                ending_start = brightness_values[0][0] - self.SAFE_MARGIN
                ending_duration = total_duration - ending_start
                if ending_duration >= self.MIN_ENDING_DURATION:
                    return (ending_duration, 0.70)

            return (0.0, 0.0)

        except Exception as e:
            print(f"    ⚠️  画面亮度检测失败: {e}")
            return (0.0, 0.0)

    def _detect_by_audio(self, video_path: str, total_duration: float) -> Dict:
        """
        方法3: 通过音频特征检测片尾

        检测特征:
        - 背景音乐节奏
        - 音量淡出
        - 音乐重复

        Returns:
            {
                'has_music': bool,
                'duration': float,
                'confidence': float
            }
        """
        try:
            # 先尝试简单的静音检测
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-af', 'silencedetect=noise=-40dB:d=1',  # 检测1秒以上的静音段
                '-f', 'null',
                '-'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # 解析静音检测结果
            silence_durations = []
            for line in result.stdout.split('\n'):
                if 'silence_start' in line:
                    parts = line.split()
                    start_idx = parts.index('silence_start') + 1
                    end_idx = parts.index('silence_end') + 1
                    start = float(parts[start_idx])
                    end = float(parts[end_idx])
                    duration = end - start
                    silence_durations.append((start, end, duration))

            # 检查最后是否有静音段
            if silence_durations:
                last_silence = silence_durations[-1]
                silence_start = last_silence[0]

                # 如果最后的静音段接近视频结尾
                if silence_start > total_duration - self.CHECK_LAST_SECONDS:
                    duration = total_duration - silence_start
                    return {
                        'has_music': False,
                        'duration': duration,
                        'confidence': 0.75
                    }

            # 如果没有明显的静音，尝试检测背景音乐
            # 这里简化处理：如果最后部分有声音但不明显，可能是音乐
            # 完整的音乐检测需要librosa，这里暂时跳过
            return {
                'has_music': False,
                'duration': 0.0,
                'confidence': 0.0
            }

        except Exception as e:
            print(f"    ⚠️  音频检测失败: {e}")
            return {
                'has_music': False,
                'duration': 0.0,
                'confidence': 0.0
            }

    def _detect_by_asr_density(
        self,
        asr_segments: List,
        total_duration: float
    ) -> Tuple[float, float]:
        """
        方法4: 通过ASR对白密度检测片尾

        Returns:
            (片尾时长, 置信度)
        """
        try:
            if not asr_segments:
                return (0.0, 0.0)

            # 统计最后N秒的对白数量
            check_start = total_duration - self.CHECK_LAST_SECONDS

            ending_asrs = [
                asr for asr in asr_segments
                if asr['start'] >= check_start
            ]

            # 计算最后N秒的对白密度
            ending_asr_duration = sum(
                asr['end'] - asr['start']
                for asr in ending_asrs
            )
            ending_density = ending_asr_duration / self.CHECK_LAST_SECONDS

            # 计算整体对白密度
            total_asr_duration = sum(
                asr['end'] - asr['start']
                for asr in asr_segments
            )
            overall_density = total_asr_duration / total_duration

            # 如果最后N秒对白密度显著降低（<50%），说明可能是片尾
            if ending_density < overall_density * 0.5 and ending_density < 0.3:
                # 进一步分析：找到对白消失的时刻
                for asr in reversed(asr_segments):
                    if asr['end'] < check_start:
                        # 这段对白之后没有对白了
                        gap = check_start - asr['end']
                        if gap > 2:  # 间隔超过2秒
                            return (gap, 0.80)

            return (0.0, 0.0)

        except Exception as e:
            print(f"    ⚠️  ASR密度分析失败: {e}")
            return (0.0, 0.0)


# ========== 批量检测功能 ==========

def detect_project_endings(
    project_path: str,
    project_name: Optional[str] = None,
    asr_data: Optional[Dict[int, List]] = None,
    output_dir: Optional[str] = None
) -> ProjectEndingResult:
    """
    批量检测项目中所有视频的片尾

    Args:
        project_path: 项目路径（包含视频文件）
        project_name: 项目名称
        asr_data: ASR数据字典 {集数: ASR列表}
        output_dir: 输出目录

    Returns:
        ProjectEndingResult
    """
    if project_name is None:
        project_name = Path(project_path).name

    print("=" * 70)
    print(f"🎬 批量检测项目片尾: {project_name}")
    print("=" * 70)

    # 查找视频文件（按文件名中的数字排序）
    video_files = sorted(Path(project_path).glob('*.mp4'), key=lambda x: int(x.stem))

    if not video_files:
        print(f"❌ 未找到视频文件: {project_path}")
        return None

    print(f"\n找到 {len(video_files)} 个视频文件")

    # 创建检测器
    detector = EndingCreditsDetector()

    # 检测每个视频
    episodes = []
    for idx, video_file in enumerate(video_files, 1):
        episode = idx  # 文件名就是集数
        print(f"\n处理进度: [{idx}/{len(video_files)}]")

        # 获取该集的ASR数据
        episode_asr = asr_data.get(episode, None) if asr_data else None

        # 检测片尾
        result = detector.detect_video_ending(
            str(video_file),
            episode,
            episode_asr
        )

        episodes.append(result)

    # 生成汇总
    has_ending_count = sum(1 for ep in episodes if ep.ending_info.has_ending)
    total_ending_duration = sum(ep.ending_info.duration for ep in episodes)
    total_effective_duration = sum(ep.effective_duration for ep in episodes)

    summary = {
        'total_episodes': len(episodes),
        'episodes_with_ending': has_ending_count,
        'total_ending_duration': total_ending_duration,
        'total_effective_duration': total_effective_duration,
        'average_ending_duration': total_ending_duration / has_ending_count if has_ending_count > 0 else 0
    }

    print(f"\n{'=' * 70}")
    print(f"📊 项目汇总")
    print(f"{'=' * 70}")
    print(f"总集数: {summary['total_episodes']}")
    print(f"有片尾的集数: {summary['episodes_with_ending']}")
    print(f"总片尾时长: {summary['total_ending_duration']:.1f}秒 ({summary['total_ending_duration']/60:.2f}分钟)")
    print(f"总有效时长: {summary['total_effective_duration']:.1f}秒 ({summary['total_effective_duration']/60:.2f}分钟)")
    print(f"平均片尾时长: {summary['average_ending_duration']:.1f}秒")

    # 创建结果对象
    result = ProjectEndingResult(
        project_name=project_name,
        project_path=project_path,
        episodes=episodes,
        summary=summary
    )

    # 保存结果
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{project_name}_ending_credits.json"
        result.save_to_file(str(output_file))

    return result


# ========== 命令行入口 ==========

def main():
    """命令行入口"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python -m scripts.detect_ending_credits <项目路径> [ASR数据目录] [输出目录]")
        print("\n示例:")
        print("  python -m scripts.detect_ending_credits data/videos/项目名")
        print("  python -m scripts.detect_ending_credits data/videos/项目名 data/asr/项目名 output/")
        sys.exit(1)

    project_path = sys.argv[1]
    asr_dir = sys.argv[2] if len(sys.argv) > 2 else None
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None

    # 加载ASR数据（如果提供）
    asr_data = None
    if asr_dir and Path(asr_dir).exists():
        print(f"\n加载ASR数据: {asr_dir}")
        # 这里需要根据实际的ASR数据格式加载
        # asr_data = load_asr_data(asr_dir)

    # 执行检测
    result = detect_project_endings(
        project_path=project_path,
        asr_data=asr_data,
        output_dir=output_dir
    )

    if result:
        print(f"\n✅ 检测完成！")
        print(f"结果已保存到: {output_dir}")


if __name__ == "__main__":
    main()
