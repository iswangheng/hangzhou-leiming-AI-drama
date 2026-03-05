# 项目待办事项

## 🔄 高优先级

### 1. 自动清理缓存机制 [CRITICAL]

**问题描述**：
缓存文件占用大量空间（当前约1.7GB）：
- `cache/keyframes/`: ~1.4GB（关键帧图片）
- `cache/audio/`: ~335MB（提取的音频文件）
- `cache/asr/`: ~4.6MB（ASR转录文本，很小）

**需求**：
- 实现自动清理机制
- 清理过期的关键帧和音频文件
- 保留ASR文本（很小且有用）

**实现建议**：

1. **基于时间的清理策略**
   ```python
   # 示例配置
   CACHE_RETENTION_DAYS = {
       'keyframes': 7,      # 关键帧保留7天
       'audio': 7,          # 音频保留7天
       'asr': -1,           # ASR文本永久保留（-1表示不删除）
   }
   ```

2. **实现位置**
   - 创建 `scripts/cache_cleaner.py`
   - 集成到 `video_understand.py` 流程末尾
   - 或作为独立的定时任务

3. **清理逻辑**
   ```bash
   # 示例命令
   python -m scripts.cache_cleaner --days 7 --dry-run
   python -m scripts.cache_cleaner --days 7 --execute
   ```

4. **安全性考虑**
   - 清理前检查是否有项目正在使用这些缓存
   - 提供 `--dry-run` 选项预览要删除的文件
   - 记录清理日志

**文件位置**：
- 待创建：`scripts/cache_cleaner.py`
- 待修改：`scripts/understand/video_understand.py`（集成清理调用）

---

## 📋 中优先级

### 2. 集成视频包装花字模块到默认渲染流程 [NEW]

**问题描述**：
视频包装花字模块已实现（V15功能），但还没有集成到默认渲染流程中。

**当前状态**：
- ✅ 花字模块已实现：`scripts/understand/video_overlay/video_overlay.py`
- ✅ 已集成到render_clips.py：可以使用`--add-overlay`参数启用
- ❌ 默认渲染流程未启用：需要手动添加`--add-overlay`参数

**功能说明**：
- **三层花字叠加**：
  1. **热门短剧**（24pt字体）：随机位置（左上/右上），随机显示3-8秒
  2. **剧名**（16pt字体）：底部居中，全时长显示
  3. **免责声明**（12pt字体）：底部居中，剧名下方40px，全时长显示
- **10种预设样式**：gold_luxury, red_passion, blue_cool, purple_mystery等
- **项目级样式统一**：同一项目的所有剪辑使用相同样式（基于项目名hash缓存）
- **自动字体检测**：优先使用Songti.ttc（macOS），fallback到系统字体

**使用方法**（当前需要手动指定参数）：
```bash
# 基础使用（启用花字叠加）
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay

# 指定样式
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay \
    --overlay-style-id gold_luxury

# 完整示例（结尾视频 + 花字叠加）
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-ending \
    --add-overlay
```

**待办事项**：
- [ ] 评估是否应该在默认渲染流程中启用花字叠加
  - 优点：增加视频吸引力，符合短视频平台习惯
  - 缺点：渲染时间稍长（需要额外的FFmpeg处理）
  - 决策：用户手动启用 OR 默认启用添加配置项控制
- [ ] 更新CLAUDE.md文档，添加`--add-overlay`参数说明
- [ ] 创建花字样式预览脚本（查看不同样式的效果）
- [ ] 测试花字叠加在不同分辨率视频下的表现
- [ ] 验证字幕安全区设置是否合理（当前150px）

**文件位置**：
- 核心模块：`scripts/understand/video_overlay/video_overlay.py`
- 样式定义：`scripts/understand/video_overlay/overlay_styles.py`
- 已集成到：`scripts/understand/render_clips.py`（第96-964行）
- 测试脚本：`scripts/understand/video_overlay/test_overlay.py`

---

### 3. 添加标准结尾帧视频功能

**问题描述**：
生成的剪辑没有自动添加标准结尾帧视频

**需求**：
- 在每个剪辑末尾添加标准结尾帧视频
- 使用 `标准结尾帧视频素材/` 目录下的标准结尾

**实现方法**：
V14版本已实现此功能，使用 `--add-ending` 参数：
```bash
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-ending
```

**待办事项**：
- [ ] 验证标准结尾帧视频素材是否存在
- [ ] 测试--add-ending功能是否正常工作
- [ ] 确认结尾帧拼接的准确性

**文件位置**：
- 功能已实现：`scripts/understand/render_clips.py`
- 素材目录：`标准结尾帧视频素材/`

---

### 3. 性能优化
- [ ] 并行处理多个项目（当前是串行）
- [ ] 关键帧提取进度显示（当前没有进度条）
- [ ] ASR转录速度优化（考虑使用更快的模型）

### 3. 质量改进
- [ ] 优化AI分析prompt提高准确率
- [ ] 增加更多质量过滤器
- [ ] 支持人工审核和修正AI标记

---

## 💡 低优先级

### 4. 功能增强
- [ ] 支持批量项目管理（一次性处理多个项目）
- [ ] Web界面可视化查看分析结果
- [ ] 导出分析报告为PDF/Excel

### 5. 文档完善
- [ ] 添加更多示例到文档
- [ ] 录制视频教程
- [ ] 编写故障排查指南

---

## 📝 更新日志

- **2026-03-05**: 创建待办事项列表，标记缓存清理为高优先级
