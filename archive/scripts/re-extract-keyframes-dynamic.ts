// ============================================
// 使用动态间隔重新提取关键帧
// 固定 30 帧，根据视频时长自动计算间隔
// ============================================

import { extractKeyframes } from '../lib/video/keyframes';
import { join } from 'path';
import { dbClient } from '../lib/db/client';
import { queries } from '../lib/db';

async function main() {
  console.log('🚀 使用动态间隔重新提取关键帧...\n');
  console.log('策略：固定 30 帧，根据视频时长自动计算间隔\n');

  // 获取需要重新提取的视频
  const sqlite = dbClient.getSqlite();
  if (!sqlite) {
    console.error('❌ 无法获取数据库连接');
    process.exit(1);
  }

  const videos = sqlite.prepare(`
    SELECT id, file_path, filename, duration_ms
    FROM videos
    WHERE id IN (11, 12, 13, 14, 15, 16, 17)
    ORDER BY id
  `).all() as any[];

  console.log(`📋 找到 ${videos.length} 个需要重新提取的视频\n`);

  for (const video of videos) {
    console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    console.log(`🎬 处理视频 ${video.id}: ${video.filename}`);
    console.log(`   时长: ${(video.duration_ms / 1000).toFixed(1)}秒`);
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);

    try {
      // 提取关键帧（固定 30 帧，动态间隔）
      console.log(`  📸 提取关键帧（固定 30 帧，动态间隔）...`);

      const result = await extractKeyframes({
        videoPath: video.file_path,
        outputDir: join(process.cwd(), 'public', 'keyframes', video.id.toString()),
        frameCount: 30,  // ✅ 固定 30 帧
        filenamePrefix: `video_${video.id}_keyframe`,
      });

      // 计算实际间隔
      const actualInterval = video.duration_ms / (result.framePaths.length + 1);

      console.log(`  ✅ 提取了 ${result.framePaths.length} 帧`);
      console.log(`  📊 实际间隔: ${(actualInterval / 1000).toFixed(2)}秒`);

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

  // 显示统计
  console.log('📊 提取统计：');
  const stats = sqlite.prepare(`
    SELECT
      video_id,
      COUNT(*) as frame_count,
      MIN(timestamp_ms) as first_frame,
      MAX(timestamp_ms) as last_frame,
      ROUND((MAX(timestamp_ms) - MIN(timestamp_ms)) / 1000.0 / COUNT(*), 2) as avg_interval
    FROM keyframes
    WHERE video_id IN (11, 12, 13, 14, 15, 16, 17)
    GROUP BY video_id
    ORDER BY video_id
  `).all();

  stats.forEach((stat: any) => {
    console.log(`  视频 ${stat.video_id}: ${stat.frame_count} 帧, 平均间隔 ${stat.avg_interval}秒`);
  });

  process.exit(0);
}

main().catch((error) => {
  console.error('❌ 脚本执行失败:', error);
  process.exit(1);
});
