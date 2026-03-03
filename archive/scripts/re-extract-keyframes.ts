// ============================================
// 重新提取关键帧脚本
// 用于修复使用了错误采样间隔的关键帧
// ============================================

import { extractKeyframes } from '../lib/video/keyframes';
import { join } from 'path';
import { dbClient } from '../lib/db/client';
import { queries } from '../lib/db';

async function main() {
  console.log('🚀 开始重新提取关键帧...\n');

  // 获取需要重新提取的视频
  const sqlite = dbClient.getSqlite();
  if (!sqlite) {
    console.error('❌ 无法获取数据库连接');
    process.exit(1);
  }

  const videos = sqlite.prepare(`
    SELECT id, file_path, filename
    FROM videos
    WHERE id IN (12, 13, 14, 15, 16, 17)
    ORDER BY id
  `).all() as any[];

  console.log(`📋 找到 ${videos.length} 个需要重新提取的视频\n`);

  for (const video of videos) {
    console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    console.log(`🎬 处理视频 ${video.id}: ${video.filename}`);
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);

    try {
      // 提取关键帧（使用正确的 3 秒间隔）
      console.log(`  📸 提取关键帧（每 3 秒一帧）...`);

      const result = await extractKeyframes({
        videoPath: video.file_path,
        outputDir: join(process.cwd(), 'public', 'keyframes', video.id.toString()),
        intervalSeconds: 3,
        filenamePrefix: `video_${video.id}_keyframe`,
      });

      console.log(`  ✅ 提取了 ${result.framePaths.length} 个关键帧`);

      // 保存到数据库
      const keyframeData = result.framePaths.map((framePath, index) => ({
        videoId: video.id,
        framePath,
        timestampMs: result.timestamps[index],
        frameNumber: index + 1,
        fileSize: 0,
      }));

      await queries.keyframe.createBatch(keyframeData);
      console.log(`  💾 保存了 ${keyframeData.length} 个关键帧到数据库`);

    } catch (error) {
      console.error(`  ❌ 视频 ${video.id} 处理失败:`, error);
    }
  }

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🎉 所有关键帧重新提取完成！');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  process.exit(0);
}

main().catch((error) => {
  console.error('❌ 脚本执行失败:', error);
  process.exit(1);
});
