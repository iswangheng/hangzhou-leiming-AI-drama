#!/bin/bash
echo "=== 🔄 监控重新处理进度 ==="
while true; do
    sleep 30
    clear
    echo "=== 📊 第一批项目（重新处理）==="
    echo ""
    echo "[1/4] 多子多福:"
    tail -n 5 analyze_duoziduofu_v2.log 2>/dev/null | grep -E "第.*集:|ASR转录完成|剪辑组合:" | tail -1 || echo "  初始化中..."
    echo ""
    echo "[2/4] 欺我年迈:"
    tail -n 5 analyze_qiwo_nianmai_v2.log 2>/dev/null | grep -E "第.*集:|ASR转录完成|剪辑组合:" | tail -1 || echo "  初始化中..."
    echo ""
    date "+%H:%M:%S - 处理中..."
    
    # 检查是否完成
    if grep -q "剪辑组合: [0-9]" analyze_duoziduofu_v2.log 2>/dev/null && \
       grep -q "剪辑组合: [0-9]" analyze_qiwo_nianmai_v2.log 2>/dev/null; then
        echo ""
        echo "🎉 第一批完成！启动渲染和第二批..."
        break
    fi
done
