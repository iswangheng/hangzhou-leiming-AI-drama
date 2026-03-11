"""
片尾结束帧智能检测模块

用于自动识别和标记每集视频的片尾结束帧时长
支持视觉（画面）+ 听觉（音频）综合分析

V15.9 更新：
- 添加 --use-cached-asr 参数支持
- 优先从缓存读取 ASR，- 缓存不存在时才执行转录

作者：V14/V15.9
创建时间：2026-03-04
更新时间：2026-03-11 (V15.9)
"""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib


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
        """转换为字典"""
        return {
            'has_ending': bool(self.has_ending),
            'duration': float(self.duration),
            'confidence': float(self.confidence),
            'method': str(self.method),
            'features': self.features
        }


@dataclass
class VideoEndingResult:
    """单集视频的片尾检测结果"""
    video_path: str
    episode: int
    total_duration: float
    ending_info: EndingCreditsInfo
    effective_duration: float

    def to_dict(self) -> dict:
        return {
            'video_path': self.video_path,
            'episode': self.episode,
            'total_duration': self.total_duration,
            'ending_info': self.ending_info.to_dict(),
            'effective_duration': self.effective_duration
        }


# ========== 核心检测功能 ==========

class EndingCreditsDetector:
    """片尾结束帧检测器"""

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = "/tmp/ending_detection_cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 配置参数
        self.CHECK_LAST_SECONDS = 10.0
        self.SIMILARITY_THRESHOLD = 0.92
        self.MIN_CONTINUOUS_FRAMES = 5
        self.SAFE_MARGIN = 0.2
        self.BRIGHTNESS_THRESHOLD = 0.3
        self.MIN_ENDING_DURATION = 0.2
        self.CHECK_LAST_SECONDS = 3.5

    def detect_video_ending(
        self,
        video_path: str,
        episode: int,
        asr_segments: Optional[List] = None,
        use_complex_method: bool = True
    ) -> VideoEndingResult:
        """检测单个视频的片尾

        Args:
            video_path: 视频文件路径
            episode: 集数编号
            asr_segments: ASR数据（可选）
            use_complex_method: 是否使用复杂算法（默认True）

        Returns:
            VideoEndingResult
        """
        if use_complex_method:
            return self._detect_video_ending_complex(video_path, episode, asr_segments)
        else:
            return self._detect_video_ending_simple(video_path, episode)

    def _detect_video_ending_simple(
        self,
        video_path: str,
        episode: int
    ) -> VideoEndingResult:
        """简化版片尾检测（使用固定公式）

        Returns:
            VideoEndingResult
        """
        print(f"\n检测第{episode}集片尾（简化算法）...")
        print(f"视频: {os.path.basename(video_path)}")

        # 1. 获取视频总时长
        total_duration = self._get_video_duration(video_path)
        print(f"总时长: {total_duration:.1f}秒")

        # 2. 简化版本：使用固定阈值
        ending_duration = min(3.0, total_duration * 0.05)
        has_ending = ending_duration > 0.5
        confidence = 0.8 if has_ending else 0.5

        ending_info = EndingCreditsInfo(
            has_ending=has_ending,
            duration=ending_duration,
            confidence=confidence,
            method='simplified_detection',
            features={'duration': ending_duration}
        )

        return VideoEndingResult(
            video_path=video_path,
            episode=episode,
            total_duration=total_duration,
            ending_info=ending_info,
            effective_duration=total_duration - ending_duration
        )

    def _detect_video_ending_complex(
        self,
        video_path: str,
        episode: int,
        asr_segments: Optional[List] = None
    ) -> VideoEndingResult:
        """复杂版片尾检测（使用多种算法）

        使用4种方法：
        1. 画面相似度检测
        2. 画面亮度检测
        3. 音频特征分析
        4. ASR对白密度分析

        Returns:
            VideoEndingResult
        """
        print(f"\n检测第{episode}集片尾（复杂算法）...")
        print(f"视频: {os.path.basename(video_path)}")

        # 1. 获取视频总时长
        total_duration = self._get_video_duration(video_path)
        print(f"总时长: {total_duration:.1f}秒")

        # 2. 综合检测
        features_found = []
        durations = []

        # 方法1: 画面相似度检测
        print(f"\n[方法1/4] 画面相似度检测...")
        sim_duration, sim_conf = self._detect_by_similarity(video_path, total_duration)
        if sim_duration > self.MIN_ENDING_DURATION:
            print(f"  ✅ 检测到慢动作片尾: {sim_duration:.1f}秒 (置信度: {sim_conf:.0%})")
            durations.append(('similarity', sim_duration, sim_conf))
            features_found.append('慢动作')
        else:
            print(f"  ❌ 未检测到明显的慢动作片尾")

        # 方法2: 画面亮度检测
        print(f"\n[方法2/4] 画面亮度检测...")
        bright_duration, bright_conf = self._detect_by_brightness(video_path, total_duration)
        if bright_duration > self.MIN_ENDING_DURATION:
            print(f"  ✅ 检测到渐变/黑屏片尾: {bright_duration:.1f}秒 (置信度: {bright_conf:.0%})")
            durations.append(('brightness', bright_duration, bright_conf))
            features_found.append('渐变/黑屏')
        else:
            print(f"  ❌ 未检测到明显的渐变/黑屏")

        # 方法3: 音频特征分析
        print(f"\n[方法3/4] 音频特征分析...")
        audio_result = self._detect_by_audio(video_path, total_duration)
        if audio_result['has_music']:
            print(f"  ✅ 检测到背景音乐片尾: {audio_result['duration']:.1f}秒")
            durations.append(('audio', audio_result['duration'], audio_result['confidence']))
            features_found.append('背景音乐')
        else:
            print(f"  ❌ 未检测到明显的背景音乐特征")

        # 方法4: ASR对白密度分析
        if asr_segments:
            print(f"\n[方法4/4] ASR对白密度分析...")
            asr_duration, asr_conf = self._detect_by_asr_density(asr_segments, total_duration)
            if asr_duration > self.MIN_ENDING_DURATION:
                print(f"  ✅ 检测到对白缺失片尾: {asr_duration:.1f}秒")
                durations.append(('asr', asr_duration, asr_conf))
                features_found.append('无对白')
            else:
                print(f"  ❌ 对白密度正常")
        else:
            print(f"\n[方法4/4] ASR对白密度分析...（无ASR数据，跳过）")

        # 3. 综合判断 - 添加ASR修正逻辑
        print(f"\n{'='*50}")
        print(f"📊 检测结果汇总")

        if not durations:
            print(f"❌ 未检测到明显的片尾特征")
            ending_info = EndingCreditsInfo(
                has_ending=False,
                duration=0.0,
                confidence=0.0,
                method='none',
                features={'methods_used': [], 'features_found': []}
            )
        else:
            # 选择最佳结果
            priority = {'similarity': 4, 'brightness': 3, 'audio': 2, 'asr': 1}
            best_method, best_duration, best_conf = max(
                durations,
                key=lambda x: (priority.get(x[0], 0), x[2])
            )
            
            # ========== ASR修正逻辑 ==========
            # 如果画面检测到片尾，但ASR还有正常对白 → 判定为误判
            if best_method == 'similarity' and asr_segments:
                # 检查最后几秒是否有正常对白
                check_start = total_duration - self.CHECK_LAST_SECONDS
                
                # ASRSegment可能是对象或字典
                def get_seg_start(seg):
                    if hasattr(seg, 'start'):
                        return seg.start
                    return seg.get('start', 0)
                
                def get_seg_end(seg):
                    if hasattr(seg, 'end'):
                        return seg.end
                    return seg.get('end', 0)
                
                def get_seg_text(seg):
                    if hasattr(seg, 'text'):
                        return seg.text
                    return seg.get('text', '')
                
                ending_asrs = [
                    seg for seg in asr_segments
                    if get_seg_start(seg) >= check_start
                ]
                
                if ending_asrs:
                    # 有对白 → 可能是误判（正常剧情不是片尾）
                    print(f"\n⚠️ ASR修正: 画面检测到片尾，但最后{self.CHECK_LAST_SECONDS}秒还有对白")
                    last_text = get_seg_text(ending_asrs[-1])
                    print(f"   最后对白: {last_text[:30]}...")
                    
                    # 进一步检查：是否是对白密集（正常剧情）还是稀疏（片尾旁白）
                    total_asr_time = sum(
                        get_seg_end(seg) - get_seg_start(seg)
                        for seg in ending_asrs
                    )
                    asr_density = total_asr_time / self.CHECK_LAST_SECONDS
                    
                    print(f"   对白密度: {asr_density:.2f}秒/秒")
                    
                    # 如果对白密度 > 0.3秒/秒，说明是正常剧情，不是片尾
                    if asr_density > 0.3:
                        print(f"   ✅ 判定为误判: 对白密度高，是正常剧情")
                        print(f"   📝 修整为: 无片尾")
                        ending_info = EndingCreditsInfo(
                            has_ending=False,
                            duration=0.0,
                            confidence=1.0,
                            method='asr_false_positive_fix',
                            features={
                                'original_method': best_method,
                                'original_duration': best_duration,
                                'reason': 'ASR修正：对白密度高，是正常剧情'
                            }
                        )
                    else:
                        # 对白稀疏，可能是片尾旁白，保持原判
                        print(f"   📝 对白稀疏，可能是片尾旁白，保持原判")
                        confidence = min(0.98, best_conf)
                        ending_info = EndingCreditsInfo(
                            has_ending=True,
                            duration=best_duration,
                            confidence=confidence,
                            method=best_method,
                            features={
                                'methods_used': [d[0] for d in durations],
                                'features_found': features_found
                            }
                        )
                else:
                    # 无对白 + 画面相似 → 确认是片尾
                    confidence = min(0.98, best_conf)
                    print(f"检测方法: {best_method}")
                    print(f"片尾时长: {best_duration:.2f}秒")
                    print(f"置信度: {confidence:.1%}")
                    ending_info = EndingCreditsInfo(
                        has_ending=True,
                        duration=best_duration,
                        confidence=confidence,
                        method=best_method,
                        features={
                            'methods_used': [d[0] for d in durations],
                            'features_found': features_found
                        }
                    )
            else:
                confidence = min(0.98, best_conf)
                print(f"检测方法: {best_method}")
                print(f"片尾时长: {best_duration:.2f}秒")
                print(f"置信度: {confidence:.1%}")
                ending_info = EndingCreditsInfo(
                    has_ending=True,
                    duration=best_duration,
                    confidence=confidence,
                    method=best_method,
                    features={
                        'methods_used': [d[0] for d in durations],
                        'features_found': features_found
                    }
                )

        effective_duration = total_duration - ending_info.duration
        print(f"\n📏 时长统计:")
        print(f"  原始时长: {total_duration:.2f}秒")
        print(f"  片尾时长: {ending_info.duration:.2f}秒")
        print(f"  有效时长: {effective_duration:.2f}秒")

        return VideoEndingResult(
            video_path=video_path,
            episode=episode,
            total_duration=total_duration,
            ending_info=ending_info,
            effective_duration=effective_duration
        )

    def _detect_by_similarity(self, video_path: str, total_duration: float) -> Tuple[float, float]:
        """方法1: 画面相似度检测"""
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
            frames = []
            frame_count = int((total_duration - start_time) * fps)

            print(f"    采样最后{self.CHECK_LAST_SECONDS}秒，共{frame_count}帧...")

            for i in range(min(frame_count, 200)):  # 限制最多200帧
                timestamp = start_time + (i / fps)
                if timestamp >= total_duration - 0.05:
                    break

                frame_file = self.cache_dir / f"ending_frame_{i}.jpg"

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

            frames.sort(key=lambda x: x[0])

            # 计算相邻帧相似度
            similarities = []
            for i in range(len(frames) - 1):
                timestamp, hash1 = frames[i]
                _, hash2 = frames[i + 1]
                distance = hash1 - hash2
                max_distance = hash1.hash.size
                similarity = 1 - (distance / max_distance)
                similarities.append((timestamp, similarity))

            # 找最长连续高相似度段
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
                    if current_count > max_continuous_count:
                        max_continuous_count = current_count
                        max_continuous_start = current_start
                    current_count = 0

            if current_count > max_continuous_count:
                max_continuous_count = current_count
                max_continuous_start = current_start

            if max_continuous_count >= self.MIN_CONTINUOUS_FRAMES:
                ending_start = max_continuous_start - self.SAFE_MARGIN
                ending_duration = total_duration - ending_start
                if ending_duration >= self.MIN_ENDING_DURATION:
                    confidence = min(0.95, 0.70 + (max_continuous_count * 0.05))
                    return (ending_duration, confidence)

            return (0.0, 0.0)

        except Exception as e:
            print(f"    ⚠️ 画面相似度检测失败: {e}")
            return (0.0, 0.0)

    def _detect_by_brightness(self, video_path: str, total_duration: float) -> Tuple[float, float]:
        """方法2: 画面亮度检测"""
        try:
            import cv2
            import numpy as np

            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()

            start_time = max(0, total_duration - self.CHECK_LAST_SECONDS)
            frame_count = int((total_duration - start_time) * fps)

            brightness_values = []
            for i in range(min(frame_count, 200)):
                timestamp = start_time + (i / fps)
                if timestamp >= total_duration - 0.01:
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

            brightness_values.sort(key=lambda x: x[0])
            timestamps, brights = zip(*brightness_values)

            # 检查最后几帧是否很暗
            last_n = min(10, len(brights))
            avg_brightness_last = sum(brights[-last_n:]) / last_n

            if avg_brightness_last < self.BRIGHTNESS_THRESHOLD:
                for timestamp, bright in brightness_values:
                    if bright < self.BRIGHTNESS_THRESHOLD:
                        ending_start = timestamp - self.SAFE_MARGIN
                        ending_duration = total_duration - ending_start
                        if ending_duration >= self.MIN_ENDING_DURATION:
                            return (ending_duration, 0.75)

            return (0.0, 0.0)

        except Exception as e:
            print(f"    ⚠️ 画面亮度检测失败: {e}")
            return (0.0, 0.0)

    def _detect_by_audio(self, video_path: str, total_duration: float) -> Dict:
        """方法3: 音频特征分析"""
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-af', 'silencedetect=noise=-40dB:d=1',
                '-f', 'null',
                '-'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            silence_durations = []
            for line in result.stdout.split('\n'):
                if 'silence_start' in line and 'silence_end' in line:
                    parts = line.split()
                    if 'silence_start' in parts and 'silence_end' in parts:
                        try:
                            start_idx = parts.index('silence_start') + 1
                            end_idx = parts.index('silence_end') + 1
                            start = float(parts[start_idx])
                            end = float(parts[end_idx])
                            silence_durations.append((start, end))
                        except:
                            pass

            if silence_durations:
                last_silence = silence_durations[-1]
                silence_start = last_silence[0]
                if silence_start > total_duration - self.CHECK_LAST_SECONDS:
                    duration = total_duration - silence_start
                    return {'has_music': True, 'duration': duration, 'confidence': 0.75}

            return {'has_music': False, 'duration': 0.0, 'confidence': 0.0}

        except Exception as e:
            return {'has_music': False, 'duration': 0.0, 'confidence': 0.0}

    def _detect_by_asr_density(
        self,
        asr_segments: List,
        total_duration: float
    ) -> Tuple[float, float]:
        """方法4: ASR对白密度分析"""
        if not asr_segments:
            return (0.0, 0.0)

        try:
            check_start = total_duration - self.CHECK_LAST_SECONDS
            ending_asrs = [asr for asr in asr_segments if asr.get('start', 0) >= check_start]

            ending_asr_duration = sum(
                asr.get('end', 0) - asr.get('start', 0)
                for asr in ending_asrs
            )
            ending_density = ending_asr_duration / self.CHECK_LAST_SECONDS

            total_asr_duration = sum(
                asr.get('end', 0) - asr.get('start', 0)
                for asr in asr_segments
            )
            overall_density = total_asr_duration / total_duration

            if ending_density < overall_density * 0.5 and ending_density < 0.3:
                for asr in reversed(asr_segments):
                    if asr.get('start', 0) < check_start:
                        gap = check_start - asr.get('end', 0)
                        if gap > 2:
                            return (gap, 0.80)

            return (0.0, 0.0)

        except Exception as e:
            return (0.0, 0.0)

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


# ========== 命令行入口 ==========

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='片尾结束帧智能检测 - 自动识别和标记每集视频的片尾时长'
    )
    parser.add_argument('project_path', help='项目路径（包含视频文件）')
    parser.add_argument('--asr-dir', help='ASR数据目录（可选）')
    parser.add_argument('--output-dir', default='data/hangzhou-leiming/ending_credits',
                        help='输出目录')
    parser.add_argument('--use-cached-asr', action='store_true',
                        help='V15.9: 优先从缓存读取 ASR')

    args = parser.parse_args()

    print(f"\n项目路径: {args.project_path}")
    print(f"输出目录: {args.output_dir}")
    print(f"使用缓存 ASR: {args.use_cached_asr}")

    # 创建检测器
    detector = EndingCreditsDetector()

    # 获取所有视频文件
    video_dir = Path(args.project_path)
    video_files = sorted(video_dir.glob("*.mp4"))

    print(f"\n找到 {len(video_files)} 个视频文件")

    # 检测每个视频
    for video_file in video_files:
        # 提取集数
        episode = None
        import re
        patterns = [
            r'第(\d+)集',
            r'EP?(\d+)',
            r'^(\d+)',
            r'[-_](\d+)\.mp4$',
            r'(\d+)(?=\.mp4)',
        ]
        for pattern in patterns:
            match = re.search(pattern, video_file.name, re.IGNORECASE)
            if match:
                episode = int(match.group(1))
                break

        if episode is None:
            print(f"跳过 {video_file.name}（无法提取集数）")
            continue

        # V15.9: 如果启用 --use-cached-asr，尝试从缓存加载
        asr_segments = None
        if args.use_cached_asr:
            try:
                from scripts.extract_asr import load_asr_from_file, get_asr_output_path

                project_name = video_dir.name
                asr_path = get_asr_output_path(project_name, episode)

                if Path(asr_path).exists():
                    asr_segments = load_asr_from_file(asr_path, episode=episode)
                    if asr_segments:
                        print(f"  📦 从缓存加载 ASR: {len(asr_segments)} 片段")
            except ImportError:
                print("  ⚠️ 无法导入 ASR 模块")

        # 执行检测
        result = detector.detect_video_ending(
            str(video_file),
            episode,
            asr_segments=asr_segments
        )

        print(f"  结果: {'有片尾' if result.ending_info.has_ending else '无片尾'}")
        if result.ending_info.has_ending:
            print(f"  片尾时长: {result.ending_info.duration:.2f}秒")


if __name__ == "__main__":
    main()
