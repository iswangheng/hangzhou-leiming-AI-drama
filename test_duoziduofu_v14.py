#!/usr/bin/env python3
"""
测试多子多福项目 - V14智能过滤版本
"""
import sys
import os
sys.path.append('/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama')

from scripts.understand.video_understand import video_understand

def main():
    print("=" * 70)
    print("🧪 测试多子多福项目 - V14智能关键帧过滤")
    print("=" * 70)

    project_path = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/晓红姐-3.4剧目/多子多福，开局就送绝美老婆"

    print(f"\n📁 项目路径：{project_path}")

    # 检查视频文件
    import os
    video_files = sorted([f for f in os.listdir(project_path) if f.endswith('.mp4')])

    print(f"\n🎬 视频文件：{len(video_files)} 个")
    for i, video_file in enumerate(video_files[:5], 1):
        print(f"   {i}. {video_file}")
    if len(video_files) > 5:
        print(f"   ... 还有 {len(video_files) - 5} 个")

    # 运行视频理解
    print("\n" + "=" * 70)
    print("🚀 开始视频理解...")
    print("=" * 70)

    try:
        result = video_understand(
            project_path=project_path
        )

        project_name = result.get('projectName', 'Unknown')

        # 显示结果统计
        print("\n" + "=" * 70)
        print("📊 处理结果")
        print("=" * 70)

        print(f"\n✅ 高光点：{len(result.get('highlights', []))} 个")
        for i, hl in enumerate(result.get('highlights', [])[:5], 1):
            print(f"   {i}. EP{hl.get('episode')} {hl.get('timestamp')}s - {hl.get('type')}")

        if len(result.get('highlights', [])) > 5:
            print(f"   ... 还有 {len(result.get('highlights', [])) - 5} 个")

        print(f"\n✅ 钩子点：{len(result.get('hooks', []))} 个")
        for i, hook in enumerate(result.get('hooks', [])[:5], 1):
            print(f"   {i}. EP{hook.get('episode')} {hook.get('timestamp')}s - {hook.get('type')}")

        if len(result.get('hooks', [])) > 5:
            print(f"   ... 还有 {len(result.get('hooks', [])) - 5} 个")

        print(f"\n✅ 剪辑组合：{len(result.get('clips', []))} 个")
        for i, clip in enumerate(result.get('clips', [])[:5], 1):
            duration_min = clip.get('duration', 0) / 60
            print(f"   {i}. EP{clip.get('episode')}→{clip.get('hookEpisode')} - {duration_min:.1f}分钟 - {clip.get('type')}")

        if len(result.get('clips', [])) > 5:
            print(f"   ... 还有 {len(result.get('clips', [])) - 5} 个")

        # 检查剪辑时长限制
        print("\n" + "=" * 70)
        print("📏 剪辑时长验证")
        print("=" * 70)

        clips = result.get('clips', [])
        if clips:
            durations = [clip.get('duration', 0) for clip in clips]
            min_duration = min(durations)
            max_duration = max(durations)
            avg_duration = sum(durations) / len(durations)

            print(f"\n最短：{min_duration / 60:.1f} 分钟 ({min_duration} 秒)")
            print(f"最长：{max_duration / 60:.1f} 分钟 ({max_duration} 秒)")
            print(f"平均：{avg_duration / 60:.1f} 分钟 ({avg_duration:.0f} 秒)")

            # 验证是否符合限制
            from scripts.understand.generate_clips import MIN_CLIP_DURATION, MAX_CLIP_DURATION

            print(f"\n限制范围：{MIN_CLIP_DURATION / 60:.0f} - {MAX_CLIP_DURATION / 60:.0f} 分钟")

            if min_duration >= MIN_CLIP_DURATION:
                print(f"✅ 最短时长符合要求 (≥ {MIN_CLIP_DURATION / 60:.0f} 分钟)")
            else:
                print(f"❌ 最短时长不符合要求 (应为 ≥ {MIN_CLIP_DURATION / 60:.0f} 分钟)")

            if max_duration <= MAX_CLIP_DURATION:
                print(f"✅ 最长时长符合要求 (≤ {MAX_CLIP_DURATION / 60:.0f} 分钟)")
            else:
                print(f"❌ 最长时长不符合要求 (应为 ≤ {MAX_CLIP_DURATION / 60:.0f} 分钟)")

        # 保存结果
        print("\n" + "=" * 70)
        print("💾 保存结果...")
        print("=" * 70)

        output_dir = f"/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/data/hangzhou-leiming/analysis/{project_name}"
        os.makedirs(output_dir, exist_ok=True)

        import json
        with open(f"{output_dir}/result.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"✅ 结果已保存到：{output_dir}/result.json")

        print("\n" + "=" * 70)
        print("🎉 测试完成！")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
