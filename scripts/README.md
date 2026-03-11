# AI训练与视频理解脚本使用说明

## 版本更新

### V5.0 - 完整训练数据 + 自动类型简化 (2026-03-03)

**新增功能**：
- ✅ **自动类型简化** (`merge_skills.py`) - 训练时自动聚类合并钩子类型
- ✅ **批量数据提取** (`batch_extract_data.py`) - 批量提取所有项目数据
- ✅ **进度监控** (`check_progress.py`) - 实时查看数据提取进度
- ✅ **完整训练流程** (`full_training_pipeline.py`) - 一键完成所有训练步骤
- ✅ **数据验证** (`verify_data.py`) - 验证项目数据完整性

**优化功能**：
- ✅ **Prompt优化** - 适度放宽标记标准（V8）
- ✅ **关键帧密度** - 每秒1帧（原每0.5秒1帧）
- ✅ **置信度阈值** - 8.0 → 6.5
- ✅ **分析窗口** - 30秒窗口（原60秒）

**目录结构更新**：
```
scripts/
├── understand/              # 视频理解模块 (V2)
│   ├── video_understand.py      # 主入口
│   ├── understand_skill.py     # 技能理解
│   ├── extract_segments.py     # 片段提取
│   ├── analyze_segment.py      # AI分析（V8 Prompt）
│   ├── generate_clips.py       # 剪辑组合生成
│   └── quality_filter.py       # 质量筛选
├── merge_skills.py         # 技能合并 + 自动类型简化 (V5新增)
├── batch_extract_data.py  # 批量数据提取 (V5新增)
├── check_progress.py       # 进度监控 (V5新增)
├── full_training_pipeline.py  # 完整训练流程 (V5新增)
├── verify_data.py          # 数据验证 (V5新增)
├── train.py                # 训练脚本
└── test_video_understanding_v2.py  # 测试脚本
```

---

### V2.0 - 精确时间戳与质量筛选 (2026-03-03)

**新增功能**：
- ✅ **视频理解模块** (`understand/`) - 自动识别高光点和钩子点
- ✅ **精确时间戳** - AI返回窗口内精确的秒数
- ✅ **质量筛选** - 置信度>7.0 + 去重 + 数量控制
- ✅ **测试脚本** - `test_video_understanding_v2.py`

---

## 项目概述

本脚本包含两个主要功能：
1. **训练流程**：从短剧视频和人工标记数据中训练剪辑技能
2. **视频理解**：使用训练好的技能，自动识别新剧的高光点和钩子点

## 环境要求

### 系统依赖
- **Python**: 3.8+
- **FFmpeg**: 用于视频关键帧提取和音频提取
- **Whisper**: 用于音频语音转录

### Python依赖
见 `requirements.txt`

## 安装步骤

### 1. 安装系统依赖

**macOS:**
```bash
# 安装FFmpeg
brew install ffmpeg

# 安装Whisper
pip install openai-whisper
```

**Linux:**
```bash
# 安装FFmpeg
sudo apt-get install ffmpeg

# 安装Whisper
pip install openai-whisper
```

### 2. 安装Python依赖
```bash
cd /Users/wangheng/Downloads/hangzhou-leiming-ai-drama
pip install -r scripts/requirements.txt
```

### 3. 配置API密钥
```bash
export GEMINI_API_KEY=your-api-key-here
```

## 使用方法

### V5.0 完整流程（推荐）

```bash
# 步骤1：检查数据提取进度
python -m scripts.check_progress

# 步骤2：批量提取数据（如需要）
python -m scripts.batch_extract_data

# 步骤3：完整训练流程（数据提取完成后）
python -m scripts.full_training_pipeline

# 步骤4：测试验证
python -m scripts.understand.video_understand "漫剧素材/百里将就" --skill-file "ai-drama-clipping-thoughts-v0.4.md"
```

### V2.0 基本用法（仍支持）

```bash
# 处理所有项目
python -m scripts.train

# 处理指定项目
python -m scripts.train --projects "重生暖宠：九爷的小娇妻不好惹,再见，心机前夫"

# 强制重新提取数据
python -m scripts.train --force-reextract

# 跳过AI分析（仅提取数据）
python -m scripts.train --skip-analysis

# 从上次中断处继续
python -m scripts.train --resume

# 清除训练进度
python -m scripts.train --clear-progress
```

### 查看帮助
```bash
python -m scripts.train --help
```

## 项目结构

```
scripts/
├── __init__.py              # 包初始化
├── dataclasses.py           # 数据结构定义
├── config.py                # 项目配置
├── read_excel.py            # Excel读取模块
├── extract_keyframes.py     # 关键帧提取模块
├── extract_asr.py          # ASR转录模块
├── extract_context.py      # 上下文提取模块
├── analyze_gemini.py       # Gemini分析模块
├── merge_skills.py         # 技能合并模块
├── train.py                # 主训练脚本
├── requirements.txt        # 依赖文件
└── README.md              # 本文件
```

## 输出目录

```
data/
├── skills/                  # 技能文件输出目录
│   ├── ai-drama-clipping-thoughts-v1.0.md
│   ├── ai-drama-clipping-thoughts-v1.1.md
│   └── ai-drama-clipping-thoughts-latest.md -> ai-drama-clipping-thoughts-v1.1.md
├── cache/                   # 缓存目录
│   ├── keyframes/          # 关键帧缓存
│   ├── audio/              # 音频缓存
│   ├── asr/                # ASR转录缓存
│   └── training_progress.json  # 训练进度文件
├── analysis/               # 视频理解结果
│   └── 项目名/
│       └── result.json
└── ending_credits/         # 片尾检测缓存
    └── 项目名_ending_credits.json
```

## 训练流程

### V5.0 流程

1. **读取Excel标记文件** - 解析人工标记的高光点和钩子点
2. **提取关键帧** - 使用FFmpeg每秒提取1帧（V5优化：原每0.5秒）
3. **ASR转录** - 使用Whisper转录语音内容
4. **提取上下文** - 为每个标记点提取前后10秒的上下文
5. **AI分析** - 调用Gemini API分析标记点特征
6. **自动类型简化** - 训练时自动聚类合并钩子类型（V5新增）
7. **合并技能** - 螺旋式迭代更新技能文件（MD + JSON）

### V5.0 新特性

**自动类型简化**：
- 按关键词聚类相似类型
- 合并重复类型
- 筛选低质量类型（出现次数<3，重叠度>80%）
- 保留最重要的10-15种类型

**完整训练数据**：
- 原版本：5个项目（50集）
- V5.0：14个项目（117集）
  - 漫剧素材：5个项目（50集）
  - 漫剧参考：5个项目（27集）
  - 新的漫剧素材：4个项目（40集）

## 注意事项

1. **首次运行**: 首次运行会提取所有数据，耗时较长
2. **断点续传**: 使用 `--resume` 可从上次中断处继续
3. **并发控制**: 默认3个并发分析，可在config.py中调整
4. **缓存管理**: 使用 `--force-reextract` 强制重新提取数据
5. **API配额**: 注意Gemini API的调用限制

## 故障排除

### FFmpeg未找到
```
错误: 未找到FFmpeg命令
解决: 安装FFmpeg并添加到PATH环境变量
```

### Whisper未找到
```
错误: 未找到Whisper命令
解决: pip install openai-whisper
```

### API密钥错误
```
错误: 未设置GEMINI_API_KEY环境变量
解决: export GEMINI_API_KEY=your-key
```

### 依赖版本冲突
```
错误: numpy.dtype size changed
解决: pip install --upgrade numpy pandas
```

## 开发者信息

- 项目路径: `/Users/wangheng/Downloads/hangzhou-leiming-ai-drama/`
- 配置文件: `scripts/config.py`
- 规范文档: `TRAINING_SPEC.md`
- Prompt模板: `prompts/hl-learning.md`