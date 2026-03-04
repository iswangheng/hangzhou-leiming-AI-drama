#!/bin/bash
echo "=== 等待所有渲染完成 ==="
while true; do
    sleep 30
    clear
    
    echo "=== 📊 全部项目渲染进度 ==="
    echo ""
    
    # 检查每个项目的渲染进度
    count=0
    for project in "多子多福，开局就送绝美老婆" "欺我年迈抢祖宅，和贫道仙法说吧" "老公成为首富那天我重生了" "飒爽女友不好惹"; do
        project_num=$((count + 1))
        echo "[$project_num/4] $(basename $project | cut -c1-10):"
        
        # 检查渲染是否完成
        if grep -q "✅ 渲染完成" render_*_$project_num.log 2>/dev/null; then
            video_count=$(ls "clips/$project"/*.mp4 2>/dev/null | wc -l | tr -d ' ')
            echo "  ✅ 已完成 ($video_count 个视频)"
        else
            # 显示当前渲染进度
            latest=$(grep "进度:" render_*_$project_num.log 2>/dev/null | tail -1)
            if [ -n "$latest" ]; then
                echo "  $latest"
            else
                echo "  初始化中..."
            fi
        fi
        
        echo ""
        count=$((count + 1))
    done
    
    date "+%H:%M:%S"
    echo ""
    
    # 检查是否全部完成
    all_done=true
    for i in 1 2 3 4; do
        if ! grep -q "✅ 渲染完成" render_*_v2.log 2>/dev/null; then
            all_done=false
            break
        fi
    done
    
    if [ "$all_done" = true ]; then
        echo ""
        echo "🎉 全部完成！生成最终报告..."
        break
    fi
done
