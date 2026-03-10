# 开发任务清单

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

### 🚧 进行中

#### 4. OCR字幕识别模块 (`scripts/preprocess/ocr_subtitle.py`)
- [x] 代码已创建
- [ ] 安装OCR库（EasyOCR/PaddleOCR）
- [ ] 测试敏感词检测

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

## 下一步计划

1. 安装OCR库
2. 测试OCR字幕识别
3. 集成到视频分析流程
4. 更新文档

---

## 当前状态

**字幕区域检测**: ✅ 完成
**马赛克遮盖**: ✅ 完成
**OCR字幕识别**: 🚧 待安装OCR库
