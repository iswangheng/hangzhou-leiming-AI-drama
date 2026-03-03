#!/usr/bin/env python3
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.filename_parser import parse_episode_number

# 测试用例
test_cases = [
    ("1.mp4", 1),
    ("01.mp4", 1),
    ("精准-1.mp4", 1),
    ("机长姐姐-5.mp4", 5),
    ("ep01.mp4", 1),
    ("EP10.mp4", 10),
    ("第1集.mp4", 1),
    ("骨血灯_03_1080p.mp4", 3),
    ("trailer.mp4", None),
]

print("=== 测试文件名解析功能 ===\n")
passed = 0
failed = 0

for filename, expected in test_cases:
    try:
        result = parse_episode_number(filename)
        status = "✅" if result == expected else "❌"

        if result == expected:
            passed += 1
        else:
            failed += 1

        result_str = f"第{result}集" if result is not None else "None"
        expected_str = f"第{expected}集" if expected is not None else "None"
        print(f"{status} {filename:25s} → {result_str:8s} (期望: {expected_str})")
    except Exception as e:
        print(f"❌ {filename:25s} → 错误: {e}")
        failed += 1

print(f"\n总计: {passed} 通过, {failed} 失败")

if failed == 0:
    print("\n✅ 所有测试通过！代码兼容性验证成功")
    sys.exit(0)
else:
    print(f"\n❌ 有 {failed} 个测试失败")
    sys.exit(1)
