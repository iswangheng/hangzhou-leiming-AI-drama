#!/bin/bash

# DramaGen AI - 自动同步守护进程
#
# 用途: 后台定期运行 git pull，保持代码同步
# 使用: nohup ./scripts/auto-sync.sh > /tmp/dramagen-sync.log 2>&1 &

# 配置
SYNC_INTERVAL=300  # 同步间隔（秒），默认 5 分钟
PROJECT_DIR="/Users/wangheng/Documents/indie-hacker/001-AI-DramaCut"
LOG_FILE="/tmp/dramagen-sync.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

# 切换到项目目录
cd "$PROJECT_DIR" || exit 1

log "INFO" "🔄 DramaGen AI 自动同步守护进程启动"
log "INFO" "项目目录: $PROJECT_DIR"
log "INFO" "同步间隔: ${SYNC_INTERVAL}秒"

# 主循环
while true; do
    log "INFO" "开始同步..."

    # 拉取最新代码
    if git pull origin main >> "$LOG_FILE" 2>&1; then
        log "SUCCESS" "✅ 同步成功"

        # 检查是否有新的依赖
        if [ -f "package.json" ]; then
            log "INFO" "检查依赖更新..."
            # 这里可以添加 npm install 的逻辑
        fi
    else
        log "ERROR" "❌ 同步失败，可能存在冲突"
    fi

    log "INFO" "下次同步: $(date -d "+${SYNC_INTERVAL} seconds" '+%H:%M:%S' 2>/dev/null || date -v+${SYNC_INTERVAL}S '+%H:%M:%S')"
    log "INFO" "等待 ${SYNC_INTERVAL} 秒..."

    # 等待下一次同步
    sleep "$SYNC_INTERVAL"
done
