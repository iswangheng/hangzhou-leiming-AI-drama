#!/bin/bash

# ============================================
# 依赖和环境检查脚本
# 快速验证所有依赖是否正确安装
# ============================================

echo "🔍 检查项目依赖和环境..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 统计变量
total_checks=0
passed_checks=0
failed_checks=0

# 检查函数
check() {
  local name=$1
  local command=$2

  total_checks=$((total_checks + 1))

  echo -n "检查 $name... "

  if eval "$command" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 通过${NC}"
    passed_checks=$((passed_checks + 1))
    return 0
  else
    echo -e "${RED}❌ 失败${NC}"
    failed_checks=$((failed_checks + 1))
    return 1
  fi
}

# ============================================
# 1. Node.js 环境
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Node.js 环境"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check "Node.js" "command -v node"
if [ $? -eq 0 ]; then
  node_version=$(node -v)
  echo "   版本: $node_version"
fi

check "npm" "command -v npm"
if [ $? -eq 0 ]; then
  npm_version=$(npm -v)
  echo "   版本: $npm_version"
fi

# ============================================
# 2. Python 环境
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 Python 环境"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check "Python 3" "command -v python3"
if [ $? -eq 0 ]; then
  python_version=$(python3 --version)
  echo "   $python_version"
fi

check "pip3" "command -v pip3"

check "Whisper 模块" "python3 -c 'import whisper'"
if [ $? -eq 0 ]; then
  whisper_version=$(python3 -c "import whisper; print(whisper.__version__)" 2>/dev/null || echo "未知")
  echo "   版本: $whisper_version"
fi

# ============================================
# 3. 外部工具
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 外部工具"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check "FFmpeg" "command -v ffmpeg"
if [ $? -eq 0 ]; then
  ffmpeg_version=$(ffmpeg -version 2>&1 | head -1)
  echo "   $ffmpeg_version"
fi

check "Redis" "command -v redis-cli"
if [ $? -eq 0 ]; then
  redis_version=$(redis-cli --version 2>&1)
  echo "   $redis_version"
fi

# 检查 Redis 是否运行
echo -n "检查 Redis 服务... "
if redis-cli ping > /dev/null 2>&1; then
  echo -e "${GREEN}✅ 运行中${NC}"
  passed_checks=$((passed_checks + 1))
else
  echo -e "${YELLOW}⚠️  未运行${NC} (启动: brew services start redis)"
fi
total_checks=$((total_checks + 1))

# ============================================
# 4. Node.js 依赖
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 Node.js 依赖"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d "node_modules" ]; then
  echo -e "${GREEN}✅ node_modules 存在${NC}"
  passed_checks=$((passed_checks + 1))
  total_checks=$((total_checks + 1))

  # 检查关键依赖
  key_deps=("next" "react" "drizzle-orm" "better-sqlite3" "bullmq" "remotion")
  for dep in "${key_deps[@]}"; do
    if [ -d "node_modules/$dep" ]; then
      echo -e "  ${GREEN}✓${NC} $dep"
    else
      echo -e "  ${RED}✗${NC} $dep (缺失)"
    fi
  done
else
  echo -e "${RED}❌ node_modules 不存在${NC}"
  echo "   请运行: npm install"
  failed_checks=$((failed_checks + 1))
  total_checks=$((total_checks + 1))
fi

# ============================================
# 5. 环境变量配置
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  环境变量配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f ".env.local" ]; then
  echo -e "${GREEN}✅ .env.local 存在${NC}"
  passed_checks=$((passed_checks + 1))
  total_checks=$((total_checks + 1))

  # 检查关键配置
  if grep -q "YUNWU_API_KEY=" .env.local && ! grep -q "YUNWU_API_KEY=sk-your_" .env.local; then
    echo -e "  ${GREEN}✓${NC} YUNWU_API_KEY 已配置"
  else
    echo -e "  ${YELLOW}⚠${NC} YUNWU_API_KEY 未配置或使用默认值"
  fi

  if grep -q "GEMINI_MODEL=" .env.local; then
    model=$(grep "GEMINI_MODEL=" .env.local | cut -d'=' -f2)
    echo -e "  ${GREEN}✓${NC} GEMINI_MODEL: $model"
  fi
else
  echo -e "${YELLOW}⚠️  .env.local 不存在${NC}"
  echo "   请运行: cp .env.example .env.local"
  total_checks=$((total_checks + 1))
fi

# ============================================
# 6. 构建测试
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔨 构建测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d ".next" ]; then
  echo -e "${GREEN}✅ .next 构建目录存在${NC}"
  passed_checks=$((passed_checks + 1))
  total_checks=$((total_checks + 1))
else
  echo -e "${YELLOW}⚠️  .next 构建目录不存在${NC}"
  echo "   请运行: npm run build"
  total_checks=$((total_checks + 1))
fi

# ============================================
# 总结
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 检查结果汇总"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "总检查项: $total_checks"
echo -e "${GREEN}通过: $passed_checks${NC}"
echo -e "${RED}失败: $failed_checks${NC}"
echo ""

if [ $failed_checks -eq 0 ]; then
  echo -e "${GREEN}🎉 所有依赖检查通过！环境配置完成。${NC}"
  echo ""
  echo "下一步操作："
  echo "  1. 启动开发服务器: npm run dev"
  echo "  2. 打开浏览器: http://localhost:3000"
  echo ""
  exit 0
else
  echo -e "${RED}⚠️  发现 $failed_checks 个问题，请修复后再继续。${NC}"
  echo ""
  echo "查看详细说明："
  echo "  📖 docs/DEPENDENCIES.md"
  echo ""
  exit 1
fi
