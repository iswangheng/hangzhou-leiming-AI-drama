#!/usr/bin/env python3
"""
Gemini API 并发压力测试

目的：测试 Gemini API 能承受的最大并发量，找到最优并发数

测试方案：
1. 从小到大测试不同并发数（3, 5, 8, 10, 15, 20）
2. 每个并发数发送 10 个请求
3. 记录成功率、总耗时、平均耗时
4. 找到最优并发数（成功率高 + 耗时短）

使用方式：
    python test/test_gemini_concurrency.py

作者: 杭州雷鸣AI短剧项目
日期: 2026-03-13
"""

import os
import sys
import time
import json
import base64
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.config import TrainingConfig


@dataclass
class TestResult:
    """测试结果"""
    concurrency: int
    total_requests: int
    success_count: int
    failed_count: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    success_rate: float


def get_test_image() -> str:
    """获取测试用的图片（Base64编码）"""
    # 查找一个关键帧图片
    keyframe_dirs = list(Path("data/cache/keyframes").glob("*"))
    if not keyframe_dirs:
        # 如果没有缓存，创建一个简单的测试图片
        from PIL import Image
        import io
        img = Image.new('RGB', (360, 640), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    # 找到第一张图片
    for keyframe_dir in keyframe_dirs:
        episode_dirs = list(keyframe_dir.glob("*"))
        for episode_dir in episode_dirs:
            images = list(episode_dir.glob("*.jpg"))
            if images:
                with open(images[0], 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')

    # 没找到，创建测试图片
    from PIL import Image
    import io
    img = Image.new('RGB', (360, 640), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def send_gemini_request(request_id: int, image_base64: str) -> Tuple[int, float, bool, str]:
    """
    发送单个 Gemini API 请求

    Args:
        request_id: 请求ID
        image_base64: Base64编码的图片

    Returns:
        (request_id, 耗时, 是否成功, 错误信息)
    """
    url = f"https://yunwu.ai/v1beta/models/gemini-2.0-flash:generateContent?key={TrainingConfig.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    # 简单的测试 Prompt
    prompt = """分析这张图片，返回 JSON 格式：
```json
{
  "description": "简短描述图片内容（10字以内）",
  "has_person": true/false
}
```
只返回 JSON，不要其他文字。"""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_base64
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 256
        }
    }

    start_time = time.time()

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and len(data['candidates']) > 0:
                return (request_id, elapsed, True, "")
            else:
                return (request_id, elapsed, False, "Invalid response format")
        else:
            return (request_id, elapsed, False, f"HTTP {response.status_code}: {response.text[:100]}")

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        return (request_id, elapsed, False, "Timeout (60s)")
    except Exception as e:
        elapsed = time.time() - start_time
        return (request_id, elapsed, False, str(e)[:50])


def test_concurrency(concurrency: int, num_requests: int, image_base64: str) -> TestResult:
    """
    测试指定并发数

    Args:
        concurrency: 并发数
        num_requests: 总请求数
        image_base64: 测试图片

    Returns:
        测试结果
    """
    print(f"\n{'='*60}")
    print(f"🧪 测试并发数: {concurrency}")
    print(f"{'='*60}")
    print(f"总请求数: {num_requests}")
    print(f"并发 Worker: {concurrency}")

    start_time = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(send_gemini_request, i, image_base64): i
            for i in range(num_requests)
        }

        completed = 0
        for future in as_completed(futures):
            request_id, elapsed, success, error = future.result()
            results.append((request_id, elapsed, success, error))
            completed += 1

            # 打印进度
            status = "✅" if success else "❌"
            if success:
                print(f"  [{completed}/{num_requests}] {status} 请求 {request_id}: {elapsed:.2f}s")
            else:
                print(f"  [{completed}/{num_requests}] {status} 请求 {request_id}: {elapsed:.2f}s - {error}")

    total_time = time.time() - start_time

    # 统计结果
    success_count = sum(1 for r in results if r[2])
    failed_count = num_requests - success_count
    times = [r[1] for r in results]
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    success_rate = success_count / num_requests * 100

    return TestResult(
        concurrency=concurrency,
        total_requests=num_requests,
        success_count=success_count,
        failed_count=failed_count,
        total_time=total_time,
        avg_time=avg_time,
        min_time=min_time,
        max_time=max_time,
        success_rate=success_rate
    )


def print_result(result: TestResult):
    """打印测试结果"""
    print(f"\n📊 测试结果 (并发数: {result.concurrency})")
    print(f"  成功率: {result.success_rate:.1f}% ({result.success_count}/{result.total_requests})")
    print(f"  总耗时: {result.total_time:.2f}s")
    print(f"  平均耗时: {result.avg_time:.2f}s/请求")
    print(f"  最小耗时: {result.min_time:.2f}s")
    print(f"  最大耗时: {result.max_time:.2f}s")

    # 计算吞吐量
    throughput = result.success_count / result.total_time
    print(f"  吞吐量: {throughput:.2f} 请求/秒")


def main():
    """主测试函数"""
    print("="*70)
    print("🚀 Gemini API 并发压力测试")
    print("="*70)

    # 检查 API Key
    if not hasattr(TrainingConfig, 'GEMINI_API_KEY') or not TrainingConfig.GEMINI_API_KEY:
        print("❌ 错误: 未配置 GEMINI_API_KEY")
        sys.exit(1)

    print(f"API Key: {TrainingConfig.GEMINI_API_KEY[:10]}...")

    # 获取测试图片
    print("\n📷 准备测试图片...")
    try:
        image_base64 = get_test_image()
        print(f"✅ 图片准备完成 (大小: {len(image_base64)/1024:.1f} KB)")
    except Exception as e:
        print(f"❌ 图片准备失败: {e}")
        sys.exit(1)

    # 测试配置
    test_configs = [
        (3, 9),    # 并发3，9个请求
        (5, 10),   # 并发5，10个请求
        (8, 16),   # 并发8，16个请求
        (10, 20),  # 并发10，20个请求
        (15, 30),  # 并发15，30个请求
    ]

    results = []

    for concurrency, num_requests in test_configs:
        result = test_concurrency(concurrency, num_requests, image_base64)
        print_result(result)
        results.append(result)

        # 如果成功率低于 80%，停止测试
        if result.success_rate < 80:
            print(f"\n⚠️  成功率低于 80%，停止测试")
            break

        # 等待一下再继续
        if concurrency < test_configs[-1][0]:
            print(f"\n⏳ 等待 5 秒后继续...")
            time.sleep(5)

    # 打印汇总
    print("\n" + "="*70)
    print("📋 测试汇总")
    print("="*70)
    print(f"{'并发数':^8} | {'成功率':^10} | {'总耗时':^10} | {'平均耗时':^10} | {'吞吐量':^12}")
    print("-" * 70)

    for r in results:
        throughput = r.success_count / r.total_time
        print(f"{r.concurrency:^8} | {r.success_rate:^10.1f}% | {r.total_time:^10.2f}s | {r.avg_time:^10.2f}s | {throughput:^12.2f}/s")

    # 推荐并发数
    print("\n" + "="*70)
    print("💡 推荐并发数")
    print("="*70)

    # 找到成功率 >= 90% 且吞吐量最高的
    valid_results = [r for r in results if r.success_rate >= 90]
    if valid_results:
        best = max(valid_results, key=lambda r: r.success_count / r.total_time)
        print(f"✅ 推荐并发数: {best.concurrency}")
        print(f"   成功率: {best.success_rate:.1f}%")
        print(f"   吞吐量: {best.success_count / best.total_time:.2f} 请求/秒")

        # 估算实际分析时间
        segments = 30  # 假设 30 个片段
        estimated_time = segments / (best.success_count / best.total_time) * best.avg_time
        print(f"\n📈 预估分析时间:")
        print(f"   {segments} 个片段，并发 {best.concurrency}")
        print(f"   预计耗时: {estimated_time:.1f}s ({estimated_time/60:.1f} 分钟)")
    else:
        print("⚠️  没有找到成功率 >= 90% 的配置，建议使用并发数 3")


if __name__ == "__main__":
    main()
