#!/bin/bash

# 杭州雷鸣页面导航栏更新脚本

# 需要更新的页面列表
pages=(
  "app/hangzhou-leiming/page.tsx"
  "app/hangzhou-leiming/training-center/training/page.tsx"
  "app/hangzhou-leiming/training-center/skills/page.tsx"
  "app/hangzhou-leiming/training-center/history/page.tsx"
  "app/hangzhou-leiming/[id]/page.tsx"
  "app/hangzhou-leiming/[id]/videos/page.tsx"
  "app/hangzhou-leiming/[id]/markings/page.tsx"
  "app/hangzhou-leiming/[id]/smart-editor/page.tsx"
  "app/hangzhou-leiming/[id]/export/page.tsx"
)

echo "开始更新杭州雷鸣页面..."

for page in "${pages[@]}"; do
  if [ -f "$page" ]; then
    echo "处理: $page"
    # 这里可以添加自动化的编辑命令
  else
    echo "文件不存在: $page"
  fi
done

echo "更新完成！"
