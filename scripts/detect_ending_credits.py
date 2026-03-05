"""
片尾结束帧智能检测模块

用于自动识别和标记每集视频的片尾结束帧时长
支持视觉（画面）+ 听觉（音频）综合分析

使用场景：
1. 预处理阶段：批量检测所有视频的片尾
2. 渲染阶段：自动跳过片尾，保证剪辑连贯性

双层防护架构：
- 第一层：项目级配置（快速开关）
- 第二层：智能检测算法（画面相似度 + ASR时序分析）

V14.2 更新（2026-03-05）：
- 【重要】扩大ASR检测范围：从3.5秒增加到10秒
- 【重要】实施保守剪辑策略：只剪纯静音部分（最后ASR结束后+0.2秒）
- 【重要】确保不会剪掉任何台词，优先保证剧情完整性

作者：V14
创建时间：2026-03-04
更新时间：2026-03-05（V14.2 保守剪辑策略）
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
        """转换为字典，确保所有字段都能被JSON序列化

        V14.1修复: 强制转换numpy类型为Python原生类型
        """
        result = {
            'has_ending': bool(self.has_ending),  # 强制转换为Python bool
            'duration': float(self.duration),    # 强制转换为Python float
            'confidence': float(self.confidence), # 强制转换为Python float
            'method': str(self.method),
            'features': {}
        }

        # 手动处理features字段，确保所有值都能被JSON序列化
        for key, value in self.features.items():
            # 处理numpy类型和其他不可序列化的类型
            try:
                # 尝试JSON序列化测试
                import json
                json.dumps(value)

                # 如果成功，检查是否需要类型转换
                if hasattr(value, 'dtype'):  # numpy类型
                    if value.dtype == 'bool':
                        result['features'][key] = bool(value)
                    elif value.dtype in ['int64', 'int32']:
                        result['features'][key] = int(value)
                    elif value.dtype in ['float64', 'float32']:
                        result['features'][key] = float(value)
                    else:
                        result['features'][key] = value.item()  # numpy标量转Python类型
                elif isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    result['features'][key] = value
                else:
                    result['features'][key] = str(value)
            except (TypeError, ValueError):
                # 如果序列化失败，转换为字符串
                result['features'][key] = str(value)

        return result


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

    def __json__(self) -> dict:
        """用于JSON序列化的方法"""
        return self.to_dict()


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

        # 配置参数（V14.2 保守剪辑策略更新）
        self.CHECK_LAST_SECONDS = 10.0        # 【重要】分析最后10秒（从3.5秒增加），确保找到真正的最后ASR
        self.SIMILARITY_THRESHOLD = 0.92      # 相似度阈值
        self.MIN_CONTINUOUS_FRAMES = 5        # 最小连续高相似度帧数（0.1秒 @ 50fps）
        self.SAFE_MARGIN = 0.2                # 【重要】安全缓冲0.2秒（从0.1秒增加），保守策略避免剪掉台词
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

        # 2. 【第二层防护】ASR时序模式分析
        asr_timing_pattern = None
        if ASR_AVAILABLE:
            print(f"\n[第二层防护] ASR时序模式分析...")
            asr_timing_pattern = self._asr_enhanced_detection(video_path, total_duration)
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

        # 3. 综合判断（应用ASR时序模式修正）
        print(f"\n{'=' * 70}")
        print(f"📊 检测结果汇总")
        print(f"{'=' * 70}")

        if not durations:
            # 所有传统检测方法都失败，检查ASR时序模式
            if asr_timing_pattern:
                pattern = asr_timing_pattern.get('pattern', 'unknown')
                reason = asr_timing_pattern.get('reason', '')

                # 根据ASR模式判断
                if pattern == 'short_asr_long_silence' or pattern == 'no_asr_only_bgm':
                    # ASR模式支持有片尾
                    print(f"✅ 传统检测未发现，但ASR时序模式支持有片尾")
                    print(f"  ASR模式: {reason}")

                    # 计算片尾时长
                    if pattern == 'no_asr_only_bgm':
                        # 纯BGM，使用默认时长
                        ending_duration = 2.0
                    else:
                        # 短ASR+长静音，使用静音时长
                        ending_duration = asr_timing_pattern['silence_after_asr']

                    ending_info = EndingCreditsInfo(
                        has_ending=True,
                        duration=ending_duration,
                        confidence=0.75,
                        method='asr_timing_only',
                        features={
                            'methods_used': [],
                            'features_found': ['ASR时序模式'],
                            'asr_timing_pattern': asr_timing_pattern
                        }
                    )
                elif pattern == 'long_asr_no_silence':
                    # ASR模式强烈指示无片尾
                    print(f"❌ 传统检测未发现，ASR时序模式显示无片尾")
                    print(f"  ASR模式: {reason}")
                    ending_info = EndingCreditsInfo(
                        has_ending=False,
                        duration=0.0,
                        confidence=0.90,
                        method='asr_timing_normal_drama',
                        features={
                            'reason': 'ASR持续到结尾，正常剧情',
                            'asr_timing_pattern': asr_timing_pattern
                        }
                    )
                else:
                    # 混合特征，保守判断
                    print(f"❌ 未检测到明显的片尾特征")
                    ending_info = EndingCreditsInfo(
                        has_ending=False,
                        duration=0.0,
                        confidence=0.0,
                        method='none',
                        features={'methods_used': [], 'features_found': []}
                    )
            else:
                # 无ASR数据
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

            # 【关键】应用ASR时序模式修正逻辑
            similarity_duration = sim_duration if 'similarity' in [d[0] for d in durations] else 0.0
            similarity_conf = sim_conf if 'similarity' in [d[0] for d in durations] else 0.0

            has_ending, final_duration, final_conf, final_method = self._apply_asr_correction(
                similarity_result=(similarity_duration, similarity_conf),
                asr_timing_pattern=asr_timing_pattern,
                total_duration=total_duration
            )

            # 计算综合置信度
            if has_ending:
                confidence = min(0.98, final_conf)
                print(f"检测方法: {final_method}")
                if asr_timing_pattern:
                    print(f"ASR修正: 已应用ASR时序模式分析")
                    print(f"修正原因: {asr_timing_pattern.get('reason', 'N/A')}")
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
                        'asr_timing_pattern': asr_timing_pattern if asr_timing_pattern else None
                    }
                )
            else:
                # ASR判断为误判，返回无片尾
                print(f"检测方法: {final_method}")
                print(f"❌ 修正结果: 无片尾（ASR时序模式检测到正常剧情）")

                ending_info = EndingCreditsInfo(
                    has_ending=False,
                    duration=0.0,
                    confidence=1.0,
                    method=final_method,
                    features={
                        'reason': 'ASR时序模式修正误判',
                        'asr_timing_pattern': asr_timing_pattern,
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

    def _asr_enhanced_detection(self, video_path: str, total_duration: float, use_consensus: bool = True) -> Optional[Dict]:
        """
        【重写】ASR时序模式分析（第二层防护，支持多次转录）

        V14.2 更新：
        - 转录视频最后10秒的音频（从3.5秒增加），确保找到真正的最后ASR
        - 实施保守策略：只剪纯静音部分（最后ASR结束后+0.2秒缓冲）
        - 确保不会剪掉任何台词

        Args:
            video_path: 视频路径
            total_duration: 视频总时长
            use_consensus: 是否使用多次转录取最稳定结果（默认True）

        Returns:
            ASR时序模式分析结果，包含：
            - pattern: 'short_asr_long_silence' | 'long_asr_no_silence' | 'no_asr_only_bgm' | 'mixed'
            - reason: 判断原因
            - asr_duration: ASR总时长
            - silence_after_asr: ASR结束后的静音时长
            - consistency_ratio: 一致性比例（如果使用多次转录）
        """
        if not ASR_AVAILABLE:
            return None

        try:
            # 初始化ASR转录器
            transcriber = ASRTranscriber(model_size="base")

            # 初始化ASR分析器
            analyzer = ASRContentAnalyzer()

            if use_consensus:
                # 【优化3】多次转录，取最稳定的结果
                # V14.2: 扩大检测范围到10秒，确保找到最后ASR
                print(f"  🎙️  多次转录最后{self.CHECK_LAST_SECONDS}秒音频...")
                timing_pattern = analyzer.transcribe_with_consensus(
                    transcriber=transcriber,
                    video_path=video_path,
                    video_end_time=total_duration,
                    n_times=3  # 转录3次
                )
            else:
                # 单次转录
                # V14.2: 扩大检测范围到10秒
                print(f"  🎙️  转录最后{self.CHECK_LAST_SECONDS}秒音频...")
                asr_segments = transcriber.transcribe_last_seconds(video_path, seconds=self.CHECK_LAST_SECONDS)

                # 分析ASR时序模式
                print(f"  📊 分析ASR时序模式...")
                timing_pattern = analyzer.analyze_timing_pattern(
                    asr_segments=asr_segments,
                    video_end_time=total_duration,
                    check_duration=self.CHECK_LAST_SECONDS
                )

            # 输出分析结果
            print(f"  ASR模式: {timing_pattern['pattern']}")
            print(f"  判断原因: {timing_pattern['reason']}")

            if 'consistency_ratio' in timing_pattern:
                print(f"  一致性: {timing_pattern['consistency_ratio']:.0%}")

            if 'asr_duration' in timing_pattern:
                print(f"  ASR详情: {timing_pattern['asr_duration']:.2f}秒ASR + {timing_pattern['silence_after_asr']:.2f}秒静音")
            else:
                print(f"  ASR详情: 无ASR，{timing_pattern['silence_after_asr']:.2f}秒BGM")

            return timing_pattern

        except Exception as e:
            print(f"  ⚠️  ASR检测失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _apply_asr_correction(
        self,
        similarity_result: Tuple[float, float],
        asr_timing_pattern: Optional[Dict],
        total_duration: float
    ) -> Tuple[bool, float, float, str]:
        """
        【重写】应用ASR时序模式分析修正画面相似度检测的误判

        Args:
            similarity_result: (相似度检测时长, 置信度)
            asr_timing_pattern: ASR时序模式分析结果
            total_duration: 视频总时长

        Returns:
            (是否有片尾, 片尾时长, 置信度, 检测方法)
        """
        sim_duration, sim_conf = similarity_result

        # 如果没有ASR分析，使用相似度结果
        if asr_timing_pattern is None:
            return (sim_duration > self.MIN_ENDING_DURATION, sim_duration, sim_conf, "similarity")

        pattern = asr_timing_pattern.get('pattern', 'unknown')
        reason = asr_timing_pattern.get('reason', '')

        # 情况1: 纯BGM（无ASR）→ 可能是片尾（V14.3修复）
        if pattern == 'no_asr_only_bgm':
            if sim_duration > self.MIN_ENDING_DURATION:
                print(f"\n[ASR修正] {reason}")
                print(f"  画面相似度: {sim_duration:.2f}秒")

                # 【V14.3修复】无ASR的片尾可能是剧情画面，需要保守处理
                MAX_SAFE_ENDING_NO_ASR = 4.0  # 无ASR时，超过4秒就很可能是剧情

                if sim_duration > MAX_SAFE_ENDING_NO_ASR:
                    # 片尾过长且无ASR，但可能有画面内容，保守剪裁
                    safe_ending = min(sim_duration * 0.5, 3.0)  # 最多剪掉一半，但不超过3秒
                    print(f"  ⚠️  片尾过长({sim_duration:.2f}秒)且无ASR，可能有剧情画面")
                    print(f"  📊 保守策略: 只剪掉 {safe_ending:.2f}秒")
                    print(f"  ✅ 综合判断: 有片尾（保守剪裁）")
                    return (True, safe_ending, min(0.90, sim_conf), "asr_timing_no_asr_conservative")
                else:
                    # 片尾长度适中，可以剪掉
                    print(f"  ✅ 综合判断: 有片尾（无ASR，只有BGM，长度适中）")
                    return (True, sim_duration, min(0.95, sim_conf + 0.1), "asr_timing_no_asr")
            else:
                return (False, 0.0, 0.0, "none")

        # 情况2: 短ASR + 长静音 → 片尾特征 ✅
        if pattern == 'short_asr_long_silence':
            print(f"\n[ASR修正] {reason}")
            print(f"  画面相似度: {sim_duration:.2f}秒")

            if sim_duration > self.MIN_ENDING_DURATION:
                # 画面相似度也支持 → 确认是片尾
                print(f"  ✅ 综合判断: 有片尾（短ASR+长静音+画面相似）")
                return (True, sim_duration, min(0.95, sim_conf + 0.15), "asr_timing_verified")
            else:
                # 画面相似度不支持，但ASR模式支持 → 可能是片尾
                # 使用ASR结束后的静音时长作为片尾时长
                ending_duration = asr_timing_pattern['silence_after_asr']
                print(f"  ⚠️  画面相似不支持，但ASR模式支持")
                print(f"  ✅ 综合判断: 有片尾（短ASR+长静音，时长{ending_duration:.2f}秒）")
                return (True, ending_duration, 0.75, "asr_timing_only")

        # 情况3: 长ASR + 持续到结尾 → 正常剧情特征 ✅
        if pattern == 'long_asr_no_silence':
            print(f"\n[ASR修正] {reason}")
            print(f"  ASR详情: {asr_timing_pattern['asr_duration']:.2f}秒，距结尾{asr_timing_pattern['silence_after_asr']:.2f}秒")
            print(f"  画面相似度: {sim_duration:.2f}秒")

            # 即使画面相似，ASR模式也强烈指示这是正常剧情
            print(f"  ✅ 综合判断: 无片尾（ASR持续到结尾，正常剧情）")
            return (False, 0.0, 0.95, "asr_timing_normal_drama")

        # 情况4: 混合特征 → 保守判断（V14.3修复）
        if pattern == 'mixed':
            print(f"\n[ASR修正] {reason}")
            print(f"  ⚠️  ASR模式不明确（混合特征）")

            # 【V14.3修复】检查片尾时长，对长片尾更保守
            # 如果片尾过长（>6秒），极大概率是剧情内容，应该减少剪掉
            MAX_SAFE_ENDING = 6.0  # 超过6秒的片尾需要更保守

            if sim_duration > self.MIN_ENDING_DURATION:
                silence_after_asr = asr_timing_pattern.get('silence_after_asr', 0.0)

                if sim_duration > MAX_SAFE_ENDING:
                    # 片尾过长，只剪掉纯静音部分（ASR结束后）
                    # 保留有画面变化和ASR的部分
                    safe_ending = min(silence_after_asr, 3.0)  # 最多剪掉3秒纯静音
                    print(f"  ⚠️  片尾过长({sim_duration:.2f}秒)，可能是剧情内容")
                    print(f"  📊 保守策略: 只剪掉纯静音部分 {safe_ending:.2f}秒")
                    print(f"  ✅ 综合判断: 有片尾（保守剪裁，保留剧情内容）")
                    return (True, safe_ending, sim_conf * 0.7, "asr_timing_mixed_conservative")
                else:
                    # 片尾长度适中，使用画面相似度结果
                    print(f"  📊 片尾长度适中({sim_duration:.2f}秒)，使用画面相似度结果")
                    print(f"  ✅ 综合判断: 有片尾（混合特征）")
                    return (True, sim_duration, sim_conf * 0.8, "asr_timing_mixed")
            else:
                return (False, 0.0, 0.0, "none")

        # 默认情况：使用相似度结果
        return (sim_duration > self.MIN_ENDING_DURATION, sim_duration, sim_conf, "similarity")

    def _apply_conservative_ending(
        self,
        sim_duration: float,
        asr_pattern: Dict,
        default_min: float = 2.0
    ) -> float:
        """
        【V14.4新增】应用保守剪裁策略，避免错误剪掉剧情内容

        V14.4更新：
        - 增加ASR安全缓冲区，避免剪掉最后一句台词的结尾部分
        - 优化mixed模式的判断逻辑

        Args:
            sim_duration: 画面相似度检测的片尾时长
            asr_pattern: ASR时序模式分析结果
            default_min: 默认最小片尾时长

        Returns:
            修正后的片尾时长
        """
        # 如果没有ASR模式信息，返回原始时长
        if not asr_pattern:
            return sim_duration if sim_duration > default_min else default_min

        pattern = asr_pattern.get('pattern', 'unknown')
        silence_after_asr = asr_pattern.get('silence_after_asr', 0.0)
        last_asr_end = asr_pattern.get('last_asr_end', None)

        # 【V14.5关键修复】优化ASR安全缓冲区，平衡剪裁片尾和保留台词
        # 因为最后一句台词可能在ASR检测窗口之外，或者台词的尾音需要保留
        ASR_SAFETY_BUFFER = 0.15  # V14.5: ASR结束后0.15秒缓冲区（恢复之前完美版本的参数）

        # V14.5: 对不同的ASR模式应用保守策略
        if pattern == 'mixed':
            # 混合模式：有ASR但混合了静音
            MAX_SAFE_ENDING = 6.0  # 超过6秒需要保守处理

            if sim_duration > MAX_SAFE_ENDING:
                # 【V14.5修复】片尾过长时，考虑ASR缓冲区
                # 如果有last_asr_end信息，使用它来计算更精确的安全片尾
                if last_asr_end is not None:
                    # 计算：纯静音部分 - ASR缓冲区
                    # V14.5: 减少缓冲区从3秒到1秒，确保至少剪掉1秒
                    safe_ending = max(1.0, silence_after_asr - ASR_SAFETY_BUFFER)
                    safe_ending = min(safe_ending, 3.0)  # 最多剪掉3秒（从2秒增加）
                    print(f"    [V14.5优化剪裁] mixed模式，片尾过长({sim_duration:.2f}s)")
                    print(f"    → 考虑ASR缓冲区1秒，纯静音{silence_after_asr:.2f}s - 缓冲区1s = {safe_ending:.2f}s")
                    return safe_ending
                else:
                    # 没有last_asr_end信息，使用旧逻辑
                    safe_ending = min(silence_after_asr, 2.0)
                    print(f"    [V14.3保守剪裁] mixed模式，片尾过长({sim_duration:.2f}s) → {safe_ending:.2f}s")
                    return safe_ending
            else:
                # 片尾长度适中（3-6秒），需要剪掉一部分
                # V14.5: 3-6秒的片尾应该剪掉2秒
                if sim_duration > 3.0:
                    print(f"    [V14.5优化剪裁] mixed模式，片尾适中({sim_duration:.2f}s)，剪掉2秒")
                    return 2.0
                else:
                    # 3秒以内保留
                    print(f"    [V14.5优化剪裁] mixed模式，片尾较短({sim_duration:.2f}s ≤ 3s)，保留")
                    return 0.0

        elif pattern == 'no_asr_only_bgm':
            # 纯BGM模式：更严格的检查
            MAX_SAFE_ENDING_NO_ASR = 4.0  # 无ASR时，超过4秒就很可能是剧情

            if sim_duration > MAX_SAFE_ENDING_NO_ASR:
                # 片尾过长且无ASR，保守剪裁
                safe_ending = min(sim_duration * 0.5, 2.0)  # V14.4: 最多剪掉2秒
                print(f"    [V14.4保守剪裁] no_asr模式，片尾过长({sim_duration:.2f}s) → {safe_ending:.2f}s")
                return safe_ending
            else:
                # 片尾长度适中，保守保留
                print(f"    [V14.4保守剪裁] no_asr模式，片尾适中({sim_duration:.2f}s ≤ 4s)，保留")
                return 0.0

        elif pattern == 'long_asr_no_silence':
            # 长ASR持续到结尾：正常剧情，不剪掉
            print(f"    [V14.4判断] long_asr_no_silence模式，ASR持续到结尾，正常剧情，不剪掉")
            return 0.0

        elif pattern == 'short_asr_long_silence':
            # 短ASR + 长静音：可能是片尾旁白
            # 但需要考虑ASR缓冲区
            if last_asr_end is not None and silence_after_asr > ASR_SAFETY_BUFFER:
                # 静音足够长（>3秒），可以剪掉超出缓冲区的部分
                safe_ending = silence_after_asr - ASR_SAFETY_BUFFER
                print(f"    [V14.4保守剪裁] short_asr_long_silence模式")
                print(f"    → 静音{silence_after_asr:.2f}s - 缓冲区3s = {safe_ending:.2f}s")
                return safe_ending
            else:
                # 静音不够长，保留
                print(f"    [V14.4保守剪裁] short_asr_long_silence模式，静音不足，保留")
                return 0.0

        else:
            # 其他模式，保守处理
            return sim_duration if sim_duration > default_min else default_min

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
    【重写】批量检测项目中所有视频的片尾（支持跨集一致性验证）

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

    # ========== 第一轮：收集所有视频的ASR时序模式 ==========
    print(f"\n{'=' * 70}")
    print(f"第一轮：收集所有视频的ASR时序模式")
    print(f"{'=' * 70}")

    asr_timing_patterns = {}  # {episode: timing_pattern}
    similarity_results = {}    # {episode: (duration, confidence)}

    for idx, video_file in enumerate(video_files, 1):
        episode = idx
        print(f"\n[{idx}/{len(video_files)}] 处理第{episode}集: {video_file.name}")

        # 获取视频时长
        total_duration = detector._get_video_duration(str(video_file))

        # 检查项目配置
        if not should_detect_ending(project_name):
            print(f"  [项目配置] 该项目配置为无需检测片尾")
            asr_timing_patterns[episode] = {
                'pattern': 'project_config_skip',
                'reason': '项目配置为无片尾'
            }
            similarity_results[episode] = (0.0, 0.0)
            continue

        # ASR时序模式分析
        if ASR_AVAILABLE:
            print(f"  [ASR分析] 转录最后3.5秒...")
            asr_timing_pattern = detector._asr_enhanced_detection(
                str(video_file),
                total_duration
            )
            if asr_timing_pattern:
                asr_timing_patterns[episode] = asr_timing_pattern
            else:
                # ASR检测失败
                asr_timing_patterns[episode] = {
                    'pattern': 'asr_failed',
                    'reason': 'ASR检测失败'
                }
        else:
            print(f"  [ASR分析] ASR模块未安装")
            asr_timing_patterns[episode] = {
                'pattern': 'asr_unavailable',
                'reason': 'ASR模块未安装'
            }

        # 画面相似度检测
        print(f"  [画面分析] 检测画面相似度...")
        sim_duration, sim_conf = detector._detect_by_similarity(
            str(video_file),
            total_duration
        )
        similarity_results[episode] = (sim_duration, sim_conf)

        if sim_duration > detector.MIN_ENDING_DURATION:
            print(f"    → 检测到片尾: {sim_duration:.2f}秒")
        else:
            print(f"    → 未检测到片尾")

    # ========== 第二轮：跨集一致性统计 ==========
    print(f"\n{'=' * 70}")
    print(f"第二轮：跨集一致性统计")
    print(f"{'=' * 70}")

    # 统计各种ASR模式的比例
    pattern_counts = {}
    for episode, pattern_info in asr_timing_patterns.items():
        pattern = pattern_info.get('pattern', 'unknown')
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    total_episodes = len(asr_timing_patterns)

    print(f"\nASR模式分布（共{total_episodes}集）:")
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        ratio = count / total_episodes
        print(f"  {pattern}: {count}集 ({ratio:.1%})")

    # 计算跨集一致性得分
    # 短ASR+长静音 和 纯BGM → 片尾特征
    ending_patterns = ['short_asr_long_silence', 'no_asr_only_bgm']
    ending_count = sum(pattern_counts.get(p, 0) for p in ending_patterns)
    ending_ratio = ending_count / total_episodes if total_episodes > 0 else 0

    # 长ASR+持续到结尾 → 正常剧情特征
    normal_drama_pattern = 'long_asr_no_silence'
    normal_drama_count = pattern_counts.get(normal_drama_pattern, 0)
    normal_drama_ratio = normal_drama_count / total_episodes if total_episodes > 0 else 0

    print(f"\n跨集一致性分析:")
    print(f"  片尾特征模式（短ASR+长静音/纯BGM）: {ending_count}集 ({ending_ratio:.1%})")
    print(f"  正常剧情模式（长ASR+持续结尾）: {normal_drama_count}集 ({normal_drama_ratio:.1%})")

    # ========== 第三轮：综合判断（ASR时序 + 跨集一致性） ==========
    print(f"\n{'=' * 70}")
    print(f"第三轮：综合判断（ASR时序 + 跨集一致性 + 画面相似度）")
    print(f"{'=' * 70}")

    episodes = []
    for idx, video_file in enumerate(video_files, 1):
        episode = idx
        total_duration = detector._get_video_duration(str(video_file))

        print(f"\n[{idx}/{len(video_files)}] 判断第{episode}集")

        # 检查项目配置
        if not should_detect_ending(project_name):
            config = load_project_config(project_name)
            result = VideoEndingResult(
                video_path=str(video_file),
                episode=episode,
                total_duration=total_duration,
                ending_info=EndingCreditsInfo(
                    has_ending=False,
                    duration=0.0,
                    confidence=1.0,
                    method="project_config",
                    features={"reason": "项目配置为无片尾"}
                ),
                effective_duration=total_duration
            )
            episodes.append(result)
            continue

        # 获取这一集的ASR模式和相似度结果
        asr_pattern = asr_timing_patterns[episode]
        sim_duration, sim_conf = similarity_results[episode]

        # 综合评分
        scores = {}
        reasons = []

        # --- 指标1：ASR时序模式（权重：0.8）---
        pattern = asr_pattern.get('pattern', 'unknown')
        consistency_ratio = asr_pattern.get('consistency_ratio', 1.0)  # 获取一致性比例

        if pattern == 'short_asr_long_silence':
            # 根据一致性调整权重
            asr_timing_score = 0.8 * consistency_ratio
            scores['asr_timing'] = asr_timing_score
            if consistency_ratio < 1.0:
                reasons.append(f"~ 短ASR+长静音（{asr_pattern['reason']}，一致性{consistency_ratio:.0%}）")
            else:
                reasons.append(f"✓ 短ASR+长静音（{asr_pattern['reason']}）")
        elif pattern == 'no_asr_only_bgm':
            scores['asr_timing'] = 0.6
            reasons.append(f"✓ 纯BGM（{asr_pattern['reason']}）")
        elif pattern == 'long_asr_no_silence':
            scores['asr_timing'] = -0.9
            reasons.append(f"✗ 长ASR+持续结尾（{asr_pattern['reason']}）")
        else:
            scores['asr_timing'] = 0.0
            reasons.append(f"~ ASR模式不确定（{pattern}）")

        # --- 指标2：跨集一致性（【优化1】权重：1.0，提高了重要性）---
        if total_episodes >= 3:
            if ending_ratio >= 0.7:
                # 大部分集数有片尾特征
                # 【优化2】根据比例线性调整权重
                cross_episode_score = 1.0 * (0.7 + (ending_ratio - 0.7) * 1.0)  # 0.7~1.0范围
                scores['cross_episode'] = cross_episode_score
                reasons.append(f"✓ 同项目{ending_ratio:.0%}集数有片尾特征")
            elif normal_drama_ratio >= 0.7:
                # 大部分集数有正常剧情特征
                cross_episode_score = -1.0 * (0.7 + (normal_drama_ratio - 0.7) * 1.0)  # -0.7~-1.0范围
                scores['cross_episode'] = cross_episode_score
                reasons.append(f"✗ 同项目{normal_drama_ratio:.0%}集数有正常剧情特征")
            else:
                scores['cross_episode'] = 0.0
                reasons.append("~ 跨集特征不明确")
        else:
            scores['cross_episode'] = 0.0
            reasons.append("~ 集数不足，跳过跨集验证")

        # --- 指标3：画面相似度（权重：0.3）---
        if sim_duration > detector.MIN_ENDING_DURATION:
            scores['similarity'] = 0.3
            reasons.append(f"✓ 画面相似（{sim_duration:.2f}秒）")
        else:
            scores['similarity'] = -0.1
            reasons.append("✗ 画面不相似")

        # --- 【优化2】综合判断（调整阈值）---
        total_score = sum(scores.values())

        print(f"  评分详情:")
        print(f"    ASR时序:     {scores.get('asr_timing', 0):+.1f}")
        print(f"    跨集一致性:  {scores.get('cross_episode', 0):+.1f}")
        print(f"    画面相似度:  {scores.get('similarity', 0):+.1f}")
        print(f"    综合得分:    {total_score:+.1f}")
        print(f"  判断依据:")
        for reason in reasons:
            print(f"    {reason}")

        # 【优化2】调整判断阈值，更细致的分层
        if total_score >= 1.5:
            # 高置信度：明显有片尾
            has_ending = True
            confidence = min(0.98, 0.8 + total_score * 0.05)
            method = "comprehensive_very_high_confidence"
            # V14.3: 应用保守剪裁策略
            final_duration = detector._apply_conservative_ending(
                sim_duration, asr_pattern, default_min=detector.MIN_ENDING_DURATION
            )
        elif total_score >= 0.8:
            # 中高置信度：很可能有片尾
            has_ending = True
            confidence = min(0.95, 0.7 + total_score * 0.1)
            method = "comprehensive_high_confidence"
            # V14.3: 应用保守剪裁策略
            final_duration = detector._apply_conservative_ending(
                sim_duration, asr_pattern, default_min=detector.MIN_ENDING_DURATION
            )
        elif total_score >= 0.3:
            # 中等置信度：可能有片尾
            has_ending = True
            confidence = 0.70
            method = "comprehensive_moderate"
            # V14.3: 应用保守剪裁策略
            final_duration = detector._apply_conservative_ending(
                sim_duration, asr_pattern, default_min=detector.MIN_ENDING_DURATION
            )
        elif total_score <= -1.0:
            # 高置信度：明显无片尾
            has_ending = False
            confidence = min(0.98, 0.8 + abs(total_score) * 0.05)
            method = "comprehensive_negative_very_high_confidence"
            final_duration = 0.0
        elif total_score <= -0.5:
            # 中高置信度：很可能无片尾
            has_ending = False
            confidence = min(0.95, 0.7 + abs(total_score) * 0.1)
            method = "comprehensive_negative_high_confidence"
            final_duration = 0.0
        elif total_score < 0.0:
            # 倾向无片尾
            has_ending = False
            confidence = 0.70
            method = "comprehensive_negative_moderate"
            final_duration = 0.0
        else:
            # 0.0到0.3之间：不确定的情况，优先看跨集一致性和ASR时序
            # 优先级：跨集一致性 > ASR时序 > 画面相似度
            if scores.get('cross_episode', 0) >= 0.5:
                # 跨集一致性强烈支持有片尾
                has_ending = True
                confidence = 0.75
                method = "cross_episode_decisive_positive"
                # V14.3: 应用保守剪裁策略
                final_duration = detector._apply_conservative_ending(
                    sim_duration, asr_pattern, default_min=detector.MIN_ENDING_DURATION
                )
            elif scores.get('cross_episode', 0) <= -0.5:
                # 跨集一致性强烈支持无片尾
                has_ending = False
                confidence = 0.85
                method = "cross_episode_decisive_negative"
                final_duration = 0.0
            elif pattern == 'long_asr_no_silence':
                # ASR时序强烈支持无片尾
                has_ending = False
                confidence = 0.80
                method = "asr_timing_decisive"
                final_duration = 0.0
            elif pattern == 'short_asr_long_silence' or pattern == 'no_asr_only_bgm':
                # ASR时序支持有片尾
                has_ending = True
                confidence = 0.75
                method = "asr_timing_decisive_positive"
                final_duration = sim_duration if sim_duration > detector.MIN_ENDING_DURATION else 2.0
            else:
                # 完全不确定，保守判断
                has_ending = False
                confidence = 0.55
                method = "conservative"
                final_duration = 0.0

        print(f"  最终判断: {'有片尾' if has_ending else '无片尾'} (置信度{confidence:.0%})")

        # 创建结果
        result = VideoEndingResult(
            video_path=str(video_file),
            episode=episode,
            total_duration=total_duration,
            ending_info=EndingCreditsInfo(
                has_ending=has_ending,
                duration=final_duration if has_ending else 0.0,
                confidence=confidence,
                method=method,
                features={
                    'total_score': total_score,
                    'scores': scores,
                    'reasons': reasons,
                    'asr_pattern': asr_pattern,
                    'cross_episode_stats': {
                        'ending_ratio': ending_ratio,
                        'normal_drama_ratio': normal_drama_ratio,
                        'pattern_counts': pattern_counts
                    }
                }
            ),
            effective_duration=total_duration - (final_duration if has_ending else 0.0)
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
    output_dir = sys.argv[3] if len(sys.argv) > 3 else 'data/hangzhou-leiming/ending_credits'

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
        actual_output_file = Path(output_dir) / f"{result.project_name}_ending_credits.json"
        print(f"结果已保存到: {actual_output_file}")

    if result:
        print(f"\n✅ 检测完成！")
        print(f"结果已保存到: {output_dir}")


if __name__ == "__main__":
    main()
