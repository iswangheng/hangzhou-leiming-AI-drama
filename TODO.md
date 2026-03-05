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

### 2. 添加标准结尾帧视频功能

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
