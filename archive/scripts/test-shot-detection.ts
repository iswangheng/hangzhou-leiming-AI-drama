#!/usr/bin/env node

/**
 * 镜头检测测试脚本
 *
 * 用途: 测试 detectShots 函数是否正常工作
 * 使用: npx tsx scripts/test-shot-detection.ts <视频文件路径>
 */

import { detectShots } from '../lib/video/shot-detection';
import { existsSync } from 'fs';

async function main() {
  const videoPath = process.argv[2];

  if (!videoPath) {
    console.error('❌ 请提供视频文件路径');
    console.log('\n使用方法:');
    console.log('  npx tsx scripts/test-shot-detection.ts <视频文件路径>');
    console.log('\n示例:');
    console.log('  npx tsx scripts/test-shot-detection.ts ./test.mp4');
    console.log('\n选项:');
    console.log('  --min-duration 2000     最小镜头时长（毫秒）');
    console.log('  --threshold 0.3          场景切换阈值');
    console.log('  --no-thumbnails          不生成缩略图');
    process.exit(1);
  }

  if (!existsSync(videoPath)) {
    console.error('❌ 视频文件不存在:', videoPath);
    process.exit(1);
  }

  try {
    console.log('🎬 开始检测镜头...');
    console.log('📹 视频:', videoPath);
    console.log('');

    // 解析选项
    const minDuration = getArgValue('--min-duration', 2000);
    const threshold = getArgValue('--threshold', 0.3);
    const noThumbnails = process.argv.includes('--no-thumbnails');

    console.log('⚙️  配置:');
    console.log(`  最小镜头时长: ${minDuration}ms`);
    console.log(`  场景切换阈值: ${threshold}`);
    console.log(`  生成缩略图: ${!noThumbnails ? '是' : '否'}`);
    console.log('');

    // 检测镜头
    const shots = await detectShots(videoPath, {
      minShotDuration: minDuration,
      generateThumbnails: !noThumbnails,
      threshold: threshold
    });

    console.log('');
    console.log('📊 检测结果:');
    console.log(`  总镜头数: ${shots.length}`);
    console.log('');

    // 显示每个镜头的详细信息
    shots.forEach((shot, index) => {
      const duration = shot.endMs - shot.startMs;
      const durationSec = (duration / 1000).toFixed(2);

      console.log(`镜头 ${index + 1}:`);
      console.log(`  时间: ${msToTime(shot.startMs)} - ${msToTime(shot.endMs)}`);
      console.log(`  时长: ${durationSec}秒`);
      console.log(`  缩略图: ${shot.thumbnailPath || '未生成'}`);
      console.log('');
    });

    // 统计信息
    const totalDuration = shots.reduce((sum, shot) => sum + (shot.endMs - shot.startMs), 0);
    const avgDuration = totalDuration / shots.length;

    console.log('📈 统计信息:');
    console.log(`  总时长: ${(totalDuration / 1000).toFixed(2)}秒`);
    console.log(`  平均时长: ${(avgDuration / 1000).toFixed(2)}秒`);
    console.log(`  最长镜头: ${(Math.max(...shots.map(s => s.endMs - s.startMs)) / 1000).toFixed(2)}秒`);
    console.log(`  最短镜头: ${(Math.min(...shots.map(s => s.endMs - s.startMs)) / 1000).toFixed(2)}秒`);
    console.log('');

    console.log('✅ 检测完成!');
    console.log('');
    console.log('💡 下一步:');
    console.log('  1. 查看生成的缩略图');
    console.log('  2. 使用 Agent 2 的 Gemini API 分析镜头');
    console.log('  3. 存入数据库（需要 Agent 4 添加 thumbnailPath 字段）');

    process.exit(0);
  } catch (error) {
    console.error('❌ 错误:', error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

/**
 * 从命令行参数获取值
 */
function getArgValue(argName: string, defaultValue: any): any {
  const index = process.argv.indexOf(argName);
  if (index === -1 || index + 1 >= process.argv.length) {
    return defaultValue;
  }

  const value = process.argv[index + 1];
  if (isNaN(Number(value))) {
    return value;
  }

  return Number(value);
}

/**
 * 将毫秒转换为 HH:MM:SS.mmm 格式
 */
function msToTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const milliseconds = ms % 1000;

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(milliseconds).padStart(3, '0')}`;
}

main();
