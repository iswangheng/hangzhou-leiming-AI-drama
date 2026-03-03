#!/usr/bin/env node

/**
 * Remotion 渲染客户端测试脚本
 *
 * 用途: 测试 renderRemotionVideo 和 renderCaptionedVideo 函数
 * 使用: npx tsx scripts/test-remotion-renderer.ts <视频文件路径> <字幕文件路径>
 *
 * @example
 * # 渲染带字幕的视频
 * npx tsx scripts/test-remotion-renderer.ts ./video.mp4 ./subtitles.json
 *
 * # 指定输出分辨率
 * npx tsx scripts/test-remotion-renderer.ts ./video.mp4 ./subtitles.json --width 1280 --height 720
 */

import { existsSync } from 'fs';
import { renderCaptionedVideo } from '../lib/remotion/renderer';

interface TestOptions {
  videoPath: string;
  subtitlesPath: string;
  outputPath: string;
  width: number;
  height: number;
  fps: number;
  fontSize: number;
  highlightColor: string;
}

function parseArgs(): TestOptions {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error('❌ 请提供视频文件路径和字幕文件路径');
    console.log('\n使用方法:');
    console.log('  npx tsx scripts/test-remotion-renderer.ts <视频文件路径> <字幕文件路径> [选项]');
    console.log('\n选项:');
    console.log('  --width <pixels>        - 输出宽度（默认 1080）');
    console.log('  --height <pixels>       - 输出高度（默认 1920）');
    console.log('  --fps <framerate>       - 输出帧率（默认 30）');
    console.log('  --font-size <size>      - 字幕字体大小（默认 60）');
    console.log('  --highlight-color <hex> - 高亮颜色（默认 #FFE600）');
    console.log('\n示例:');
    console.log('  # 渲染带字幕的视频');
    console.log('  npx tsx scripts/test-remotion-renderer.ts ./video.mp4 ./subtitles.json');
    console.log('');
    console.log('  # 指定输出分辨率');
    console.log('  npx tsx scripts/test-remotion-renderer.ts ./video.mp4 ./subtitles.json \\');
    console.log('    --width 1280 --height 720');
    process.exit(1);
  }

  const options: TestOptions = {
    videoPath: args[0],
    subtitlesPath: args[1],
    outputPath: `./test-remotion-renderer/${Date.now()}/output.mp4`,
    width: 1080,
    height: 1920,
    fps: 30,
    fontSize: 60,
    highlightColor: '#FFE600',
  };

  let i = 2;
  while (i < args.length) {
    const arg = args[i];

    if (arg === '--width') {
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
    } else if (arg === '--highlight-color') {
      options.highlightColor = args[i + 1] || '#FFE600';
      i += 2;
    } else {
      console.error(`❌ 未知选项: ${arg}`);
      process.exit(1);
    }
  }

  return options;
}

async function main() {
  console.log('🧪 Remotion 渲染客户端测试\n');

  const options = parseArgs();

  console.log('配置:');
  console.log(`  视频文件: ${options.videoPath}`);
  console.log(`  字幕文件: ${options.subtitlesPath}`);
  console.log(`  输出分辨率: ${options.width}x${options.height}`);
  console.log(`  输出帧率: ${options.fps} fps`);
  console.log(`  字幕字体: ${options.fontSize}px`);
  console.log(`  高亮颜色: ${options.highlightColor}`);
  console.log(`  输出路径: ${options.outputPath}\n`);

  // 验证视频文件存在
  if (!existsSync(options.videoPath)) {
    console.error(`❌ 视频文件不存在: ${options.videoPath}`);
    process.exit(1);
  }

  // 验证字幕文件存在
  if (!existsSync(options.subtitlesPath)) {
    console.error(`❌ 字幕文件不存在: ${options.subtitlesPath}`);
    process.exit(1);
  }

  // 读取字幕文件
  const { readFileSync } = await import('fs');
  let subtitles: any[] = [];

  try {
    const subtitleContent = readFileSync(options.subtitlesPath, 'utf-8');
    subtitles = JSON.parse(subtitleContent);
  } catch (error) {
    console.error(`❌ 解析字幕文件失败:`, error);
    process.exit(1);
  }

  console.log(`   字幕条目: ${subtitles.length} 条\n`);

  // 创建输出目录
  const { promises } = await import('fs');
  const { dirname } = await import('path');
  await promises.mkdir(dirname(options.outputPath), { recursive: true });

  try {
    const startTime = Date.now();

    // 执行渲染
    const result = await renderCaptionedVideo({
      videoPath: options.videoPath,
      subtitles,
      outputPath: options.outputPath,
      width: options.width,
      height: options.height,
      fps: options.fps,
      fontSize: options.fontSize,
      highlightColor: options.highlightColor,
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
    console.log(`\n💡 提示: Remotion 渲染客户端可以集成到 BullMQ 任务队列中`);
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
