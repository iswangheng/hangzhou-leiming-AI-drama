#!/usr/bin/env python3
"""
提取错误视频的ASR转录文本
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from scripts.asr_transcriber import ASRTranscriber

# 错误视频列表
error_videos = [
    ("晓红姐-3.4剧目/多子多福，开局就送绝美老婆/9.mp4", "有片尾"),
    ("晓红姐-3.4剧目/欺我年迈抢祖宅，和贫道仙法说吧/2.mp4", "有片尾"),
    ("晓红姐-3.4剧目/老公成为首富那天我重生了/2.mp4", "有片尾"),
    ("晓红姐-3.4剧目/老公成为首富那天我重生了/3.mp4", "有片尾"),
    ("晓红姐-3.4剧目/老公成为首富那天我重生了/5.mp4", "有片尾"),
]

print("=" * 100)
print("🔍 提取错误视频的ASR转录文本")
print("=" * 100)

transcriber = ASRTranscriber(model_size="base")

for video_path, expected in error_videos:
    print(f"\n{'=' * 100}")
    print(f"视频: {Path(video_path).parent.name} / {Path(video_path).name}")
    print(f"期望: {expected}")
    print(f"{'=' * 100}")

    if not Path(video_path).exists():
        print(f"⚠️  文件不存在: {video_path}")
        continue

    try:
        # 转录最后3.5秒
        asr_segments = transcriber.transcribe_last_seconds(video_path, seconds=3.5)

        print(f"\nASR转录结果:")
        if not asr_segments:
            print("  (无ASR片段)")
        else:
            for i, seg in enumerate(asr_segments):
                print(f"  [{i+1}] {seg['start']:.2f}s-{seg['end']:.2f}s: \"{seg['text']}\"")

            # 统计信息
            full_text = " ".join(seg['text'] for seg in asr_segments)
            total_duration = asr_segments[-1]['end'] - asr_segments[0]['start']
            text_length = len(full_text)

            print(f"\n统计:")
            print(f"  ASR片段数: {len(asr_segments)}")
            print(f"  总时长: {total_duration:.2f}秒")
            print(f"  文本长度: {text_length}字")
            print(f"  完整文本: \"{full_text}\"")

    except Exception as e:
        print(f"❌ 转录失败: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'=' * 100}")
print("✅ ASR文本提取完成")
print(f"{'=' * 100}")
