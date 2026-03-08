# overlay_styles.py 使用说明文档

## 📋 overlay_styles.py 是什么？

**overlay_styles.py** 是花字叠加的样式配置模块，定义了10种预设的颜色主题样式。

## 🎨 包含的内容

### 1️⃣ 10种预设样式

| 样式ID | 名称 | 描述 | 主题色 |
|--------|------|------|--------|
| gold_luxury | 金色豪华 | 金色渐变、粗体描边，适合高端短剧 | 金色 #FFD700 |
| red_passion | 红色激情 | 鲜红色调、醒目突出，适合爱情/都市剧 | 红色系 |
| blue_cool | 蓝色冷艳 | 冷色调、科技感，适合悬疑/刑侦剧 | 蓝色系 |
| purple_mystery | 紫色神秘 | 紫色渐变、神秘感，适合玄幻/仙侠剧 | 紫色系 |
| green_fresh | 绿色清新 | 绿色调、清新自然，适合青春/校园剧 | 绿色系 |
| orange_vitality | 橙色活力 | 橙色调、活力四射，适合都市/喜剧剧 | 橙色系 |
| pink_romantic | 粉色浪漫 | 粉色调、浪漫温馨，适合爱情剧 | 粉色系 |
| silver_elegant | 银色优雅 | 银灰色、简洁优雅，适合职场剧 | 银灰色系 |
| cyan_tech | 青色科技 | 青色调、科技感强，适合科幻/现代剧 | 青色系 |
| retro_brown | 复古棕色 | 棕色调、复古怀旧，适合年代剧 | 棕色系 |

### 2️⃣ 三行文本配置

每种样式都定义了三个文本层：

```python
@dataclass
class OverlayStyle:
    hot_drama: TextLayer      # "热门短剧" 文本
    drama_title: TextLayer    # 剧名（如"《锦庭别后意》"）
    disclaimer: TextLayer     # 免责声明（如"本故事纯属虚构请勿模仿"）
```

### 3️⃣ 文本属性配置

每个TextLayer包含以下属性：

| 属性 | 说明 | 示例值 |
|------|------|--------|
| text | 文本内容 | "热门短剧", "《{title}》" |
| font_size | 字体大小（像素） | 28, 36 |
| font_color | 字体颜色 | "#FFFFFF"（白色） |
| font_alpha | 字体透明度 | 1.0（完全不透明） |
| border_color | 描边颜色 | "#000000"（黑色） |
| border_width | 描边宽度 | 1.0, 2.0 |
| shadow_color | 阴影颜色 | "#000000" |
| shadow_x, shadow_y | 阴影偏移 | 2, 2 |
| x, y | 位置坐标 | "(w-tw)/2", "h-90" |
| rotation | 旋转角度 | -15（向左倾斜15度） |

---

## ✅ 实际使用情况

### ⚠️ 重要说明：V15.6中的实际应用

**虽然overlay_styles.py定义了10种样式，但在V15.6中，实际应用的效果是有限的：**

#### 📌 实际会应用的样式属性：

1. **免责声明文本** ✅
   - 从4种免责声明文案中随机选择：
     - "本故事纯属虚构请勿模仿"
     - "本剧情纯属虚构如有雷同纯属巧合"
     - "影视效果无不良引导请勿模仿"
     - "纯属虚构请勿模仿"

2. **剧名颜色** ⚠️ **被覆盖**
   - 虽然加载了样式，但video_overlay.py会强制覆盖为：
     - 白色（#FFFFFF）或淡紫色（#E6E6FA）
     - **不使用样式中定义的颜色**

3. **剧名描边** ⚠️ **被覆盖**
   - 强制使用：黑色描边，宽度1.0
   - **不使用样式中定义的描边**

#### 📌 不会应用的样式属性：

1. **热门短剧** ❌
   - 样式中的hot_drama配置**完全不用**
   - 实际使用tilted_label.py生成的倾斜角标（红色条幅+白色文字）

2. **字体大小** ❌
   - 样式中的font_size**完全不用**
   - 实际使用video_overlay.py的动态缩放算法（V2.3 v3）

3. **位置坐标** ❌
   - 样式中的x, y坐标**完全不用**
   - 实际位置由video_overlay.py动态计算

4. **旋转角度** ❌
   - 样式中的rotation**不用**
   - 当前版本所有文字都不旋转

5. **阴影效果** ⚠️ **部分覆盖**
   - 强制使用：shadow_x=1, shadow_y=1（轻阴影）
   - **不使用样式中定义的阴影值**

---

## 🎬 最终视频效果

### 实际会出现在视频中的内容：

```
┌─────────────────────────────┐
│  ╱热╲                        │  ← 热门短剧（左上角/右上角，红色条幅）
│ ╱门剧╲                       │
│                              │
│                              │
│         《锦庭别后意》         │  ← 剧名（底部居中，白色或淡紫色）
│                              │
│    本故事纯属虚构请勿模仿     │  ← 免责声明（剧名下方）
└─────────────────────────────┘
```

### 详细说明：

1. **热门短剧**（倾斜角标）
   - 位置：左上角或右上角
   - 样式：红色条幅（95%不透明度）+ 白色文字
   - 字体大小：动态缩放（360p: 22px, 1080p: 68px）
   - 旋转：45度倾斜
   - 来源：**tilted_label.py**（不使用overlay_styles）

2. **剧名**
   - 位置：底部居中
   - 颜色：白色或淡紫色（随机选择）
   - 描边：黑色细描边（宽度1.0）
   - 字体大小：动态缩放（360p: 18px, 1080p: 52px）
   - 文字：从样式模板替换`{title}`占位符

3. **免责声明**
   - 位置：剧名下方，底部居中
   - 颜色：黄色或白色（固定）
   - 字体大小：动态缩放（360p: 16px, 1080p: 46px）
   - 文字：从4种文案中随机选择

---

## 🔍 样式加载流程

### 代码执行流程：

```python
# 1. 加载样式（第85-95行）
def _get_or_select_style(self) -> OverlayStyle:
    if self.config.style_id:
        # 使用指定样式
        style = get_style(self.config.style_id)
    else:
        # 随机选择样式（基于项目名称hash，确保项目级统一）
        style = get_random_style(self.config.project_name)

    # 缓存样式选择
    self._cache_style_selection(style.id)
    return style

# 2. 准备文本图层（第153-193行）
def _prepare_text_layers(self) -> None:
    # ⚠️ 覆盖剧名颜色（不使用样式的颜色）
    color_schemes = [
        {"font": "#FFFFFF", "border": "#000000", "name": "白色"},
        {"font": "#E6E6FA", "border": "#000000", "name": "淡紫色"},
    ]
    selected_color = random.choice(color_schemes)
    self.style.drama_title.font_color = selected_color["font"]
    self.style.drama_title.border_color = selected_color["border"]

    # 强制设置描边宽度（不使用样式的宽度）
    self.style.drama_title.border_width = 1.0

    # 替换剧名占位符
    title = self.config.drama_title or self.config.project_name
    self.style.drama_title.text = self.style.drama_title.text.replace(
        "{title}", title
    )

    # 替换免责声明占位符
    disclaimer = self.config.disclaimer or get_random_disclaimer()
    self.style.disclaimer.text = self.style.disclaimer.text.replace(
        "{disclaimer}", disclaimer
    )
```

---

## 💡 为什么overlay_styles存在但大部分配置不用？

### 历史原因：

1. **V15.0-V15.3**: 最初设计时，overlay_styles的配置是全部生效的
2. **V15.4**: 集成tilted_label后，"热门短剧"改用倾斜角标，不再使用样式的hot_drama配置
3. **V15.5-V15.6**: 为了保持朴素清晰的效果，强制覆盖了剧名的颜色和描边

### 当前设计理念：

**优先级顺序**：
```
用户明确需求 > 动态适配算法 > 样式配置
```

**简化设计的好处**：
- ✅ 视觉效果统一（所有项目风格一致）
- ✅ 代码维护简单（不需要维护10种样式的差异）
- ✅ 用户体验好（朴素清晰，不花哨）

---

## 📊 总结

### overlay_styles.py 在V15.6中的作用：

| 配置项 | 是否使用 | 实际来源 |
|--------|---------|----------|
| 热门短剧文本 | ❌ | tilted_label.py（固定"热门短剧"） |
| 热门短剧样式 | ❌ | tilted_label.py（红色条幅） |
| 剧名 | ✅ | 样式模板 + 覆盖颜色 |
| 剧名颜色 | ❌ | video_overlay.py（白/淡紫随机） |
| 剧名字体大小 | ❌ | video_overlay.py（动态缩放） |
| 免责声明 | ✅ | 样式模板（4种随机） |
| 免责声明颜色 | ⚠️ | 部分使用（黄色/白色） |
| 字体大小 | ❌ | video_overlay.py（动态缩放） |
| 位置坐标 | ❌ | video_overlay.py（动态计算） |
| 旋转角度 | ❌ | 不旋转 |

### 实际效果：

**overlay_styles.py在V15.6中主要起到两个作用**：

1. ✅ **提供免责声明模板**：4种免责声明文案
2. ✅ **提供剧名占位符**：`{title}`用于替换真实剧名

**其他90%的配置都被覆盖或不使用**。

---

## 🚀 如果要完全使用样式配置

如果将来需要完全使用overlay_styles的配置，需要修改video_overlay.py：

1. 移除`_prepare_text_layers()`中的颜色覆盖逻辑
2. 使用样式中定义的font_size、font_color、border_width等
3. 实现样式的rotation、animation等高级特性

但当前设计**有意简化**，以保持视觉效果的一致性和朴素性。
