#!/bin/bash
echo "=== 等待第二批分析完成 ==="
while true; do
    sleep 20
    
    # 检查第二批是否都完成了分析（有剪辑组合）
    if grep -q "剪辑组合: [0-9]" analyze_laogong_chongfu_v2.log 2>/dev/null && \
       grep -q "剪辑组合: [0-9]" analyze_sashuang_nvyou_v2.log 2>/dev/null; then
        echo ""
        echo "🎉 第二批分析完成！启动渲染..."
        
        # 启动第二批渲染
        python -m scripts.understand.render_clips \
            "data/hangzhou-leiming/analysis/老公成为首富那天我重生了" \
            "晓红姐-3.4剧目/老公成为首富那天我重生了" \
            > render_laogong_chongfu_v2.log 2>&1 &
        echo "✅ [3/4] 老公首富 渲染已启动"
        
        python -m scripts.understand.render_clips \
            "data/hangzhou-leiming/analysis/飒爽女友不好惹" \
            "晓红姐-3.4剧目/飒爽女友不好惹" \
            > render_sashuang_nvyou_v2.log 2>&1 &
        echo "✅ [4/4] 飒爽女友 渲染已启动"
        
        break
    fi
    
    # 显示进度
    clear
    echo "=== 📊 第二批分析进度 ==="
    echo ""
    echo "[3/4] 老公首富:"
    tail -n 5 analyze_laogong_chongfu_v2.log 2>/dev/null | grep -E "第.*集:|剪辑组合:" | tail -1 || echo "  处理中..."
    echo ""
    echo "[4/4] 飒爽女友:"
    tail -n 5 analyze_sashuang_nvyou_v2.log 2>/dev/null | grep -E "第.*集:|剪辑组合:" | tail -1 || echo "  处理中..."
    echo ""
    date "+%H:%M:%S"
done
