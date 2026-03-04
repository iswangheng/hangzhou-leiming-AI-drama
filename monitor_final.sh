#!/bin/bash
echo "=== 📊 全部项目最终进度 ==="
while true; do
    sleep 30
    clear
    
    echo "🎬 正在渲染:"
    echo "[1/4] 多子多福:"
    if [ -f render_duoziduofu_v2.log ]; then
        tail -n 3 render_duoziduofu_v2.log | grep -E "✅ 渲染完成|进度:" | tail -1
    fi
    echo "[2/4] 欺我年迈:"
    if [ -f render_qiwo_nianmai_v2.log ]; then
        tail -n 3 render_qiwo_nianmai_v2.log | grep -E "✅ 渲染完成|进度:" | tail -1
    fi
    
    echo ""
    echo "🧠 正在分析:"
    echo "[3/4] 老公首富:"
    if [ -f analyze_laogong_chongfu_v2.log ]; then
        tail -n 5 analyze_laogong_chongfu_v2.log | grep -E "第.*集:|剪辑组合:" | tail -1
    fi
    echo "[4/4] 飒爽女友:"
    if [ -f analyze_sashuang_nvyou_v2.log ]; then
        tail -n 5 analyze_sashuang_nvyou_v2.log | grep -E "第.*集:|剪辑组合:" | tail -1
    fi
    
    echo ""
    date "+%H:%M:%S"
    
    # 检查是否全部完成
    if grep -q "✅ 渲染完成" render_duoziduofu_v2.log 2>/dev/null && \
       grep -q "✅ 渲染完成" render_qiwo_nianmai_v2.log 2>/dev/null && \
       grep -q "剪辑组合: [0-9]" analyze_laogong_chongfu_v2.log 2>/dev/null && \
       grep -q "剪辑组合: [0-9]" analyze_sashuang_nvyou_v2.log 2>/dev/null; then
        echo ""
        echo "🎉 全部完成！生成最终报告..."
        break
    fi
done
