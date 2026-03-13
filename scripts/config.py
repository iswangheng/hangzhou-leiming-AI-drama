"""
项目配置模块 - AI训练流程
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 项目名映射：代码用名 -> 缓存文件夹名
PROJECT_NAME_MAP = {
    "再见，心机前夫": "再见，心机前夫",
    "小小飞梦": "小小飞梦",
    "弃女归来嚣张真千金不好惹": "弃女归来：嚣张真千金不好惹",
    "重生暖宠九爷的小娇妻不好惹": "重生暖宠：九爷的小娇妻不好惹"
}

def get_cache_project_name(project_name: str) -> str:
    """获取缓存文件夹的实际名称"""
    return PROJECT_NAME_MAP.get(project_name, project_name)


@dataclass
class ProjectConfig:
    """项目配置类"""
    name: str           # 短剧名称
    video_path: str    # 视频文件夹路径（相对于项目根目录）
    excel_path: str    # Excel 人工标记文件路径

    def get_absolute_video_path(self) -> str:
        """获取视频文件夹的绝对路径"""
        return str(PROJECT_ROOT / self.video_path)

    def get_absolute_excel_path(self) -> str:
        """获取Excel文件的绝对路径"""
        return str(PROJECT_ROOT / self.excel_path)

    def get_video_path(self, episode_number: int) -> str:
        """
        获取指定集数的视频文件路径（支持多种文件命名格式）

        支持的格式：
        - 纯数字: 1.mp4, 2.mp4
        - 带前缀: 精准-1.mp4, 机长姐姐-01.mp4
        - EP前缀: ep01.mp4, EP1.mp4
        - 混合格式: 骨血灯_03_1080p.mp4
        """
        video_dir = Path(self.get_absolute_video_path())

        # 导入增强的文件查找函数
        from .utils.filename_parser import find_video_files

        # 使用增强的文件查找函数
        video_path = find_video_files(str(video_dir), episode_number)

        if video_path:
            return video_path

        # 提供更详细的错误信息
        raise FileNotFoundError(
            f"找不到第{episode_number}集的视频文件 (目录: {video_dir})"
        )


# 完整配置示例 - 14个短剧项目（V5.0完整训练数据）
PROJECTS: List[ProjectConfig] = [
    # 漫剧素材（原5个项目）
    ProjectConfig(
        name="重生暖宠：九爷的小娇妻不好惹",
        video_path="./漫剧素材/重生暖宠九爷的小娇妻不好惹",
        excel_path="./漫剧素材/重生暖宠九爷的小娇妻不好惹/重生暖宠：九爷的小娇妻不好惹.xlsx"
    ),
    ProjectConfig(
        name="再见，心机前夫",
        video_path="./漫剧素材/再见，心机前夫",
        excel_path="./漫剧素材/再见，心机前夫/再见，心机前夫.xlsx"
    ),
    ProjectConfig(
        name="小小飞梦",
        video_path="./漫剧素材/小小飞梦",
        excel_path="./漫剧素材/小小飞梦/小小飞梦.xlsx"
    ),
    ProjectConfig(
        name="弃女归来：嚣张真千金不好惹",
        video_path="./漫剧素材/弃女归来嚣张真千金不好惹",
        excel_path="./漫剧素材/弃女归来嚣张真千金不好惹/弃女归来：嚣张真千金不好惹.xlsx"
    ),
    ProjectConfig(
        name="百里将就",
        video_path="./漫剧素材/百里将就",
        excel_path="./漫剧素材/百里将就/百里将就.xlsx"
    ),
    # 漫剧参考（5个项目）
    ProjectConfig(
        name="假面丈夫",
        video_path="./漫剧参考/假面丈夫",
        excel_path="./漫剧参考/假面丈夫/丈夫的假面.xlsx"
    ),
    ProjectConfig(
        name="学乖的代价",
        video_path="./漫剧参考/学乖的代价",
        excel_path="./漫剧参考/学乖的代价/学乖的代价.xlsx"
    ),
    ProjectConfig(
        name="机长姐姐",
        video_path="./漫剧参考/机长姐姐",
        excel_path="./漫剧参考/机长姐姐/机长姐姐与寡王弟弟.xlsx"
    ),
    ProjectConfig(
        name="精准",
        video_path="./漫剧参考/精准",
        excel_path="./漫剧参考/精准/精准猎物.xlsx"
    ),
    ProjectConfig(
        name="紫雪",
        video_path="./漫剧参考/紫雪",
        excel_path="./漫剧参考/紫雪/紫雪容忍.xlsx"
    ),
    # 新的漫剧素材（4个项目）
    ProjectConfig(
        name="不晚忘忧",
        video_path="./新的漫剧素材/不晚忘忧",
        excel_path="./新的漫剧素材/不晚忘忧/不晚忘忧.xlsx"
    ),
    ProjectConfig(
        name="休书落纸",
        video_path="./新的漫剧素材/休书落纸",
        excel_path="./新的漫剧素材/休书落纸/休书落纸.xlsx"
    ),
    ProjectConfig(
        name="恋爱综艺，匹配到心动男友",
        video_path="./新的漫剧素材/恋爱综艺，匹配到心动男友",
        excel_path="./新的漫剧素材/恋爱综艺，匹配到心动男友/恋爱综艺，匹配到心动男友.xlsx"
    ),
    ProjectConfig(
        name="雪烬梨香",
        video_path="./新的漫剧素材/雪烬梨香",
        excel_path="./新的漫剧素材/雪烬梨香/雪烬梨香.xlsx"
    ),
]


# 训练参数配置
class TrainingConfig:
    """训练参数配置"""

    # 关键帧提取参数
    KEYFRAME_FPS = 1.0  # V5.0优化：每秒1帧 = 1fps（原2.0fps）
    KEYFRAME_QUALITY = 2  # JPEG质量 (1-31, 越小越好)

    # 上下文提取参数
    CONTEXT_SECONDS = 10.0  # 上下文时间（秒）

    # ASR参数
    ASR_MODEL = "tiny"  # Whisper模型大小
    ASR_LANGUAGE = "zh"  # 语言
    ASR_SAMPLE_RATE = 16000  # 采样率

    # Gemini API配置
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "sk-iKGxKJOSZ4ZVAE9noaVSe3ahYkRVP7BbyfqFQtC7x88JatLW")
    # 使用正确的端点格式：query参数传递key
    GEMINI_ENDPOINT = f"https://yunwu.ai/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    GEMINI_MAX_TOKENS = 2048
    GEMINI_TEMPERATURE = 0.3  # V5优化：降低随机性

    # 并发参数
    MAX_CONCURRENT_ANALYSIS = 3  # 最大并发分析数
    REQUEST_TIMEOUT = 120  # 请求超时时间（秒）
    MAX_RETRIES = 3  # 最大重试次数

    # 输出路径配置
    DATA_DIR = PROJECT_ROOT / "data"
    SKILLS_DIR = DATA_DIR / "skills"
    CACHE_DIR = DATA_DIR / "cache"
    PROGRESS_FILE = CACHE_DIR / "training_progress.json"

    # Prompt模板路径
    PROMPT_TEMPLATE_PATH = PROJECT_ROOT / "prompts" / "hl-learning.md"


def create_directories():
    """创建必要的目录结构"""
    directories = [
        TrainingConfig.DATA_DIR,
        TrainingConfig.SKILLS_DIR,
        TrainingConfig.CACHE_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_prompt_template() -> str:
    """读取Prompt模板"""
    prompt_path = TrainingConfig.PROMPT_TEMPLATE_PATH
    if prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        # 如果文件不存在，返回默认模板
        return get_default_prompt_template()


class TimeoutConfig:
    """所有 subprocess 操作的超时配置（秒）

    设计原则：
    - 轻量查询（ffprobe）：秒级完成，超时=30-60秒
    - 中等操作（关键帧提取、音频提取）：分钟级，超时=2-10分钟
    - 重型操作（马赛克、压缩、渲染）：可能很长，超时=0.5-1小时
    """

    # ── ffprobe 查询（轻量，应该秒级完成）────────────────────
    FFPROBE_QUICK = 30          # 获取时长、分辨率、帧率等元数据
    FFPROBE_METADATA = 60       # 较复杂的元数据查询

    # ── FFmpeg 轻量操作 ───────────────────────────────────
    FFMPEG_FRAME_SINGLE = 30    # 单帧提取（-vframes 1）
    FFMPEG_AUDIO_EXTRACT = 120  # 音频提取（wav 格式，供 ASR 使用）
    FFMPEG_HWACCEL_CHECK = 10   # 硬件加速检测

    # ── FFmpeg 中等操作 ───────────────────────────────────
    FFMPEG_KEYFRAME_EXTRACT = 600   # 单集关键帧批量提取（10分钟上限）
    FFMPEG_ENDING_DETECT = 60       # 片尾检测帧提取（轻量，60秒足够）
    FFMPEG_ENDING_PREPROCESS = 300  # 结尾视频预处理（转码、帧率对齐）
    FFMPEG_CLIP_RENDER = 600        # 单条 clip 渲染（剪切+concat+花字）

    # ── FFmpeg 重型操作 ───────────────────────────────────
    FFMPEG_MASK_APPLY = 1800    # 全片马赛克遮罩（短剧单集5-15分钟，30分钟足够）
    FFMPEG_COMPRESS = 1800      # 视频压缩（30 分钟）


def get_default_prompt_template() -> str:
    """获取默认的Prompt模板"""
    return """你是一位专业的短剧剪辑分析师。你的任务是分析历史标记数据，总结剪辑技能。

## 输入数据

- **视频集数**: {episode}
- **标记时间点**: {timestamp}
- **标记类型**: {type}（高光点/钩子点）
- **时间范围**: {time_range}
- **ASR语音转录**: {asr_text}

请基于关键帧画面和ASR语音转录，从视觉、听觉、情绪、剧情、内容爽点等多个维度全面分析这个标记点，并返回JSON格式的分析结果。"""