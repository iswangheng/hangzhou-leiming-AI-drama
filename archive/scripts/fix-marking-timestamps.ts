/**
 * 修复标记数据的秒数字段
 *
 * 问题：时间戳格式是 MM:SS:ms（分钟:秒:毫秒）
 * 但之前按 HH:MM:SS 解析，导致秒数错误
 *
 * 例如：
 * - "0:05:00" 错误解析为 300秒（0小时5分）
 * - "1:34:00" 错误解析为 5640秒（1小时34分）
 *
 * 正确应该是：
 * - "0:05:00" → 0分5秒 = 5秒
 * - "1:34:00" → 1分34秒 = 94秒
 */

import { db } from '../lib/db/client';
import { hlMarkings } from '../lib/db/schema';
import { sql } from 'drizzle-orm';

async function fixMarkingTimestamps() {
  try {
    console.log('🔧 开始修复标记时间戳...\n');

    // 查询所有标记
    const markings = await db.select({
      id: hlMarkings.id,
      timestamp: hlMarkings.timestamp,
      oldSeconds: hlMarkings.seconds,
    }).from(hlMarkings);

    console.log(`📋 找到 ${markings.length} 个标记\n`);

    let fixedCount = 0;

    for (const marking of markings) {
      const correctSeconds = parseTimestamp(marking.timestamp);

      if (correctSeconds !== marking.oldSeconds) {
        await db
          .update(hlMarkings)
          .set({ seconds: correctSeconds })
          .where(sql`${hlMarkings.id} = ${marking.id}`);

        console.log(`✅ ID ${marking.id}: "${marking.timestamp}" ${marking.oldSeconds}秒 → ${correctSeconds}秒`);
        fixedCount++;
      } else {
        console.log(`  ✓ ID ${marking.id}: "${marking.timestamp}" ${correctSeconds}秒（已正确）`);
      }
    }

    console.log(`\n🎉 修复完成！共更新 ${fixedCount} 个标记`);

    // 验证修复结果
    console.log(`\n📊 验证修复结果：`);
    const results = await db
      .select({
        id: hlMarkings.id,
        timestamp: hlMarkings.timestamp,
        seconds: hlMarkings.seconds,
      })
      .from(hlMarkings)
      .orderBy(hlMarkings.id);

    for (const r of results) {
      console.log(`  ID ${r.id}: "${r.timestamp}" → ${r.seconds}秒`);
    }

    process.exit(0);
  } catch (error) {
    console.error('❌ 修复失败:', error);
    process.exit(1);
  }
}

/**
 * 解析时间戳为秒数（MM:SS:ms 格式）
 * 例如："0:05:00" → 0分5秒 = 5秒
 * "1:34:00" → 1分34秒 = 94秒
 */
function parseTimestamp(timestamp: string): number {
  const parts = timestamp.split(":").map(Number);

  if (parts.length === 2) {
    // MM:SS
    const [minutes, seconds] = parts;
    return minutes * 60 + seconds;
  } else if (parts.length === 3) {
    // MM:SS:ms
    const [minutes, seconds, milliseconds] = parts;
    return minutes * 60 + seconds;
  }

  return 0;
}

// 运行修复脚本
fixMarkingTimestamps();
