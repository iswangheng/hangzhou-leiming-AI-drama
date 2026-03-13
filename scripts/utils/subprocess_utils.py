"""
subprocess 工具模块 - 带超时和重试的 subprocess 封装

功能：
1. run_command() - 替换 subprocess.run()，支持超时、重试
2. run_popen_with_timeout() - 替换 Popen + wait()，保留实时流式输出

超时后行为：
- 超时时 kill 进程并可选重试
- 重试耗尽返回 None（调用方决定 fallback/跳过）
- run_popen_with_timeout 超时返回 -1

V17+ 新增
"""

import subprocess
import threading
import time
from typing import List, Optional, Callable


def run_command(
    cmd: List[str],
    timeout: int,
    retries: int = 0,
    retry_delay: float = 2.0,
    error_msg: str = "",
    raise_on_error: bool = False,
    log_prefix: str = ""
) -> Optional[subprocess.CompletedProcess]:
    """
    带超时和可选重试的 subprocess.run 包装器。

    Args:
        cmd: 要执行的命令列表
        timeout: 超时秒数
        retries: 超时/失败后的重试次数（默认不重试）
        retry_delay: 重试间隔（秒）
        error_msg: 自定义错误信息（用于日志）
        raise_on_error: 非零返回码时是否抛出 RuntimeError
        log_prefix: 日志前缀字符串

    Returns:
        CompletedProcess 对象；超时耗尽所有重试后返回 None

    超时行为：kill 进程，等待 retry_delay 后重试；重试耗尽后返回 None
    失败行为：raise_on_error=True 时抛 RuntimeError（同时覆盖超时和非零返回码）
    返回 None：表示超时耗尽（且 raise_on_error=False），调用方决定 fallback/跳过
    """
    prefix = f"[{log_prefix}] " if log_prefix else ""
    msg = error_msg or f"命令超时（{timeout}秒）: {' '.join(cmd[:3])}"

    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode != 0 and raise_on_error:
                raise RuntimeError(
                    f"{error_msg or cmd[0]} 失败\n{result.stderr[:500]}"
                )
            return result

        except subprocess.TimeoutExpired:
            if attempt < retries:
                print(
                    f"  {prefix}⏰ {msg}，"
                    f"{retry_delay:.0f}秒后重试（{attempt + 1}/{retries}）..."
                )
                time.sleep(retry_delay)
            else:
                print(f"  {prefix}⏰ {msg}，已达最大重试次数")

        except Exception as e:
            if raise_on_error:
                raise
            print(f"  {prefix}❌ 命令异常: {e}")
            return None

    # 所有重试耗尽：超时
    if raise_on_error:
        raise RuntimeError(error_msg or f"命令超时（{timeout}秒），已达最大重试次数: {' '.join(cmd[:3])}")
    return None


def run_popen_with_timeout(
    cmd: List[str],
    timeout: int,
    on_line: Optional[Callable[[str], None]] = None,
    log_prefix: str = ""
) -> int:
    """
    带超时的 Popen 包装器，保留实时流式输出。

    使用 threading.Timer 在超时后 kill 进程（保留实时日志）。
    返回 returncode；超时时返回 -1（调用方判断 -1 来决定跳过）。

    Args:
        cmd: 要执行的命令列表
        timeout: 超时秒数
        on_line: 每行输出的回调函数（可选）；未提供时打印到 stdout
        log_prefix: 日志前缀字符串

    Returns:
        进程返回码；超时返回 -1
    """
    prefix = f"[{log_prefix}] " if log_prefix else ""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    timed_out = False

    def _kill():
        nonlocal timed_out
        timed_out = True
        print(f"\n  {prefix}⏰ FFmpeg 超时（{timeout}秒），强制终止")
        process.kill()

    timer = threading.Timer(timeout, _kill)
    try:
        timer.start()
        for line in process.stdout:
            if on_line:
                on_line(line.strip())
            else:
                print(f"\r  {line.strip()[:100]}", end='', flush=True)
        process.wait()
    finally:
        timer.cancel()

    return -1 if timed_out else process.returncode
