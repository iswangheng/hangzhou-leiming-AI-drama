#!/bin/bash
while true; do
    sleep 30
    
    # 检查第二批是否都完成
    if grep -q "剪辑组合: [0-9]" analyze_laogong_chongfu.log 2>/dev/null && \
       grep -q "剪辑组合: [0-9]" analyze_sashuang_nvyou.log 2>/dev/null; then
        echo ""
        echo "🎉 第二批分析全部完成！"
        break
    fi
    
    # 显示进度
    clear
    echo "=== 📊 第二批分析进度 ==="
    echo ""
    echo "[3/4] 老公首富:"
    tail -n 5 analyze_laogong_chongfu.log 2>/dev/null | grep -E "第.*集:|ASR转录完成" | tail -1 || echo "  处理中..."
    echo ""
    echo "[4/4] 飒爽女友:"
    tail -n 5 analyze_sashuang_nvyou.log 2>/dev/null | grep -E "第.*集:|ASR转录完成" | tail -1 || echo "  处理中..."
    echo ""
    date "+%H:%M:%S - 等待第二批完成..."
done
