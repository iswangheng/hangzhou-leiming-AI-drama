#!/bin/bash
# 查看测试进度

echo "========================================="
echo "📊 测试进度报告"
echo "========================================="
echo ""

# 查看日志文件最后的内容
echo "📝 最近进展:"
echo "-----------------------------------------"
tail -50 test_final.log | grep -E "(项目:|第.*集:|总体|准确率)" | tail -20

echo ""
echo "========================================="
echo "📊 完成情况:"
echo "========================================="

# 统计已完成的集数
completed=$(grep -c "第.*集:" test_final.log 2>/dev/null || echo "0")
total=80

echo "已完成: $completed / $total 集"
echo "进度: $(echo "scale=1; $completed * 100 / $total" | bc)%"
echo ""

# 查看是否有错误
errors=$(grep -c "❌" test_final.log 2>/dev/null || echo "0")
echo "错误数: $errors"

# 查看测试是否还在运行
if pgrep -f "final_test.py" > /dev/null; then
    echo "状态: 🔄 运行中"
else
    echo "状态: ✅ 已完成"
fi

echo ""
echo "========================================="
echo "📋 结果文件:"
echo "========================================="
ls -lh test/comprehensive_test/*.json 2>/dev/null | tail -5

echo ""
echo "提示: 使用 'tail -f test_final.log' 实时查看日志"
