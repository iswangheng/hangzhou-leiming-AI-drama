/**
 * 修复视频时长元数据
 *
 * 问题：上传时没有使用 ffprobe 获取时长，所有视频 duration_ms = 0
 * 解决：使用 ffprobe 批量获取所有视频的真实时长
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { db } from '../lib/db/client';
import { hlVideos } from '../lib/db/schema';
import { eq } from 'drizzle-orm';

const execAsync = promisify(exec);

async function fixVideoDurations() {
  try {
    console.log('🔧 开始修复视频时长...\n');

    // 查询所有 duration_ms = 0 的视频
    const videos = await db
      .select()
      .from(hlVideos)
      .where(eq(hlVideos.durationMs, 0));

    console.log(`📋 找到 ${videos.length} 个需要修复的视频\n`);

    let updateCount = 0;

    for (const video of videos) {
      try {
        // 使用 ffprobe 获取时长
        const duration = await getVideoDuration(video.filePath);

        if (duration > 0) {
          await db
            .update(hlVideos)
            .set({ durationMs: duration })
            .where(eq(hlVideos.id, video.id));

          const durationSec = (duration / 1000).toFixed(1);
          console.log(`✅ 视频 ${video.filename}: ${durationSec}秒 (${duration}ms)`);
          updateCount++;
        } else {
          console.log(`⚠️  视频 ${video.filename}: 无法获取时长`);
        }
      } catch (error) {
        console.error(`❌ 视频 ${video.filename} 获取时长失败:`, error);
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
 * 使用 ffprobe 获取视频时长（毫秒）
 */
async function getVideoDuration(filePath: string): Promise<number> {
  const command = `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${filePath}"`;

  try {
    const { stdout } = await execAsync(command);
    const durationSeconds = parseFloat(stdout.trim());

    if (isNaN(durationSeconds)) {
      return 0;
    }

    // 转换为毫秒
    return Math.floor(durationSeconds * 1000);
  } catch (error) {
    console.error(`ffprobe 执行失败:`, error);
    return 0;
  }
}

// 运行修复脚本
fixVideoDurations();
