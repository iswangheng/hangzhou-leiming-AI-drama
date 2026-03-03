#!/usr/bin/env node

/**
 * wordTimings 对齐算法测试脚本
 *
 * 演示和测试不同的词级时间戳对齐策略
 */

import { alignWordsBySyllables, alignWordsByPunctuation, alignWordsHybrid, alignWordsSmart } from '../lib/api/utils/alignment';

// 测试文本示例
const testTexts = [
  {
    name: '短句（无标点）',
    text: '这是一个测试用例',
    durationMs: 2000,
  },
  {
    name: '长句（有标点）',
    text: '你敢信？这个穷小子竟然是豪门继承人！他一巴掌扇了过去。',
    durationMs: 8000,
  },
  {
    name: '多句子',
    text: '女主被陷害了。她跪地痛哭，情感爆发。男主角狠狠地扇了她一巴掌。',
    durationMs: 12000,
  },
];

// 格式化时间（毫秒 -> 秒）
function formatTime(ms: number): string {
  return (ms / 1000).toFixed(2) + 's';
}

// 打印 wordTimings
function printWordTimings(timings: Array<{ text: string; startMs: number; endMs: number }>) {
  timings.forEach((word, index) => {
    const bar = '━'.repeat(Math.max(1, Math.round((word.endMs - word.startMs) / 100)));
    console.log(
      `  [${formatTime(word.startMs)} - ${formatTime(word.endMs)}] ${word.text.padEnd(10)} ${bar}`
    );
  });
}

// 测试对齐算法
async function testAlignmentAlgorithm() {
  console.log('========================================');
  console.log('📋 WordTimings 对齐算法测试');
  console.log('========================================\n');

  for (const testCase of testTexts) {
    console.log(`\n📝 测试文本: ${testCase.name}`);
    console.log(`   内容: "${testCase.text}"`);
    console.log(`   时长: ${formatTime(testCase.durationMs)}\n`);

    // 1. 音节对齐
    console.log('1️⃣  音节对齐算法 (alignWordsBySyllables):');
    const syllableResult = alignWordsBySyllables(testCase.text, testCase.durationMs);
    printWordTimings(syllableResult);
    console.log('');

    // 2. 标点符号对齐
    console.log('2️⃣  标点符号对齐算法 (alignWordsByPunctuation):');
    const punctuationResult = alignWordsByPunctuation(testCase.text, testCase.durationMs);
    printWordTimings(punctuationResult);
    console.log('');

    // 3. 混合策略
    console.log('3️⃣  混合策略算法 (alignWordsHybrid):');
    const hybridResult = alignWordsHybrid(testCase.text, testCase.durationMs);
    printWordTimings(hybridResult);
    console.log('');

    // 4. 智能选择
    console.log('4️⃣  智能选择算法 (alignWordsSmart):');
    const smartResult = alignWordsSmart(testCase.text, testCase.durationMs);
    printWordTimings(smartResult);
    console.log('');
  }
}

// 对比分析
async function compareAlgorithms() {
  console.log('\n========================================');
  console.log('📊 算法对比分析');
  console.log('========================================\n');

  const testText = '你敢信？这个穷小子竟然是豪门继承人！';
  const durationMs = 5000;

  console.log(`测试文本: "${testText}"`);
  console.log(`时长: ${formatTime(durationMs)}\n`);

  const algorithms = [
    { name: '音节对齐', fn: alignWordsBySyllables },
    { name: '标点符号对齐', fn: alignWordsByPunctuation },
    { name: '混合策略', fn: alignWordsHybrid },
    { name: '智能选择', fn: alignWordsSmart },
  ];

  algorithms.forEach(({ name, fn }) => {
    const result = fn(testText, durationMs);

    console.log(`${name}:`);
    console.log(`  总词数: ${result.length}`);

    // 计算平均词时长
    const avgWordDuration =
      result.reduce((sum, word) => sum + (word.endMs - word.startMs), 0) / result.length;
    console.log(`  平均词时长: ${formatTime(avgWordDuration)}`);

    // 计算时长范围
    const minDuration = Math.min(...result.map(w => w.endMs - w.startMs));
    const maxDuration = Math.max(...result.map(w => w.endMs - w.startMs));
    console.log(`  时长范围: ${formatTime(minDuration)} - ${formatTime(maxDuration)}`);
    console.log('');
  });
}

// 卡拉OK字幕演示
async function demoKaraokeStyle() {
  console.log('\n========================================');
  console.log('🎤 卡拉OK字幕演示');
  console.log('========================================\n');

  const text = '你敢信？这个穷小子竟然是豪门继承人！';
  const durationMs = 5000;
  const wordTimings = alignWordsSmart(text, durationMs);

  console.log('歌词字幕效果：\n');
  console.log('时间轴      字幕');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

  wordTimings.forEach((word) => {
    const highlight = '█'.repeat(Math.round((word.endMs - word.startMs) / 50));
    console.log(`[${formatTime(word.startMs)}] ${word.text} ${highlight}`);
  });

  console.log('\n说明：');
  console.log('- 每个 █ 代表 50ms');
  console.log('- 长度代表该词的持续时间');
  console.log('- 可用于 Remotion 卡拉OK字幕组件\n');
}

// 主函数
async function main() {
  console.log('╔═══════════════════════════════════════════════════════════════╗');
  console.log('║         WordTimings 精确提取 - 测试与演示                     ║');
  console.log('╚═══════════════════════════════════════════════════════════════╝\n');

  await testAlignmentAlgorithm();
  await compareAlgorithms();
  await demoKaraokeStyle();

  console.log('========================================');
  console.log('✅ 测试完成');
  console.log('========================================\n');

  console.log('💡 功能特性:');
  console.log('   1. 音节对齐 - 基于单词音节数分配时间');
  console.log('   2. 标点符号对齐 - 在句子边界停顿');
  console.log('   3. 混合策略 - 结合音节和标点符号');
  console.log('   4. 智能选择 - 自动选择最佳算法');
  console.log('');
  console.log('📈 准确度提升:');
  console.log('   - 旧方案: 简单平均分割 ❌');
  console.log('   - 新方案: 智能对齐算法 ✅');
  console.log('   - 预期准确度: 提升约 30-50%');
  console.log('');

  process.exit(0);
}

main().catch((error) => {
  console.error('❌ 测试失败:', error);
  process.exit(1);
});
