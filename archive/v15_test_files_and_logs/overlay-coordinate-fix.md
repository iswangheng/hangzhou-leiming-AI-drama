# 花字叠加坐标问题修复报告

## 问题概述

**严重问题**：杭州雷鸣AI短剧剪辑服务中，剧名位置错误

- **用户期望**：剧名显示在视频底部
- **实际效果**：剧名显示在视频顶部
- **影响范围**：所有10个花字叠加样式

## 调研过程

### 1. FFmpeg坐标系统验证

**测试方法**：创建纯色视频，在不同Y坐标位置添加文本

**测试代码**：`test/ffmpeg_coordinate_test.py` 和 `test/detailed_coordinate_test.py`

**测试结果**：

```
✅ 红色文本 "TOP_y=30" - 在顶部（距离顶部30像素）
✅ 绿色文本 "UPPER_y=120" - 在中上部（距离顶部120像素）
✅ 蓝色文本 "LOWER_y=520" - 在中下部（距离顶部520像素）
✅ 黄色文本 "BOTTOM_h-45" - 在底部（距离底部45像素）✨
✅ 紫色文本 "ABS_BOTTOM_h-20" - 在最底部（距离底部20像素）
```

**结论**：
- ✅ FFmpeg坐标系统**完全正常**
- ✅ `y="h-45"` 确实在底部（y = 640 - 45 = 595）
- ✅ `(0,0)` 在左上角，Y轴从上到下增加

### 2. 实际代码分析

**分析工具**：`test/analyze_actual_overlay.py`

**发现的问题**：

```python
# 所有10个样式的剧名配置
drama_title=TextLayer(
    text="《{title}》",
    font_size=16,
    font_color="#FFA500",
    x="(w-tw)/2",  # 水平居中 ✅
    y="120",        # ❌ 问题在这里！应该在底部
)
```

**统计结果**：
- 总样式数：10个
- 底部显示（y=h-*）：0个 ❌
- 顶部显示（y=120-130）：10个 ❌

### 3. 问题根源

**配置错误**：所有样式的 `drama_title.y` 都设置为固定值（120-130），而不是相对底部值（h-45）

**原因分析**：
1. 可能是复制粘贴错误
2. 可能是对坐标系统理解不足
3. 可能是设计需求变更但未更新配置

## 修复方案

### 修复内容

#### 1. 剧名位置修复

**修复前**：
```python
drama_title=TextLayer(
    ...
    y="120",  # 或 y="125", y="128" 等固定值
)
```

**修复后**：
```python
drama_title=TextLayer(
    ...
    y="h-45",  # 距离底部45像素
)
```

**计算公式**：
- 视频高度：640像素（竖屏）
- 目标位置：y = h - 45 = 640 - 45 = 595
- 实际效果：距离底部45像素

#### 2. "热门短剧"颜色修复

**修复前**：
- 红色系：#FF0000, #FF4500, #FF1493等
- 用户反馈：不够鲜艳、活泼

**修复后**：
- 主色：**金黄色 #FFD700**
- 描边：根据样式主题变化
  - 金色豪华：橙色描边 #FFA500
  - 红色激情：深橙色描边 #FF8C00
  - 蓝色冷艳：深青色描边 #00CED1
  - 等等...

### 修复的样式列表

✅ 所有10个样式已全部修复：

1. **gold_luxury**（金色豪华）
2. **red_passion**（红色激情）
3. **blue_cool**（蓝色冷艳）
4. **purple_mystery**（紫色神秘）
5. **green_fresh**（绿色清新）
6. **orange_vitality**（橙色活力）
7. **pink_romantic**（粉色浪漫）
8. **silver_elegant**（银色优雅）
9. **cyan_tech**（青色科技）
10. **retro_brown**（复古棕色）

### 修复后的布局

```
┌─────────────────────────┐
│  🔥 热门短剧 (左上/右上) │  ← y=50, 随机左右
│                         │
│                         │
│                         │
│                         │
│                         │
│                         │
│                         │
│                         │
│   《剧名标题》           │  ← y=h-45, 居中 ✨
│   ⚠️ 免责声明            │  ← y=h-25/h-70, 居中
└─────────────────────────┘
```

## 验证结果

### 自动验证

**验证脚本**：`test/final_verification.py`

**验证结果**：
```
✅ 所有10个样式的剧名位置: y=h-45
✅ 所有样式的"热门短剧"颜色: #FFD700
✅ FFmpeg坐标系统: 正常工作
```

### 手动验证

**测试视频截图**：
- 文件：`/var/folders/.../screenshot_00_00_01.png`
- 验证点：
  - ✅ 黄色文本 "BOTTOM_h-45" 在底部
  - ✅ 红色文本 "TOP_y=30" 在顶部
  - ✅ 坐标系统符合预期

## 技术要点

### FFmpeg drawtext 坐标系统

1. **坐标原点**：左上角 (0,0)
2. **Y轴方向**：从上到下增加
3. **表达式支持**：
   - `h`：视频高度
   - `w`：视频宽度
   - `tw`：文本宽度
   - `th`：文本高度
   - `h-45`：距离底部45像素

### 转义规则

```python
# 表达式参数需要转义特殊字符
def format_param_value(key: str, value: str) -> str:
    if key in ['x', 'y', 'enable']:
        escaped = str(value).replace('\\', '\\\\') \
                            .replace(':', '\\:') \
                            .replace(',', '\\,') \
                            .replace('(', '\\(') \
                            .replace(')', '\\)')
        return f"{key}={escaped}"
    return f"{key}={value}"
```

### 示例命令

```bash
ffmpeg -i input.mp4 \
  -vf "drawtext=text='剧名':fontsize=16:x=(w-tw)/2:y=h-45:fontcolor=#FFA500" \
  -c:a copy output.mp4
```

## 文件变更

### 修改的文件

1. **scripts/understand/video_overlay/overlay_styles.py**
   - 修改所有10个样式的 `drama_title.y` 参数
   - 修改所有样式的 `hot_drama.font_color` 为 #FFD700
   - 调整部分描边颜色以匹配新主题

### 新增的测试文件

1. **test/ffmpeg_coordinate_test.py**
   - 基础坐标系统测试

2. **test/detailed_coordinate_test.py**
   - 详细的坐标验证（带截图）

3. **test/analyze_actual_overlay.py**
   - 分析实际配置问题

4. **test/final_verification.py**
   - 修复后的完整验证

## 测试建议

### 自动测试

```bash
# 运行所有测试
python test/ffmpeg_coordinate_test.py
python test/detailed_coordinate_test.py
python test/analyze_actual_overlay.py
python test/final_verification.py
```

### 手动测试

1. **生成测试视频**
   ```bash
   python test/final_verification.py
   ```

2. **检查输出**
   - 打开临时目录中的视频文件
   - 验证剧名位置（应该在底部）
   - 验证"热门短剧"颜色（金黄色）
   - 验证免责声明位置（最底部）

3. **实际项目测试**
   ```bash
   python -m scripts.understand.render_clips \
       data/hangzhou-leiming/analysis/项目名 \
       漫剧素材/项目名 \
       --add-overlay
   ```

## 预防措施

### 代码审查清单

- [ ] 坐标参数使用相对值（h-*, w-*）而非绝对值
- [ ] 颜色选择符合用户需求
- [ ] 表达式正确转义
- [ ] 测试覆盖所有样式

### 文档更新

- ✅ 更新 CLAUDE.md 中的花字叠加说明
- ✅ 添加坐标系统验证方法
- ✅ 记录常见问题和解决方案

## 总结

### 问题根源

**配置错误**：所有样式的剧名Y坐标使用固定值（120-130）而非相对底部值（h-45）

### 修复方法

**参数修改**：将所有样式的 `drama_title.y` 从 `"120"` 改为 `"h-45"`

### 修复效果

- ✅ 剧名正确显示在视频底部（距底部45像素）
- ✅ "热门短剧"使用更鲜艳的金黄色（#FFD700）
- ✅ 所有10个样式已全部修复
- ✅ FFmpeg坐标系统验证正常

### 经验教训

1. **理解底层系统**：FFmpeg坐标系统本身没问题，问题在配置
2. **全面测试**：需要测试所有样式，不能只测一个
3. **表达式优于硬编码**：使用 `h-45` 比 `120` 更可靠
4. **用户反馈重要**：颜色问题需要及时响应

---

**修复日期**：2026-03-05
**修复版本**：V15.1
**修复人员**：Claude AI
**测试状态**：✅ 已验证
