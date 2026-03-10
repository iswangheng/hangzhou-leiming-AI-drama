"""
数据结构定义 - AI训练流程
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Marking:
    """标记数据"""
    id: int
    episode: str           # 集数，如 "第1集"
    episode_number: int    # 集数编号，如 1
    timestamp: str          # 时间点字符串，如 "00:35"
    seconds: float          # 时间点秒数，如 35.0
    type: str              # "高光点" 或 "钩子点"
    sub_type: Optional[str] = None
    description: Optional[str] = None
    score: Optional[int] = None


@dataclass
class KeyFrame:
    """关键帧"""
    frame_path: str        # 帧图片路径
    timestamp_ms: int      # 时间戳（毫秒）
    base64: Optional[str] = None  # Base64 编码（用于传给 Gemini）


@dataclass
class ASRSegment:
    """ASR 片段"""
    text: str              # 文本内容
    start: float           # 开始时间（秒）
    end: float             # 结束时间（秒）
    episode: int = 0       # 所属集数（V15.4新增，用于时间戳优化）


@dataclass
class MarkingContext:
    """标记上下文（核心数据结构）"""
    project_name: str
    marking: Marking

    # 高光点：从标记时间往后10秒
    # 钩子点：从标记时间往前10秒
    keyframes: List[KeyFrame] = field(default_factory=list)
    asr_segments: List[ASRSegment] = field(default_factory=list)
    asr_text: str = ""


@dataclass
class AnalysisResult:
    """分析结果"""
    type: str              # "高光点" 或 "钩子点"
    category: str          # 泛化的类型名称
    category_description: str  # 类型详细描述
    # 多维度特征
    visual_features: Dict[str, Any] = field(default_factory=dict)    # 视觉特征(关键帧画面)
    audio_features: Dict[str, Any] = field(default_factory=dict)     # 听觉特征(仅ASR转录分析)
    emotion_features: Dict[str, Any] = field(default_factory=dict)   # 情绪特征
    plot_features: Dict[str, Any] = field(default_factory=dict)       # 剧情特征
    content_features: Dict[str, Any] = field(default_factory=dict)   # 内容爽点特征

    reasoning: str = ""   # 分析原因


@dataclass
class HighlightType:
    """高光类型"""
    name: str
    description: str

    # 多维度特征
    visual_features: Dict[str, Any] = field(default_factory=dict)    # 视觉特征
    audio_features: Dict[str, Any] = field(default_factory=dict)     # 听觉特征
    emotion_features: Dict[str, Any] = field(default_factory=dict)   # 情绪特征
    plot_features: Dict[str, Any] = field(default_factory=dict)       # 剧情特征
    content_features: Dict[str, Any] = field(default_factory=dict)   # 内容爽点特征

    typical_scenarios: List[str] = field(default_factory=list)


@dataclass
class HookType:
    """钩子类型"""
    name: str
    description: str

    # 多维度特征
    visual_features: Dict[str, Any] = field(default_factory=dict)    # 视觉特征
    audio_features: Dict[str, Any] = field(default_factory=dict)     # 听觉特征
    emotion_features: Dict[str, Any] = field(default_factory=dict)   # 情绪特征
    plot_features: Dict[str, Any] = field(default_factory=dict)       # 剧情特征
    content_features: Dict[str, Any] = field(default_factory=dict)   # 内容氪点特征

    typical_scenarios: List[str] = field(default_factory=list)


@dataclass
class EditingRule:
    """剪辑规则"""
    scenario: str
    duration: str
    rhythm: str
    combination: str
    cut_in: str
    cut_out: str


@dataclass
class SkillFile:
    """技能文件结构"""
    version: str
    updated_at: str
    highlight_types: List[HighlightType] = field(default_factory=list)
    hook_types: List[HookType] = field(default_factory=list)
    editing_rules: List[EditingRule] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)