# 视频花字叠加模块调用流程图

## 📊 完整调用链路

```
用户命令（CLI）
    ↓
render_clips.py (主渲染流程)
    ↓
video_overlay.py (V15.6 花字叠加主模块)
    ↓
    ├─→ tilted_label.py (V4.9 热门短剧倾斜角标)
    └─→ overlay_styles.py (10种预设样式)
```

## 🔍 详细流程说明

### 1️⃣ 用户入口（CLI）

**命令示例**：
```bash
# 基础用法：添加花字叠加
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay

# 指定样式
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-overlay \
    --overlay-style gold_luxury

# 完整功能（片尾检测 + 结尾视频 + 花字叠加）
python -m scripts.understand.render_clips \
    data/hangzhou-leiming/analysis/项目名 \
    漫剧素材/项目名 \
    --add-ending \
    --add-overlay
```

**参数说明**：
- `--add-overlay`: 启用花字叠加功能
- `--overlay-style`: 指定花字样式ID（可选，默认随机）

---

### 2️⃣ render_clips.py（渲染流程）

**文件路径**: `scripts/understand/render_clips.py`

**初始化**（第191-213行）：
```python
class ClipRenderer:
    def __init__(self, ..., add_overlay=False, overlay_style_id=None):
        # V15: 花字叠加配置
        self.add_overlay = add_overlay
        self.overlay_style_id = overlay_style_id

        if add_overlay:
            # 延迟导入花字叠加模块
            from .video_overlay.video_overlay import VideoOverlayRenderer, OverlayConfig

            # 创建配置对象
            self.overlay_config = OverlayConfig(
                enabled=True,
                style_id=overlay_style_id,
                project_name=project_name,
                drama_title=project_name
            )

            # 保存渲染器类（延迟创建）
            self._overlay_renderer_class = VideoOverlayRenderer
```

**渲染流程**（第1143-1145行）：
```python
def render_clip(self, clip: Clip, ...):
    # 1. 剪辑视频
    output_path = self._clip_video(...)

    # 2. 添加结尾视频（如果配置了）
    if self.add_ending_clip:
        output_path = self._append_ending_video(output_path)

    # 3. 添加花字叠加（如果配置了）
    if self.add_overlay and hasattr(self, '_overlay_renderer_class'):
        output_path = self._apply_video_overlay(output_path)

    return output_path
```

**花字叠加应用**（第1025-1059行）：
```python
def _apply_video_overlay(self, clip_path: str) -> str:
    # 延迟创建渲染器实例（确保项目级样式统一）
    if not hasattr(self, '_overlay_renderer_instance'):
        self._overlay_renderer_instance = self._overlay_renderer_class(
            self.overlay_config
        )

    # 生成新的输出文件名（添加 "_带花字" 标记）
    new_filename = clip_path_obj.stem + "_带花字" + clip_path_obj.suffix
    new_output_path = str(clip_path_obj.parent / new_filename)

    # 应用花字叠加
    result_path = self._overlay_renderer_instance.apply_overlay(
        input_video=clip_path,
        output_video=new_output_path
    )

    # 删除原视频文件
    Path(clip_path).unlink()

    return result_path
```

---

### 3️⃣ video_overlay.py（花字叠加主模块 V15.6）

**文件路径**: `scripts/understand/video_overlay/video_overlay.py`

**职责**：
- 整合三个文字元素的叠加（热门短剧 + 剧名 + 免责声明）
- 管理样式系统（10种预设样式）
- 处理项目级样式缓存
- 构建FFmpeg滤镜链

**关键类**：
```python
@dataclass
class OverlayConfig:
    """花字叠加配置"""
    enabled: bool = True
    style_id: Optional[str] = None
    project_name: str = ""
    drama_title: str = ""
    disclaimer: Optional[str] = None
    hot_drama_position: str = "top-right"  # V15.6新增
    # ...

class VideoOverlayRenderer:
    """视频花字叠加渲染器"""

    def apply_overlay(self, input_video: str, output_video: str) -> str:
        """主方法：应用完整花字叠加"""
        # 1. 生成热门短剧倾斜角标PNG
        tilted_png_path = self._generate_tilted_label()

        # 2. 构建滤镜链（剧名 + 免责声明）
        drawtext_filters = self._build_drawtext_filters()

        # 3. 执行FFmpeg命令
        self._execute_ffmpeg(tilted_png_path, drawtext_filters)
```

**热门短剧生成**（第420-499行）：
```python
def _generate_tilted_label(self) -> str:
    """生成倾斜角标PNG"""
    # 完全复制tilted_label的apply_label缩放逻辑（V15.6修复）
    smaller_dimension = min(video_width, video_height)
    resolution_ratio = smaller_dimension / 360.0
    scale_factor = resolution_ratio * 0.8

    scaled_font_size = int(28 * scale_factor)
    scaled_box_height = int(60 * scale_factor)
    scaled_corner_offset = int(70 * scale_factor)

    # 创建倾斜角标配置（传递已缩放的值）
    tilted_config = TiltedLabelConfig(
        label_text=self.style.hot_drama.text,
        font_size=scaled_font_size,
        label_color="red@0.95",
        text_color="white",
        position=self.config.hot_drama_position,
        box_height=scaled_box_height,
        corner_offset=scaled_corner_offset
    )

    # 创建渲染器并生成PNG
    tilted_renderer = TiltedLabelRenderer(tilted_config)
    tilted_renderer._generate_png(png_path)

    # 计算overlay位置
    x, y = tilted_renderer._get_overlay_position(video_width, video_height)

    return png_path, x, y
```

---

### 4️⃣ tilted_label.py（倾斜角标模块 V4.9）

**文件路径**: `scripts/understand/video_overlay/tilted_label.py`

**职责**：
- 生成45度倾斜的半透明条幅角标
- 支持不同分辨率的动态字体大小缩放
- PNG预渲染（性能优化）
- 支持左上角和右上角位置

**关键类**：
```python
@dataclass
class TiltedLabelConfig:
    """倾斜角标配置"""
    label_text: str = "热门短剧"
    font_size: int = 28
    label_color: str = "red@0.95"
    text_color: str = "white"
    position: Literal["top-left", "top-right"] = "top-right"
    corner_offset: int = 70
    # ...

class TiltedLabelRenderer:
    """倾斜角标渲染器"""

    def _generate_png(self, output_path: str) -> str:
        """预渲染倾斜角标PNG"""
        # 1. 创建透明画布
        # 2. 绘制半透明色块
        # 3. 绘制文字
        # 4. 旋转45度
        # 5. 输出PNG

    def _get_overlay_position(self, video_width: int, video_height: int) -> tuple:
        """计算overlay位置（V4.9修复版）"""
        canvas_half = 200  # 画布半径
        corner_offset = self.config.corner_offset

        if self.config.position == "top-right":
            x = video_width - corner_offset - canvas_half
            y = corner_offset - canvas_half
        else:  # top-left
            x = corner_offset - canvas_half
            y = corner_offset - canvas_half

        return x, y
```

**V4.9关键修复**：
- ✅ 使用`canvas_half=200px`而非`projection=141px`
- ✅ 修复360p"过于靠中间"的问题
- ✅ 所有分辨率视觉比例一致

---

### 5️⃣ overlay_styles.py（样式定义模块）

**文件路径**: `scripts/understand/video_overlay/overlay_styles.py`

**职责**：
- 定义10种预设样式（颜色主题）
- 管理TextLayer数据结构
- 提供随机样式选择功能

**10种预设样式**：
1. gold_luxury - 金色奢华
2. red_passion - 红色激情
3. blue_cool - 蓝色冷艳
4. purple_mystery - 紫色神秘
5. green_fresh - 绿色清新
6. orange_vitality - 橙色活力
7. pink_romantic - 粉色浪漫
8. silver_elegant - 银色优雅
9. cyan_tech - 青色科技
10. retro_brown - 复古棕色

---

## 🔄 数据流转过程

```
1. 用户运行命令
   └─> render_clips.py接收参数

2. ClipRenderer初始化
   └─> 创建OverlayConfig（保存配置）
   └─> 保存VideoOverlayRenderer类（延迟创建）

3. 渲染每个clip
   ├─> _clip_video()           # 剪辑视频
   ├─> _append_ending_video()   # 添加结尾视频
   └─> _apply_video_overlay()   # 添加花字叠加 ✨
       ├─> 创建VideoOverlayRenderer实例
       ├─> 调用apply_overlay()
       │   ├─> 生成热门短剧PNG（调用tilted_label.py）
       │   ├─> 构建剧名+免责声明滤镜
       │   └─> 执行FFmpeg命令
       └─> 返回带花字的视频路径

4. 输出最终视频
   └─> clips/项目名/clip_带花字.mp4
```

---

## 📦 文件输出示例

**输入视频**：
- `clips/项目名/clip_001.mp4`

**输出视频**（添加花字后）：
- `clips/项目名/clip_001_带花字.mp4`

**花字叠加内容**：
1. **热门短剧** - 左上角/右上角倾斜角标（V4.9）
2. **剧名** - 底部居中，动态字体大小
3. **免责声明** - 底部居中，剧名下方

---

## 🎯 总结

**调用关系**：
- ✅ **tilted_label.py** 可以独立使用（CLI），也可以被video_overlay.py引用
- ✅ **video_overlay.py** 整合tilted_label.py，提供完整的三层叠加
- ✅ **render_clips.py** 引用video_overlay.py，在渲染流程中添加花字

**设计优势**：
- 📦 **模块化**：每个模块职责单一，便于维护
- 🔄 **可复用**：tilted_label.py可独立使用
- 🎨 **可扩展**：overlay_styles.py支持10种预设样式
- ⚡ **高性能**：PNG预渲染，性能提升100倍+

**版本信息**：
- tilted_label.py: **V4.9**（修复投影计算错误）
- video_overlay.py: **V15.6**（统一缩放逻辑）
- render_clips.py: **V15**（集成花字叠加）
