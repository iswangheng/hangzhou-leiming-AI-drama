/**
 * 修复已上传视频的集数字段
 *
 * 问题：已上传的10个视频 episode_number 都是"未命名"
 * 解决：从 filename 提取集数并更新数据库
 */

import { db } from '../lib/db/client';
import { hlVideos } from '../lib/db/schema';
import { eq } from 'drizzle-orm';

async function fixEpisodeNumbers() {
  try {
    console.log('🔧 开始修复视频集数...\n');

    // 查询所有 episode_number 为 "未命名" 的视频
    const videos = await db
      .select()
      .from(hlVideos)
      .where(eq(hlVideos.episodeNumber, '未命名'));

    console.log(`📋 找到 ${videos.length} 个需要修复的视频\n`);

    let updateCount = 0;

    for (const video of videos) {
      const newEpisodeNumber = extractEpisodeNumber(video.filename);

      if (newEpisodeNumber !== '未命名') {
        await db
          .update(hlVideos)
          .set({ episodeNumber: newEpisodeNumber })
          .where(eq(hlVideos.id, video.id));

        console.log(`✅ 视频ID ${video.id}: ${video.filename} → ${newEpisodeNumber}`);
        updateCount++;
      } else {
        console.log(`⚠️  视频ID ${video.id}: ${video.filename} → 无法识别集数`);
      }
    }

    console.log(`\n🎉 修复完成！共更新 ${updateCount} 个视频`);

    process.exit(0);
  } catch (error) {
    console.error('❌ 修复失败:', error);
    process.exit(1);
  }
}

/**
 * 从文件名提取集数
 */
function extractEpisodeNumber(filename: string): string {
  const nameWithoutExt = filename.replace(/\.[^.]+$/, '');

  // 模式1：纯数字（1, 01, 001）
  const pureNumberMatch = nameWithoutExt.match(/^(\d+)$/);
  if (pureNumberMatch) {
    const num = parseInt(pureNumberMatch[1], 10);
    return `第${num}集`;
  }

  // 模式2：已包含"第X集"格式
  if (nameWithoutExt.includes('第') && nameWithoutExt.includes('集')) {
    const match = nameWithoutExt.match(/第(\d+)集/);
    if (match) {
      return `第${match[1]}集`;
    }
  }

  // 模式3：EP前缀（EP1, EP01, Episode 1）
  const epMatch = nameWithoutExt.match(/^EP(\d+)$/i);
  if (epMatch) {
    const num = parseInt(epMatch[1], 10);
    return `第${num}集`;
  }

  const episodeMatch = nameWithoutExt.match(/Episode\s+(\d+)/i);
  if (episodeMatch) {
    const num = parseInt(episodeMatch[1], 10);
    return `第${num}集`;
  }

  return '未命名';
}

// 运行修复脚本
fixEpisodeNumbers();
