#!/usr/bin/env node

/**
 * FFmpeg 进度监控测试脚本
 *
 * 用途: 测试带进度监控的视频处理功能
 * 使用: npx tsx scripts/test-ffmpeg-progress.ts <视频文件路径>
 *
 * @example
 * # 测试视频裁剪进度
 * npx tsx scripts/test-ffmpeg-progress.ts ./test.mp4 trim
 *
 * # 测试音频混合进度
 * npx tsx scripts/test-ffmpeg-progress.ts ./test.mp4 mix
 *
 * # 测试帧率对齐进度
 * npx tsx scripts/test-ffmpeg-progress.ts ./test.mp4 normalize
 */

import { existsSync } from 'fs';
import { join } from 'path';
import { getMetadata } from '../lib/video/metadata';
import {
  trimVideoWithProgress,
  mixAudioWithProgress,
  normalizeFrameRateWithProgress,
} from '../lib/ffmpeg/progress';

interface TestOptions {
  videoPath: string;
  testType: 'trim' | 'mix' | 'normalize';
  outputDir: string;
}

async function testTrimProgress(videoPath: string, outputDir: string) {
  console.log('\n🎬 测试 1: 视频裁剪进度监控\n');

  const metadata = await getMetadata(videoPath);
  const outputPath = join(outputDir, 'trimmed.mp4');
  const startTimeMs = 5000; // 从第 5 秒开始
  const durationMs = 30000; // 裁剪 30 秒

  console.log(`原始视频时长: ${metadata.duration.toFixed(1)}秒`);
  console.log(`裁剪范围: ${startTimeMs / 1000}s - ${(startTimeMs + durationMs) / 1000}s`);
  console.log(`输出路径: ${outputPath}\n`);

  const startTime = Date.now();

  await trimVideoWithProgress({
    inputPath: videoPath,
    outputPath,
    startTimeMs,
    durationMs,
    crf: 18,
    preset: 'fast',
    totalDuration: metadata.duration,
    onProgress: (progress, currentTime, totalTime) => {
      const bar = '█'.repeat(Math.floor(progress / 2)) + '░'.repeat(50 - Math.floor(progress / 2));
      process.stdout.write(`\r[${bar}] ${progress.toFixed(1)}% (${currentTime.toFixed(1)}s / ${totalTime.toFixed(1)}s)`);
    },
  });

  const duration = ((Date.now() - startTime) / 1000).toFixed(2);
  console.log(`\n\n✅ 裁剪完成！耗时: ${duration}秒`);
}

async function testMixProgress(videoPath: string, outputDir: string) {
  console.log('\n🎵 测试 2: 音频混合进度监控\n');

  const metadata = await getMetadata(videoPath);
  const outputPath = join(outputDir, 'mixed.mp4');

  console.log(`视频路径: ${videoPath}`);
  console.log(`音频路径: ${videoPath} (使用原视频作为测试音频)`);
  console.log(`输出路径: ${outputPath}\n`);

  const startTime = Date.now();

  await mixAudioWithProgress({
    videoPath,
    audioPath: videoPath, // 测试用：使用原视频
    outputPath,
    videoVolume: 0.5,
    audioVolume: 0.5,
    totalDuration: metadata.duration,
    onProgress: (progress, currentTime, totalTime) => {
      const bar = '█'.repeat(Math.floor(progress / 2)) + '░'.repeat(50 - Math.floor(progress / 2));
      process.stdout.write(`\r[${bar}] ${progress.toFixed(1)}% (${currentTime.toFixed(1)}s / ${totalTime.toFixed(1)}s)`);
    },
  });

  const duration = ((Date.now() - startTime) / 1000).toFixed(2);
  console.log(`\n\n✅ 混合完成！耗时: ${duration}秒`);
}

async function testNormalizeProgress(videoPath: string, outputDir: string) {
  console.log('\n⚙️  测试 3: 帧率对齐进度监控\n');

  const metadata = await getMetadata(videoPath);
  const outputPath = join(outputDir, 'normalized.mp4');

  console.log(`原始帧率: ${metadata.fps} fps`);
  console.log(`目标帧率: 30 fps`);
  console.log(`输出路径: ${outputPath}\n`);

  const startTime = Date.now();

  await normalizeFrameRateWithProgress({
    inputPath: videoPath,
    outputPath,
    fps: 30,
    totalDuration: metadata.duration,
    onProgress: (progress, currentTime, totalTime) => {
      const bar = '█'.repeat(Math.floor(progress / 2)) + '░'.repeat(50 - Math.floor(progress / 2));
      process.stdout.write(`\r[${bar}] ${progress.toFixed(1)}% (${currentTime.toFixed(1)}s / ${totalTime.toFixed(1)}s)`);
    },
  });

  const duration = ((Date.now() - startTime) / 1000).toFixed(2);
  console.log(`\n\n✅ 对齐完成！耗时: ${duration}秒`);
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('❌ 请提供视频文件路径');
    console.log('\n使用方法:');
    console.log('  npx tsx scripts/test-ffmpeg-progress.ts <视频文件路径> [测试类型]');
    console.log('\n测试类型:');
    console.log('  trim (默认)      - 视频裁剪进度测试');
    console.log('  mix              - 音频混合进度测试');
    console.log('  normalize        - 帧率对齐进度测试');
    console.log('\n示例:');
    console.log('  # 测试视频裁剪进度');
    console.log('  npx tsx scripts/test-ffmpeg-progress.ts ./test.mp4 trim');
    console.log('');
    console.log('  # 测试音频混合进度');
    console.log('  npx tsx scripts/test-ffmpeg-progress.ts ./test.mp4 mix');
    console.log('');
    console.log('  # 测试帧率对齐进度');
    console.log('  npx tsx scripts/test-ffmpeg-progress.ts ./test.mp4 normalize');
    process.exit(1);
  }

  const videoPath = args[0];
  const testType = (args[1] as 'trim' | 'mix' | 'normalize') || 'trim';
  const outputDir = `./test-ffmpeg-progress/${Date.now()}`;

  console.log('🧪 FFmpeg 进度监控测试\n');
  console.log('配置:');
  console.log(`  视频: ${videoPath}`);
  console.log(`  测试类型: ${testType}`);
  console.log(`  输出目录: ${outputDir}`);

  // 验证文件存在
  if (!existsSync(videoPath)) {
    console.error(`\n❌ 视频文件不存在: ${videoPath}`);
    process.exit(1);
  }

  // 创建输出目录
  const { mkdirSync } = await import('fs');
  mkdirSync(outputDir, { recursive: true });

  try {
    switch (testType) {
      case 'trim':
        await testTrimProgress(videoPath, outputDir);
        break;
      case 'mix':
        await testMixProgress(videoPath, outputDir);
        break;
      case 'normalize':
        await testNormalizeProgress(videoPath, outputDir);
        break;
    }

    console.log(`\n📁 输出文件保存在: ${outputDir}`);
    console.log('\n💡 提示: 进度回调可用于 WebSocket 实时更新到 UI');
    process.exit(0);
  } catch (error) {
    console.error('\n❌ 测试失败:', error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

main();
