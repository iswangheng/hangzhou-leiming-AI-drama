# GPU 加速渲染指南 (V16.2)

本文档说明如何在不同平台上启用GPU加速渲染，以及如何自动检测和安装依赖。

---

## 快速开始

```bash
# 启用GPU加速（自动检测最佳编码器）
python -m scripts.understand.render_clips data/... video_dir --hwaccel

# 同时启用GPU加速和快速预设
python -m scripts.understand.render_clips data/... video_dir --hwaccel --fast-preset
```

---

## 平台支持

### macOS (Apple Silicon / Intel Mac)

**支持编码器**: `h264_videotoolbox`

**前置条件**:
- macOS 10.13 或更高版本
- FFmpeg 编译时启用 `--enable-videotoolbox`

**检查支持**:
```bash
ffmpeg -encoders | grep videotoolbox
```

**无需额外安装**，macOS自带VideoToolbox框架。

---

### Windows

#### 选项1: NVIDIA GPU (推荐)

**支持编码器**: `h264_nvenc`

**前置条件**:
1. NVIDIA显卡 (GTX 600系列或更高)
2. NVIDIA驱动程序 (版本 390.00 或更高)
3. FFmpeg 编译时启用 `--enable-nvenc`

**检查支持**:
```bash
# 检查FFmpeg是否支持NVENC
ffmpeg -encoders | grep nvenc

# 检查NVIDIA GPU是否识别
nvidia-smi
```

**安装步骤**:

1. **安装NVIDIA驱动**:
   ```powershell
   # 访问 NVIDIA官网下载最新驱动
   # https://www.nvidia.com/Download/index.aspx
   ```

2. **安装支持NVENC的FFmpeg**:
   ```powershell
   # 方式1: 使用scoop安装（推荐）
   scoop install ffmpeg

   # 方式2: 使用chocolatey安装
   choco install ffmpeg

   # 方式3: 使用预编译版本
   # 下载 https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
   # 解压后添加到PATH
   ```

3. **验证安装**:
   ```powershell
   ffmpeg -encoders | findstr nvenc
   # 应该看到: V..... h264_nvenc           NVIDIA NVENC H.264 encoder
   ```

---

#### 选项2: Intel GPU (集成显卡)

**支持编码器**: `h264_qsv`

**前置条件**:
1. Intel 第6代酷睿或更高CPU
2. Intel Graphics Driver
3. FFmpeg 编译时启用 `--enable-libmfx`

**检查支持**:
```powershell
ffmpeg -encoders | findstr qsv
```

**安装步骤**:

1. **更新Intel显卡驱动**:
   ```
   https://www.intel.com/content/www/us/en/download-center/home.html
   ```

2. **安装支持QSV的FFmpeg**:
   - 使用 Intel Media SDK 版本的FFmpeg
   - 或使用 full-build 版本的FFmpeg

---

#### 选项3: AMD GPU

**支持编码器**: `h264_amf`

**前置条件**:
1. AMD Radeon 显卡 (RX 400系列或更高)
2. AMD 驱动程序 (Adrenalin 17.7 或更高)

**检查支持**:
```powershell
ffmpeg -encoders | findstr amf
```

---

### Linux

#### NVIDIA GPU

```bash
# 安装NVIDIA驱动
sudo apt install nvidia-driver-535  # Ubuntu/Debian

# 安装支持NVENC的FFmpeg
sudo apt install ffmpeg

# 或使用snap
sudo snap install ffmpeg
```

#### Intel GPU

```bash
# 安装Intel Media Driver
sudo apt install intel-media-va-driver-non-free

# 安装VAAPI工具
sudo apt install vainfo

# 检查支持
vainfo
```

---

## 自动检测与安装

### 检测GPU加速支持

运行以下命令自动检测你的系统是否支持GPU加速：

```bash
python -c "from scripts.understand.render_clips import _detect_gpu_encoder; print(_detect_gpu_encoder())"
```

**输出示例**:
```
🎮 GPU加速: NVIDIA NVENC
{'encoder': 'h264_nvenc', 'hwaccel': 'cuda', 'name': 'NVIDIA NVENC'}
```

### 自动安装依赖

我们提供了一个自动安装脚本：

```bash
# 检测并安装GPU加速依赖
python -m scripts.setup_gpu_accel
```

---

## 性能对比

| 配置 | 1080p 60秒视频编码时间 | CPU占用 |
|------|----------------------|---------|
| CPU (libx264, preset=fast) | ~50秒 | 100% |
| CPU (libx264, preset=ultrafast) | ~35秒 | 100% |
| **GPU (NVIDIA NVENC)** | **~15秒** | **20%** |
| **GPU (Intel QSV)** | **~18秒** | **25%** |
| **GPU (macOS VideoToolbox)** | **~12秒** | **15%** |

---

## 故障排除

### Windows: "h264_nvenc not found"

**原因**: FFmpeg未编译NVENC支持

**解决方案**:
1. 卸载当前FFmpeg
2. 安装完整版FFmpeg:
   ```powershell
   # 使用scoop
   scoop uninstall ffmpeg
   scoop install ffmpeg-full

   # 或下载gyan.dev完整版
   # https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z
   ```

### Windows: "Could not load nvcuda.dll"

**原因**: NVIDIA驱动未安装或版本过低

**解决方案**:
```powershell
# 检查GPU状态
nvidia-smi

# 如果失败，安装NVIDIA驱动
# https://www.nvidia.com/Download/index.aspx
```

### Linux: "NVENC capable device not found"

**原因**: 驱动未正确安装

**解决方案**:
```bash
# 检查NVIDIA驱动
nvidia-smi

# 如果失败，重新安装驱动
sudo apt purge nvidia*
sudo apt install nvidia-driver-535
sudo reboot
```

### macOS: "VideoToolbox not available"

**原因**: FFmpeg未编译VideoToolbox支持

**解决方案**:
```bash
# 使用homebrew重新安装
brew reinstall ffmpeg

# 或使用homebrew-ffmpeg
brew tap homebrew-ffmpeg/ffmpeg
brew install homebrew-ffmpeg/ffmpeg/ffmpeg
```

---

## 更新日志

- **2026-03-11 V16.2**: 初始版本，支持macOS/Windows/Linux跨平台GPU加速
