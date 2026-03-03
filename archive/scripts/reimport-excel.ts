/**
 * 重新导入已保存的Excel文件（使用修复后的解析逻辑）
 */

import * as XLSX from 'xlsx';
import { readFile } from 'fs/promises';
import { db } from '../lib/db/client';
import { hlMarkings, hlVideos } from '../lib/db/schema';
import { eq } from 'drizzle-orm';

async function reimportExcel() {
  try {
    const projectId = 1;
    const excelPath = '/Users/wangheng/Documents/indie-hacker/001-AI-DramaCut/data/hangzhou-leiming/1/excel/markings_1772367000612.xlsx';

    console.log(`📂 读取Excel文件: ${excelPath}`);

    // 读取Excel文件
    const buffer = await readFile(excelPath);
    const workbook = XLSX.read(buffer, { type: 'buffer' });
    const sheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[sheetName];
    const data = XLSX.utils.sheet_to_json(worksheet, { raw: false });

    console.log(`✅ Excel数据解析成功，共 ${data.length} 行\n`);

    // 获取项目的所有视频
    const videos = await db
      .select()
      .from(hlVideos)
      .where(eq(hlVideos.projectId, projectId));

    const videoMap = new Map<string, any>(
      videos.map((v: any) => [v.episodeNumber, v])
    );

    console.log(`📹 项目视频数量: ${videos.length}\n`);

    // 解析并插入标记数据
    const markingsToInsert = [];
    let successCount = 0;
    let errorCount = 0;

    for (const row of data as any[]) {
      try {
        const episode = row['集数'];
        const timestamp = row['时间点'];
        const type = row['标记类型'];
        const description = row['描述'] || '';

        // 验证必填字段
        if (!episode || !timestamp || !type) {
          console.warn('⚠️  跳过无效行:', row);
          errorCount++;
          continue;
        }

        // 查找对应的视频
        const video = videoMap.get(episode);
        if (!video) {
          console.warn(`⚠️  未找到集数 ${episode} 对应的视频`);
          errorCount++;
          continue;
        }

        // 解析时间点（使用修复后的逻辑）
        const seconds = parseTimestamp(timestamp);

        if (isNaN(seconds)) {
          console.warn(`⚠️  无效的时间格式: ${timestamp}`);
          errorCount++;
          continue;
        }

        // 验证标记点是否在视频时长范围内
        const markingMs = seconds * 1000;
        if (markingMs > video.durationMs) {
          console.warn(`⚠️  标记点 ${seconds}秒 超出视频时长 ${(video.durationMs / 1000).toFixed(1)}秒，跳过`);
          errorCount++;
          continue;
        }

        markingsToInsert.push({
          projectId,
          videoId: video.id,
          timestamp,
          seconds,
          type,
          subType: description,
          aiEnhanced: false,
          createdAt: new Date(),
          updatedAt: new Date(),
        });

        successCount++;
        console.log(`  ✓ ${episode} - ${timestamp} (${seconds}秒) - ${type}`);

      } catch (error) {
        console.error('❌ 解析行失败:', row, error);
        errorCount++;
      }
    }

    // 批量插入数据库
    if (markingsToInsert.length > 0) {
      await db.insert(hlMarkings).values(markingsToInsert);
      console.log(`\n✅ 导入完成！成功 ${successCount} 条，失败 ${errorCount} 条`);
    } else {
      console.log('\n⚠️  没有有效数据可导入');
    }

    process.exit(0);
  } catch (error) {
    console.error('❌ 导入失败:', error);
    process.exit(1);
  }
}

/**
 * 解析时间戳为秒数（MM:SS:ms 格式）
 * 例如："0:05:00" → 0分5秒 = 5秒
 * "1:34:00" → 1分34秒 = 94秒
 */
function parseTimestamp(timestamp: string): number {
  const parts = timestamp.split(':').map(Number);

  if (parts.length === 2) {
    // MM:SS
    const [minutes, seconds] = parts;
    return minutes * 60 + seconds;
  } else if (parts.length === 3) {
    // MM:SS:ms（忽略毫秒）
    const [minutes, seconds, milliseconds] = parts;
    return minutes * 60 + seconds;
  }

  return NaN;
}

// 运行重新导入
reimportExcel();
