#!/usr/bin/env node

/**
 * 视频拼接测试脚本
 *
 * 用途: 测试 concatVideos 函数
 * 使用: npx tsx scripts/test-concat.ts <视频文件路径1> <视频文件路径2> ...
 *
 * @example
 * # 简单拼接两个视频
 * npx tsx scripts/test-concat.ts ./segment1.mp4 ./segment2.mp4
 *
 * # 拼接三个视频并使用淡入淡出转场
 * npx tsx scripts/test-concat.ts ./seg1.mp4 ./seg2.mp4 ./seg3.mp4 --transition fade
 *
 * # 指定输出分辨率和帧率
 * npx tsx scripts/test-concat.ts ./seg1.mp4 ./seg2.mp4 --width 1280 --height 720 --fps 30
 */

import { existsSync } from 'fs';
import { concatVideos } from '../lib/ffmpeg/concat';

interface TestOptions {
  segments: string[];
  outputPath: string;
  transition: null | 'fade' | 'crossfade';
  transitionDurationMs: number;
  width: number;
  height: number;
  fps: number;
  crf: number;
  preset: string;
}

function parseArgs(): TestOptions {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error('❌ 请提供至少两个视频文件路径');
    console.log('\n使用方法:');
    console.log('  npx tsx scripts/test-concat.ts <视频1> <视频2> [视频3...] [选项]');
    console.log('\n选项:');
    console.log('  --transition <type>    - 转场类型 (null|fade|crossfade，默认 null)');
    console.log('  --transition-duration  - 转场持续时间（毫秒，默认 500）');
    console.log('  --width <pixels>       - 输出宽度（默认 1920）');
    console.log('  --height <pixels>      - 输出高度（默认 1080）');
    console.log('  --fps <framerate>      - 输出帧率（默认 30）');
    console.log('  --crf <quality>        - CRF 质量（默认 18）');
    console.log('  --preset <speed>       - 编码预设（默认 fast）');
    console.log('\n示例:');
    console.log('  # 简单拼接');
    console.log('  npx tsx scripts/test-concat.ts ./seg1.mp4 ./seg2.mp4');
    console.log('');
    console.log('  # 带淡入淡出转场');
    console.log('  npx tsx scripts/test-concat.ts ./seg1.mp4 ./seg2.mp4 --transition fade');
    console.log('');
    console.log('  # 指定分辨率');
    console.log('  npx tsx scripts/test-concat.ts ./seg1.mp4 ./seg2.mp4 --width 1280 --height 720');
    process.exit(1);
  }

  const options: TestOptions = {
    segments: [],
    outputPath: '',
    transition: null,
    transitionDurationMs: 500,
    width: 1920,
    height: 1080,
    fps: 30,
    crf: 18,
    preset: 'fast',
  };

  let i = 0;
  while (i < args.length) {
    const arg = args[i];

    if (arg === '--transition') {
      const transitionValue = args[i + 1];
      options.transition = (transitionValue === 'null' ? null : (transitionValue as 'fade' | 'crossfade')) || 'fade';
      i += 2;
    } else if (arg === '--transition-duration') {
      options.transitionDurationMs = parseInt(args[i + 1]) || 500;
      i += 2;
    } else if (arg === '--width') {
      options.width = parseInt(args[i + 1]) || 1920;
      i += 2;
    } else if (arg === '--height') {
      options.height = parseInt(args[i + 1]) || 1080;
      i += 2;
    } else if (arg === '--fps') {
      options.fps = parseInt(args[i + 1]) || 30;
      i += 2;
    } else if (arg === '--crf') {
      options.crf = parseInt(args[i + 1]) || 18;
      i += 2;
    } else if (arg === '--preset') {
      options.preset = args[i + 1] || 'fast';
      i += 2;
    } else {
      // 假设是视频文件路径
      options.segments.push(arg);
      i++;
    }
  }

  if (options.segments.length < 2) {
    console.error('❌ 请提供至少两个视频文件路径');
    process.exit(1);
  }

  options.outputPath = `./test-concat/${Date.now()}/output.mp4`;

  return options;
}

async function main() {
  console.log('🧪 视频拼接测试\n');

  const options = parseArgs();

  console.log('配置:');
  console.log(`  片段数量: ${options.segments.length}`);
  console.log(`  片段列表:`);
  options.segments.forEach((seg, index) => {
    console.log(`    ${index + 1}. ${seg}`);
  });
  console.log(`  转场效果: ${options.transition || '无'}`);
  if (options.transition) {
    console.log(`  转场时长: ${options.transitionDurationMs}ms`);
  }
  console.log(`  输出分辨率: ${options.width}x${options.height}`);
  console.log(`  输出帧率: ${options.fps} fps`);
  console.log(`  CRF 质量: ${options.crf}`);
  console.log(`  编码预设: ${options.preset}`);
  console.log(`  输出路径: ${options.outputPath}\n`);

  // 验证所有文件存在
  for (const seg of options.segments) {
    if (!existsSync(seg)) {
      console.error(`❌ 视频文件不存在: ${seg}`);
      process.exit(1);
    }
  }

  // 创建输出目录
  const { dirname } = await import('path');
  const { promises } = await import('fs');
  await promises.mkdir(dirname(options.outputPath), { recursive: true });

  try {
    const startTime = Date.now();

    // 执行拼接
    const result = await concatVideos({
      segments: options.segments.map((path) => ({ path })),
      outputPath: options.outputPath,
      transition: options.transition,
      transitionDurationMs: options.transitionDurationMs,
      width: options.width,
      height: options.height,
      fps: options.fps,
      crf: options.crf,
      preset: options.preset,
      onProgress: (progress, currentTime, totalTime) => {
        const bar = '█'.repeat(Math.floor(progress / 2)) + '░'.repeat(50 - Math.floor(progress / 2));
        process.stdout.write(`\r[${bar}] ${progress.toFixed(1)}% (${currentTime.toFixed(1)}s / ${totalTime.toFixed(1)}s)`);
      },
    });

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);

    console.log(`\n\n✅ 测试成功！`);
    console.log(`⏱️  耗时: ${duration}秒`);
    console.log(`📊 结果统计:`);
    console.log(`   - 输出文件: ${result.outputPath}`);
    console.log(`   - 文件大小: ${(result.size / 1024 / 1024).toFixed(2)} MB`);
    console.log(`   - 拼接片段: ${result.segmentCount} 个`);
    console.log(`\n💡 提示: 你可以使用此功能将多个短剧片段合并为完整剧集`);
    console.log(`\n📁 输出文件: ${result.outputPath}`);

    process.exit(0);
  } catch (error) {
    console.error('\n❌ 测试失败:', error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

main();
