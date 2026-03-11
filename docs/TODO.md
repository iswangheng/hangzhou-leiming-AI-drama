# 开发任务清单

## 缓存清理机制优化 (2026-03-11) ✅ 已完成

### 问题描述
- `cleanup_project_cache()` 函数在分析/渲染完成后立即删除所有缓存
- 太着急了，用户希望保留3小时方便后续测试

### 解决方案
修改 `cleanup_project_cache()` 函数，从"立即清理"改为"清理3小时以前的缓存"

### 已完成的工作
- [x] 修改函数签名：`cleanup_project_cache(project_name: str, min_age_hours: float = 3.0) -> dict`
- [x] 基于文件 mtime 判断，只清理超过 min_age_hours 小时的缓存
- [x] 添加日志打印，显示跳过了多少文件（因为时间未到）
- [x] 更新三个文件中的清理调用逻辑：
  - `scripts/understand/video_understand.py`
  - `scripts/understand/render_clips.py`
  - `scripts/train.py`
- [x] 创建测试脚本验证功能

### 测试结果
```
✅ 测试通过！缓存清理的时间保留策略工作正常
  - 旧文件（4小时前）已删除: True
  - 新文件（1小时前）已保留: True
  - 跳过文件数正确: 3
```

### 相关文件
- `scripts/understand/video_understand.py` - cleanup_project_cache() 函数
- `scripts/understand/render_clips.py` - cleanup_project_cache() 函数
- `scripts/train.py` - cleanup_project_cache() 函数
- `test/test_cache_cleanup_with_age.py` - 测试脚本

---

## 敏感词遮盖功能 (2026-03-10)

### ✅ 已完成

#### 1. 字幕区域检测模块 (`scripts/preprocess/subtitle_detector.py`)
- [x] 嬴素变化检测法（首选，- [x] Gemini视觉分析（备选）
- [x] OCR检测（备选）
- [x] 默认比例（最后备选）
- [x] 配置保存/加载
- [x] **8个项目测试通过**：
  - 锦庭别后意、我是外星人、 三世后
  - 我是乌鸦嘴、 上班不垫钱
  - 年终奖五千
  - 烈日重生

#### 2. 敏感词配置 (`config/sensitive_words.txt`)
- [x] 28个敏感词
- [x] TXT格式，方便编辑
- [x] 从 `漫剧敏感词.docx` 提取

#### 3. 马赛克遮盖模块 (`scripts/preprocess/video_cleaner.py`)
- [x] FFmpeg boxblur滤镜
- [x] 多片段遮盖
- [x] 遮盖记录保存
- [x] **烈日重生测试通过**

### ✅ 已完成

#### 4. OCR字幕识别模块 (`scripts/preprocess/ocr_subtitle.py`)
- [x] 代码已创建
- [x] 安装OCR库（EasyOCR已安装）
- [x] 修复语法错误（第143行）
- [x] 测试敏感词检测功能
- [x] **测试结果**：
  - ✅ OCR引擎初始化：通过
  - ✅ 帧提取功能：通过
  - ✅ 字幕区域检测：通过
  - ✅ 敏感词检测：通过
  - ✅ 真实视频OCR：识别出字幕 "迟到5分钟[卫"
  - 测试通过率：100% (6/6)

### 📝 待开发

#### 5. 集成到视频分析流程
- [ ] 修改 `video_understand.py`
- [ ] 自动预处理敏感词
- [ ] 生成干净视频

#### 6. 巻加命令行参数
- [ ] `--enable-sensitive-mask`
- [ ] `--sensitive-words-file`

#### 7. 测试验证
- [ ] 多项目测试
- [ ] 不同分辨率测试
- [ ] 性能测试

---

## 当前状态

**字幕区域检测**: ✅ 完成
**马赛克遮盖**: ✅ 完成
**OCR字幕识别**: ✅ 完成

---

## 下一步计划

1. ✅ ~~安装OCR库~~
2. ✅ ~~测试OCR字幕识别~~
3. 集成到视频分析流程
4. 更新文档
