#!/bin/bash
echo "=== 🔄 监控第一批项目进度 ==="
while true; do
    sleep 30
    
    # 检查项目1是否完成
    if grep -q "剪辑组合: [1-9]" analyze_duoziduofu.log 2>/dev/null; then
        echo "✅ [1/4] 多子多福 已完成！"
        
        # 检查项目2是否完成
        if grep -q "剪辑组合: [1-9]" analyze_qiwo_nianmai.log 2>/dev/null; then
            echo "✅ [2/4] 欺我年迈抢祖宅 已完成！"
            echo ""
            echo "🎉 第一批全部完成！开始渲染和第二批..."
            break
        fi
    fi
    
    # 显示当前进度
    clear
    echo "=== 📊 第一批项目实时进度 ==="
    echo ""
    echo "[1/4] 多子多福:"
    tail -n 5 analyze_duoziduofu.log | grep -E "第.*集:|ASR转录完成" | tail -1
    echo ""
    echo "[2/4] 欺我年迈抢祖宅:"
    tail -n 5 analyze_qiwo_nianmai.log | grep -E "第.*集:|ASR转录完成" | tail -1
    echo ""
    date "+%H:%M:%S - 等待完成..."
done
