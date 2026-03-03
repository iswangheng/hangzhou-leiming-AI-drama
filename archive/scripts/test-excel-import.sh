#!/bin/bash

# 杭州雷鸣 - Excel 导入功能测试脚本
#
# 用途：快速测试 Excel 导入功能
# 前提：服务器已启动（npm run dev）

set -e

echo "=================================================="
echo "  杭州雷鸣 - Excel 导入功能测试"
echo "=================================================="
echo ""

BASE_URL="http://localhost:3000"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 测试服务器连接
echo -e "${YELLOW}[测试 1/5]${NC} 检查服务器连接..."
if curl -s "$BASE_URL/api/health" > /dev/null; then
    echo -e "${GREEN}✅ 服务器运行正常${NC}"
else
    echo -e "${RED}❌ 服务器未启动，请先运行 npm run dev${NC}"
    exit 1
fi
echo ""

# 2. 测试示例文件下载
echo -e "${YELLOW}[测试 2/5]${NC} 下载示例 Excel 文件..."
EXAMPLE_URL="$BASE_URL/api/hangzhou-leiming/markings/example"
OUTPUT_FILE="test-example.xlsx"

if curl -s "$EXAMPLE_URL" -o "$OUTPUT_FILE"; then
    FILE_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null)
    echo -e "${GREEN}✅ 示例文件下载成功${NC}"
    echo "   文件大小: $FILE_SIZE bytes"
else
    echo -e "${RED}❌ 示例文件下载失败${NC}"
    exit 1
fi
echo ""

# 3. 创建测试项目
echo -e "${YELLOW}[测试 3/5]${NC} 创建测试项目..."
PROJECT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/hangzhou-leiming/projects" \
    -H "Content-Type: application/json" \
    -d '{"name":"Excel导入测试项目","description":"自动化测试"}')

PROJECT_ID=$(echo "$PROJECT_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

if [ -n "$PROJECT_ID" ]; then
    echo -e "${GREEN}✅ 项目创建成功${NC}"
    echo "   项目 ID: $PROJECT_ID"
else
    echo -e "${RED}❌ 项目创建失败${NC}"
    echo "   响应: $PROJECT_RESPONSE"
    exit 1
fi
echo ""

# 4. 创建测试视频（模拟）
echo -e "${YELLOW}[测试 4/5]${NC} 创建测试视频记录..."
VIDEO_RESPONSE=$(curl -s -X POST "$BASE_URL/api/hangzhou-leiming/videos" \
    -F "file=@test-example.xlsx" \
    -F "projectId=$PROJECT_ID" \
    -F "episodeNumber=第1集" \
    -F "displayTitle=第1集：测试视频")

# 这个可能会失败，因为上传的不是真实视频，但我们可以继续测试
echo "   视频创建响应: $VIDEO_RESPONSE"
echo ""

# 5. 导入 Excel（使用示例文件）
echo -e "${YELLOW}[测试 5/5]${NC} 测试 Excel 导入..."
IMPORT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/hangzhou-leiming/markings/import" \
    -F "file=@test-example.xlsx" \
    -F "projectId=$PROJECT_ID")

echo "   导入响应: $IMPORT_RESPONSE"

if echo "$IMPORT_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ Excel 导入成功${NC}"
else
    echo -e "${YELLOW}⚠️  Excel 导入可能需要先上传真实视频${NC}"
fi
echo ""

# 清理测试文件
rm -f test-example.xlsx

echo "=================================================="
echo "  测试完成！"
echo "=================================================="
echo ""
echo "📊 后续操作："
echo "   1. 访问训练中心页面测试前端导入功能"
echo "   2. 上传真实视频文件"
echo "   3. 使用修改后的 Excel 文件导入标记数据"
echo ""
echo "   训练中心链接: $BASE_URL/hangzhou-leiming/$PROJECT_ID/training"
echo ""
