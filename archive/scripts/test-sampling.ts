#!/usr/bin/env node

/**
 * 关键帧采样测试脚本
 *
 * 用途: 测试 sampleKeyFrames 函数
 * 使用: npx tsx scripts/test-sampling.ts <视频文件路径> [采样策略]
 *
 * @example
 * # 均匀采样 30 帧（默认）
 * npx tsx scripts/test-sampling.ts ./test.mp4
 *
 * # 均匀采样 50 帧
 * npx tsx scripts/test-sampling.ts ./test.mp4 uniform 50
 *
 * # 基于场景采样 50 帧
 * npx tsx scripts/test-sampling.ts ./test.mp4 scene-based 50
 */

import { sampleKeyFrames } from '../lib/video/sampling';
import { existsSync } from 'fs';

interface TestOptions {
  videoPath: string;
  strategy: 'uniform' | 'scene-based';
  frameCount: number;
  outputDir: string;
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error('❌ 请提供视频文件路径');
    console.log('\n使用方法:');
    console.log('  npx tsx scripts/test-sampling.ts <视频文件路径> [策略] [帧数]');
    console.log('\n策略:');
    console.log('  uniform (默认) - 均匀采样');
    console.log('  scene-based     - 基于场景采样');
    console.log('\n示例:');
    console.log('  # 均匀采样 30 帧（默认）');
    console.log('  npx tsx scripts/test-sampling.ts ./test.mp4');
    console.log('');
    console.log('  # 均匀采样 50 帧');
    console.log('  npx tsx scripts/test-sampling.ts ./test.mp4 uniform 50');
    console.log('');
    console.log('  # 基于场景采样 50 帧');
    console.log('  npx tsx scripts/test-sampling.ts ./test.mp4 scene-based 50');
    process.exit(1);
  }

  const videoPath = args[0];
  const strategy = (args[1] as 'uniform' | 'scene-based') || 'uniform';
  const frameCount = parseInt(args[2]) || 30;

  const options: TestOptions = {
    videoPath,
    strategy,
    frameCount,
    outputDir: `./test-frames/${Date.now()}`
  };

  console.log('🧪 关键帧采样测试\n');
  console.log('配置:');
  console.log(`  视频: ${videoPath}`);
  console.log(`  策略: ${strategy}`);
  console.log(`  帧数: ${frameCount}`);
  console.log(`  输出目录: ${options.outputDir}\n`);

  // 验证文件存在
  if (!existsSync(videoPath)) {
    console.error(`❌ 视频文件不存在: ${videoPath}`);
    process.exit(1);
  }

  try {
    const startTime = Date.now();

    // 执行采样
    const result = await sampleKeyFrames(options);

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);

    console.log('\n✅ 测试成功！');
    console.log(`⏱️  耗时: ${duration}秒`);
    console.log(`📊 采样统计:`);
    console.log(`   - 总帧数: ${result.totalFrames}`);
    console.log(`   - 策略: ${result.strategy}`);
    console.log(`   - 输出目录: ${result.outputDir}`);
    console.log(`\n📁 采样帧文件:`);

    // 显示前 5 个和后 5 个文件
    const displayFrames = result.frames.slice(0, 5);
    if (result.frames.length > 10) {
      displayFrames.push('...');
      displayFrames.push(...result.frames.slice(-5));
    }

    displayFrames.forEach((frame, index) => {
      const prefix = index === 0 ? '  ' : '     ';
      console.log(`${prefix}${index + 1}. ${frame}`);
    });

    if (result.frames.length > 10) {
      console.log(`     ... 还有 ${result.frames.length - 10} 帧`);
    }

    console.log(`\n💡 提示: 你可以使用这些帧作为 Gemini 视频分析的输入素材`);

    process.exit(0);
  } catch (error) {
    console.error('\n❌ 测试失败:', error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

main();
