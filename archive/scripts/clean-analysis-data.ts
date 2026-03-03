// ============================================
// 清理历史分析数据（方案 A）
// ============================================
//
// 用途：清理所有AI分析结果，保留视频上传记录
// 执行：npx tsx scripts/clean-analysis-data.ts
// ============================================

import { db } from '../lib/db/client';
import { schema } from '../lib/db/schema';
import { sql } from 'drizzle-orm';

async function cleanAnalysisData() {
  console.log('🧹 开始清理历史分析数据...\n');

  try {
    // 获取清理前的数据统计
    const beforeStats = {
      shots: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.shots),
      highlights: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.highlights),
      storylines: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.storylines),
      storylineSegments: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.storylineSegments),
      audioTranscriptions: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.audioTranscriptions),
      keyframes: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.keyframes),
      projectAnalysis: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.projectAnalysis),
      queueJobs: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.queueJobs),
    };

    console.log('📊 清理前的数据统计:');
    console.log(`  - 镜头分析 (shots): ${beforeStats.shots[0].count} 条`);
    console.log(`  - 高光片段 (highlights): ${beforeStats.highlights[0].count} 条`);
    console.log(`  - 故事线 (storylines): ${beforeStats.storylines[0].count} 条`);
    console.log(`  - 故事线片段 (storylineSegments): ${beforeStats.storylineSegments[0].count} 条`);
    console.log(`  - 音频转录 (audioTranscriptions): ${beforeStats.audioTranscriptions[0].count} 条`);
    console.log(`  - 关键帧 (keyframes): ${beforeStats.keyframes[0].count} 条`);
    console.log(`  - 项目分析 (projectAnalysis): ${beforeStats.projectAnalysis[0].count} 条`);
    console.log(`  - 队列任务 (queueJobs): ${beforeStats.queueJobs[0].count} 条`);
    console.log('');

    // 确认清理
    console.log('⚠️  警告：此操作将删除上述所有数据！');
    console.log('✅ 保留：videos（视频基本信息）');
    console.log('');

    // 开始清理
    console.log('🗑️  开始清理...\n');

    // 1. 清空队列任务（最外层，避免孤立任务）
    console.log('  [1/8] 清空队列任务...');
    await db.delete(schema.queueJobs);
    console.log('  ✅ 队列任务已清空');

    // 2. 清空音频转录
    console.log('  [2/8] 清空音频转录...');
    await db.delete(schema.audioTranscriptions);
    console.log('  ✅ 音频转录已清空');

    // 3. 清空关键帧
    console.log('  [3/8] 清空关键帧...');
    await db.delete(schema.keyframes);
    console.log('  ✅ 关键帧已清空');

    // 4. 清空故事线片段（要先清空子表）
    console.log('  [4/8] 清空故事线片段...');
    await db.delete(schema.storylineSegments);
    console.log('  ✅ 故事线片段已清空');

    // 5. 清空故事线
    console.log('  [5/8] 清空故事线...');
    await db.delete(schema.storylines);
    console.log('  ✅ 故事线已清空');

    // 6. 清空高光片段
    console.log('  [6/8] 清空高光片段...');
    await db.delete(schema.highlights);
    console.log('  ✅ 高光片段已清空');

    // 7. 清空镜头分析
    console.log('  [7/8] 清空镜头分析...');
    await db.delete(schema.shots);
    console.log('  ✅ 镜头分析已清空');

    // 8. 清空项目级分析
    console.log('  [8/8] 清空项目级分析...');
    await db.delete(schema.projectAnalysis);
    console.log('  ✅ 项目级分析已清空');

    // 重置视频状态
    console.log('\n🔄 重置视频状态...');
    await db
      .update(schema.videos)
      .set({
        status: 'ready',
        enhancedSummary: null,
        keyframesExtracted: 0,
      });

    console.log('  ✅ 视频状态已重置');

    // 获取清理后的数据统计
    const afterStats = {
      shots: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.shots),
      highlights: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.highlights),
      storylines: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.storylines),
      storylineSegments: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.storylineSegments),
      audioTranscriptions: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.audioTranscriptions),
      keyframes: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.keyframes),
      projectAnalysis: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.projectAnalysis),
      queueJobs: await db.select({ count: sql<number>`COUNT(*)` }).from(schema.queueJobs),
    };

    console.log('\n✅ 清理完成！\n');
    console.log('📊 清理后的数据统计:');
    console.log(`  - 镜头分析 (shots): ${afterStats.shots[0].count} 条`);
    console.log(`  - 高光片段 (highlights): ${afterStats.highlights[0].count} 条`);
    console.log(`  - 故事线 (storylines): ${afterStats.storylines[0].count} 条`);
    console.log(`  - 故事线片段 (storylineSegments): ${afterStats.storylineSegments[0].count} 条`);
    console.log(`  - 音频转录 (audioTranscriptions): ${afterStats.audioTranscriptions[0].count} 条`);
    console.log(`  - 关键帧 (keyframes): ${afterStats.keyframes[0].count} 条`);
    console.log(`  - 项目分析 (projectAnalysis): ${afterStats.projectAnalysis[0].count} 条`);
    console.log(`  - 队列任务 (queueJobs): ${afterStats.queueJobs[0].count} 条`);

    const videos = await db.select({ count: sql<number>`COUNT(*)` }).from(schema.videos);
    console.log(`\n📹 保留的视频数: ${videos[0].count} 个\n`);

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🎉 清理成功！现在可以重新开始分析了');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  } catch (error) {
    console.error('❌ 清理失败:', error);
    process.exit(1);
  }
}

// 执行清理
cleanAnalysisData()
  .then(() => {
    process.exit(0);
  })
  .catch((error) => {
    console.error('❌ 脚本执行失败:', error);
    process.exit(1);
  });
