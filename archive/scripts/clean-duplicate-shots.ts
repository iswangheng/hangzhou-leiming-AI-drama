// ============================================
// 清理重复的镜头数据（修复版）
// 按创建时间分组，只保留最早的一套完整镜头
// ============================================

import { dbClient } from '../lib/db/client';

async function main() {
  console.log('🧹 开始清理重复的镜头数据...\n');

  const sqlite = dbClient.getSqlite();
  if (!sqlite) {
    console.error('❌ 无法获取数据库连接');
    process.exit(1);
  }

  // 获取需要处理的视频 ID
  const videos = sqlite.prepare(`
    SELECT DISTINCT video_id
    FROM shots
    WHERE video_id IN (11, 12, 13, 14, 15, 16, 17)
    ORDER BY video_id
  `).all() as any[];

  console.log(`📋 找到 ${videos.length} 个视频需要清理\n`);

  let totalDeleted = 0;
  let totalKept = 0;

  for (const video of videos) {
    const videoId = video.video_id;

    // 获取该视频的所有镜头，按创建时间排序
    const shots = sqlite.prepare(`
      SELECT id, video_id, start_ms, end_ms, created_at
      FROM shots
      WHERE video_id = ?
      ORDER BY created_at, id
    `).all(videoId) as any[];

    if (shots.length === 0) {
      console.log(`  ⚠️  视频 ${videoId}: 没有镜头数据`);
      continue;
    }

    // 找出第一套镜头（最早创建时间）
    const firstCreatedAt = shots[0].created_at;

    // 只保留第一套镜头的所有记录
    const shotsToKeep = shots.filter(s => s.created_at === firstCreatedAt);
    const shotsToDelete = shots.filter(s => s.created_at !== firstCreatedAt);

    if (shotsToDelete.length > 0) {
      // 删除其他创建时间的镜头
      const idsToDelete = shotsToDelete.map(s => s.id);
      const placeholders = idsToDelete.map(() => '?').join(',');

      sqlite.prepare(`
        DELETE FROM shots
        WHERE id IN (${placeholders})
      `).run(...idsToDelete);

      console.log(`  ✅ 视频 ${videoId}: 保留 ${shotsToKeep.length} 个镜头（${new Date(firstCreatedAt * 1000).toLocaleTimeString('zh-CN')}）, 删除 ${shotsToDelete.length} 个重复镜头`);
      totalDeleted += shotsToDelete.length;
      totalKept += shotsToKeep.length;
    } else {
      console.log(`  ✅ 视频 ${videoId}: ${shots.length} 个镜头（无重复）`);
      totalKept += shots.length;
    }
  }

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🎉 清理完成！');
  console.log(`📊 统计: 保留 ${totalKept} 个镜头, 删除 ${totalDeleted} 个重复镜头`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  process.exit(0);
}

main().catch((error) => {
  console.error('❌ 脚本执行失败:', error);
  process.exit(1);
});
