# 视频画面内容审核与马赛克遮盖技术方案

> 调研日期: 2026-03-12
> 需求来源: 客户需求 - 短剧画面违规内容遮盖

## 📋 需求背景

当前项目已实现**字幕敏感词检测**（V16），可以检测字幕中的敏感词并应用马赛克遮盖。

**新需求**：对视频**画面中的违规内容**（如暴露镜头、血腥画面）进行自动检测和遮盖。

> 注：这是与字幕敏感词检测不同的另一个维度，一个是**文字层面**，一个是**画面层面**。

---

## 🎯 需求分析

### 需要遮盖的内容类型

| 类型 | 描述 | 检测难度 |
|------|------|---------|
| **色情暴露** | 身体暴露部位 | ⭐⭐⭐ 中等 |
| **血腥暴力** | 暴力画面、出血场景 | ⭐⭐⭐ 中等 |
| **纹身/伤疤** | 特殊纹身、明显伤疤 | ⭐⭐ 简单 |
| **敏感标志** | 品牌Logo、身份证件 | ⭐ 简单 |

### 核心挑战

1. **违规内容定义模糊** - "擦边"内容 vs 真正违规难以界定
2. **检测精度** - 开源模型准确率不如商业API
3. **实时性** - 视频帧数多，检测耗时长
4. **误伤** - 正常剧情可能被误判

---

## 🛠️ 技术方案对比

### 方案一：商业云服务API（推荐）

#### 阿里云视频审核

**产品地址**: https://ai.aliyun.com/vi/censor

**能力**:
- 色情识别：露点、肤色、姿态、性暗示
- 暴恐识别：武器、血腥、爆炸、战争
- 政治敏感：人物、旗帜、标语
- 广告识别：二维码、logo、水印

**计费**: 按视频时长计费

| 计费方式 | 价格 | 备注 |
|---------|------|------|
| **按量付费** | **0.1元/分钟** | 0-3000分钟区间 |
| 阶梯优惠 | 0.05元/分钟 | 3000分钟以上 |
| 批量采购 | 0.02元/分钟 | 1万分钟以上 |

**换算示例**:
- 1部10集短剧（每集3分钟）= 30分钟 = **3元/部**
- 1个月处理100部剧 = 3000分钟 = **300元/月**

**接入方式**:
```python
# 阿里云视频审核SDK
from aliyunsdkcore import client
from aliyunsdkviapi_regen.request.v20211117 import SubmitVideoCensorJobRequest

# 调用API获取违规时间区间和坐标
response = client.do_action_with_exception(request)
# 返回违规片段列表，包含时间区间和坐标
```

#### 腾讯云 视频审核（数据万象）

**产品地址**: https://cloud.tencent.com/document/product/460/58119

**特点**:
- 支持实时流和点播
- 返回违规标签、时间、坐标
- 支持批量处理

**计费**: 按视频时长计费

| 计费方式 | 价格 | 备注 |
|---------|------|------|
| **视频审核** | **约0.05元/分钟** | 按视频时长计费 |
| 图片审核 | 0.067美元/千次 | 按帧计费 |

**换算示例**:
- 1部10集短剧（每集3分钟）= 30分钟 = **1.5元/部**
- 1个月处理100部剧 = 3000分钟 = **150元/月**

#### 七牛云 内容审核

**产品地址**: https://www.qiniu.com/products/censor

**特点**:
- 按量计费
- 支持图片、视频、语音、文本
- 覆盖主流违规类型

**计费**:

| 类型 | 价格 |
|------|------|
| 视频审核 | 约 ¥20-30/万张 |
| 图片鉴黄 | ¥50/万张 |

---

### 方案二：开源模型 + 自建（免费）

#### 2.1 人体检测 + 关键点

**技术栈**:
- **YOLOv8** - 人体检测
- **DWPose / OpenPose** - 身体关键点检测
- **FFmpeg** - 视频马赛克处理

**检测目标**:
- 人脸 → 可用成熟技术（MTCNN/RetinaFace）
- 身体部位 → 需要自定义训练
- 暴力场景 → 需要目标检测模型

**开源项目参考**:
- [deface](https://github.com/ORB-HD/deface) - 人脸自动打码
- [YOLOv8-nude](https://github.com/notAI-tech/YOLOv8-nude) - 身体暴露检测

#### 2.2 NSFW检测模型

| 模型 | 能力 | 精度 |
|------|------|------|
| OpenNSFW2 (Yahoo) | 色情内容检测 | 高 |
| nude_detector | 身体暴露检测 | 中 |
| Q16-NSFW | NSFW内容分类 | 高 |

**使用示例**:
```python
from opennsfw2 import predict_image, predict_video

# 检测单帧
result = predict_image(frame)  # 返回 NSFW 概率
# result: {'nsfw': 0.85, 'drawing': 0.12, ...}
```

---

### 方案三：混合方案（推荐）

```
┌─────────────────────────────────────────────────────────────┐
│                   视频画面审核流程                            │
├─────────────────────────────────────────────────────────────┤
│  1. 抽帧检测                                                │
│     └── 每隔 N 秒抽取一帧画面                                │
│           ↓                                                 │
│  2. 多模型并行检测                                          │
│     ├── 人脸检测 → 记录坐标                                 │
│     ├── NSFW检测 → 标记违规帧                               │
│     ├── 暴恐检测 → 标记违规帧                               │
│     └── 文字识别 → 敏感标志                                │
│           ↓                                                 │
│  3. 坐标聚合                                                │
│     └── 将帧级坐标映射到时间轴                               │
│           ↓                                                 │
│  4. FFmpeg马赛克                                           │
│     └── 对违规区域应用马赛克/模糊                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 技术实现方案

### 推荐方案：分阶段实现

#### Phase 1: 人脸马赛克（最简单）

**实现目标**: 对视频中的人脸自动打马赛克

**技术方案**:
```python
# 1. 视频抽帧
ffmpeg -i input.mp4 -vf "fps=1" frames/frame_%04d.jpg

# 2. 人脸检测
import cv2
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
faces = face_cascade.detectMultiScale(gray, 1.3, 5)

# 3. 记录时间坐标
face_regions = []
for frame_idx, face in enumerate(faces):
    timestamp = frame_idx  # 每秒1帧
    face_regions.append({
        'timestamp': timestamp,
        'bbox': face  # x, y, w, h
    })

# 4. FFmpeg马赛克
ffmpeg -i input.mp4 -vf "delogo=x=..:y=..:w=..:h=.." output.mp4
```

**优点**: 技术成熟，效果稳定
**适用场景**: 演员需遮盖、隐私保护

---

#### Phase 2: 接入商业API

**实现目标**: 全面检测色情、血腥、暴力等内容

**技术方案**:
```python
# 阿里云视频审核示例
from aliyunsdkviapi_regen.request.v20211117 import SubmitVideoCensorJobRequest

def detect_video_censor(video_path):
    # 1. 提交审核任务
    request = SubmitVideoCensorJobRequest.Request()
    request.set_FileUrl(video_path)
    request.set_Scenes(["porn", "terror", "politics"])

    # 2. 获取审核结果
    response = client.do_action_with_exception(request)

    # 3. 解析违规片段
    violations = []
    for result in response['Data']['Results']:
        if result['Suggestion'] == 'block':
            violations.append({
                'label': result['Label'],
                'start': result['StartTime'],
                'end': result['EndTime'],
                'bbox': result.get('Location', {})
            })

    return violations
```

**优点**: 识别准确率高，无需自己训练
**缺点**: 付费，需要网络调用

---

#### Phase 3: 自建NSFW检测模型（可选）

**实现目标**: 降低API调用成本，做初筛

**技术方案**:
```python
# 使用开源NSFW模型做初筛
import torch
from transformers import AutoModelForImageClassification

model = AutoModelForImageClassification.from_pretrained("Falconsai/nsfw_image_detection")

def detect_nsfw(frame):
    inputs = processor(frame, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)

    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    return probs[0][1].item()  # NSFW概率
```

---

## 📝 FFmpeg马赛克实现

### 方式一：马赛克模糊

```bash
# 方式1：使用boxblur
ffmpeg -i input.mp4 -vf "delogo=x=100:y=50:w=200:h=100" output.mp4

# 方式2：使用盒子模糊
ffmpeg -i input.mp4 -vf "boxblur=2:1" -c:a copy output.mp4

# 方式3：使用gblur（高斯模糊）
ffmpeg -i input.mp4 -vf "gblur=sigma=5" -c:a copy output.mp4
```

### 方式二：指定区域模糊

```python
# Python + FFmpeg 实现指定区域马赛克
def apply_mosaic(video_path, regions, output_path):
    """
    regions: [{'x': 100, 'y': 50, 'w': 200, 'h': 100}, ...]
    """
    # 构建filter
    filters = []
    for i, r in enumerate(regions):
        filters.append(f"delogo=x={r['x']}:y={r['y']}:w={r['w']}:h={r['h']}")

    filter_str = ",".join(filters)
    cmd = f"ffmpeg -i {video_path} -vf '{filter_str}' -c:a copy {output_path}"

    subprocess.run(cmd, shell=True)
```

---

## 💰 成本估算

### 商业API成本（按量付费）

#### 阿里云 视频审核增强版

| 用量区间 | 单价 | 100部剧/月成本 |
|---------|------|---------------|
| 0-3000分钟 | 0.1元/分钟 | ¥300/月 |
| 3000分钟以上 | 0.05元/分钟 | ¥150/月 |
| 1万分钟以上 | 0.02元/分钟 | ¥60/月 |

#### 腾讯云 数据万象

| 用量 | 单价 | 100部剧/月成本 |
|------|------|---------------|
| 任意用量 | 约0.05元/分钟 | ¥150/月 |

### 业务场景成本估算

假设业务场景：
- **每天**处理 **10部** 短剧
- 每部短剧 **10集**，每集 **3分钟**
- 总计：10 × 10 × 3 = **300分钟/天**

| 供应商 | 单价 | 日成本 | 月成本（30天） |
|--------|------|--------|---------------|
| 阿里云 | 0.1元/分钟 | ¥30/天 | **¥900/月** |
| 腾讯云 | 0.05元/分钟 | ¥15/天 | **¥450/月** |

### 自建模型成本（可选）

| 方案 | 硬件 | 一次性成本 | 月成本 |
|------|------|-----------|--------|
| GPU服务器 | RTX 4090 | ¥15,000 | ¥0 |
| 云GPU | V100 | ¥0 | ¥500/月 |

**说明**: 自建模型需要：
- 购买/租赁GPU服务器
- 训练或微调NSFW检测模型
- 持续维护和更新模型
- 初期投入大，适合大规模场景（>1000部/月）

---

## 📌 建议实施路径

```
┌─────────────────────────────────────────────────────────────┐
│                    实施路径建议                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  阶段一：人脸马赛克（1-2周）                                │
│  ├── 技术成熟，实现简单                                      │
│  ├── 适用于：演员遮盖、隐私保护                              │
│  └── 预估效果：⭐⭐⭐⭐⭐                                   │
│                                                             │
│  阶段二：接入商业API（2-3周）                               │
│  ├── 覆盖全面：色情、暴恐、政治敏感                          │
│  ├── 适用于：全面内容审核                                   │
│  └── 预估效果：⭐⭐⭐⭐⭐                                   │
│                                                             │
│  阶段三：自建模型（可选，4-8周）                            │
│  ├── 降低成本，长期可控                                     │
│  ├── 适用于：大流量场景                                     │
│  └── 预估效果：⭐⭐⭐                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔗 相关文档

- [敏感词检测设计](./docs/sensitive_word_mask_design.md) - V16 字幕敏感词检测方案
- [CLAUDE.md](./CLAUDE.md) - 项目技术文档
- [TODO.md](./TODO.md) - 待办事项列表

---

## 📝 技术参考

### 云服务文档
- 阿里云视频审核: https://ai.aliyun.com/vi/censor
- 腾讯云内容安全: https://cloud.tencent.com/document/product/1124
- 七牛云内容审核: https://www.qiniu.com/products/censor

### 开源项目
- YOLOv8: https://github.com/ultralytics/ultralytics
- OpenNSFW2: https://github.com/b-arriviere/opennsfw2
- deface: https://github.com/ORB-HD/deface
- DWPose: https://github.com/IDEA-Research/DWPose

---

*本文档为技术调研记录，未来可作为功能实现参考*
