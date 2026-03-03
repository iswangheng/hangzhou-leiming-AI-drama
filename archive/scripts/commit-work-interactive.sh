#!/bin/bash

# ============================================
# 交互式功能完成提交脚本
# ============================================
# 用途：交互式完成功能提交，自动更新文档
# 使用：npm run commit 或者 ./scripts/commit-work-interactive.sh
# ============================================

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# 当前时间
CURRENT_DATE=$(date +"%Y-%m-%d")
CURRENT_TIME=$(date +"%H:%M")

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   🎯 功能完成提交向导               ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

# ============================================
# 步骤 1: 检查 Git 状态
# ============================================
echo -e "${BOLD}${BLUE}📊 步骤 1/5: 检查代码变更${NC}"
echo "-------------------------------------------"

if [ -z "$(git status --porcelain)" ]; then
    echo -e "${RED}❌ 没有检测到任何代码变更${NC}"
    echo ""
    echo "💡 建议："
    echo "  1. 先完成代码修改"
    echo "  2. 保存所有文件"
    echo "  3. 再次运行此脚本"
    exit 1
fi

CHANGED_FILES=$(git status --porcelain | wc -l | tr -d ' ')
echo -e "${GREEN}✅ 检测到 ${CHANGED_FILES} 个文件变更${NC}"
echo ""

git status --short
echo ""

# ============================================
# 步骤 2: 选择提交类型
# ============================================
echo -e "${BOLD}${BLUE}🏷️  步骤 2/5: 选择提交类型${NC}"
echo "-------------------------------------------"
echo "请选择最符合的提交类型："
echo ""
echo "  ${BOLD}1${NC}. feat     ✨ 新功能"
echo "  ${BOLD}2${NC}. fix      🐛 修复 Bug"
echo "  ${BOLD}3${NC}. refactor ♻️  重构代码"
echo "  ${BOLD}4${NC}. docs     📝 文档更新"
echo "  ${BOLD}5${NC}. test     ✅ 测试相关"
echo "  ${BOLD}6${NC}. chore    🔧 构建/工具"
echo ""

read -p "请输入选项 [1-6]: " type_choice

case $type_choice in
    1) COMMIT_TYPE="feat" TYPE_EMOJI="✨" ;;
    2) COMMIT_TYPE="fix" TYPE_EMOJI="🐛" ;;
    3) COMMIT_TYPE="refactor" TYPE_EMOJI="♻️" ;;
    4) COMMIT_TYPE="docs" TYPE_EMOJI="📝" ;;
    5) COMMIT_TYPE="test" TYPE_EMOJI="✅" ;;
    6) COMMIT_TYPE="chore" TYPE_EMOJI="🔧" ;;
    *)
        echo -e "${RED}❌ 无效选项，默认使用 feat${NC}"
        COMMIT_TYPE="feat"
        TYPE_EMOJI="✨"
        ;;
esac

echo ""
echo -e "${GREEN}✅ 已选择: ${TYPE_EMOJI} ${COMMIT_TYPE}${NC}"
echo ""

# ============================================
# 步骤 3: 输入功能描述
# ============================================
echo -e "${BOLD}${BLUE}📝 步骤 3/5: 功能描述${NC}"
echo "-------------------------------------------"
echo "请简要描述您完成的功能（建议 10-50 字）"
echo ""

read -p "描述: " feature_desc

if [ -z "$feature_desc" ]; then
    echo -e "${RED}❌ 描述不能为空${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ 描述: ${feature_desc}${NC}"
echo ""

# ============================================
# 步骤 4: 确认提交
# ============================================
echo -e "${BOLD}${BLUE}👀 步骤 4/5: 确认提交信息${NC}"
echo "-------------------------------------------"
echo ""
echo -e "${BOLD}提交类型:${NC}   ${TYPE_EMOJI} ${COMMIT_TYPE}"
echo -e "${BOLD}功能描述:${NC}   ${feature_desc}"
echo -e "${BOLD}提交时间:${NC}   ${CURRENT_DATE} ${CURRENT_TIME}"
echo -e "${BOLD}变更文件:${NC}   ${CHANGED_FILES} 个"
echo ""
echo -e "${YELLOW}即将执行的操作：${NC}"
echo "  1. ✏️  更新 docs/PROGRESS.md"
echo "  2. 📦 git add 所有变更"
echo "  3. 🎯 git commit"
echo ""

read -p "确认提交？[y/N]: " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ 已取消提交${NC}"
    exit 0
fi

echo ""

# ============================================
# 步骤 5: 执行提交
# ============================================
echo -e "${BOLD}${BLUE}🚀 步骤 5/5: 执行提交${NC}"
echo "-------------------------------------------"

# 5.1 更新 PROGRESS.md
echo -ne "${YELLOW}✏️  更新进度文档...${NC}"

PROGRESS_FILE="docs/PROGRESS.md"

if [ ! -f "$PROGRESS_FILE" ]; then
    echo -e " ${RED}失败（文件不存在）${NC}"
    exit 1
fi

# 使用临时文件来避免 awk 的输出问题
TMP_FILE=$(mktemp)

awk -v date="$CURRENT_DATE" -v time="$CURRENT_TIME" -v desc="$feature_desc" -v type="${COMMIT_TYPE}" '
    /^## 📅 更新日志/ {
        print
        print ""
        print "### " date " - " desc
        print ""
        print "#### ✅ 完成事项"
        print "- ✅ " desc " (" type ")"
        print ""
        next
    }
    { print }
' "$PROGRESS_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$PROGRESS_FILE"

echo -e " ${GREEN}✅${NC}"

# 5.2 添加所有变更
echo -ne "${YELLOW}📦 添加文件到暂存区...${NC}"
git add -A > /dev/null 2>&1
echo -e " ${GREEN}✅${NC}"

# 5.3 提交
echo -ne "${YELLOW}🎯 创建提交...${NC}"

COMMIT_MESSAGE="${type} ${feature_desc}

📅 时间: ${CURRENT_DATE} ${CURRENT_TIME}
📄 文档: 已更新 docs/PROGRESS.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

echo "$COMMIT_MESSAGE" | git commit -F - > /dev/null 2>&1

echo -e " ${GREEN}✅${NC}"
echo ""

# ============================================
# 完成
# ============================================
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         ✅ 提交成功！                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BOLD}${BLUE}📊 提交详情：${NC}"
echo "-------------------------------------------"
git log -1 --oneline
echo ""

echo -e "${BOLD}${BLUE}📁 变更统计：${NC}"
echo "-------------------------------------------"
git log -1 --stat | tail -n $(($(git log -1 --stat | wc -l) - 2))
echo ""

echo -e "${YELLOW}💡 下一步操作：${NC}"
echo "  推送到远程仓库:  ${CYAN}git push${NC}"
echo "  查看提交历史:    ${CYAN}git log --oneline -5${NC}"
echo "  查看状态:        ${CYAN}git status${NC}"
echo ""
