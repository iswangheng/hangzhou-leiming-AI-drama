#!/usr/bin/env python3
"""
Gemini API 并行调用测试

目的：验证并行调用Gemini API是否能提升分析速度

测试方案：
1. 串行调用：逐个发送请求
2. 并行调用：使用ThreadPoolExecutor并发发送

对比指标：
- 总耗时
- 成功率
- 平均单次请求耗时

作者: 杭州雷鸣AI短剧项目
日期: 2026-03-11
"""

import os
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.config import TrainingConfig


def call_gemini_api(request_id: int, test_payload: dict) -> Tuple[int, float, bool, str]:
    """
    调用单次Gemini API

    Args:
        request_id: 请求ID
        test_payload: 测试用的payload

    Returns:
        (request_id, elapsed_time, success, error_message)
    """
    url = f"https://yunwu.ai/v1beta/models/gemini-2.0-flash:generateContent?key={TrainingConfig.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    start_time = time.time()

    try:
        response = requests.post(
            url,
            headers=headers,
            json=test_payload,
            timeout=60
        )
        response.raise_for_status()

        elapsed = time.time() - start_time
        return (request_id, elapsed, True, "")

    except Exception as e:
        elapsed = time.time() - start_time
        return (request_id, elapsed, False, str(e))


def create_test_payload(simple: bool = True) -> dict:
    """
    创建测试用的payload

    Args:
        simple: 是否使用简化payload（无图片，速度更快）

    Returns:
        测试payload
    """
    if simple:
        # 简化版本：纯文本请求，用于测试API响应速度
        return {
            "contents": [{
                "parts": [{
                    "text": "请用一句话回答：什么是短剧？"
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 100
            }
        }
    else:
        # 完整版本：包含图片的请求（模拟实际分析场景）
        # 这里暂时不使用图片，因为需要base64编码
        return {
            "contents": [{
                "parts": [{
                    "text": """请分析以下视频片段是否包含高光点或钩子点。

视频信息：
- 时长：30秒
- 内容：短剧片段

请用JSON格式返回分析结果。"""
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 500
            }
        }


def test_serial_requests(num_requests: int = 6) -> Dict:
    """
    测试串行请求

    Args:
        num_requests: 请求数量

    Returns:
        测试结果
    """
    print(f"\n{'='*60}")
    print(f"📋 测试1: 串行调用 ({num_requests}个请求)")
    print(f"{'='*60}")

    payload = create_test_payload(simple=True)
    results = []

    start_time = time.time()

    for i in range(num_requests):
        print(f"  [{i+1}/{num_requests}] 发送请求...", end=" ", flush=True)
        request_id, elapsed, success, error = call_gemini_api(i, payload)

        if success:
            print(f"✅ 成功 ({elapsed:.2f}秒)")
        else:
            print(f"❌ 失败: {error}")

        results.append({
            "id": request_id,
            "elapsed": elapsed,
            "success": success,
            "error": error
        })

    total_time = time.time() - start_time

    # 统计
    success_count = sum(1 for r in results if r["success"])
    avg_time = sum(r["elapsed"] for r in results) / len(results)

    print(f"\n📊 串行测试结果:")
    print(f"   总耗时: {total_time:.2f}秒")
    print(f"   成功率: {success_count}/{num_requests} ({success_count/num_requests*100:.1f}%)")
    print(f"   平均单次: {avg_time:.2f}秒")

    return {
        "mode": "serial",
        "total_time": total_time,
        "success_count": success_count,
        "total_requests": num_requests,
        "avg_time": avg_time,
        "results": results
    }


def test_parallel_requests(num_requests: int = 6, max_workers: int = 3) -> Dict:
    """
    测试并行请求

    Args:
        num_requests: 请求数量
        max_workers: 最大并发数

    Returns:
        测试结果
    """
    print(f"\n{'='*60}")
    print(f"📋 测试2: 并行调用 ({num_requests}个请求, {max_workers}个并发)")
    print(f"{'='*60}")

    payload = create_test_payload(simple=True)
    results = []

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = {
            executor.submit(call_gemini_api, i, payload): i
            for i in range(num_requests)
        }

        # 收集结果
        for future in as_completed(futures):
            request_id, elapsed, success, error = future.result()

            if success:
                print(f"  ✅ 请求 {request_id+1} 完成 ({elapsed:.2f}秒)")
            else:
                print(f"  ❌ 请求 {request_id+1} 失败: {error}")

            results.append({
                "id": request_id,
                "elapsed": elapsed,
                "success": success,
                "error": error
            })

    total_time = time.time() - start_time

    # 统计
    success_count = sum(1 for r in results if r["success"])
    avg_time = sum(r["elapsed"] for r in results) / len(results)

    print(f"\n📊 并行测试结果:")
    print(f"   总耗时: {total_time:.2f}秒")
    print(f"   成功率: {success_count}/{num_requests} ({success_count/num_requests*100:.1f}%)")
    print(f"   平均单次: {avg_time:.2f}秒")

    return {
        "mode": "parallel",
        "max_workers": max_workers,
        "total_time": total_time,
        "success_count": success_count,
        "total_requests": num_requests,
        "avg_time": avg_time,
        "results": results
    }


def compare_results(serial_result: Dict, parallel_result: Dict):
    """
    对比两种模式的结果
    """
    print(f"\n{'='*60}")
    print(f"📈 性能对比")
    print(f"{'='*60}")

    serial_time = serial_result["total_time"]
    parallel_time = parallel_result["total_time"]
    speedup = serial_time / parallel_time if parallel_time > 0 else 0

    print(f"\n| 指标 | 串行 | 并行({parallel_result['max_workers']}workers) |")
    print(f"|------|------|------------|")
    print(f"| 总耗时 | {serial_time:.2f}秒 | {parallel_time:.2f}秒 |")
    print(f"| 成功率 | {serial_result['success_count']}/{serial_result['total_requests']} | {parallel_result['success_count']}/{parallel_result['total_requests']} |")
    print(f"| 平均单次 | {serial_result['avg_time']:.2f}秒 | {parallel_result['avg_time']:.2f}秒 |")

    print(f"\n🚀 加速比: {speedup:.2f}x")

    if speedup > 1.5:
        print(f"   ✅ 并行化效果显著！建议使用")
    elif speedup > 1.1:
        print(f"   ⚠️  并行化有一定效果，但提升有限")
    else:
        print(f"   ❌ 并行化效果不明显，可能受到API限流影响")

    return speedup


def main():
    """
    主测试函数
    """
    print("\n" + "="*60)
    print("🧪 Gemini API 并行调用测试")
    print("="*60)
    print(f"\n测试目的: 验证并行调用是否能提升分析速度")
    print(f"API端点: yunwu.ai (Gemini 2.0 Flash代理)")
    print(f"当前配置并发数: {TrainingConfig.MAX_CONCURRENT_ANALYSIS}")

    # 测试参数
    num_requests = 6  # 每组测试的请求数量
    max_workers = 3   # 并行worker数

    print(f"\n测试配置:")
    print(f"  - 请求数量: {num_requests}")
    print(f"  - 并发数: {max_workers}")
    print(f"  - 测试类型: 简化文本请求（无图片）")

    # 运行测试
    serial_result = test_serial_requests(num_requests)
    parallel_result = test_parallel_requests(num_requests, max_workers)

    # 对比结果
    speedup = compare_results(serial_result, parallel_result)

    # 结论
    print(f"\n{'='*60}")
    print(f"📝 测试结论")
    print(f"{'='*60}")

    if speedup > 1.5:
        print(f"""
✅ 建议：继续使用并行调用

当前系统已经使用 ThreadPoolExecutor(max_workers=3) 进行并行分析，
测试证明这种方案是有效的。

可能的进一步优化：
1. 如果API限流允许，可以尝试增加 max_workers 到 4-5
2. 监控API返回的429错误，如果频繁出现则降低并发数
""")
    elif speedup > 1.1:
        print(f"""
⚠️  建议：并行化效果有限

可能的原因：
1. API代理服务器有限流
2. 网络延迟较高
3. Gemini API本身的处理速度

建议保持当前的并发设置(3)，继续监控。
""")
    else:
        print(f"""
❌ 建议：并行化效果不明显

可能受到以下限制：
1. API速率限制（RPM）
2. 代理服务器瓶颈
3. 网络带宽限制

建议：
1. 检查API配额和限流情况
2. 考虑使用官方API而非代理
3. 保持串行调用以避免触发限流
""")

    return speedup


if __name__ == "__main__":
    main()
