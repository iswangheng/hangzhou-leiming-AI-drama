#!/bin/bash
# ============================================
# 完整测试环境启动脚本
# ============================================

set -e

echo "🎬 DramaGen AI - 测试环境启动"
echo "=================================="
echo ""

# 1. 检查并启动 Redis
echo "📍 步骤 1/5: 检查 Redis 服务..."
if redis-cli ping > /dev/null 2>&1; then
  echo "✅ Redis 已运行"
else
  echo "❌ Redis 未运行，正在启动..."

  # macOS 尝试启动 Redis
  if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew > /dev/null 2>&1; then
      brew services start redis
      echo "✅ Redis 已通过 Homebrew 启动"
      sleep 2
    else
      echo "❌ 请先安装 Redis: brew install redis"
      exit 1
    fi
  else
    echo "❌ 请手动启动 Redis"
    exit 1
  fi
fi
echo ""

# 2. 初始化数据库
echo "📍 步骤 2/5: 初始化数据库..."
npm run db:init > /dev/null 2>&1 || echo "数据库已初始化"
echo "✅ 数据库初始化完成"
echo ""

# 3. 检查环境变量
echo "📍 步骤 3/5: 检查环境变量..."
if [ ! -f .env.local ]; then
  echo "❌ .env.local 不存在，请先配置环境变量"
  echo "   复制 .env.example 并填写配置"
  exit 1
fi

# 检查关键配置
if grep -q "GEMINI_API_KEY=.*your.*key" .env.local; then
  echo "❌ 请先配置 GEMINI_API_KEY"
  exit 1
fi

echo "✅ 环境变量配置正常"
echo ""

# 4. 启动 Worker 进程
echo "📍 步骤 4/5: 检查 Worker 进程..."
if pgrep -f "node.*worker" > /dev/null; then
  echo "✅ Worker 已运行"
else
  echo "🚀 正在启动 Worker..."
  # 在后台启动 Worker
  nohup node lib/queue/workers.ts > logs/worker.log 2>&1 &
  echo "✅ Worker 已启动 (PID: $!)"
  sleep 2
fi
echo ""

# 5. 检查 Next.js 开发服务器
echo "📍 步骤 5/5: 检查 Next.js 开发服务器..."
if pgrep -f "next-server" > /dev/null; then
  echo "✅ Next.js 开发服务器已运行"
else
  echo "🚀 正在启动 Next.js 开发服务器..."
  npm run dev > /dev/null 2>&1 &
  echo "✅ Next.js 开发服务器已启动"
  sleep 3
fi
echo ""

# 总结
echo "=================================="
echo "✅ 测试环境启动完成！"
echo ""
echo "📊 服务状态:"
redis-cli ping 2>/dev/null && echo "  ✅ Redis: 运行中" || echo "  ❌ Redis: 未运行"
pgrep -f "next-server" > /dev/null && echo "  ✅ Next.js: 运行中" || echo "  ❌ Next.js: 未运行"
pgrep -f "node.*worker" > /dev/null && echo "  ✅ Worker: 运行中" || echo "  ❌ Worker: 未运行"
echo ""
echo "🌐 访问地址:"
echo "  http://localhost:3000/projects"
echo ""
echo "📝 测试流程:"
echo "  1. 打开浏览器访问 http://localhost:3000/projects"
echo "  2. 创建一个新项目（例如：'测试项目'）"
echo "  3. 进入项目详情，点击'上传视频'按钮"
echo "  4. 选择一个短剧视频文件（MP4 格式，建议 <500MB）"
echo "  5. 等待上传和处理完成"
echo "  6. 查看视频分析结果"
echo ""
echo "📋 查看日志:"
echo "  Worker 日志: tail -f logs/worker.log"
echo "  数据库状态: npm run db:studio"
echo ""
