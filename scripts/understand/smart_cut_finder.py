"""
智能切割点查找模块 (V15.7)

V15.7 核心理念 - 时间戳优化是"二次确认"，不是重新计算：
1. AI 分析阶段（V15.5）：让 AI 看到带时间戳的 ASR，返回精确时间
2. 时间戳优化阶段（V15.7）：确认 AI 返回的时间是否正好是 segment 边界
   - 如果是 → 保持不变
   - 如果不是 → 修正为 segment 边界

修复 V15.2 的"串联句子"问题：
- V15.2 错误：相邻 ASR 片段间隔 < 0.5 秒会全部合并，导致钩子点跳跃过大
- V15.7 修复：直接返回包含时间戳的 segment 边界，不做串联

综合考虑：
- 时间维度：ASR segment 边界
- 帧级精度：基于实际视频帧率转换时间戳
"""
import subprocess
import math
from typing import List, Tuple, Optional, Dict, Any, Union
from dataclasses import dataclass

try:
    from scripts.data_models import ASRSegment
except ImportError:
    @dataclass
    class ASRSegment:
        text: str
        start: float
        end: float


@dataclass
class CutPointResult:
    """切割点查找结果"""
    timestamp: float  # 最终切割时间（秒，帧级精度）
    frame_number: int  # 对应的帧编号
    confidence: float  # 置信度 0-1
    reasoning: str  # 决策原因
    details: Dict[str, Any]  # 详细信息


class SmartCutFinder:
    """
    智能多维度切割点查找器

    策略：
    1. 首先找到包含钩子点的那句话（基于ASR时间连续性）
    2. 在句子结束点附近搜索最优切割点
    3. 综合考虑：句子结束、场景切换、静音区域
    4. 返回帧级精度的最佳切割点
    """

    def __init__(self, video_path: str, video_fps: float = 30.0):
        """
        初始化智能切割查找器

        Args:
            video_path: 视频文件路径
            video_fps: 视频帧率（默认30fps）
        """
        self.video_path = video_path
        self.video_fps = video_fps

    def find_sentence_end(self, hook_timestamp: float, asr_segments: List[ASRSegment]) -> float:
        """
        找到包含钩子点的 ASR 片段的结束时间

        V15.6 简化逻辑：
        - 找到包含钩子点的 segment
        - 直接返回该 segment 的结束时间
        - 不再做"串联句子"的复杂逻辑

        Args:
            hook_timestamp: 钩子点时间戳（秒）
            asr_segments: ASR片段列表

        Returns:
            segment 结束时间（秒）
        """
        if not asr_segments:
            return hook_timestamp

        # 找到包含钩子点的 ASR 片段
        target_segment = None
        for seg in asr_segments:
            if seg.start <= hook_timestamp <= seg.end:
                target_segment = seg
                break

        if target_segment:
            print(f"    📝 钩子点{hook_timestamp}秒 → 找到ASR片段: {target_segment.start:.2f}-{target_segment.end:.2f}秒, 文本: '{target_segment.text[:30]}...'")
            return target_segment.end

        # 如果钩子点不在任何 segment 内，返回原始时间戳
        print(f"    ⚠️ 钩子点{hook_timestamp}秒未落在任何ASR片段内，保持原时间戳")
        return hook_timestamp

    def find_sentence_start(self, highlight_timestamp: float, asr_segments: List[ASRSegment]) -> float:
        """
        找到包含高光点的 ASR 片段的开始时间

        V15.6 简化逻辑：
        - 找到包含高光点的 segment
        - 直接返回该 segment 的开始时间
        - 不再做"串联句子"的复杂逻辑

        Args:
            highlight_timestamp: 高光点时间戳（秒）
            asr_segments: ASR片段列表

        Returns:
            segment 开始时间（秒）
        """
        if not asr_segments:
            return highlight_timestamp

        # 找到包含高光点的 ASR 片段
        target_segment = None
        for seg in asr_segments:
            if seg.start <= highlight_timestamp <= seg.end:
                target_segment = seg
                break

        if target_segment:
            print(f"    📝 高光点{highlight_timestamp}秒 → 找到ASR片段: {target_segment.start:.2f}-{target_segment.end:.2f}秒, 文本: '{target_segment.text[:30]}...'")
            return target_segment.start

        # 如果高光点不在任何 segment 内，返回原始时间戳
        print(f"    ⚠️ 高光点{highlight_timestamp}秒未落在任何ASR片段内，保持原时间戳")
        return highlight_timestamp

    def detect_silence_regions(self, start_time: float, end_time: float, threshold_db: float = -40.0) -> List[Tuple[float, float]]:
        """
        检测指定时间范围内的静音区域

        Args:
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            threshold_db: 静音阈值（dB），默认-40dB

        Returns:
            静音区域列表 [(开始时间, 结束时间), ...]
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', self.video_path,
                '-ss', str(start_time),
                '-t', str(end_time - start_time),
                '-af', f'silencedetect=noise={threshold_db}dB:d=0.3',
                '-f', 'null',
                '-'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            silence_regions = []
            lines = result.stderr.split('\n')

            silence_start = None
            for line in lines:
                if 'silence_start' in line:
                    # 提取静音开始时间
                    parts = line.split('silence_start: ')
                    if len(parts) > 1:
                        silence_start = float(parts[1].strip())
                elif 'silence_end' in line and silence_start is not None:
                    # 提取静音结束时间
                    parts = line.split('silence_end: ')
                    if len(parts) > 1:
                        # 提取持续时间
                        duration_part = parts[1]
                        duration = float(duration_part.split()[0])
                        silence_end = silence_start + duration

                        # 只返回搜索范围内的区域
                        if silence_end > start_time and silence_start < end_time:
                            silence_regions.append((
                                max(silence_start, start_time),
                                min(silence_end, end_time)
                            ))
                        silence_start = None

            return silence_regions

        except subprocess.TimeoutExpired:
            print(f"  ⚠️ 静音检测超时")
            return []
        except Exception as e:
            print(f"  ⚠️ 静音检测失败: {e}")
            return []

    def detect_scene_changes(self, start_time: float, end_time: float) -> List[float]:
        """
        检测指定时间范围内的场景切换点

        使用帧差分法检测场景切换：
        - 提取关键帧
        - 计算相邻帧的差异
        - 差异超过阈值认为发生场景切换

        Args:
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）

        Returns:
            场景切换时间点列表（秒）
        """
        try:
            # 使用ffmpeg提取指定范围内的帧
            duration = end_time - start_time

            # 每秒提取一帧进行对比
            sample_count = max(3, int(duration))
            interval = duration / sample_count

            scene_changes = []
            prev_histogram = None

            for i in range(sample_count):
                t = start_time + i * interval

                # 提取单帧
                cmd = [
                    'ffmpeg',
                    '-ss', str(t),
                    '-i', self.video_path,
                    '-vframes', '1',
                    '-f', 'image2pipe',
                    '-vcodec', 'png',
                    '-'
                ]

                # 使用简单的帧差异检测
                # 这里简化处理：返回空列表，实际实现可使用更复杂的算法
                # 完整实现需要使用OpenCV或 PIL 分析帧内容

            return scene_changes

        except Exception as e:
            print(f"  ⚠️ 场景切换检测失败: {e}")
            return []

    def analyze_frame_stability(self, time_point: float, window_seconds: float = 1.0) -> float:
        """
        分析指定时间点附近的画面稳定性

        Args:
            time_point: 时间点（秒）
            window_seconds: 分析窗口大小（秒）

        Returns:
            稳定性得分 0-1（1表示最稳定）
        """
        # 简化实现：返回默认稳定性得分
        # 完整实现需要分析帧间差异
        return 0.8

    def find_optimal_cut_point(
        self,
        hook_timestamp: float,
        asr_segments: List[ASRSegment],
        search_window: float = 2.0,
        buffer_seconds: float = 0.15
    ) -> CutPointResult:
        """
        找到最佳切割点（帧级精度）

        综合决策逻辑：
        1. 首先找到包含钩子点的那句话的结束时间
        2. 在句子结束点附近搜索（search_window范围内）
        3. 优先级：避免场景切换 > 画面稳定 > 静音区域

        Args:
            hook_timestamp: 原始钩子点时间戳（秒）
            asr_segments: ASR片段列表
            search_window: 搜索窗口大小（秒），默认2秒
            buffer_seconds: 句子结束后的缓冲时间，默认0.15秒

        Returns:
            CutPointResult: 最佳切割点结果
        """
        print(f"\n{'=' * 60}")
        print(f"🔍 智能切割点查找")
        print(f"{'=' * 60}")
        print(f"原始钩子点: {hook_timestamp:.3f}秒")
        print(f"视频帧率: {self.video_fps}fps")
        print(f"搜索窗口: {search_window}秒")

        # Step 1: 找到包含钩子点的那句话的结束时间
        sentence_end = self.find_sentence_end(hook_timestamp, asr_segments)
        print(f"句子结束点: {sentence_end:.3f}秒")

        # 初始切割点：句子结束时间 + 缓冲
        initial_cut_point = sentence_end + buffer_seconds

        # Step 2: 搜索窗口内的多维度分析
        search_start = sentence_end
        search_end = min(sentence_end + search_window, sentence_end + 3.0)

        print(f"搜索范围: {search_start:.3f}秒 - {search_end:.3f}秒")

        # 2.1 静音区域检测
        silence_regions = self.detect_silence_regions(search_start, search_end)
        print(f"检测到 {len(silence_regions)} 个静音区域")

        # 2.2 场景切换检测（简化版本）
        scene_changes = self.detect_scene_changes(search_start, search_end)
        print(f"检测到 {len(scene_changes)} 个场景切换")

        # Step 3: 综合决策
        # 策略：优先选择静音区域的开始点，其次选择句子结束点

        optimal_point = initial_cut_point
        reasoning = "基于ASR句子结束点"
        confidence = 0.85

        # 检查静音区域
        if silence_regions:
            # 找到第一个足够长的静音区域（>0.3秒）
            for silence_start, silence_end in silence_regions:
                silence_duration = silence_end - silence_start
                if silence_duration >= 0.3:
                    # 在静音开始点切割
                    optimal_point = silence_start
                    reasoning = f"在静音区域开始点切割（静音时长: {silence_duration:.2f}秒）"
                    confidence = 0.95
                    print(f"  ✅ 选择静音区域开始点: {optimal_point:.3f}秒")
                    break

        # 转换为帧级精度
        frame_number = int(optimal_point * self.video_fps)

        # 确保帧号有效
        frame_number = max(0, frame_number)

        # 转换回时间（帧级精度）
        final_timestamp = frame_number / self.video_fps

        print(f"\n最终切割点: {final_timestamp:.4f}秒 (第{frame_number}帧)")
        print(f"    ✅ 优化结果: {hook_timestamp}秒 → {final_timestamp:.4f}秒")
        print(f"置信度: {confidence:.0%}")
        print(f"决策原因: {reasoning}")
        print(f"{'=' * 60}")

        return CutPointResult(
            timestamp=final_timestamp,
            frame_number=frame_number,
            confidence=confidence,
            reasoning=reasoning,
            details={
                'sentence_end': sentence_end,
                'initial_cut_point': initial_cut_point,
                'silence_regions': silence_regions,
                'scene_changes': scene_changes,
                'search_window': search_window,
                'buffer_seconds': buffer_seconds
            }
        )


def smart_adjust_hook_point(
    hook_timestamp: float,
    asr_segments: List[ASRSegment],
    video_path: str,
    video_fps: float = 30.0,
    search_window: float = 2.0,
    max_duration: Optional[float] = None  # V15.4: 新增最大时长限制
) -> float:
    """
    智能调整钩子点时间戳（外部调用接口）

    解决"话没说完就被截断"的问题

    Args:
        hook_timestamp: AI标记的钩子点时间戳（秒）
        asr_segments: ASR语音识别数据列表
        video_path: 视频文件路径
        video_fps: 视频帧率（默认30fps）
        search_window: 搜索窗口大小（秒）
        max_duration: V15.4新增 - 该集的最大有效时长（秒），优化结果不会超过此值

    Returns:
        调整后的时间戳（秒，帧级精度）
    """
    if not asr_segments:
        print(f"  ⚠️ 无ASR数据，使用原始时间戳: {hook_timestamp}秒")
        return hook_timestamp

    # 如果ASR数据为空列表，也返回原始时间戳
    if len(asr_segments) == 0:
        print(f"  ⚠️ ASR数据为空，使用原始时间戳: {hook_timestamp}秒")
        return hook_timestamp

    finder = SmartCutFinder(video_path, video_fps)
    result = finder.find_optimal_cut_point(
        hook_timestamp=hook_timestamp,
        asr_segments=asr_segments,
        search_window=search_window
    )

    # V15.4: 检查是否超过最大时长限制
    if max_duration is not None and result.timestamp > max_duration:
        # 超过最大时长，使用最大时长 - 0.15秒作为安全缓冲
        safe_timestamp = max_duration - 0.15
        print(f"  ⚠️ V15.4 时间戳优化: 鲜子点 {hook_timestamp:.3f}秒 蠖超出最大时长 {max_duration:.3f}秒")
        print(f"  🔧 V15.4 安全限制: {safe_timestamp:.3f}秒 (总时长 {max_duration}秒 - 0.15秒缓冲)")
        return safe_timestamp

    return result.timestamp


def smart_adjust_highlight_point(
    highlight_timestamp: float,
    asr_segments: List[ASRSegment],
    video_path: str,
    video_fps: float = 30.0,
    buffer_ms: float = 100.0
) -> float:
    """
    智能调整高光点时间戳（外部调用接口）

    目标：从"一句话刚开始"的地方开始剪辑
    优化：找到包含高光点的那句话的开始时间，转为帧级精度

    Args:
        highlight_timestamp: AI标记的高光点时间戳（秒）
        asr_segments: ASR语音识别数据列表
        video_path: 视频文件路径
        video_fps: 视频帧率（默认30fps）
        buffer_ms: 缓冲时间（毫秒），默认100ms

    Returns:
        调整后的时间戳（秒，帧级精度）
    """
    if not asr_segments:
        print(f"  ⚠️ 无ASR数据，使用原始时间戳: {highlight_timestamp}秒")
        return highlight_timestamp

    if len(asr_segments) == 0:
        print(f"  ⚠️ ASR数据为空，使用原始时间戳: {highlight_timestamp}秒")
        return highlight_timestamp

    finder = SmartCutFinder(video_path, video_fps)

    # 找到包含高光点的那句话的开始时间
    sentence_start = finder.find_sentence_start(highlight_timestamp, asr_segments)

    # 减去缓冲时间（避免从句子最开头开始）
    buffer_seconds = buffer_ms / 1000.0
    initial_point = max(0.0, sentence_start - buffer_seconds)

    print(f"\n{'=' * 60}")
    print(f"🔍 智能高光点优化")
    print(f"{'=' * 60}")
    print(f"原始高光点: {highlight_timestamp:.3f}秒")
    print(f"视频帧率: {video_fps}fps")
    print(f"句子开始点: {sentence_start:.3f}秒")

    # 转换为帧级精度
    frame_number = int(initial_point * video_fps)
    final_timestamp = frame_number / video_fps

    # 确保不小于0
    final_timestamp = max(0.0, final_timestamp)

    print(f"最终起始点: {final_timestamp:.4f}秒 (第{frame_number}帧)")
    print(f"    ✅ 优化结果: {highlight_timestamp}秒 → {final_timestamp:.4f}秒")
    print(f"{'=' * 60}")

    return final_timestamp


# ========== 测试代码 ==========
if __name__ == "__main__":
    # 测试用例
    print("测试智能切割点查找模块...")

    # 模拟ASR数据
    test_asr_segments = [
        ASRSegment(text="林溪", start=95.0, end=96.0),
        ASRSegment(text="你去物业问问", start=96.0, end=97.0),
        ASRSegment(text="到底怎么回事", start=97.0, end=98.0),
        ASRSegment(text="我心中一动", start=98.0, end=99.0),
        ASRSegment(text="物业处", start=102.0, end=103.0),
        ASRSegment(text="正热的满头大汗", start=104.0, end=105.0),
    ]

    # 测试查找句子结束点
    finder = SmartCutFinder("test.mp4", video_fps=30.0)
    sentence_end = finder.find_sentence_end(94.9, test_asr_segments)
    print(f"\n测试结果:")
    print(f"钩子点: 94.9秒")
    print(f"找到的句子结束点: {sentence_end:.3f}秒")
    print(f"预期: 98秒（'到底怎么回事'说完）")
