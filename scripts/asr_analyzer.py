"""
ASR内容分析模块

分析ASR转录内容，判断是"片尾旁白"还是"正常剧情对白"
"""

import re
from typing import List, Dict, Any


class ASRContentAnalyzer:
    """ASR内容分析器"""

    # 片尾旁白关键词
    ENDING_KEYWORDS = [
        "精彩剧集", "敬请期待", "下集", "预告",
        "关注", "点赞", "收藏", "转发", "关注我",
        "未完待续", "待续", "想看更多", "后续更精彩",
        "下期", "预告", "精彩", "不要走开"
    ]

    # 正常剧情关键词（提示这是有意义的剧情对白）
    DRAMA_KEYWORDS = [
        # 疑问词
        "怎么回事", "为什么", "怎么会", "不可能", "什么",
        "你是谁", "我是谁", "这是哪里", "这是哪里", "哪里",
        "你知道吗", "我告诉你", "让我说", "等等", "等等我",
        # 对话常用词
        "不要", "别走", "等等", "等一下", "怎么了",
        "你说什么", "你说", "听我说", "我知道", "我知道了",
        # 情感表达
        "我爱你", "喜欢你", "讨厌", "恨你", "对不起",
        # 动作相关
        "过来", "回去", "走吧", "走开", "站住",
        # 剧情推进
        "原来", "竟然", "居然", "真的", "假的"
    ]

    def __init__(self):
        """初始化分析器"""
        self.ending_keywords = self.ENDING_KEYWORDS
        self.drama_keywords = self.DRAMA_KEYWORDS

    def analyze_segments(
        self,
        asr_segments: List[Dict[str, Any]],
        video_end_time: float
    ) -> Dict[str, Any]:
        """
        分析ASR片段内容

        Args:
            asr_segments: ASR片段列表
            video_end_time: 视频结束时间

        Returns:
            分析结果字典
        """
        if not asr_segments or len(asr_segments) == 0:
            return {
                "has_speech": False,
                "is_ending": True,
                "reason": "无ASR内容，判定为片尾"
            }

        # 提取信息
        full_text = " ".join(seg['text'] for seg in asr_segments)
        last_asr_end = max(seg['end'] for seg in asr_segments)
        first_asr_start = min(seg['start'] for seg in asr_segments)
        total_asr_duration = last_asr_end - first_asr_start
        silence_duration = video_end_time - last_asr_end

        # 分析1: 检查片尾旁白关键词
        has_ending_keywords = self._check_ending_keywords(full_text)

        # 分析2: 检查正常剧情关键词
        has_drama_keywords = self._check_drama_keywords(full_text)

        # 分析3: ASR时长特征
        # 片尾旁白/声效通常很短（<3.5秒）
        # 正常剧情通常较长（>3秒）
        is_short_asr = total_asr_duration < 3.5  # 提高阈值，捕获更多片尾声效
        is_very_short_asr = total_asr_duration < 1.0  # 非常短的ASR，可能是噪音
        is_medium_asr = 3.5 > total_asr_duration >= 1.0  # 中等时长ASR

        # 分析4: ASR停止位置
        # 如果ASR一直持续到最后，可能是正常剧情
        # 如果ASR在视频结束前就停止，可能是片尾
        asr_ends_before_end = silence_duration > 0.5  # 结束前0.5秒以上

        # 分析5: ASR文本长度（字符数）
        # 正常对白通常有较多文字（>15字）
        # 片尾声效通常文本较短（<20字）
        text_length = len(full_text.strip())
        is_very_short_text = text_length < 5  # 极短文本可能是噪音
        is_short_text = text_length < 20  # 短文本可能是片尾声效

        # 【关键】综合判断（按优先级从高到低）
        # 情况1: 非常短的ASR（<1秒）+ 极短文本（<5字）→ 可能是噪音，忽略
        if is_very_short_asr and is_very_short_text:
            return {
                "has_speech": False,  # 视为无语音
                "is_ending": True,
                "reason": f"ASR非常短（{total_asr_duration:.2f}秒）且文本极短（{text_length}字），视为噪音",
                "first_asr_start": first_asr_start,
                "last_asr_end": last_asr_end,
                "total_asr_duration": total_asr_duration,
                "full_text": full_text
            }

        # 情况2: 有片尾旁白关键词 + 短ASR → 片尾旁白
        if has_ending_keywords and is_short_asr:
            return {
                "has_speech": True,
                "is_ending": True,
                "is_ending_narration": True,
                "first_asr_start": first_asr_start,
                "last_asr_end": last_asr_end,
                "total_asr_duration": total_asr_duration,
                "silence_duration": silence_duration,
                "is_short_asr": is_short_asr,
                "asr_ends_before_end": asr_ends_before_end,
                "has_ending_keywords": has_ending_keywords,
                "has_drama_keywords": has_drama_keywords,
                "full_text": full_text,
                "reason": "检测到片尾旁白关键词且ASR较短"
            }

        # 情况3: 有正常剧情关键词 + 较长ASR + 较长文本 → 正常剧情对白
        # 严格判定：必须同时满足三个条件
        if has_drama_keywords and total_asr_duration > 2.5 and text_length > 15:
            return {
                "has_speech": True,
                "is_ending": False,
                "is_ending_narration": False,
                "first_asr_start": first_asr_start,
                "last_asr_end": last_asr_end,
                "total_asr_duration": total_asr_duration,
                "silence_duration": silence_duration,
                "is_short_asr": is_short_asr,
                "asr_ends_before_end": asr_ends_before_end,
                "has_ending_keywords": has_ending_keywords,
                "has_drama_keywords": has_drama_keywords,
                "full_text": full_text,
                "reason": "检测到正常剧情关键词且ASR较长且文本较长"
            }

        # 情况4: 短/中等ASR + 短文本 + 无剧情关键词 → 片尾声效/旁白
        # 这是关键优化点：捕获"但是 补大了"(3.00s,6字)这类情况
        if is_medium_asr and is_short_text and not has_drama_keywords:
            return {
                "has_speech": True,
                "is_ending": True,
                "is_ending_narration": False,
                "first_asr_start": first_asr_start,
                "last_asr_end": last_asr_end,
                "total_asr_duration": total_asr_duration,
                "silence_duration": silence_duration,
                "is_short_asr": is_short_asr,
                "asr_ends_before_end": asr_ends_before_end,
                "has_ending_keywords": has_ending_keywords,
                "has_drama_keywords": has_drama_keywords,
                "full_text": full_text,
                "reason": f"ASR中等时长（{total_asr_duration:.2f}秒）+ 短文本（{text_length}字）+ 无剧情关键词，视为片尾声效"
            }

        # 情况5: 短ASR但无明确剧情特征 → 保守判定为片尾
        if is_short_asr:
            return {
                "has_speech": True,
                "is_ending": True,
                "is_ending_narration": False,  # 不是旁白，但可能是片尾的一部分
                "first_asr_start": first_asr_start,
                "last_asr_end": last_asr_end,
                "total_asr_duration": total_asr_duration,
                "silence_duration": silence_duration,
                "is_short_asr": is_short_asr,
                "asr_ends_before_end": asr_ends_before_end,
                "has_ending_keywords": has_ending_keywords,
                "has_drama_keywords": has_drama_keywords,
                "full_text": full_text,
                "reason": "ASR较短且无明确的剧情特征，保守判定为片尾"
            }

        # 默认情况：较长ASR + 无明确剧情关键词 → 保守判定为片尾（减少误报）
        # 只有明确检测到剧情对白才判定为不是片尾
        return {
            "has_speech": True,
            "is_ending": True,  # 默认判定为片尾，除非明确是剧情对白
            "is_ending_narration": False,
            "first_asr_start": first_asr_start,
            "last_asr_end": last_asr_end,
            "total_asr_duration": total_asr_duration,
            "silence_duration": silence_duration,
            "is_short_asr": is_short_asr,
            "asr_ends_before_end": asr_ends_before_end,
            "has_ending_keywords": has_ending_keywords,
            "has_drama_keywords": has_drama_keywords,
            "full_text": full_text,
            "reason": "ASR较长但无明确剧情特征，保守判定为片尾"
        }

    def _check_ending_keywords(self, text: str) -> bool:
        """检查是否包含片尾旁白关键词"""
        return any(kw in text for kw in self.ending_keywords)

    def _check_drama_keywords(self, text: str) -> bool:
        """检查是否包含正常剧情关键词"""
        return any(kw in text for kw in self.drama_keywords)

    def _get_reason(self, is_ending: bool, has_keywords: bool, is_short: bool) -> str:
        """生成判断原因"""
        if is_ending:
            if has_keywords:
                return "检测到片尾旁白关键词且ASR较短"
            else:
                return "ASR内容符合片尾特征"
        else:
            if has_keywords:
                return "检测到正常剧情关键词"
            else:
                return "ASR内容较长且持续到视频末尾，疑似正常剧情"

    def analyze_with_similarity(
        self,
        asr_segments: List[Dict[str, Any]],
        video_end_time: float,
        similarity_has_ending: bool,
        similarity_duration: float
    ) -> Dict[str, Any]:
        """
        结合画面相似度和ASR内容综合判断

        Args:
            asr_segments: ASR片段列表
            video_end_time: 视频结束时间
            similarity_has_ending: 画面相似度检测是否有片尾
            similarity_duration: 画面相似度检测的片尾时长

        Returns:
            最终判断结果
        """
        # 先分析ASR内容
        asr_analysis = self.analyze_segments(asr_segments, video_end_time)

        # 如果画面相似度没有检测到片尾，ASR有再多也是正常的
        if not similarity_has_ending:
            return {
                "has_ending": False,
                "method": "similarity_only",
                "reason": "画面相似度未检测到片尾，判定为无片尾",
                "asr_analysis": asr_analysis
            }

        # 画面相似度检测到片尾，需要ASR来验证
        if asr_analysis.get("has_speech", False):
            # 有ASR内容，检查ASR分析的判断
            if asr_analysis.get("is_ending", False):
                # ASR分析认为这是片尾（包括：片尾旁白、短ASR无明确剧情等）
                return {
                    "has_ending": True,
                    "method": "similarity_plus_asr_ending" if asr_analysis.get("is_ending_narration") else "similarity_plus_short_asr",
                    "duration": similarity_duration,
                    "reason": f"画面相似 + ASR验证 ({asr_analysis['reason']})",
                    "asr_analysis": asr_analysis
                }
            else:
                # ASR分析认为这不是片尾（有正常剧情对白）
                return {
                    "has_ending": False,
                    "method": "asr_correction",
                    "reason": f"画面相似但检测到正常剧情对白 ({asr_analysis['reason']}) - 误判修正",
                    "asr_analysis": asr_analysis
                }
        else:
            # 无ASR内容
            if similarity_has_ending:
                return {
                    "has_ending": True,
                    "method": "similarity_only_no_asr",
                    "duration": similarity_duration,
                    "reason": "画面相似 + 无ASR内容，确认为片尾",
                    "asr_analysis": asr_analysis
                }

        return {
            "has_ending": False,
            "method": "unknown",
            "reason": "无法判断"
        }


# 便捷函数
def analyze_asr_content(
    asr_segments: List[Dict[str, Any]],
    video_end_time: float
) -> Dict[str, Any]:
    """分析ASR内容"""
    analyzer = ASRContentAnalyzer()
    return analyzer.analyze_segments(asr_segments, video_end_time)


def analyze_with_similarity(
    asr_segments: List[Dict[str, Any]],
    video_end_time: float,
    similarity_has_ending: bool,
    similarity_duration: float
) -> Dict[str, Any]:
    """结合画面相似度分析ASR内容"""
    analyzer = ASRContentAnalyzer()
    return analyzer.analyze_with_similarity(
        asr_segments,
        video_end_time,
        similarity_has_ending,
        similarity_duration
    )


if __name__ == "__main__":
    # 测试
    print("=" * 80)
    print("🧪 测试ASR内容分析功能")
    print("=" * 80)

    # 模拟ASR数据
    test_cases = [
        {
            "name": "片尾旁白",
            "segments": [
                {"start": 656.0, "end": 657.5, "text": "精彩剧集，敬请期待"},
                {"start": 657.5, "end": 659.0, "text": "关注我"}
            ],
            "video_end": 660.0
        },
        {
            "name": "正常剧情",
            "segments": [
                {"start": 55.0, "end": 60.0, "text": "你怎么会在这里？"},
                {"start": 60.0, "end": 62.0, "text": "我告诉你一个秘密"}
            ],
            "video_end": 62.0
        }
    ]

    analyzer = ASRContentAnalyzer()

    for case in test_cases:
        print(f"\n{'=' * 60}")
        print(f"测试: {case['name']}")
        print(f"{'=' * 60}")

        result = analyzer.analyze_segments(
            case['segments'],
            case['video_end']
        )

        print(f"判断结果: {'片尾' if result['is_ending_narration'] else '正常剧情'}")
        print(f"原因: {result['reason']}")

        if result['has_speech']:
            print(f"ASR时长: {result['total_asr_duration']:.2f}秒")
            print(f"ASR内容: {result['full_text']}")
