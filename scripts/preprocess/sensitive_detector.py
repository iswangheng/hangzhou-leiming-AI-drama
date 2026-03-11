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
        sensitive_words: 敏感词集合
        verbose: 是否打印详细信息

    Returns:
        敏感词片段列表

    匹配规则：
        - 包含即匹配：只要ASR文本包含敏感词就返回
        - 大小写不敏感：统一转小写后匹配
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

        # 检查是否包含敏感词
        for word in sensitive_words:
            if word in text:
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
