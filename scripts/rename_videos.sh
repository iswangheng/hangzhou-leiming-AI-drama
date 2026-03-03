#!/bin/bash
# 视频文件重命名脚本
# 会自动备份，然后重命名文件为纯数字格式

set -e  # 遇到错误立即退出

# 基础路径
BASE_DIR="/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/漫剧参考"

# 时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "========================================"
echo "视频文件重命名工具"
echo "========================================"
echo ""
echo "模式: 正式执行"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "========================================"
echo ""

# 项目列表
PROJECTS=("精准" "机长姐姐" "假面丈夫" "紫雪" "学乖的代价")

total_renamed=0
total_backups=0

for project in "${PROJECTS[@]}"; do
    PROJECT_DIR="$BASE_DIR/$project"

    if [ ! -d "$PROJECT_DIR" ]; then
        echo "⚠️  跳过（目录不存在）: $project"
        continue
    fi

    echo "📁 $project/"
    echo "-" "--" "--" "--" "--" "--" "--" "--" "--" "--" "-"

    # 备份
    BACKUP_DIR="${PROJECT_DIR}_backup_${TIMESTAMP}"
    echo "💾 备份到: $(basename "$BACKUP_DIR")"
    cp -R "$PROJECT_DIR" "$BACKUP_DIR"
    total_backups=$((total_backups + 1))

    # 重命名文件
    count=0
    for file in "$PROJECT_DIR"/*.mp4; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")

            # 提取集数
            # 格式1: 精准-1.mp4 → 1
            # 格式2: 机长姐姐-1.mp4 → 1
            episode=$(echo "$filename" | sed -E 's/.*-([0-9]+)\.mp4/\1/')

            # 检查是否已经提取成功
            if [ "$episode" != "$filename" ]; then
                new_name="${episode}.mp4"
                new_path="$PROJECT_DIR/$new_name"

                # 检查目标文件是否已存在
                if [ -f "$new_path" ]; then
                    echo "   ⚠️  跳过（已存在）: $filename → $new_name"
                else
                    mv "$file" "$new_path"
                    echo "   ✅ $filename → $new_name"
                    count=$((count + 1))
                    total_renamed=$((total_renamed + 1))
                fi
            fi
        fi
    done

    echo "   ✅ 重命名完成: $count 个文件"
    echo ""
done

echo "========================================"
echo "执行完成"
echo "========================================"
echo ""
echo "✅ 成功: $total_renamed 个文件"
echo "💾 备份: $total_backups 个项目"
echo ""
echo "备份目录格式: 项目名_backup_${TIMESTAMP}"
echo ""
echo "如需回滚，请运行:"
echo "  rm -rf 项目名/"
echo "  mv 项目名_backup_${TIMESTAMP} 项目名"
