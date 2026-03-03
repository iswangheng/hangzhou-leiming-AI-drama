#!/usr/bin/env node

/**
 * API 流式响应测试脚本
 *
 * 测试 Gemini API 的流式生成功能
 */

import { createMockStream, StreamProgressTracker } from '../lib/api/utils/streaming';

// 模拟测试文本
const testText = `你敢信？这个穷小子竟然是豪门继承人！

他一巴掌扇了过去，全场震惊。女主跪地痛哭，情感爆发。

这个反转太刺激了！`;

// 格式化流式输出
function formatStreamOutput(chunk: { text: string; done: boolean; index: number }) {
  const timestamp = new Date().toISOString().split('T')[1].slice(0, 12);
  const status = chunk.done ? '✅' : '⏳';

  console.log(`[${timestamp}] ${status} Chunk #${chunk.index}: "${chunk.text}"`);

  if (chunk.done) {
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  }
}

// 测试 1：基础流式响应
async function testBasicStreaming() {
  console.log('🧪 测试 1: 基础流式响应...\n');

  const tracker = new StreamProgressTracker();
  tracker.start();

  for await (const chunk of createMockStream(testText, 20, 50)) {
    tracker.update(chunk);
    formatStreamOutput(chunk);
  }

  const stats = tracker.getStats();
  console.log(`\n📊 统计信息:`);
  console.log(`   总块数: ${stats.chunksReceived}`);
  console.log(`   总字符数: ${stats.totalCharacters}`);
  console.log(`   总耗时: ${(stats.elapsedMs / 1000).toFixed(2)}s`);
  console.log(`   速率: ${stats.chunksPerSecond} chunks/s\n`);
}

// 测试 2：实时打字效果
async function testTypewriterEffect() {
  console.log('🧪 测试 2: 实时打字效果...\n');

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('生成的文案：');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  process.stdout.write('   ');

  for await (const chunk of createMockStream(testText, 5, 30)) {
    process.stdout.write(chunk.text);

    if (chunk.done) {
      process.stdout.write('\n');
    }
  }

  console.log('\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
}

// 测试 3：不同块大小对比
async function testDifferentChunkSizes() {
  console.log('🧪 测试 3: 不同块大小对比...\n');

  const chunkSizes = [10, 20, 50];

  for (const chunkSize of chunkSizes) {
    console.log(`\n块大小: ${chunkSize} 字符`);
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    const startTime = Date.now();
    let chunkCount = 0;

    for await (const chunk of createMockStream(testText, chunkSize, 20)) {
      chunkCount++;
    }

    const elapsed = Date.now() - startTime;
    console.log(`   块数: ${chunkCount}`);
    console.log(`   耗时: ${elapsed}ms\n`);
  }
}

// 测试 4：流式进度模拟
async function testProgressSimulation() {
  console.log('🧪 测试 4: 流式进度模拟...\n');

  const tracker = new StreamProgressTracker();
  tracker.start();

  console.log('生成进度:');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  for await (const chunk of createMockStream(testText, 30, 40)) {
    tracker.update(chunk);
    const stats = tracker.getStats();

    const progress = Math.min(100, Math.round((stats.totalCharacters / testText.length) * 100));

    // 进度条
    const barLength = 40;
    const filledLength = Math.round((progress / 100) * barLength);
    const bar = '█'.repeat(filledLength) + '░'.repeat(barLength - filledLength);

    process.stdout.write(`\r   [${bar}] ${progress}%`);
  }

  console.log('\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
}

// 测试 5：错误处理
async function testErrorHandling() {
  console.log('🧪 测试 5: 错误处理...\n');

  try {
    // 模拟中途出错
    let index = 0;
    const errorStream = async function* () {
      const chunks = ['这是', '一个', '测试'];
      for (const chunk of chunks) {
        yield { text: chunk, done: false, index: index++ };

        if (index === 2) {
          throw new Error('模拟网络错误');
        }
      }
    };

    for await (const chunk of errorStream()) {
      console.log(`   收到: ${chunk.text}`);
    }
  } catch (error) {
    console.log(`\n✅ 捕获到错误: ${(error as Error).message}`);
  }

  console.log('');
}

// 主函数
async function main() {
  console.log('╔═══════════════════════════════════════════════════════════════╗');
  console.log('║              API 流式响应 - 测试与演示                        ║');
  console.log('╚═══════════════════════════════════════════════════════════════╝\n');

  await testBasicStreaming();
  await testTypewriterEffect();
  await testDifferentChunkSizes();
  await testProgressSimulation();
  await testErrorHandling();

  console.log('========================================');
  console.log('✅ 流式响应测试完成');
  console.log('========================================\n');

  console.log('💡 功能特性:');
  console.log('   1. Server-Sent Events (SSE) 支持');
  console.log('   2. 实时进度推送');
  console.log('   3. 打字机效果');
  console.log('   4. 错误处理和重试');
  console.log('   5. 进度跟踪和统计');
  console.log('');

  console.log('📋 使用方法:');
  console.log('   前端可以使用 EventSource 接收流式数据:');
  console.log('');
  console.log('   const eventSource = new EventSource(');
  console.log('     "/api/gemini/generate-narration-stream"');
  console.log('   );');
  console.log('');
  console.log('   eventSource.addEventListener("message", (e) => {');
  console.log('     const chunk = JSON.parse(e.data);');
  console.log('     console.log(chunk.text);');
  console.log('   });');
  console.log('');

  process.exit(0);
}

main().catch((error) => {
  console.error('❌ 测试失败:', error);
  process.exit(1);
});
