"""
敏感词检测模块

功能：
1. 从TXT文件加载敏感词列表
2. 检测ASR文本中的敏感词
3. 返回敏感词出现的时间段列表

使用方法：
    from scripts.preprocess.sensitive_detector import (
        load_sensitive_words,
        detect_sensitive_segments
    )

    # 加载敏感词
    words = load_sensitive_words("config/sensitive_words.txt")

    # 检测ASR中的敏感词
    segments = detect_sensitive_segments(asr_segments, words)
"""

import re
from pathlib import Path
from typing import List, Set, Optional
from dataclasses import dataclass


@dataclass
class SensitiveSegment:
    """敏感词片段 - 记录敏感词出现的时间段"""
    episode: int              # 集数
    sensitive_word: str       # 敏感词
    asr_text: str            # ASR原文
    start_time: float        # 开始时间（秒）
    end_time: float          # 结束时间（秒）
    boxes: List = None       # 文字框坐标（精确遮罩用）

    def __post_init__(self):
        if self.boxes is None:
            self.boxes = []

    def __repr__(self):
        return f"SensitiveSegment(ep{self.episode}, {self.start_time:.1f}s-{self.end_time:.1f}s, '{self.sensitive_word}')"


def load_sensitive_words(config_path: str = "config/sensitive_words.txt") -> Set[str]:
    """
    从TXT文件加载敏感词列表

    Args:
        config_path: 配置文件路径，默认为 config/sensitive_words.txt

    Returns:
        敏感词集合（小写）

    格式要求：
        - 每行一个敏感词
        - # 开头的行为注释
        - 空行自动忽略
    """
    config_file = Path(config_path)

    if not config_file.exists():
        print(f"⚠️ 敏感词配置文件不存在: {config_path}")
        print("   将使用空敏感词列表")
        return set()

    sensitive_words = set()

    with open(config_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue

            # 添加到集合（转小写，方便匹配）
            sensitive_words.add(line.lower())

    print(f"✅ 加载敏感词: {len(sensitive_words)}个")

    return sensitive_words


def detect_sensitive_segments(
    asr_segments: List,  # List[ASRSegment]
    sensitive_words: Set[str],
    verbose: bool = True
) -> List[SensitiveSegment]:
    """
    检测ASR文本中的敏感词

    Args:
        asr_segments: ASR片段列表（来自 extract_asr.py）
        sensitive_words: 敏感词集合（词组，如"热死"）
        verbose: 是否打印详细信息

    Returns:
        敏感词片段列表

    匹配规则：
        - 词组匹配：只有敏感词作为一个整体出现才算（如"热死"）
        - 不拆分匹配：单独"热"或"死"不算敏感词
    """
    if not sensitive_words:
        if verbose:
            print("⚠️ 敏感词列表为空，跳过检测")
        return []

    if not asr_segments:
        if verbose:
            print("⚠️ ASR片段列表为空，跳过检测")
        return []

    sensitive_segments = []
    current_episode = 1

    for segment in asr_segments:
        # 获取集数（如果ASRSegment有episode字段）
        episode = getattr(segment, 'episode', current_episode)

        # 获取ASR文本（转小写）
        text = segment.text.lower()
        original_text = segment.text

        # 检查是否包含敏感词（词组匹配，不拆分）
        for word in sensitive_words:
            word_lower = word.lower()
            if word_lower in text:  # 词组完整匹配
                sensitive_seg = SensitiveSegment(
                    episode=episode,
                    sensitive_word=word,
                    asr_text=original_text,
                    start_time=segment.start,
                    end_time=segment.end
                )
                sensitive_segments.append(sensitive_seg)

                if verbose:
                    print(f"  🔍 第{episode}集 {segment.start:.1f}s-{segment.end:.1f}s: 发现敏感词 '{word}'")
                    print(f"     ASR原文: {original_text}")

    if verbose:
        print(f"\n📊 敏感词检测完成: 共发现 {len(sensitive_segments)} 个敏感片段")

    return sensitive_segments


class SensitiveDetector:
    """
    敏感词检测器（类封装版本）

    使用方法：
        detector = SensitiveDetector("config/sensitive_words.txt")
        segments = detector.detect(asr_segments)
    """

    def __init__(self, config_path: str = "config/sensitive_words.txt"):
        """
        初始化检测器

        Args:
            config_path: 敏感词配置文件路径
        """
        self.config_path = config_path
        self.sensitive_words = load_sensitive_words(config_path)

    def detect(self, asr_segments: List, verbose: bool = True) -> List[SensitiveSegment]:
        """
        检测ASR中的敏感词

        Args:
            asr_segments: ASR片段列表
            verbose: 是否打印详细信息

        Returns:
            敏感词片段列表
        """
        return detect_sensitive_segments(asr_segments, self.sensitive_words, verbose)

    def reload(self):
        """重新加载敏感词配置"""
        self.sensitive_words = load_sensitive_words(self.config_path)

    def add_word(self, word: str):
        """添加敏感词"""
        self.sensitive_words.add(word.lower())

    def remove_word(self, word: str):
        """移除敏感词"""
        self.sensitive_words.discard(word.lower())

    def get_words(self) -> Set[str]:
        """获取当前敏感词列表"""
        return self.sensitive_words.copy()


def detect_sensitive_segments_with_ocr_asr(
    ocr_results: List[dict],
    asr_segments: List,
    sensitive_words: Set[str],
    verbose: bool = True
) -> List[SensitiveSegment]:
    """
    OCR + ASR结合的敏感词检测

    流程：
    1. OCR扫描检测到敏感词的时间点和完整句子
    2. 用OCR时间点找到ASR中能拼成相似句子的片段
    3. 合并ASR片段，要求：包含敏感词 + 相似度>60%
    """
    if not ocr_results:
        return []

    if not asr_segments:
        return []

    if verbose:
        print("=" * 60)
        print("OCR + ASR 敏感词检测")
        print("=" * 60)

    def calculate_similarity(text1: str, text2: str) -> float:
        """计算两个句子的相似度（简单字符匹配）"""
        text1 = text1.replace(' ', '').replace('\n', '')
        text2 = text2.replace(' ', '').replace('\n', '')
        
        if not text1 or not text2:
            return 0.0
        
        # 找出相同的字符数
        set1 = set(text1)
        set2 = set(text2)
        common = len(set1 & set2)
        total = len(set1 | set2)
        
        return common / total if total > 0 else 0.0

    sensitive_segments = []
    current_episode = 1
    processed_ranges = []

    for ocr_result in ocr_results:
        ocr_time = ocr_result.get('timestamp', 0)
        ocr_text = ocr_result.get('text', '').strip()
        sensitive_word = ocr_result.get('sensitive_word', '')

        if not ocr_text:
            continue

        # 找到OCR时间点在ASR中的位置
        target_idx = 0
        for i, seg in enumerate(asr_segments):
            start = seg.start if hasattr(seg, 'start') else seg.get('start', 0)
            if start >= ocr_time:
                target_idx = i
                break

        # 尝试合并相邻ASR片段，看能否匹配OCR句子
        found_start_idx = None
        found_end_idx = None
        found_similarity = 0.0
        best_merged_text = ''

        # 尝试不同的合并范围：只合并1个、2个、3个相邻片段
        for merge_count in range(1, 4):
            for start_offset in range(merge_count):
                start_idx = target_idx - start_offset
                end_idx = start_idx + merge_count - 1

                if start_idx < 0 or end_idx >= len(asr_segments):
                    continue

                # 合并片段文本
                merged_text = ''
                for i in range(start_idx, end_idx + 1):
                    seg_text = asr_segments[i].text if hasattr(asr_segments[i], 'text') else asr_segments[i].get('text', '')
                    merged_text += seg_text

                # 模糊匹配条件：
                # 1. 包含敏感词
                # 2. 相似度>60%
                sensitive_word_lower = sensitive_word.lower()
                merged_clean = merged_text.replace(' ', '').replace('\n', '')
                ocr_clean = ocr_text.replace(' ', '').replace('\n', '')
                
                has_sensitive = sensitive_word_lower in merged_clean.lower()
                similarity = calculate_similarity(merged_clean, ocr_clean)

                if has_sensitive and similarity > 0.6:
                    found_start_idx = start_idx
                    found_end_idx = end_idx
                    found_similarity = similarity
                    best_merged_text = merged_text
                    break

            if found_start_idx is not None:
                break

        if found_start_idx is None or found_end_idx is None:
            if verbose:
                print(f"  ⚠️ OCR时间={ocr_time:.2f}s: 未找到匹配的ASR片段")
                print(f"     OCR句子: {ocr_text}")
            continue

        # 获取该片段的精确时间范围
        start_seg = asr_segments[found_start_idx]
        end_seg = asr_segments[found_end_idx]
        seg_start = start_seg.start if hasattr(start_seg, 'start') else start_seg.get('start', 0)
        seg_end = end_seg.end if hasattr(end_seg, 'end') else end_seg.get('end', 0)

        # 去重
        is_duplicate = False
        for p_start, p_end in processed_ranges:
            if abs(p_start - seg_start) < 0.5 and abs(p_end - seg_end) < 0.5:
                is_duplicate = True
                break

        if is_duplicate:
            continue

        processed_ranges.append((seg_start, seg_end))

        sensitive_seg = SensitiveSegment(
            episode=current_episode,
            sensitive_word=sensitive_word,
            asr_text=ocr_text,
            start_time=seg_start,
            end_time=seg_end
        )
        sensitive_segments.append(sensitive_seg)

        if verbose:
            print(f"  ✅ OCR时间={ocr_time:.2f}s -> ASR片段{found_start_idx}-{found_end_idx}")
            print(f"     OCR句子: {ocr_text}")
            print(f"     ASR合并: {best_merged_text}")
            print(f"     相似度: {found_similarity*100:.1f}%")
            print(f"     时间: {seg_start:.2f}s - {seg_end:.2f}s")

    if verbose:
        print(f"\n📊 检测完成: {len(sensitive_segments)} 个敏感片段")

    return sensitive_segments


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("敏感词检测模块测试")
    print("=" * 60)

    # 测试加载敏感词
    words = load_sensitive_words()
    print(f"\n敏感词列表: {words}")

    # 模拟ASR片段
    from dataclasses import dataclass

    @dataclass
    class MockASRSegment:
        text: str
        start: float
        end: float
        episode: int = 1

    test_asr = [
        MockASRSegment("大家好，欢迎收看今天的节目", 0.0, 2.5, 1),
        MockASRSegment("他出轨了，真是让人震惊", 5.0, 7.5, 1),
        MockASRSegment("下一集我们继续", 10.0, 12.0, 1),
        MockASRSegment("警察来了，快跑", 0.0, 2.0, 2),
    ]

    # 测试检测
    segments = detect_sensitive_segments(test_asr, words)

    print(f"\n检测结果:")
    for seg in segments:
        print(f"  {seg}")


def detect_sensitive_words_with_boxes(
    subtitle_segments: List,
    sensitive_words: Set[str],
    episode: int = 1,
    verbose: bool = True
) -> List[SensitiveSegment]:
    """
    检测字幕中的敏感词，并计算精确的box坐标

    使用字符等分策略：根据敏感词在句子中的位置，计算对应的box坐标

    Args:
        subtitle_segments: OCR识别结果，包含text和boxes
        sensitive_words: 敏感词集合
        episode: 集数
        verbose: 是否打印详细信息

    Returns:
        敏感词片段列表，包含精确的box坐标
    """
    if not sensitive_words:
        if verbose:
            print("⚠️ 敏感词列表为空，跳过检测")
        return []

    results = []

    for seg in subtitle_segments:
        text = seg.text if hasattr(seg, 'text') else seg.get('text', '')
        boxes = seg.boxes if hasattr(seg, 'boxes') else seg.get('boxes', [])

        if not text:
            continue

        # 检查每个敏感词
        for word in sensitive_words:
            if word in text:
                # 找到敏感词在句子中的位置
                start_idx = text.find(word)
                end_idx = start_idx + len(word)
                total_chars = len(text)

                # 计算位置比例
                start_ratio = start_idx / total_chars if total_chars > 0 else 0
                end_ratio = end_idx / total_chars if total_chars > 0 else 1

                # 计算精确的box坐标
                # PaddleOCR返回格式: [x1, y1, x2, y2]，这里boxes只有1个元素（整行）
                keyword_boxes = []

                for box in boxes:
                    # box可能是numpy array或list
                    try:
                        if hasattr(box, '__iter__') and len(box) >= 4:
                            x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                        else:
                            continue
                    except:
                        continue

                    # 等分计算关键词的x范围
                    keyword_x1 = int(x1 + (x2 - x1) * start_ratio)
                    keyword_x2 = int(x1 + (x2 - x1) * end_ratio)

                    keyword_boxes.append([keyword_x1, int(y1), keyword_x2, int(y2)])

                if keyword_boxes:
                    results.append(SensitiveSegment(
                        episode=episode,
                        sensitive_word=word,
                        asr_text=text,
                        start_time=seg.start_time if hasattr(seg, 'start_time') else seg.get('start_time', 0),
                        end_time=seg.end_time if hasattr(seg, 'end_time') else seg.get('end_time', 0),
                        boxes=keyword_boxes
                    ))

                    if verbose:
                        print(f"  🔍 [{seg.start_time:.1f}s-{seg.end_time:.1f}s] 发现敏感词'{word}'")
                        print(f"     原文: {text}")
                        print(f"     精确box: {keyword_boxes}")

    if verbose:
        if results:
            print(f"\n📊 敏感词检测完成: 共发现 {len(results)} 个敏感片段")
        else:
            print("\n📊 敏感词检测完成: 未发现敏感词")

    return results
