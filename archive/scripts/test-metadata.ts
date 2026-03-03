#!/usr/bin/env node

/**
 * 视频元数据提取测试脚本
 *
 * 用途: 测试 getMetadata 函数是否正常工作
 * 使用: npx tsx scripts/test-metadata.ts <视频文件路径>
 */

import { getMetadata, validateVideoMetadata, formatMetadata } from '../lib/video/metadata';

async function main() {
  const videoPath = process.argv[2];

  if (!videoPath) {
    console.error('❌ 请提供视频文件路径');
    console.log('\n使用方法:');
    console.log('  npx tsx scripts/test-metadata.ts <视频文件路径>');
    console.log('\n示例:');
    console.log('  npx tsx scripts/test-metadata.ts ./test.mp4');
    process.exit(1);
  }

  try {
    console.log('📹 正在分析视频:', videoPath);
    console.log('');

    // 获取元数据
    const metadata = await getMetadata(videoPath);

    // 格式化输出
    console.log(formatMetadata(metadata));
    console.log('');

    // 验证元数据
    const validation = validateVideoMetadata(metadata);

    if (validation.valid) {
      console.log('✅ 视频符合处理要求');
    } else {
      console.log('⚠️  视频验证警告:');
      validation.errors.forEach((error) => {
        console.log(`  - ${error}`);
      });
    }

    console.log('');
    console.log('📊 完整元数据 (JSON):');
    console.log(JSON.stringify(metadata, null, 2));

    process.exit(0);
  } catch (error) {
    console.error('❌ 错误:', error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

main();
