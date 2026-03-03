#!/bin/bash

# ============================================
# 自动化功能完成提交脚本
# ============================================
# 用途：完成功能后自动更新文档并提交代码
# 使用：./scripts/commit-work.sh "功能描述" "类型"
#
# 类型选项：
#   - feat: 新功能
#   - fix: 修复bug
#   - refactor: 重构
#   - docs: 文档更新
#   - test: 测试
#   - chore: 构建/工具
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 获取参数
FEATURE_DESC="$1"
COMMIT_TYPE="${2:-feat}"

# 验证参数
if [ -z "$FEATURE_DESC" ]; then
    echo -e "${RED}❌ 错误：请提供功能描述${NC}"
    echo ""
    echo "用法: ./scripts/commit-work.sh \"功能描述\" \"类型\""
    echo ""
    echo "示例:"
    echo "  ./scripts/commit-work.sh \"完成高光切片前端集成\" \"feat\""
    echo "  ./scripts/commit-work.sh \"修复视频裁剪精度问题\" \"fix\""
    echo "  ./scripts/commit-work.sh \"更新文档结构\" \"docs\""
    exit 1
fi

# 当前时间
CURRENT_DATE=$(date +"%Y-%m-%d")
CURRENT_TIME=$(date +"%H:%M")

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}📝 自动化功能完成提交流程${NC}"
echo -e "${BLUE}====================================${NC}"
echo ""

# ============================================
# 步骤 1: 检查是否有变更
# ============================================
echo -e "${YELLOW}📊 步骤 1/6: 检查代码变更...${NC}"

if [ -z "$(git status --porcelain)" ]; then
    echo -e "${RED}❌ 没有检测到任何代码变更${NC}"
    echo "提示：请先完成代码修改后再运行此脚本"
    exit 1
fi

CHANGED_FILES=$(git status --porcelain | wc -l | tr -d ' ')
echo -e "${GREEN}✅ 检测到 ${CHANGED_FILES} 个文件变更${NC}"
echo ""

# ============================================
# 步骤 2: 显示变更的文件
# ============================================
echo -e "${YELLOW}📁 步骤 2/6: 变更文件列表：${NC}"
git status --short
echo ""

# ============================================
# 步骤 3: 更新 PROGRESS.md
# ============================================
echo -e "${YELLOW}✏️  步骤 3/6: 更新项目进度文档...${NC}"

PROGRESS_FILE="docs/PROGRESS.md"

# 检查 PROGRESS.md 是否存在
if [ ! -f "$PROGRESS_FILE" ]; then
    echo -e "${RED}❌ 错误：$PROGRESS_FILE 不存在${NC}"
    exit 1
fi

# 在更新日志部分添加新的进度记录
# 使用 awk 在"## 📅 更新日志"后添加新内容
awk -v date="$CURRENT_DATE" -v time="$CURRENT_TIME" -v desc="$FEATURE_DESC" '
    /^## 📅 更新日志/ {
        print
        print ""
        print "### " date " - " desc
        print ""
        print "#### ✅ 完成事项"
        print "- ✅ " desc
        print ""
        print "#### 📦 变更文件"
        print "<!-- 请手动添加重要文件的变更说明 -->"
        print ""
        next
    }
    { print }
' "$PROGRESS_FILE" > "${PROGRESS_FILE}.tmp" && mv "${PROGRESS_FILE}.tmp" "$PROGRESS_FILE"

echo -e "${GREEN}✅ 已更新 $PROGRESS_FILE${NC}"
echo ""

# ============================================
# 步骤 4: Git add 所有变更
# ============================================
echo -e "${YELLOW}📦 步骤 4/6: 添加文件到暂存区...${NC}"

# 添加所有变更
git add .

echo -e "${GREEN}✅ 所有文件已添加到暂存区${NC}"
echo ""

# ============================================
# 步骤 5: 生成 Commit Message
# ============================================
echo -e "${YELLOW}💬 步骤 5/6: 生成 Commit Message...${NC}"

# 生成符合规范的 commit message
COMMIT_BODY="${COMMIT_TYPE}: ${FEATURE_DESC}

📅 时间: ${CURRENT_DATE} ${CURRENT_TIME}
📄 文档: 已更新 docs/PROGRESS.md

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

echo -e "${BLUE}Commit Message:${NC}"
echo "$COMMIT_BODY"
echo ""

# ============================================
# 步骤 6: Git Commit
# ============================================
echo -e "${YELLOW}🎯 步骤 6/6: 提交代码...${NC}"

# 执行 commit
echo "$COMMIT_BODY" | git commit -F -

echo ""
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}✅ 功能完成并提交成功！${NC}"
echo -e "${GREEN}====================================${NC}"
echo ""
echo -e "${BLUE}📊 提交信息：${NC}"
git log -1 --stat
echo ""
echo -e "${YELLOW}💡 提示：${NC}"
echo "  - 如需推送到远程仓库，请运行: git push"
echo "  - 查看提交历史: git log --oneline -5"
echo ""
