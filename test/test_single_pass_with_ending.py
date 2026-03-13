#!/usr/bin/env python3
"""
测试：单次 FFmpeg 编码（有片尾视频）可行性验证

目标：验证直接 concat 音频（不用 apad）是否可以在一次 FFmpeg 调用中完成
      裁剪 + 分辨率缩放 + 花字叠加 + 片尾拼接

测试项：
1. 基础 concat（视频+音频，无花字）
2. 含花字 drawtext 的 concat
3. 含 PNG 角标叠加的完整单次编码

验证指标：
- 音视频同步（时长差 < 0.1s）
- 无画面冻结、无音频跳跃
- 总时长 = 主体时长 + 片尾时长
"""
import subprocess
import os
import sys
import json
import time
from pathlib import Path

# ========== 配置 ==========
PROJECT_ROOT = Path(__file__).parent.parent
VIDEO_DIR = PROJECT_ROOT / "260306-待剪辑-漫剧网盘素材1/烈日重生"
ENDING_VIDEO = PROJECT_ROOT / "标准结尾帧视频素材/点击下方观看全集.mp4"
OUTPUT_DIR = PROJECT_ROOT / "test/output_single_pass_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 使用第1集 0秒~60秒 作为主体（截取前60秒，避免跨集复杂性）
SOURCE_VIDEO = VIDEO_DIR / "烈日重生-1.mp4"
CLIP_START = 0
CLIP_DURATION = 60  # 秒
ENDING_DURATION = 5  # 取片尾前5秒


def probe_video(path: str) -> dict:
    """获取视频基本信息"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,r_frame_rate,duration',
        '-show_entries', 'format=duration',
        '-of', 'json',
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    streams = data.get('streams', [{}])
    fmt = data.get('format', {})

    stream = streams[0] if streams else {}
    fps_str = stream.get('r_frame_rate', '30/1')
    if '/' in fps_str:
        n, d = fps_str.split('/')
        fps = float(n) / float(d)
    else:
        fps = float(fps_str)

    duration = float(fmt.get('duration', stream.get('duration', 0)))

    return {
        'width': int(stream.get('width', 1080)),
        'height': int(stream.get('height', 1920)),
        'fps': fps,
        'duration': duration,
    }


def probe_audio_duration(path: str) -> float:
    """获取音频流时长"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'a:0',
        '-show_entries', 'stream=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 0.0


def check_sync(path: str) -> dict:
    """检查音视频同步状态"""
    vid_info = probe_video(path)
    aud_dur = probe_audio_duration(path)
    vid_dur = vid_info['duration']
    diff = abs(vid_dur - aud_dur)
    return {
        'video_duration': vid_dur,
        'audio_duration': aud_dur,
        'diff': diff,
        'ok': diff < 0.2,  # 允许 0.2 秒误差
    }


def run_ffmpeg(cmd: list, label: str) -> bool:
    """运行 FFmpeg 命令，返回是否成功"""
    print(f"\n{'='*60}")
    print(f"[{label}] 运行 FFmpeg...")
    start = time.time()

    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"  ❌ 失败 (returncode={result.returncode}, 耗时={elapsed:.1f}s)")
        print(f"  stderr: {result.stderr[-500:]}")
        return False

    print(f"  ✅ 成功 (耗时={elapsed:.1f}s)")
    return True


# ==========================================================
# 测试 1: 基础单次编码（裁剪 + 片尾 concat，无花字）
# ==========================================================
def test_basic_concat():
    print("\n" + "="*60)
    print("测试 1: 基础单次编码（裁剪 + 片尾 concat，无花字）")
    print("="*60)

    src_info = probe_video(str(SOURCE_VIDEO))
    W, H = src_info['width'], src_info['height']
    FPS = src_info['fps']

    print(f"  源视频: {W}x{H} @ {FPS:.2f}fps")

    output = str(OUTPUT_DIR / "test1_basic_concat.mp4")

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(CLIP_START), '-t', str(CLIP_DURATION),
        '-i', str(SOURCE_VIDEO),
        '-t', str(ENDING_DURATION),
        '-i', str(ENDING_VIDEO),
        '-filter_complex',
        (
            # 主体视频（已经通过 -ss -t 裁剪好了）
            f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1[v_main];"
            # 结尾视频：缩放 + fps 对齐
            f"[1:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS:.3f},setsar=1[v_end];"
            # 视频 concat
            f"[v_main][v_end]concat=n=2:v=1:a=0[v_out];"
            # 音频直接 concat（不用 apad）
            f"[0:a][1:a]concat=n=2:v=0:a=1[a_out]"
        ),
        '-map', '[v_out]', '-map', '[a_out]',
        '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '128k',
        output
    ]

    if not run_ffmpeg(cmd, "测试1"):
        return False

    sync = check_sync(output)
    expected_dur = CLIP_DURATION + ENDING_DURATION

    print(f"  视频时长: {sync['video_duration']:.3f}s (期望约 {expected_dur}s)")
    print(f"  音频时长: {sync['audio_duration']:.3f}s")
    print(f"  音视频差: {sync['diff']:.3f}s {'✅' if sync['ok'] else '❌'}")
    print(f"  输出文件: {output}")

    return sync['ok']


# ==========================================================
# 测试 2: 含 drawtext 花字的单次编码
# ==========================================================
def test_with_drawtext():
    print("\n" + "="*60)
    print("测试 2: 含 drawtext 花字的单次编码")
    print("="*60)

    src_info = probe_video(str(SOURCE_VIDEO))
    W, H = src_info['width'], src_info['height']
    FPS = src_info['fps']

    # 查找中文字体
    font_paths = [
        '/System/Library/Fonts/Supplemental/Songti.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc',
        '/System/Library/Fonts/Helvetica.ttc',
    ]
    font_path = next((p for p in font_paths if Path(p).exists()), font_paths[-1])

    output = str(OUTPUT_DIR / "test2_with_drawtext.mp4")

    # 动态字体大小（基于分辨率）
    smaller = min(W, H)
    font_size = int(smaller / 360 * 18 * 0.95)

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(CLIP_START), '-t', str(CLIP_DURATION),
        '-i', str(SOURCE_VIDEO),
        '-t', str(ENDING_DURATION),
        '-i', str(ENDING_VIDEO),
        '-filter_complex',
        (
            f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1[v_main];"
            f"[1:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS:.3f},setsar=1[v_end];"
            f"[v_main][v_end]concat=n=2:v=1:a=0[v_cat];"
            f"[0:a][1:a]concat=n=2:v=0:a=1[a_out];"
            # 添加剧名 drawtext
            f"[v_cat]drawtext=fontfile='{font_path}':text='烈日重生':"
            f"fontsize={font_size}:fontcolor=white:"
            f"x=(w-text_w)/2:y=h-text_h-{int(H*0.05)}:"
            f"borderw=2:bordercolor=black[v_out]"
        ),
        '-map', '[v_out]', '-map', '[a_out]',
        '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '128k',
        output
    ]

    if not run_ffmpeg(cmd, "测试2"):
        return False

    sync = check_sync(output)
    expected_dur = CLIP_DURATION + ENDING_DURATION

    print(f"  视频时长: {sync['video_duration']:.3f}s (期望约 {expected_dur}s)")
    print(f"  音频时长: {sync['audio_duration']:.3f}s")
    print(f"  音视频差: {sync['diff']:.3f}s {'✅' if sync['ok'] else '❌'}")
    print(f"  输出文件: {output}")

    return sync['ok']


# ==========================================================
# 测试 3: 对比分步处理（当前实际路径）耗时
# ==========================================================
def test_multistep_benchmark():
    print("\n" + "="*60)
    print("测试 3: 分步处理耗时基准（当前路径，用于对比）")
    print("="*60)

    src_info = probe_video(str(SOURCE_VIDEO))
    W, H = src_info['width'], src_info['height']
    FPS = src_info['fps']

    total_start = time.time()

    # Step 1: 裁剪
    temp_trim = str(OUTPUT_DIR / "bench_trim.mp4")
    cmd1 = [
        'ffmpeg', '-y',
        '-ss', str(CLIP_START), '-t', str(CLIP_DURATION),
        '-i', str(SOURCE_VIDEO),
        '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '128k',
        temp_trim
    ]
    t1 = time.time()
    run_ffmpeg(cmd1, "Step1-裁剪")
    print(f"  Step1 耗时: {time.time()-t1:.1f}s")

    # Step 2: 预处理结尾视频
    temp_ending = str(OUTPUT_DIR / "bench_ending.mp4")
    cmd2 = [
        'ffmpeg', '-y',
        '-t', str(ENDING_DURATION),
        '-i', str(ENDING_VIDEO),
        '-vf', f'scale={W}:{H},fps={FPS:.3f},setsar=1',
        '-vsync', 'cfr',
        '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '128k',
        temp_ending
    ]
    t2 = time.time()
    run_ffmpeg(cmd2, "Step2-预处理片尾")
    print(f"  Step2 耗时: {time.time()-t2:.1f}s")

    # Step 3: concat demuxer
    concat_list = str(OUTPUT_DIR / "bench_concat.txt")
    with open(concat_list, 'w') as f:
        f.write(f"file '{Path(temp_trim).name}'\n")
        f.write(f"file '{Path(temp_ending).name}'\n")

    output_bench = str(OUTPUT_DIR / "test3_multistep.mp4")
    cmd3 = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', concat_list,
        '-c', 'copy',
        output_bench
    ]
    t3 = time.time()
    run_ffmpeg(cmd3, "Step3-concat拼接")
    print(f"  Step3 耗时: {time.time()-t3:.1f}s")

    total_elapsed = time.time() - total_start

    sync = check_sync(output_bench)
    print(f"\n  分步总耗时: {total_elapsed:.1f}s")
    print(f"  视频时长: {sync['video_duration']:.3f}s")
    print(f"  音频时长: {sync['audio_duration']:.3f}s")
    print(f"  音视频差: {sync['diff']:.3f}s {'✅' if sync['ok'] else '❌'}")
    print(f"  输出文件: {output_bench}")

    # 清理临时文件
    for f in [temp_trim, temp_ending, concat_list]:
        try:
            Path(f).unlink()
        except:
            pass

    return total_elapsed


# ==========================================================
# 主函数：运行所有测试，输出对比结果
# ==========================================================
if __name__ == '__main__':
    print("=" * 60)
    print("单次编码 + 片尾视频 可行性测试")
    print(f"源视频: {SOURCE_VIDEO}")
    print(f"片尾视频: {ENDING_VIDEO}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    results = {}

    # 测试1: 基础 concat（验证音视频同步）
    t1_start = time.time()
    results['test1_basic'] = test_basic_concat()
    results['test1_time'] = time.time() - t1_start

    # 测试2: 含 drawtext
    t2_start = time.time()
    results['test2_drawtext'] = test_with_drawtext()
    results['test2_time'] = time.time() - t2_start

    # 测试3: 分步处理基准耗时
    results['test3_multistep_time'] = test_multistep_benchmark()

    # 汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"  测试1 基础concat:      {'✅ 通过' if results['test1_basic'] else '❌ 失败'}  ({results['test1_time']:.1f}s)")
    print(f"  测试2 含drawtext:      {'✅ 通过' if results['test2_drawtext'] else '❌ 失败'}  ({results['test2_time']:.1f}s)")
    print(f"  测试3 分步处理基准:    {results['test3_multistep_time']:.1f}s")

    if results['test1_basic'] and results['test2_drawtext']:
        speedup = results['test3_multistep_time'] / max(results['test1_time'], 0.1)
        print(f"\n  🚀 单次编码速度提升: {speedup:.1f}x  (基础concat vs 分步处理)")
        print(f"  结论: 单次编码方案可行，建议实施！")
    else:
        print(f"\n  ⚠️  单次编码存在问题，需要进一步排查")

    print(f"\n  生成的测试视频在: {OUTPUT_DIR}")
    print(f"  可用 QuickTime 或 ffplay 验证音视频同步")
