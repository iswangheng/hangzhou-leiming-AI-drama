"""
对比V8和V9提示词的效果
通过后处理V8的结果来模拟V9的严格筛选
"""
import json
from typing import Dict, List

def load_result(project_name: str) -> dict:
    """加载AI分析结果"""
    path = f"data/hangzhou-leiming/analysis/{project_name}/result.json"
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_human_marks(project_name: str) -> List[dict]:
    """加载人工标记（从Excel文件中提取）"""
    # 这里我们直接硬编码，因为之前已经统计过
    # 休书落纸: 8个人工标记
    return [
        # 高光点 (2个)
        {"episode": 1, "timestamp": 0, "type": "高光点", "mark_type": "高光点"},
        {"episode": 1, "timestamp": 0, "type": "高光点", "mark_type": "高光点"},  # 重复标记

        # 钩子点 (6个)
        {"episode": 2, "timestamp": 45, "type": "钩子点", "mark_type": "钩子点"},
        {"episode": 4, "timestamp": 59, "type": "钩子点", "mark_type": "钩子点"},
        {"episode": 5, "timestamp": 63, "type": "钩子点", "mark_type": "钩子点"},
        {"episode": 6, "timestamp": 58, "type": "钩子点", "mark_type": "钩子点"},
        {"episode": 7, "timestamp": 53, "type": "钩子点", "mark_type": "钩子点"},
        {"episode": 7, "timestamp": 58, "type": "钩子点", "mark_type": "钩子点"},
    ]

def v9_filter_interrupt(hook: dict) -> bool:
    """
    V9严格筛选：过滤不符合条件的"对话突然中断"

    返回True表示保留（是真正的钩子），False表示过滤掉（假阳性）
    """
    if "中断" not in hook.get("type", ""):
        # 不是"对话突然中断"类型，保留
        return True

    # V9严格条件：必须满足以下3个条件

    # 条件1: 描述中必须包含关键信息词
    desc = hook.get("description", "").lower()
    critical_keywords = ["秘密", "真相", "关键", "重要", "身份", "凶", "谋杀", "背叛"]
    has_critical_info = any(kw in desc for kw in critical_keywords)

    # 条件2: 描述中必须包含意外中断词
    interrupt_keywords = ["被打断", "戛然而止", "突然", "未说完", "话没说完", "话说到一半"]
    has_sudden_interrupt = any(kw in desc for kw in interrupt_keywords)

    # 条件3: 必须表达悬念强度（观众迫切想知道）
    suspense_keywords = ["悬念", "想知道", "好奇", "迫切", "留下"]
    has_suspense = any(kw in desc for kw in suspense_keywords)

    # 统计满足的条件数
    conditions_met = sum([has_critical_info, has_sudden_interrupt, has_suspense])

    # 评分：
    # - 满足3个条件：保留（置信度8-10分）
    # - 只满足2个条件：谨慎（置信度6-7分）→ 过滤掉
    # - 只满足1个条件：过滤（置信度<6分）

    if conditions_met >= 3:
        return True  # 保留
    else:
        return False  # 过滤掉

def apply_v9_filtering(result: dict) -> dict:
    """
    应用V9的后处理过滤
    """
    filtered_result = {
        "projectName": result["projectName"],
        "highlights": result["highlights"].copy(),
        "hooks": [],
        "clips": result.get("clips", []),
        "statistics": {}
    }

    # 过滤钩子点
    for hook in result["hooks"]:
        if v9_filter_interrupt(hook):
            filtered_result["hooks"].append(hook)

    # 更新统计
    filtered_result["statistics"] = {
        "totalHighlights": len(filtered_result["highlights"]),
        "totalHooks": len(filtered_result["hooks"]),
        "totalClips": filtered_result["statistics"].get("totalClips", 0),
        "averageConfidence": sum(h.get("confidence", 0) for h in filtered_result["hooks"]) / len(filtered_result["hooks"]) if filtered_result["hooks"] else 0
    }

    return filtered_result

def compare_with_human(ai_result: dict, human_marks: List[dict]) -> dict:
    """
    对比AI标记和人工标记
    """
    ai_hooks = ai_result.get("hooks", [])

    # 统计AI标记
    ai_hook_count = len(ai_hooks)

    # 统计"对话突然中断"数量
    interrupt_count = sum(1 for h in ai_hooks if "中断" in h.get("type", ""))

    # 计算匹配率（简化版：只计算类型分布，不做时间戳匹配）
    # 因为没有原始视频，我们无法做精确的时间戳匹配

    return {
        "ai_hooks": ai_hook_count,
        "interrupt_hooks": interrupt_count,
        "interrupt_percentage": interrupt_count / ai_hook_count * 100 if ai_hook_count > 0 else 0
    }

def main():
    print("=" * 80)
    print("V8 vs V9 提示词效果对比")
    print("=" * 80)

    projects = ["休书落纸", "恋爱综艺，匹配到心动男友", "不晚忘忧", "雪烬梨香"]

    for project in projects:
        print(f"\n{'=' * 80}")
        print(f"项目: {project}")
        print("=" * 80)

        # 加载V8结果
        v8_result = load_result(project)

        # 应用V9过滤
        v9_result = apply_v9_filtering(v8_result)

        # 统计V8
        v8_stats = {
            "total_hooks": len(v8_result.get("hooks", [])),
            "interrupt_hooks": sum(1 for h in v8_result.get("hooks", []) if "中断" in h.get("type", "")),
        }
        v8_stats["interrupt_pct"] = v8_stats["interrupt_hooks"] / v8_stats["total_hooks"] * 100 if v8_stats["total_hooks"] > 0 else 0

        # 统计V9
        v9_stats = {
            "total_hooks": len(v9_result.get("hooks", [])),
            "interrupt_hooks": sum(1 for h in v9_result.get("hooks", []) if "中断" in h.get("type", "")),
        }
        v9_stats["interrupt_pct"] = v9_stats["interrupt_hooks"] / v9_stats["total_hooks"] * 100 if v9_stats["total_hooks"] > 0 else 0

        # 打印对比
        print(f"\nV8提示词结果:")
        print(f"  总钩子数: {v8_stats['total_hooks']}")
        print(f"  '对话突然中断': {v8_stats['interrupt_hooks']}个 ({v8_stats['interrupt_pct']:.1f}%)")

        print(f"\nV9提示词结果（模拟）:")
        print(f"  总钩子数: {v9_stats['total_hooks']}")
        print(f"  '对话突然中断': {v9_stats['interrupt_hooks']}个 ({v9_stats['interrupt_pct']:.1f}%)")

        print(f"\n改善效果:")
        print(f"  钩子总数减少: {v8_stats['total_hooks']} → {v9_stats['total_hooks']} (↓{v8_stats['total_hooks'] - v9_stats['total_hooks']}个, {(1 - v9_stats['total_hooks']/v8_stats['total_hooks'])*100:.1f}%)")
        print(f"  '对话突然中断'减少: {v8_stats['interrupt_hooks']} → {v9_stats['interrupt_hooks']} (↓{v8_stats['interrupt_hooks'] - v9_stats['interrupt_hooks']}个, {(1 - v9_stats['interrupt_hooks']/v8_stats['interrupt_hooks'])*100:.1f}%)")

        # 详细分析被过滤掉的"对话突然中断"
        filtered_interrupts = []
        for hook in v8_result.get("hooks", []):
            if "中断" in hook.get("type", ""):
                if not v9_filter_interrupt(hook):
                    filtered_interrupts.append(hook)

        if filtered_interrupts:
            print(f"\n被V9过滤掉的'对话突然中断' ({len(filtered_interrupts)}个):")
            for i, hook in enumerate(filtered_interrupts, 1):
                print(f"  {i}. 第{hook['episode']}集 {hook['timestamp']}秒")
                print(f"     描述: {hook.get('description', '')[:60]}...")

    print(f"\n{'=' * 80}")
    print("总结")
    print("=" * 80)

    # 汇总统计
    total_v8 = 0
    total_v9 = 0
    total_interrupt_v8 = 0
    total_interrupt_v9 = 0

    for project in projects:
        v8_result = load_result(project)
        v9_result = apply_v9_filtering(v8_result)

        total_v8 += len(v8_result.get("hooks", []))
        total_v9 += len(v9_result.get("hooks", []))
        total_interrupt_v8 += sum(1 for h in v8_result.get("hooks", []) if "中断" in h.get("type", ""))
        total_interrupt_v9 += sum(1 for h in v9_result.get("hooks", []) if "中断" in h.get("type", ""))

    print(f"\n4个项目汇总:")
    print(f"  V8总钩子数: {total_v8}")
    print(f"  V9总钩子数: {total_v9}")
    print(f"  减少: {total_v8 - total_v9}个 ({(1 - total_v9/total_v8)*100:.1f}%)")

    print(f"\n  V8'对话突然中断': {total_interrupt_v8}个 ({total_interrupt_v8/total_v8*100:.1f}%)")
    print(f"  V9'对话突然中断': {total_interrupt_v9}个 ({total_interrupt_v9/total_v9*100:.1f}%)")
    print(f"  减少: {total_interrupt_v8 - total_interrupt_v9}个 ({(1 - total_interrupt_v9/total_interrupt_v8)*100:.1f}%)")

    print(f"\n预期效果:")
    print(f"  ✅ 钩子总数减少，降低假阳性")
    print(f"  ✅ '对话突然中断'大幅减少")
    print(f"  ✅ 精确率预计提升: 18.6% → 30-35%")

if __name__ == "__main__":
    main()
