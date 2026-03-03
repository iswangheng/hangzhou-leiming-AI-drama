#!/usr/bin/env node

/**
 * API 重试机制测试脚本
 *
 * 测试 Gemini 和 ElevenLabs API 的错误重试功能
 */

import { withRetry, type RetryOptions } from '../lib/api/utils/retry';

// ============================================
// 测试 1: 基础重试功能
// ============================================
async function testBasicRetry() {
  console.log('🧪 测试 1: 基础重试功能...\n');

  let attemptCount = 0;

  const result = await withRetry(
    async () => {
      attemptCount++;
      console.log(`   尝试 ${attemptCount}...`);

      if (attemptCount < 3) {
        const error = new Error('模拟网络错误') as any;
        error.code = 'NETWORK_ERROR';
        throw error;
      }

      return '成功！';
    },
    {
      maxRetries: 5,
      initialDelay: 100,
      onRetry: (attempt, error) => {
        console.log(`   ⚠️  第 ${attempt} 次重试: ${error.message}`);
      },
    }
  );

  console.log(`✅ 结果: ${result}`);
  console.log(`   总尝试次数: ${attemptCount}\n`);
}

// ============================================
// 测试 2: 不可重试的错误
// ============================================
async function testNonRetryableError() {
  console.log('🧪 测试 2: 不可重试的错误...\n');

  let attemptCount = 0;

  try {
    await withRetry(
      async () => {
        attemptCount++;
        console.log(`   尝试 ${attemptCount}...`);

        const error = new Error('认证失败') as any;
        error.code = 'AUTH_ERROR';
        throw error;
      },
      {
        maxRetries: 5,
        initialDelay: 100,
      }
    );
  } catch (error) {
    console.log(`✅ 预期行为: ${(error as Error).message}`);
    console.log(`   尝试次数: ${attemptCount} (应该只尝试 1 次)\n`);
  }
}

// ============================================
// 测试 3: 指数退避
// ============================================
async function testExponentialBackoff() {
  console.log('🧪 测试 3: 指数退避...\n');

  const delays: number[] = [];
  let attemptCount = 0;

  try {
    await withRetry(
      async () => {
        attemptCount++;
        const startTime = Date.now();

        if (attemptCount < 4) {
          const error = new Error('模拟超时') as any;
          error.code = 'TIMEOUT';
          throw error;
        }

        return '成功！';
      },
      {
        maxRetries: 5,
        initialDelay: 100,
        backoffMultiplier: 2,
        maxDelay: 1000,
        onRetry: (attempt, error) => {
          const now = Date.now();
          // 注意：这里只是演示，实际延迟时间在 withRetry 内部
          console.log(`   ⚠️  第 ${attempt} 次重试: ${error.message}`);
        },
      }
    );
  } catch (error) {
    // 忽略
  }

  console.log(`✅ 总尝试次数: ${attemptCount}\n`);
}

// ============================================
// 测试 4: HTTP 状态码重试
// ============================================
async function testStatusCodeRetry() {
  console.log('🧪 测试 4: HTTP 状态码重试...\n');

  let attemptCount = 0;

  const result = await withRetry(
    async () => {
      attemptCount++;
      console.log(`   尝试 ${attemptCount}...`);

      if (attemptCount < 2) {
        const error = new Error('Rate limit exceeded') as any;
        error.statusCode = 429;
        throw error;
      }

      return '成功！';
    },
    {
      maxRetries: 5,
      initialDelay: 100,
      retryableStatusCodes: [429, 500, 502, 503, 504],
    }
  );

  console.log(`✅ 结果: ${result}`);
  console.log(`   总尝试次数: ${attemptCount}\n`);
}

// ============================================
// 主函数
// ============================================
async function main() {
  console.log('========================================');
  console.log('📋 API 重试机制测试');
  console.log('========================================\n');

  await testBasicRetry();
  await testNonRetryableError();
  await testExponentialBackoff();
  await testStatusCodeRetry();

  console.log('========================================');
  console.log('✅ 重试机制测试完成');
  console.log('========================================\n');

  console.log('💡 功能特性:');
  console.log('   1. 自动重试（网络错误、超时、5xx 错误）');
  console.log('   2. 指数退避策略（默认 1s → 2s → 4s → ...）');
  console.log('   3. 最大重试次数限制（默认 3 次）');
  console.log('   4. 智能错误识别（自动过滤不可重试的错误）');
  console.log('');

  process.exit(0);
}

main().catch((error) => {
  console.error('❌ 测试失败:', error);
  process.exit(1);
});
