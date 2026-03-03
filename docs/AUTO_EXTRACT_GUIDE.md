# 自动提取功能说明

**更新日期**: 2026-03-03  
**版本**: v1.0

---

## 🎯 功能概述

视频理解流程现在支持**自动检查并提取**缺失的关键帧和ASR数据，无需手动运行提取脚本！

---

## 🚀 使用方法

### 方式1：命令行运行（推荐）

```bash
# 基本用法
python -m scripts.understand.video_understand <项目路径> [技能文件]

# 示例1：使用默认技能文件
python -m scripts.understand.video_understand "./漫剧素材/百里将就"

# 示例2：指定v0.5技能文件
python -m scripts.understand.video_understand \
  "./新的漫剧素材/不晚忘忧" \
  "data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-v0.5.md"
```

### 方式2：Python代码调用

```python
from scripts.understand.video_understand import video_understand

result = video_understand(
    project_path="./漫剧素材/百里将就",
    skill_file="data/hangzhou-leiming/skills/ai-drama-clipping-thoughts-v0.5.md"
)
```

---

## 📋 完整流程（5个步骤）

```
[1/5] 理解技能文件
  ↓ 加载技能文件（MD格式）
  ↓ 解析高光类型和钩子类型

[2/5] 加载项目数据（自动检查并提取）  ← 🆕 自动化关键步骤
  ↓ 检查关键帧是否存在
  ↓ ❌ 不存在 → 自动提取（每秒1帧）
  ↓ ✅ 已存在 → 直接加载
  ↓ 
  ↓ 检查ASR是否存在
  ↓ ❌ 不存在 → 自动提取音频 + Whisper转录
  ↓ ✅ 已存在 → 直接加载

[3/5] 提取分析片段
  ↓ 将视频分割成30秒片段

[4/5] AI逐段分析
  ↓ 调用Gemini 2.0 Flash分析每个片段
  ↓ 识别高光点和钩子点

[5/5] 质量筛选
  ↓ 置信度筛选（≥7.0分）
  ↓ 去重（10秒内重复标记）
  ↓ 类型多样性限制
  ↓ 数量限制（每集最多2高光+3钩子）

生成剪辑组合 & 保存结果
```

---

## 🔧 提取参数

### 关键帧提取

```python
fps=1.0,              # 每秒1帧（V5.0优化参数）
quality=2,            # JPEG质量 (1-31, 越小越好)
```

**输出位置**: `data/hangzhou-leiming/cache/keyframes/<项目名>/<集数>/`

### ASR转录

```python
model="tiny",         # Whisper模型（tiny最快）
language="zh",        # 中文
sample_rate=16000,    # 采样率16kHz
```

**输出位置**: 
- 音频: `data/hangzhou-leiming/cache/audio/<项目名>/<集数>.wav`
- 转录: `data/hangzhou-leiming/cache/asr/<项目名>/<集数>.json`

---

## 📊 性能参考

### 提取耗时（参考值）

| 视频时长 | 关键帧提取 | ASR转录 | 总计 |
|---------|-----------|---------|------|
| 1分钟 | ~5秒 | ~10秒 | ~15秒 |
| 5分钟 | ~20秒 | ~30秒 | ~50秒 |
| 10分钟 | ~40秒 | ~60秒 | ~100秒 |

### 示例：10集项目

假设每集平均5分钟：
- 数据准备：~8分钟（首次运行）
- AI分析：~2-5分钟
- **总计**: ~10-15分钟

**注意**：第二次运行时，如果数据已存在，会直接加载，无需重新提取！

---

## 🐛 故障排查

### 问题1：FFmpeg未找到

**错误**: `FileNotFoundError: 未找到FFmpeg命令`

**解决方案**:
```bash
# macOS
brew install ffmpeg

# Linux
apt-get install ffmpeg
```

### 问题2：Whisper模型下载失败

**错误**: `下载模型失败`

**解决方案**:
```bash
# 手动下载模型（首次运行会自动下载）
# 或设置代理
export HF_ENDPOINT=https://hf-mirror.com
```

---

**更新日志**:
- v1.0 (2026-03-03): 新增自动提取功能，支持关键帧和ASR自动检查与提取
