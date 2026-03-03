/**
 * 清理无效的标记数据
 *
 * 删除超出视频时长的标记点
 */

import { db } from '../lib/db/client';
import { hlMarkings, hlVideos } from '../lib/db/schema';
import { eq, sql } from 'drizzle-orm';

async function cleanInvalidMarkings() {
  try {
    console.log('🔧 开始清理无效标记...\n');

    // 查找所有无效的标记（超出视频时长）
    const invalidMarkings = await db
      .select({
        id: hlMarkings.id,
        seconds: hlMarkings.seconds,
        filename: hlVideos.filename,
        durationSec: sql<number>`CAST(${hlVideos.durationMs} / 1000 AS INTEGER)`,
        markingSec: hlMarkings.seconds,
      })
      .from(hlMarkings)
      .innerJoin(hlVideos, eq(hlMarkings.videoId, hlVideos.id))
      .where(sql`${hlMarkings.seconds} * 1000 > ${hlVideos.durationMs}`);

    console.log(`📋 找到 ${invalidMarkings.length} 个无效标记\n`);

    for (const m of invalidMarkings) {
      console.log(`  ID ${(m as any).id}: ${(m as any).filename}, 标记点 ${(m as any).markingSec}秒 > 视频 ${(m as any).durationSec}秒`);
    }

    if (invalidMarkings.length > 0) {
      // 删除无效标记
      const idsToDelete = invalidMarkings.map((m: any) => m.id);
      await db.delete(hlMarkings).where(sql`${hlMarkings.id} IN ${sql.raw(`(${idsToDelete.join(',')})`)}`);

      console.log(`\n✅ 已删除 ${idsToDelete.length} 个无效标记`);
    } else {
      console.log('✅ 没有无效标记');
    }

    // 显示剩余标记
    const [remainingCount] = await db
      .select({ count: sql<number>`count(*)` })
      .from(hlMarkings);

    console.log(`\n📊 剩余标记数量: ${remainingCount.count}`);

    process.exit(0);
  } catch (error) {
    console.error('❌ 清理失败:', error);
    process.exit(1);
  }
}

cleanInvalidMarkings();
