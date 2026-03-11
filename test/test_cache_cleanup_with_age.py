"""
测试缓存清理的时间保留策略

测试 cleanup_project_cache() 函数是否正确实现了基于文件修改时间的清理逻辑
"""
import os
import sys
import time
import tempfile
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.config import TrainingConfig
from scripts.understand.video_understand import cleanup_project_cache


def test_cleanup_with_age():
    """测试缓存清理的时间保留策略"""
    print("="*60)
    print("测试缓存清理的时间保留策略")
    print("="*60)

    # 创建测试项目目录
    test_project = "test_cache_age_project"
    cache_dir = TrainingConfig.CACHE_DIR

    # 创建测试缓存目录
    keyframes_dir = cache_dir / "keyframes" / test_project
    audio_dir = cache_dir / "audio" / test_project
    asr_dir = cache_dir / "asr" / test_project

    # 创建目录
    for d in [keyframes_dir, audio_dir, asr_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 创建测试文件
    # 1. 创建"旧"文件（4小时前）
    old_time = time.time() - (4 * 3600)

    old_file_1 = keyframes_dir / "old_frame_001.jpg"
    old_file_1.write_text("old keyframe")
    os.utime(old_file_1, (old_time, old_time))

    old_file_2 = audio_dir / "old_audio.wav"
    old_file_2.write_text("old audio")
    os.utime(old_file_2, (old_time, old_time))

    old_file_3 = asr_dir / "old_asr.json"
    old_file_3.write_text("old asr")
    os.utime(old_file_3, (old_time, old_time))

    # 2. 创建"新"文件（1小时前）
    new_time = time.time() - (1 * 3600)

    new_file_1 = keyframes_dir / "new_frame_001.jpg"
    new_file_1.write_text("new keyframe")
    os.utime(new_file_1, (new_time, new_time))

    new_file_2 = audio_dir / "new_audio.wav"
    new_file_2.write_text("new audio")
    os.utime(new_file_2, (new_time, new_time))

    new_file_3 = asr_dir / "new_asr.json"
    new_file_3.write_text("new asr")
    os.utime(new_file_3, (new_time, new_time))

    print(f"\n测试项目: {test_project}")
    print(f"缓存目录: {cache_dir}")
    print(f"\n创建的测试文件:")
    print(f"  旧文件（4小时前）: 3 个")
    print(f"  新文件（1小时前）: 3 个")
    print(f"  总计: 6 个文件")

    # 执行清理（3小时保留期）
    print(f"\n执行清理（保留期: 3小时）...")
    result = cleanup_project_cache(test_project, min_age_hours=3.0)

    print(f"\n清理结果:")
    print(f"  已清理目录数: 关键帧={result['keyframes_cleaned']}, "
          f"音频={result['audio_cleaned']}, "
          f"ASR={result['asr_cleaned']}")
    print(f"  跳过的文件数: {result['skipped']}")
    print(f"  释放空间: {result['total_size_freed_mb']:.4f} MB")

    # 验证结果
    print(f"\n验证结果:")

    # 检查旧文件是否被删除
    old_files_exist = [
        old_file_1.exists(),
        old_file_2.exists(),
        old_file_3.exists()
    ]
    old_files_deleted = not any(old_files_exist)

    print(f"  ✅ 旧文件（4小时前）已删除: {old_files_deleted}")
    if not old_files_deleted:
        print(f"     警告: 部分旧文件仍然存在")

    # 检查新文件是否被保留
    new_files_exist = [
        new_file_1.exists(),
        new_file_2.exists(),
        new_file_3.exists()
    ]
    new_files_kept = all(new_files_exist)

    print(f"  ✅ 新文件（1小时前）已保留: {new_files_kept}")
    if not new_files_kept:
        print(f"     警告: 部分新文件被误删")

    # 检查跳过的文件数
    expected_skipped = 3  # 3个新文件应该被跳过
    print(f"  ✅ 跳过文件数正确: {result['skipped'] == expected_skipped} "
          f"(期望: {expected_skipped}, 实际: {result['skipped']})")

    # 清理测试目录
    print(f"\n清理测试目录...")
    for d in [keyframes_dir, audio_dir, asr_dir]:
        if d.exists():
            import shutil
            shutil.rmtree(d)

    # 判断测试是否通过
    test_passed = (
        old_files_deleted and
        new_files_kept and
        result['skipped'] == expected_skipped
    )

    print(f"\n{'='*60}")
    if test_passed:
        print("✅ 测试通过！缓存清理的时间保留策略工作正常")
    else:
        print("❌ 测试失败！请检查实现逻辑")
    print(f"{'='*60}")

    return test_passed


if __name__ == "__main__":
    test_cleanup_with_age()
