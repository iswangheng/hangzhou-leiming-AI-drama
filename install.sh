#!/bin/bash
# ============================================================
# 杭州雷鸣 AI 短剧剪辑服务 - 一键安装脚本
# 用法：bash install.sh
# 支持：macOS / Ubuntu / Debian
# ============================================================

set -e  # 任何命令失败立即退出

# ── 颜色输出 ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERR]${NC}  $1"; exit 1; }

echo ""
echo "============================================================"
echo "  杭州雷鸣 AI 短剧剪辑服务 - 环境安装"
echo "============================================================"
echo ""

# ── 1. 检查 Python ────────────────────────────────────────────
info "检查 Python 版本..."
if ! command -v python3 &>/dev/null; then
    error "未找到 python3，请先安装 Python 3.8+"
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
PY_MINOR=$(echo $PY_VER | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    error "Python 版本过低 ($PY_VER)，需要 3.8+，当前 $PY_VER"
fi
success "Python $PY_VER"

# ── 2. 检查并安装 FFmpeg ──────────────────────────────────────
info "检查 FFmpeg..."
if command -v ffmpeg &>/dev/null; then
    FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1)
    success "FFmpeg 已安装: $FFMPEG_VER"
    # 检查 drawtext 支持（需要 libfreetype）
    if ! ffmpeg -filters 2>/dev/null | grep -q drawtext; then
        warn "FFmpeg 未启用 drawtext 滤镜（需要 --enable-libfreetype），花字叠加功能不可用"
        warn "建议通过 brew install ffmpeg 重新安装（macOS）"
    else
        success "FFmpeg drawtext 滤镜支持正常"
    fi
else
    warn "FFmpeg 未安装，正在自动安装..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &>/dev/null; then
            brew install ffmpeg
            success "FFmpeg 安装完成（macOS via Homebrew）"
        else
            error "请先安装 Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y ffmpeg
        success "FFmpeg 安装完成（Linux via apt）"
    else
        error "请手动安装 FFmpeg: https://ffmpeg.org/download.html"
    fi
fi

# ── 3. 安装 Python 依赖 ───────────────────────────────────────
info "安装 Python 依赖..."

# 升级 pip
python3 -m pip install --upgrade pip -q

# torch 需要单独处理（体积大，区分 CPU/GPU）
info "安装 PyTorch（这可能需要几分钟）..."
if python3 -c "import torch" 2>/dev/null; then
    success "PyTorch 已安装，跳过"
else
    # 检测是否有 NVIDIA GPU
    if command -v nvidia-smi &>/dev/null; then
        info "检测到 NVIDIA GPU，安装 CUDA 版 PyTorch..."
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
    else
        info "未检测到 GPU，安装 CPU 版 PyTorch..."
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    fi
    success "PyTorch 安装完成"
fi

# PaddlePaddle 单独处理（区分 CPU/GPU）
info "安装 PaddlePaddle（这可能需要几分钟）..."
if python3 -c "import paddle" 2>/dev/null; then
    success "PaddlePaddle 已安装，跳过"
else
    if command -v nvidia-smi &>/dev/null; then
        info "检测到 NVIDIA GPU，安装 GPU 版 PaddlePaddle..."
        pip install paddlepaddle-gpu -i https://pypi.tuna.tsinghua.edu.cn/simple
    else
        info "安装 CPU 版 PaddlePaddle..."
        pip install paddlepaddle -i https://pypi.tuna.tsinghua.edu.cn/simple
    fi
    success "PaddlePaddle 安装完成"
fi

# 其余依赖
info "安装其他依赖..."
pip install -r requirements.txt --ignore-requires-python -q \
    --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple
success "Python 依赖安装完成"

# ── 4. 检查中文字体 ───────────────────────────────────────────
info "检查中文字体..."
FONT_FOUND=false
FONT_PATHS=(
    "/System/Library/Fonts/Supplemental/Songti.ttc"
    "/System/Library/Fonts/STHeiti Medium.ttc"
    "/System/share/fonts/truetype/wqy/wqy-zenhei.ttc"
)
for f in "${FONT_PATHS[@]}"; do
    if [ -f "$f" ]; then
        success "中文字体: $f"
        FONT_FOUND=true
        break
    fi
done
if [ "$FONT_FOUND" = false ]; then
    warn "未找到中文字体，花字文字可能显示为方块"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        warn "Linux 安装中文字体：sudo apt-get install -y fonts-wqy-zenhei"
    fi
fi

# ── 5. 检查 .env 文件 ─────────────────────────────────────────
info "检查环境变量配置..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        warn "已从 .env.example 创建 .env，请填写 GEMINI_API_KEY"
    else
        echo "GEMINI_API_KEY=your_key_here" > .env
        warn "已创建 .env 文件，请填写 GEMINI_API_KEY"
    fi
else
    if grep -q "your_key_here" .env 2>/dev/null; then
        warn ".env 中 GEMINI_API_KEY 尚未填写"
    else
        success ".env 配置正常"
    fi
fi

# ── 完成 ──────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo -e "  ${GREEN}✅ 安装完成！${NC}"
echo "============================================================"
echo ""
echo "  下一步："
echo "  1. 编辑 .env 填入 GEMINI_API_KEY"
echo "  2. 把素材放入 漫剧素材/<项目名>/ 目录"
echo "  3. 运行：python -m scripts.understand.video_understand 漫剧素材/<项目名>"
echo ""
