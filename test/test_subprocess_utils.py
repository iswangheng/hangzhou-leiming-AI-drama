"""
subprocess_utils 单元测试

验证内容：
1. run_command() 正常执行返回结果
2. run_command() 超时返回 None（用 sleep 模拟卡死）
3. run_command() 超时后正确重试指定次数
4. run_popen_with_timeout() 超时返回 -1 且进程被 kill
"""

import sys
import time
from pathlib import Path

# 将项目根目录加入 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.subprocess_utils import run_command, run_popen_with_timeout


def test_run_command_normal():
    """测试正常命令执行"""
    result = run_command(['echo', 'hello'], timeout=10)
    assert result is not None, "正常命令应返回结果"
    assert result.returncode == 0, "返回码应为0"
    assert 'hello' in result.stdout, "输出应包含 'hello'"
    print("✅ test_run_command_normal 通过")


def test_run_command_timeout_returns_none():
    """测试超时返回 None"""
    start = time.time()
    result = run_command(['sleep', '999'], timeout=2)
    elapsed = time.time() - start
    assert result is None, "超时应返回 None"
    assert elapsed < 5, f"超时时间不应太长（实际: {elapsed:.1f}s）"
    print(f"✅ test_run_command_timeout_returns_none 通过（{elapsed:.1f}s）")


def test_run_command_retry_count():
    """测试超时后重试正确次数"""
    attempt_count = [0]
    original_run = __import__('subprocess').run

    # 通过检查实际用时来验证重试次数（重试1次，每次超时1秒，间隔0.5秒）
    start = time.time()
    result = run_command(
        ['sleep', '999'],
        timeout=1,
        retries=2,
        retry_delay=0.5
    )
    elapsed = time.time() - start

    assert result is None, "超时耗尽所有重试后应返回 None"
    # 3次执行（原始+重试2次），每次约1秒，间隔0.5秒 → 约4秒
    assert elapsed >= 3.0, f"应至少经过重试等待时间（实际: {elapsed:.1f}s）"
    print(f"✅ test_run_command_retry_count 通过（重试2次，总用时{elapsed:.1f}s）")


def test_run_command_nonzero_return():
    """测试非零返回码（不抛异常时正常返回）"""
    result = run_command(['false'], timeout=10)
    assert result is not None, "非零返回码命令应返回结果"
    assert result.returncode != 0, "返回码应非0"
    print("✅ test_run_command_nonzero_return 通过")


def test_run_command_raise_on_error():
    """测试 raise_on_error=True 时抛出 RuntimeError"""
    try:
        result = run_command(['false'], timeout=10, raise_on_error=True)
        assert False, "应该抛出 RuntimeError"
    except RuntimeError:
        pass
    print("✅ test_run_command_raise_on_error 通过")


def test_run_popen_with_timeout_normal():
    """测试 run_popen_with_timeout 正常执行"""
    returncode = run_popen_with_timeout(['echo', 'hello'], timeout=10)
    assert returncode == 0, "正常命令应返回0"
    print("✅ test_run_popen_with_timeout_normal 通过")


def test_run_popen_with_timeout_timeout():
    """测试 run_popen_with_timeout 超时返回 -1"""
    start = time.time()
    returncode = run_popen_with_timeout(['sleep', '999'], timeout=2)
    elapsed = time.time() - start
    assert returncode == -1, f"超时应返回 -1（实际: {returncode}）"
    assert elapsed < 5, f"超时时间不应太长（实际: {elapsed:.1f}s）"
    print(f"✅ test_run_popen_with_timeout_timeout 通过（{elapsed:.1f}s）")


def test_run_popen_on_line_callback():
    """测试 on_line 回调函数"""
    lines = []
    returncode = run_popen_with_timeout(
        ['echo', 'test line'],
        timeout=10,
        on_line=lambda l: lines.append(l)
    )
    assert returncode == 0
    assert any('test line' in l for l in lines), f"应捕获到输出行（实际: {lines}）"
    print("✅ test_run_popen_on_line_callback 通过")


if __name__ == '__main__':
    print("=" * 60)
    print("subprocess_utils 单元测试")
    print("=" * 60)

    tests = [
        test_run_command_normal,
        test_run_command_timeout_returns_none,
        test_run_command_retry_count,
        test_run_command_nonzero_return,
        test_run_command_raise_on_error,
        test_run_popen_with_timeout_normal,
        test_run_popen_with_timeout_timeout,
        test_run_popen_on_line_callback,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} 失败: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"结果：{passed} 通过，{failed} 失败")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
