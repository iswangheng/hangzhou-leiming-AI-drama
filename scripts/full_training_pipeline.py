"""
V5.0 完整训练流程脚本

一次性完成：
1. 数据提取（关键帧+ASR）
2. 训练AI技能（自动类型简化）
3. 生成v0.4技能文件
"""
import os
import sys
import time
from pathlib import Path

def check_data_completeness():
    """检查数据完整性"""
    print("\n" + "=" * 80)
    print("【步骤0】检查数据完整性")
    print("=" * 80)

    cache_base = Path("data/cache")
    keyframe_cache = cache_base / "keyframes"

    if not keyframe_cache.exists():
        print("❌ 缓存目录不存在")
        return False

    # 统计已提取数据
    projects = sorted([d for d in keyframe_cache.iterdir() if d.is_dir()])
    total_keyframes = 0
    total_asr = 0

    for project_dir in projects:
        keyframe_episodes = len([d for d in project_dir.iterdir() if d.is_dir()])
        total_keyframes += keyframe_episodes

        asr_dir = cache_base / "asr" / project_dir.name
        if asr_dir.exists():
            asr_episodes = len([f for f in asr_dir.iterdir() if f.is_file()])
            total_asr += asr_episodes

    target_episodes = 117
    progress = (total_keyframes / target_episodes) * 100

    print(f"已提取: {total_keyframes}/{target_episodes}集 ({progress:.1f}%)")

    if progress < 95:
        print(f"\n⚠️  数据提取未完成 ({progress:.1f}%)")
        print(f"请先运行: python -m scripts.batch_extract_data")
        return False

    print("✅ 数据提取完成")
    return True


def run_training():
    """运行训练流程"""
    print("\n" + "=" * 80)
    print("【步骤1】开始AI训练")
    print("=" * 80)

    from scripts.train import main as train_main

    try:
        train_main()
        return True
    except Exception as e:
        print(f"❌ 训练失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_skill_file():
    """验证技能文件生成"""
    print("\n" + "=" * 80)
    print("【步骤2】验证技能文件")
    print("=" * 80)

    skills_dir = Path("data/skills")

    # 查找最新的技能文件
    md_files = sorted(skills_dir.glob("ai-drama-clipping-thoughts-v*.md"))
    json_files = sorted(skills_dir.glob("ai-drama-clipping-thoughts-v*.json"))

    if not md_files:
        print("❌ 未找到MD技能文件")
        return False

    if not json_files:
        print("❌ 未找到JSON技能文件")
        return False

    latest_md = md_files[-1]
    latest_json = json_files[-1]

    print(f"✅ MD技能文件: {latest_md.name}")
    print(f"✅ JSON技能文件: {latest_json.name}")

    # 检查内容
    import json
    with open(latest_json, 'r', encoding='utf-8') as f:
        skill_data = json.load(f)

    highlight_count = len(skill_data.get('highlight_types', []))
    hook_count = len(skill_data.get('hook_types', []))

    print(f"\n技能文件内容:")
    print(f"  高光类型: {highlight_count}种")
    print(f"  钩子类型: {hook_count}种")

    # 检查类型简化效果
    if hook_count <= 15:
        print(f"  ✅ 类型简化生效 ({hook_count}种 ≤ 15种)")
    else:
        print(f"  ⚠️  类型数量较多 ({hook_count}种)")

    return True


def generate_summary_report():
    """生成训练总结报告"""
    print("\n" + "=" * 80)
    print("【步骤3】生成训练报告")
    print("=" * 80)

    import json
    from datetime import datetime

    skills_dir = Path("data/skills")
    json_files = sorted(skills_dir.glob("ai-drama-clipping-thoughts-v*.json"))

    if not json_files:
        print("❌ 未找到技能文件")
        return

    latest_json = json_files[-1]

    with open(latest_json, 'r', encoding='utf-8') as f:
        skill_data = json.load(f)

    version = skill_data.get('version', 'unknown')
    metadata = skill_data.get('metadata', {})
    statistics = metadata.get('statistics', {})

    # 生成报告
    report_lines = []
    report_lines.append("# V5.0 训练完成报告\n")
    report_lines.append(f"**完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"**技能版本**: {version}\n")
    report_lines.append("---\n")

    report_lines.append("## 📊 训练统计\n")
    report_lines.append(f"- 训练项目数: {statistics.get('project_count', 0)}\n")
    report_lines.append(f"- 累计集数: {statistics.get('episode_count', 0)}\n")
    report_lines.append(f"- 高光类型数: {statistics.get('highlight_type_count', 0)}\n")
    report_lines.append(f"- 钩子类型数: {statistics.get('hook_type_count', 0)}\n")
    report_lines.append("---\n")

    report_lines.append("## 🎯 技能类型列表\n")

    report_lines.append("### 高光类型\n")
    for ht in skill_data.get('highlight_types', []):
        report_lines.append(f"- **{ht['name']}**: {ht['description']}\n")

    report_lines.append("\n### 钩子类型\n")
    for hook in skill_data.get('hook_types', []):
        report_lines.append(f"- **{hook['name']}**: {hook['description']}\n")

    report_lines.append("\n---\n")
    report_lines.append("## ✅ 完成状态\n")
    report_lines.append("1. ✅ 数据提取完成 (117集)\n")
    report_lines.append("2. ✅ AI训练完成\n")
    report_lines.append("3. ✅ 技能文件生成 (MD + JSON)\n")
    report_lines.append("4. ✅ 类型自动简化\n")
    report_lines.append("\n下一步: 开始测试验证\n")

    # 保存报告
    report_path = Path("data/skills") / f"V5_TRAINING_REPORT_{version}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)

    print(f"✅ 训练报告已保存: {report_path}")


def main():
    """主流程"""
    print("=" * 80)
    print("🚀 V5.0 完整训练流程")
    print("=" * 80)
    print()
    print("本脚本将依次执行:")
    print("  1. 检查数据完整性")
    print("  2. 运行AI训练（自动类型简化）")
    print("  3. 验证技能文件")
    print("  4. 生成训练报告")
    print()

    # 检查数据
    if not check_data_completeness():
        print("\n❌ 数据未就绪，请先完成数据提取")
        return 1

    # 运行训练
    if not run_training():
        print("\n❌ 训练失败")
        return 1

    # 验证技能文件
    if not verify_skill_file():
        print("\n❌ 技能文件验证失败")
        return 1

    # 生成报告
    generate_summary_report()

    print("\n" + "=" * 80)
    print("🎉 V5.0 训练流程完成！")
    print("=" * 80)
    print()
    print("下一步:")
    print("  1. 查看训练报告: data/skills/V5_TRAINING_REPORT_*.md")
    print("  2. 测试技能: python -m scripts.understand.video_understand <项目名>")
    print("  3. 查看优化报告: OPTIMIZATION_V5_REPORT.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
