// ============================================
// 重新检测项目2的视频镜头（使用修复后的代码）
// 修复问题：先删除旧镜头，再插入新镜头
// ============================================

import { detectShots } from '../lib/video/shot-detection';
import { join } from 'path';
import { dbClient } from '../lib/db/client';
import { queries } from '../lib/db';

async function main() {
  console.log('🎬 重新检测项目2的视频镜头...\n');
  console.log('✅ 已修复：先删除旧镜头，再插入新镜头（无重复）\n');

  // 获取项目2的所有视频
  const sqlite = dbClient.getSqlite();
  if (!sqlite) {
    console.error('❌ 无法获取数据库连接');
    process.exit(1);
  }

  const videos = sqlite.prepare(`
    SELECT id, file_path, filename, duration_ms
    FROM videos
    WHERE project_id = 2
    ORDER BY id
  `).all() as any[];

  console.log(`📋 找到 ${videos.length} 个视频需要重新检测\n`);

  for (const video of videos) {
    console.log(`\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    console.log(`🎬 处理视频 ${video.id}: ${video.filename}`);
    console.log(`   时长: ${(video.duration_ms / 1000).toFixed(1)}秒`);
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);

    try {
      // 删除旧镜头数据（使用修复后的方法）
      console.log(`  🗑️  删除旧镜头数据...`);
      await queries.shot.deleteByVideoId(video.id);

      // 检测镜头
      console.log(`  🔍 检测镜头（threshold=0.3, minDuration=2s）...`);

      const shots = await detectShots(video.file_path, {
        minShotDuration: 2000,  // 最小镜头时长 2 秒
        threshold: 0.3,         // 场景切换阈值
        generateThumbnails: false, // 不生成缩略图（节省空间）
      });

      console.log(`  ✅ 检测到 ${shots.length} 个镜头`);

      // 保存镜头到数据库
      const shotsData = shots.map((shot) => ({
        videoId: video.id,
        startMs: shot.startMs,
        endMs: shot.endMs,
        description: `镜头 ${(shot.startMs / 1000).toFixed(1)}-${(shot.endMs / 1000).toFixed(1)}秒`,
        emotion: 'neutral',
        viralScore: 5.0,
        startFrame: Math.floor((shot.startMs / 1000) * 30),
        endFrame: Math.floor((shot.endMs / 1000) * 30),
      }));

      await queries.shot.createMany(shotsData);
      console.log(`  💾 保存了 ${shotsData.length} 个镜头到数据库`);

    } catch (error) {
      console.error(`  ❌ 视频 ${video.id} 处理失败:`, error);
    }
  }

  console.log('\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🎉 所有的视频镜头重新检测完成！');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n');

  // 显示统计
  console.log('📊 检测统计：');
  const stats = sqlite.prepare(`
    SELECT
      video_id,
      COUNT(*) as shot_count,
      MIN(start_ms) as first_shot,
      MAX(end_ms) as last_shot,
      ROUND((MAX(end_ms) - MIN(start_ms)) / 1000.0 / COUNT(*), 2) as avg_duration
    FROM shots
    WHERE video_id IN (11, 12, 13, 14, 15, 16, 17)
    GROUP BY video_id
    ORDER BY video_id
  `).all();

  stats.forEach((stat: any) => {
    console.log(`  视频 ${stat.video_id}: ${stat.shot_count} 个镜头, 平均时长 ${stat.avg_duration}秒`);
  });

  process.exit(0);
}

main().catch((error) => {
  console.error('❌ 脚本执行失败:', error);
  process.exit(1);
});
