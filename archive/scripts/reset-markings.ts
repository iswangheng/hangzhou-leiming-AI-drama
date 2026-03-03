/**
 * 清空项目的所有标记数据（用于重新导入）
 */

import { db } from '../lib/db/client';
import { hlMarkings } from '../lib/db/schema';
import { eq } from 'drizzle-orm';

async function resetMarkings(projectId: number) {
  try {
    const result = await db
      .delete(hlMarkings)
      .where(eq(hlMarkings.projectId, projectId));

    console.log(`✅ 已清空项目 ${projectId} 的所有标记数据`);
    process.exit(0);
  } catch (error) {
    console.error('❌ 清空失败:', error);
    process.exit(1);
  }
}

const projectId = parseInt(process.argv[2]) || 1;
resetMarkings(projectId);
