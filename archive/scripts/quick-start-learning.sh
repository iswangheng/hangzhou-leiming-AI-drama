#!/bin/bash

# ============================================
# AI 学习流程快速启动脚本
# ============================================

set -e

PROJECT_ID=${1:-1}
API_URL="http://localhost:3000"
WS_URL="ws://localhost:3001"

echo "========================================"
echo "  AI 学习流程快速启动"
echo "========================================"
echo ""
echo "项目 ID: $PROJECT_ID"
echo "API 地址: $API_URL"
echo "WebSocket 地址: $WS_URL"
echo ""

# 检查项目是否存在
echo "1. 检查项目..."
PROJECT_CHECK=$(curl -s "$API_URL/api/hangzhou-leiming/projects/$PROJECT_ID")

if echo "$PROJECT_CHECK" | grep -q "success"; then
  echo "   ✅ 项目存在"
else
  echo "   ❌ 项目不存在，请先创建项目"
  exit 1
fi

# 启动学习任务
echo ""
echo "2. 启动学习任务..."
RESPONSE=$(curl -s -X POST "$API_URL/api/hangzhou-leiming/projects/$PROJECT_ID/learn" \
  -H "Content-Type: application/json" \
  -d '{
    "framesPerMarking": 30,
    "skipExistingFrames": true,
    "skipExistingTranscript": true
  }')

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

# 提取任务 ID
JOB_ID=$(echo "$RESPONSE" | grep -o '"jobId":"[^"]*' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
  echo ""
  echo "❌ 无法获取任务 ID"
  exit 1
fi

echo ""
echo "3. 任务已启动"
echo "   任务 ID: $JOB_ID"
echo ""
echo "4. 监听进度（使用 WebSocket）"
echo ""
echo "可以使用以下 JavaScript 代码监听进度："
echo ""
cat <<'EOF'
const ws = new WebSocket('ws://localhost:3001');

ws.onopen = () => {
  console.log('已连接到 WebSocket 服务器');
  ws.send(JSON.stringify({
    type: 'progress',
    data: { jobId: 'JOB_ID' }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'progress') {
    console.log(`[${message.data.progress}%] ${message.data.message}`);
  } else if (message.type === 'complete') {
    console.log('✅ 学习完成！', message.data);
    ws.close();
  } else if (message.type === 'error') {
    console.error('❌ 学习失败：', message.data.error);
    ws.close();
  }
};

ws.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};
EOF
echo ""
echo "请将上面的脚本中的 JOB_ID 替换为: $JOB_ID"
echo ""

# 可选：使用 websocat 监听（如果安装了）
if command -v websocat &> /dev/null; then
  echo "检测到 websocat，可以使用以下命令监听进度："
  echo ""
  echo "websocat $WS_URL"
  echo ""
else
  echo "提示：安装 websocat 可以更方便地监听 WebSocket"
  echo "brew install websocat"
  echo ""
fi

echo "========================================"
echo "  完成"
echo "========================================"
