#!/bin/bash
while true; do
    sleep 20
    clear
    echo "=== 📊 全部项目实时进度 ==="
    echo "================================"
    
    # 渲染进度
    echo ""
    echo "🎬 正在渲染（第一批）:"
    echo "[1/4] 多子多福:"
    if [ -f render_duoziduofu.log ]; then
        tail -n 3 render_duoziduofu.log | grep -E "渲染剪辑:|✅ 渲染完成" | tail -1
    fi
    echo "[2/4] 欺我年迈:"
    if [ -f render_qiwo_nianmai.log ]; then
        tail -n 3 render_qiwo_nianmai.log | grep -E "渲染剪辑:|✅ 渲染完成" | tail -1
    fi
    
    # 分析进度
    echo ""
    echo "🧠 正在分析（第二批）:"
    echo "[3/4] 老公首富:"
    if [ -f analyze_laogong_chongfu.log ]; then
        tail -n 5 analyze_laogong_chongfu.log | grep -E "第.*集:|ASR转录完成|剪辑组合:" | tail -1
    fi
    echo "[4/4] 飒爽女友:"
    if [ -f analyze_sashuang_nvyou.log ]; then
        tail -n 5 analyze_sashuang_nvyou.log | grep -E "第.*集:|ASR转录完成|剪辑组合:" | tail -1
    fi
    
    echo ""
    echo "================================"
    date "+%H:%M:%S - 持续监控中..."
done
