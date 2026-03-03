# 文档整理完整方案

**制定时间**: 2026-03-03  
**目标**: 清理过期文档，归档临时文件，更新过时信息

---

## 📋 整理原则

1. **保留当前版本** - 只保留最新的v0.5技能文件和latest软链接
2. **归档历史版本** - v0.1-v0.4技能文件移到archive
3. **删除重复文件** - 删除analysis目录中的重复result.json
4. **合并优化报告** - 将多个优化报告合并为一个版本历史文档
5. **归档临时脚本** - 移动测试脚本到archive/scripts
6. **更新主要文档** - 更新README.md和主要文档到V5.1

---

## 🗂️ 文件分类整理

### 1. 根目录MD文档（需要整理）

#### 保留并更新的文档
- ✅ **README.md** - 需要更新到V5.1
- ✅ **TRAINING_SPEC.md** - 训练规范（可能需要更新）

#### 需要归档的文档（到 archive/docs/）
- ❌ IMPLEMENTATION_REPORT.md - 实施报告（过时）
- ❌ PRODUCT_PLAN.md - 产品计划（过时）
- ❌ VIDEO_UNDERSTAND_SPEC.md - 视频理解规范（过时）

#### 需要合并的优化报告
- 📦 **OPTIMIZATION_V3_REPORT.md** → 合并到版本历史
- 📦 **OPTIMIZATION_V4_REPORT.md** → 合并到版本历史
- 📦 **OPTIMIZATION_V5_PLAN.md** → 合并到版本历史
- 📦 **OPTIMIZATION_V5_COMPLETE.md** → 合并到版本历史
- 📦 **OPTIMIZATION_V5.1_COMPLETE.md** → 合并到版本历史
- 📦 **V5.1_EXECUTION_SUMMARY.md** → 合并到版本历史
- 📦 **OPTIMIZE_TASK.md** → 删除（临时任务）
- 📦 **OPTIMIZATION_PLAN.md** → 删除（临时计划）

**生成新文档**: `docs/VERSION_HISTORY.md` - 完整版本历史

---

### 2. 技能文件（data/hangzhou-leiming/skills/）

#### 保留
- ✅ `ai-drama-clipping-thoughts-v0.5.md` - 最新版本
- ✅ `ai-drama-clipping-thoughts-v0.5.json` - 最新版本
- ✅ `ai-drama-clipping-thoughts-latest.md` → v0.5.md
- ✅ `ai-drama-clipping-thoughts-latest.json` → v0.5.json

#### 归档（到 archive/data/hangzhou-leiming/skills/）
- ❌ `ai-drama-clipping-thoughts-v0.1.md`
- ❌ `ai-drama-clipping-thoughts-v0.2.md`
- ❌ `ai-drama-clipping-thoughts-v0.2.json`
- ❌ `ai-drama-clipping-thoughts-v0.3.md`
- ❌ `ai-drama-clipping-thoughts-v0.3.json`
- ❌ `ai-drama-clipping-thoughts-v0.4.md`
- ❌ `ai-drama-clipping-thoughts-v0.4.json`

#### 删除
- 🗑️ `framework.json` - 重复（已在其他地方）
- 🗑️ `test_skill.json` - 测试文件
- 🗑️ `V5_TRAINING_REPORT_v0.4.md` - 训练报告（移到docs）

---

### 3. 分析结果文件（data/hangzhou-leiming/analysis/）

#### 问题
- 大量重复的result.json文件
- 文件名不统一（有的有空格，有的带_v2后缀）

#### 整理方案

**保留（最新版本）**:
- ✅ `不晚忘忧/result.json`
- ✅ `休书落纸/result.json`
- ✅ `再见，心机前夫/result.json`
- ✅ `小小飞梦/result.json`
- ✅ `弃女归来嚣张真千金不好惹/result.json`
- ✅ `百里将就/result.json`
- ✅ `重生暖宠九爷的小娇妻不好惹/result.json`

**归档（到 archive/data/hangzhou-leiming/analysis/）**:
- ❌ 所有带_v2、_v4后缀的文件
- ❌ `再见，心机前夫_result.json`
- ❌ `小小飞梦_result.json`
- ❌ `弃女归来嚣张真千金不好惹_result.json`
- ❌ `百里将就_result.json`
- ❌ `百里将就_v2/` 文件夹
- ❌ `重生暖宠九爷的小娇妻不好惹_result.json`
- ❌ `V4_TEST_REPORT.md`

---

### 4. 漫剧素材目录（.json和-transcript.json文件）

#### 问题
- 每个项目目录下有大量.json和-transcript.json文件
- 这些是临时测试/调试文件

#### 整理方案

**全部归档（到 archive/漫剧素材/项目名/）**:
- ❌ 所有 `-transcript.json` 文件
- ❌ 所有 `.json` 文件（非Excel）

**保留**:
- ✅ Excel文件（*.xlsx）
- ✅ 视频文件（*.mp4）

---

### 5. 测试脚本（scripts/test/）

#### 归档（到 archive/scripts/test/）
- ❌ `test_filename_parser.py`
- ❌ `test_simple.py`
- ❌ `test_video_understand.py`
- ❌ `test_video_understand_v3.py`
- ❌ `test_video_understanding_v2.py`
- ❌ `test_video_understand_v2.py`

---

### 6. 测试数据（test/目录）

#### 保留
- ✅ `V0.5_SKILL_TEST_REPORT.md`
- ✅ `test_human_marks_baseline.json`
- ✅ `test_human_marks_converted.json`
- ✅ `test_comparison_report_不晚忘忧.json`

#### 归档（如果需要）
- 考虑归档到 `archive/test/`

---

### 7. 新文档目录（docs/）

#### 当前结构（很好！）
- ✅ `AUTO_EXTRACT_GUIDE.md` - 自动提取使用指南
- ✅ `AUTO_EXTRACT_IMPLEMENTATION.md` - 自动提取实现报告

#### 建议新增
- 📝 `VERSION_HISTORY.md` - 完整版本历史
- 📝 `PROJECT_STRUCTURE.md` - 项目结构说明
- 📝 `API_REFERENCE.md` - API参考文档

---

## 📁 整理后的目录结构

```
hangzhou-leiming-AI-drama/
│
├── README.md                          # ✅ 更新到V5.1
├── TRAINING_SPEC.md                   # ✅ 保留（可能需要更新）
│
├── docs/                              # 📚 文档目录
│   ├── AUTO_EXTRACT_GUIDE.md          # ✅ 保留
│   ├── AUTO_EXTRACT_IMPLEMENTATION.md # ✅ 保留
│   ├── VERSION_HISTORY.md             # 🆕 完整版本历史
│   ├── PROJECT_STRUCTURE.md           # 🆕 项目结构
│   └── API_REFERENCE.md               # 🆕 API参考
│
├── archive/                           # 📦 归档目录
│   ├── docs/                          # 归档的文档
│   │   ├── IMPLEMENTATION_REPORT.md
│   │   ├── PRODUCT_PLAN.md
│   │   ├── VIDEO_UNDERSTAND_SPEC.md
│   │   └── OPTIMIZATION_REPORTS/      # 所有优化报告
│   │
│   ├── data/hangzhou-leiming/
│   │   ├── skills/                    # 归档的技能文件
│   │   │   ├── v0.1/
│   │   │   ├── v0.2/
│   │   │   ├── v0.3/
│   │   │   └── v0.4/
│   │   └── analysis/                  # 归档的分析结果
│   │
│   ├── 漫剧素材/                      # 归档的测试文件
│   │   ├── 再见，心机前夫/
│   │   ├── 小小飞梦/
│   │   └── ...
│   │
│   └── scripts/                       # 归档的脚本
│       └── test/
│
├── data/hangzhou-leiming/
│   ├── skills/                        # ✅ 只保留v0.5
│   │   ├── ai-drama-clipping-thoughts-v0.5.md
│   │   ├── ai-drama-clipping-thoughts-v0.5.json
│   │   ├── ai-drama-clipping-thoughts-latest.md → v0.5.md
│   │   └── ai-drama-clipping-thoughts-latest.json → v0.5.json
│   │
│   ├── analysis/                      # ✅ 清理后只保留最新
│   │   ├── 不晚忘忧/result.json
│   │   ├── 休书落纸/result.json
│   │   └── ...
│   │
│   └── cache/                         # ✅ 保留（缓存数据）
│
├── scripts/                           # ✅ 清理测试脚本
├── test/                              # ✅ 保留测试数据
├── prompts/                           # ✅ 保留
├── 漫剧素材/                          # ✅ 清理后只保留视频和Excel
└── 新的漫剧素材/                      # ✅ 清理后只保留视频和Excel
```

---

## 🚀 执行步骤

### 第1步：创建归档目录结构
```bash
mkdir -p archive/docs
mkdir -p archive/data/hangzhou-leiming/skills/v0.1
mkdir -p archive/data/hangzhou-leiming/skills/v0.2
mkdir -p archive/data/hangzhou-leiming/skills/v0.3
mkdir -p archive/data/hangzhou-leiming/skills/v0.4
mkdir -p archive/data/hangzhou-leiming/analysis
mkdir -p archive/漫剧素材
mkdir -p archive/scripts/test
```

### 第2步：归档根目录文档
```bash
# 归档过时文档
mv IMPLEMENTATION_REPORT.md archive/docs/
mv PRODUCT_PLAN.md archive/docs/
mv VIDEO_UNDERSTAND_SPEC.md archive/docs/

# 归档优化报告
mkdir -p archive/docs/OPTIMIZATION_REPORTS
mv OPTIMIZATION_*.md archive/docs/OPTIMIZATION_REPORTS/
mv V5.1_EXECUTION_SUMMARY.md archive/docs/OPTIMIZATION_REPORTS/
mv OPTIMIZE_TASK.md archive/docs/OPTIMIZATION_REPORTS/
mv OPTIMIZATION_PLAN.md archive/docs/OPTIMIZATION_REPORTS/
```

### 第3步：归档技能文件
```bash
cd data/hangzhou-leiming/skills/
mv ai-drama-clipping-thoughts-v0.1.* ../../archive/data/hangzhou-leiming/skills/v0.1/
mv ai-drama-clipping-thoughts-v0.2.* ../../archive/data/hangzhou-leiming/skills/v0.2/
mv ai-drama-clipping-thoughts-v0.3.* ../../archive/data/hangzhou-leiming/skills/v0.3/
mv ai-drama-clipping-thoughts-v0.4.* ../../archive/data/hangzhou-leiming/skills/v0.4/

# 删除无用文件
rm framework.json test_skill.json
mv V5_TRAINING_REPORT_v0.4.md ../../../docs/
```

### 第4步：清理分析结果
```bash
cd data/hangzhou-leiming/analysis/

# 归档重复文件
mv *_v2_result.json ../../archive/data/hangzhou-leiming/analysis/
mv *_v4_result.json ../../archive/data/hangzhou-leiming/analysis/
mv *_result.json ../../archive/data/hangzhou-leiming/analysis/ 2>/dev/null || true
mv V4_TEST_REPORT.md ../../archive/data/hangzhou-leiming/analysis/

# 归档百里将就_v2文件夹
mv 百里将就_v2 ../../archive/data/hangzhou-leiming/analysis/
```

### 第5步：清理漫剧素材目录
```bash
# 归档所有JSON文件（保留xlsx和mp4）
find 漫剧素材/ -name "*.json" -exec mv {} archive/漫剧素材/ \;
find 新的漫剧素材/ -name "*.json" -exec mv {} archive/漫剧素材/ \;
```

### 第6步：归档测试脚本
```bash
mv scripts/test/*.py archive/scripts/test/
```

### 第7步：生成新文档
- 📝 创建 `docs/VERSION_HISTORY.md`
- 📝 创建 `docs/PROJECT_STRUCTURE.md`
- 📝 更新 `README.md` 到V5.1

---

## ⚠️ 注意事项

1. **备份优先** - 执行前先创建备份
2. **软链接处理** - 注意latest软链接的正确性
3. **测试验证** - 整理后运行一次完整测试
4. **Git提交** - 整理完成后创建git commit

---

## 📊 整理效果预估

### 文件数量变化
- **删除**: ~100个临时文件
- **归档**: ~50个历史文件
- **保留**: ~20个核心文件

### 目录清晰度
- **根目录**: 13个MD文档 → 2个MD文档
- **技能目录**: 7个文件 → 4个文件
- **分析目录**: 20个文件 → 7个文件

### 维护性提升
- ✅ 目录结构清晰
- ✅ 历史版本归档
- ✅ 文档易于查找
- ✅ 新人友好

---

**下一步**: 确认方案后，开始执行整理操作
