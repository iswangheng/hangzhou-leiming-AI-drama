#!/usr/bin/env node

/**
 * 多片段组合测试脚本
 *
 * 用途: 测试 MultiClipComposition 组件和 renderMultiClipComposition 函数
 * 使用: npx tsx scripts/test-multiclip.ts <视频1> <视频2> [视频3...]
 *
 * @example
 * # 组合两个视频片段
 * npx tsx scripts/test-multiclip.ts ./clip1.mp4 ./clip2.mp4
 *
 * # 使用淡入淡出转场
 * npx tsx scripts/test-multiclip.ts ./clip1.mp4 ./clip2.mp4 --transition fade
 *
 * # 指定转场持续时间
 * npx tsx scripts/test-multiclip.ts ./clip1.mp4 ./clip2.mp4 --transition fade --transition-duration 1000
 */

import { existsSync } from 'fs';
import { renderMultiClipComposition } from '../lib/remotion/renderer';

interface TestOptions {
  clips: string[];
  outputPath: string;
  transition: 'none' | 'fade' | 'slide' | 'zoom';
  transitionDurationMs: number;
  width: number;
  height: number;
  fps: number;
  fontSize: number;
}

function parseArgs(): TestOptions {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error('❌ 请提供至少两个视频文件路径');
    console.log('\n使用方法:');
    console.log('  npx tsx scripts/test-multiclip.ts <视频1> <视频2> [视频3...] [选项]');
    console.log('\n选项:');
    console.log('  --transition <type>        - 转场类型 (none|fade|slide|zoom，默认 none)');
    console.log('  --transition-duration     - 转场持续时间（毫秒，默认 500）');
    console.log('  --width <pixels>          - 输出宽度（默认 1080）');
    console.log('  --height <pixels>         - 输出高度（默认 1920）');
    console.log('  --fps <framerate>         - 输出帧率（默认 30）');
    console.log('  --font-size <size>        - 字幕字体大小（默认 60）');
    console.log('\n示例:');
    console.log('  # 组合两个视频片段');
    console.log('  npx tsx scripts/test-multiclip.ts ./clip1.mp4 ./clip2.mp4');
    console.log('');
    console.log('  # 使用淡入淡出转场');
    console.log('  npx tsx scripts/test-multiclip.ts ./clip1.mp4 ./clip2.mp3 --transition fade');
    console.log('');
    console.log('  # 指定转场持续时间');
    console.log('  npx tsx scripts/test-multiclip.ts ./clip1.mp4 ./clip2.mp4 --transition fade --transition-duration 1000');
    process.exit(1);
  }

  const options: TestOptions = {
    clips: [],
    outputPath: `./test-multiclip/${Date.now()}/output.mp4`,
    transition: 'none',
    transitionDurationMs: 500,
    width: 1080,
    height: 1920,
    fps: 30,
    fontSize: 60,
  };

  let i = 0;
  while (i < args.length) {
    const arg = args[i];

    if (arg === '--transition') {
      options.transition = (args[i + 1] as 'none' | 'fade' | 'slide' | 'zoom') || 'fade';
      i += 2;
    } else if (arg === '--transition-duration') {
      options.transitionDurationMs = parseInt(args[i + 1]) || 500;
      i += 2;
    } else if (arg === '--width') {
      options.width = parseInt(args[i + 1]) || 1080;
      i += 2;
    } else if (arg === '--height') {
      options.height = parseInt(args[i + 1]) || 1920;
      i += 2;
    } else if (arg === '--fps') {
      options.fps = parseInt(args[i + 1]) || 30;
      i += 2;
    } else if (arg === '--font-size') {
      options.fontSize = parseInt(args[i + 1]) || 60;
      i += 2;
    } else {
      // 假设是视频文件路径
      options.clips.push(arg);
      i++;
    }
  }

  if (options.clips.length < 2) {
    console.error('❌ 请提供至少两个视频文件路径');
    process.exit(1);
  }

  return options;
}

async function main() {
  console.log('🧪 多片段组合测试\n');

  const options = parseArgs();

  console.log('配置:');
  console.log(`  片段数量: ${options.clips.length}`);
  console.log(`  片段列表:`);
  options.clips.forEach((clip, index) => {
    console.log(`    ${index + 1}. ${clip}`);
  });
  console.log(`  转场效果: ${options.transition}`);
  if (options.transition !== 'none') {
    console.log(`  转场时长: ${options.transitionDurationMs}ms`);
  }
  console.log(`  输出分辨率: ${options.width}x${options.height}`);
  console.log(`  输出帧率: ${options.fps} fps`);
  console.log(`  输出路径: ${options.outputPath}\n`);

  // 验证所有文件存在
  for (const clip of options.clips) {
    if (!existsSync(clip)) {
      console.error(`❌ 视频文件不存在: ${clip}`);
      process.exit(1);
    }
  }

  // 创建输出目录
  const { promises } = await import('fs');
  const { dirname } = await import('path');
  await promises.mkdir(dirname(options.outputPath), { recursive: true });

  try {
    const startTime = Date.now();

    // 执行渲染
    const result = await renderMultiClipComposition({
      clips: options.clips.map((src) => ({ src })),
      outputPath: options.outputPath,
      transition: options.transition,
      transitionDurationMs: options.transitionDurationMs,
      width: options.width,
      height: options.height,
      fps: options.fps,
      fontSize: options.fontSize,
      onProgress: (progress, renderedFrames, totalFrames, renderedDuration) => {
        const bar = '█'.repeat(Math.floor(progress / 2)) + '░'.repeat(50 - Math.floor(progress / 2));
        process.stdout.write(`\r[${bar}] ${progress.toFixed(1)}% (${renderedFrames}/${totalFrames} 帧, ${renderedDuration.toFixed(1)}s)`);
      },
    });

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);

    console.log(`\n\n✅ 测试成功！`);
    console.log(`⏱️  总耗时: ${duration}秒`);
    console.log(`📊 结果统计:`);
    console.log(`   - 输出文件: ${result.outputPath}`);
    console.log(`   - 文件大小: ${(result.size / 1024 / 1024).toFixed(2)} MB`);
    console.log(`   - 视频时长: ${result.duration.toFixed(2)} 秒`);
    console.log(`   - 总帧数: ${result.totalFrames} 帧`);
    console.log(`   - 渲染速度: ${(result.size / 1024 / 1024 / (result.renderTime / 1000)).toFixed(2)} MB/s`);
    console.log(`\n💡 提示: 多片段组合适用于模式 B 的解说视频生成`);
    console.log(`\n📁 输出文件: ${result.outputPath}`);

    process.exit(0);
  } catch (error) {
    console.error('\n❌ 测试失败:', error instanceof Error ? error.message : error);
    console.error('\n提示: 请确保已安装 @remotion/* 依赖:');
    console.error('  npm install @remotion/cli @remotion/renderer @remotion/bundler');
    process.exit(1);
  }
}

main();
