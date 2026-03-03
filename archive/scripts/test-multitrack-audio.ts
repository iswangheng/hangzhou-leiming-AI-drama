#!/usr/bin/env node

/**
 * 多轨道音频混合测试脚本
 *
 * 用途: 测试 mixAudioMultitrack 函数
 * 使用: npx tsx scripts/test-multitrack-audio.ts <视频文件路径> [选项]
 *
 * @example
 * # 三轨道混合（解说 + BGM + 音效）
 * npx tsx scripts/test-multitrack-audio.ts ./video.mp4 \
 *   --voiceover ./voiceover.mp3 \
 *   --bgm ./bgm.mp3 \
 *   --sfx ./sfx.mp3
 *
 * # 自定义音量
 * npx tsx scripts/test-multitrack-audio.ts ./video.mp4 \
 *   --voiceover ./voiceover.mp3 \
 *   --bgm ./bgm.mp3 \
 *   --voiceover-volume 0.8 \
 *   --bgm-volume 0.4
 */

import { existsSync } from 'fs';
import { createStandardMix, mixAudioMultitrack } from '../lib/ffmpeg/multitrack-audio';

interface TestOptions {
  videoPath: string;
  voiceoverPath?: string;
  bgmPath?: string;
  sfxPath?: string;
  voiceoverVolume: number;
  bgmVolume: number;
  sfxVolume: number;
  outputPath: string;
}

function parseArgs(): TestOptions {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('❌ 请提供视频文件路径');
    console.log('\n使用方法:');
    console.log('  npx tsx scripts/test-multitrack-audio.ts <视频文件路径> [选项]');
    console.log('\n选项:');
    console.log('  --voiceover <path>       - 解说配音文件路径');
    console.log('  --bgm <path>             - BGM 文件路径');
    console.log('  --sfx <path>             - 音效文件路径（可选）');
    console.log('  --voiceover-volume <0-1> - 解说音量（默认 1.0）');
    console.log('  --bgm-volume <0-1>       - BGM 音量（默认 0.3）');
    console.log('  --sfx-volume <0-1>       - 音效音量（默认 0.5）');
    console.log('\n示例:');
    console.log('  # 三轨道混合');
    console.log('  npx tsx scripts/test-multitrack-audio.ts ./video.mp4 \\');
    console.log('    --voiceover ./voiceover.mp3 \\');
    console.log('    --bgm ./bgm.mp3 \\');
    console.log('    --sfx ./sfx.mp3');
    console.log('');
    console.log('  # 自定义音量');
    console.log('  npx tsx scripts/test-multitrack-audio.ts ./video.mp4 \\');
    console.log('    --voiceover ./voiceover.mp3 \\');
    console.log('    --bgm ./bgm.mp3 \\');
    console.log('    --voiceover-volume 0.8 \\');
    console.log('    --bgm-volume 0.4');
    process.exit(1);
  }

  const options: TestOptions = {
    videoPath: args[0],
    voiceoverPath: undefined,
    bgmPath: undefined,
    sfxPath: undefined,
    voiceoverVolume: 1.0,
    bgmVolume: 0.3,
    sfxVolume: 0.5,
    outputPath: `./test-multitrack-audio/${Date.now()}/output.mp4`,
  };

  let i = 1;
  while (i < args.length) {
    const arg = args[i];

    if (arg === '--voiceover') {
      options.voiceoverPath = args[i + 1];
      i += 2;
    } else if (arg === '--bgm') {
      options.bgmPath = args[i + 1];
      i += 2;
    } else if (arg === '--sfx') {
      options.sfxPath = args[i + 1];
      i += 2;
    } else if (arg === '--voiceover-volume') {
      options.voiceoverVolume = parseFloat(args[i + 1]) || 1.0;
      i += 2;
    } else if (arg === '--bgm-volume') {
      options.bgmVolume = parseFloat(args[i + 1]) || 0.3;
      i += 2;
    } else if (arg === '--sfx-volume') {
      options.sfxVolume = parseFloat(args[i + 1]) || 0.5;
      i += 2;
    } else {
      console.error(`❌ 未知选项: ${arg}`);
      process.exit(1);
    }
  }

  return options;
}

async function main() {
  console.log('🧪 多轨道音频混合测试\n');

  const options = parseArgs();

  console.log('配置:');
  console.log(`  视频文件: ${options.videoPath}`);
  console.log(`  解说配音: ${options.voiceoverPath || '未指定'}`);
  console.log(`  BGM: ${options.bgmPath || '未指定'}`);
  console.log(`  音效: ${options.sfxPath || '未指定'}`);
  console.log(`\n  音量设置:`);
  console.log(`    解说: ${(options.voiceoverVolume * 100).toFixed(0)}%`);
  console.log(`    原音: 15% (固定)`);
  console.log(`    BGM: ${(options.bgmVolume * 100).toFixed(0)}%`);
  if (options.sfxPath) {
    console.log(`    音效: ${(options.sfxVolume * 100).toFixed(0)}%`);
  }
  console.log(`  输出路径: ${options.outputPath}\n`);

  // 验证视频文件存在
  if (!existsSync(options.videoPath)) {
    console.error(`❌ 视频文件不存在: ${options.videoPath}`);
    process.exit(1);
  }

  // 验证必需的音频文件
  if (!options.voiceoverPath || !existsSync(options.voiceoverPath)) {
    console.error('❌ 请提供有效的解说配音文件 (--voiceover)');
    process.exit(1);
  }

  if (!options.bgmPath || !existsSync(options.bgmPath)) {
    console.error('❌ 请提供有效的 BGM 文件 (--bgm)');
    process.exit(1);
  }

  if (options.sfxPath && !existsSync(options.sfxPath)) {
    console.error(`❌ 音效文件不存在: ${options.sfxPath}`);
    process.exit(1);
  }

  // 创建输出目录
  const { promises } = await import('fs');
  const { dirname } = await import('path');
  await promises.mkdir(dirname(options.outputPath), { recursive: true });

  try {
    const startTime = Date.now();

    // 执行混合
    const result = await createStandardMix({
      videoPath: options.videoPath,
      voiceoverPath: options.voiceoverPath,
      bgmPath: options.bgmPath,
      sfxPath: options.sfxPath,
      outputPath: options.outputPath,
      voiceoverVolume: options.voiceoverVolume,
      bgmVolume: options.bgmVolume,
      sfxVolume: options.sfxVolume,
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
    console.log(`   - 混合轨道: ${result.trackCount} 个`);
    console.log(`\n💡 提示: 四轨道混音适用于深度解说视频，可同时播放解说、原音、BGM 和音效`);
    console.log(`\n📁 输出文件: ${result.outputPath}`);

    process.exit(0);
  } catch (error) {
    console.error('\n❌ 测试失败:', error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

main();
