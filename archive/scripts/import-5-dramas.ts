/**
 * 导入五部剧的标记数据
 */

import * as XLSX from 'xlsx';
import { readFile } from 'fs/promises';
import { db } from '../lib/db/client';
import { hlProjects, hlVideos, hlMarkings } from '../lib/db/schema';
import { eq } from 'drizzle-orm';

const dramas = [
  {
    name: '重生暖宠：九爷的小娇妻不好惹',
    folder: '/Users/wangheng/Downloads/漫剧素材/重生暖宠九爷的小娇妻不好惹',
    excel: '/Users/wangheng/Downloads/重生暖宠：九爷的小娇妻不好惹.xlsx'
  },
  {
    name: '再见，心机前夫',
    folder: '/Users/wangheng/Downloads/漫剧素材/再见，心机前夫',
    excel: '/Users/wangheng/Downloads/再见，心机前夫.xlsx'
  },
  {
    name: '小小飞梦',
    folder: '/Users/wangheng/Downloads/漫剧素材/小小飞梦',
    excel: '/Users/wangheng/Downloads/小小飞梦.xlsx'
  },
  {
    name: '弃女归来：嚣张真千金不好惹',
    folder: '/Users/wangheng/Downloads/漫剧素材/弃女归来嚣张真千金不好惹',
    excel: '/Users/wangheng/Downloads/弃女归来：嚣张真千金不好惹.xlsx'
  },
  {
    name: '百里将就',
    folder: '/Users/wangheng/Downloads/漫剧素材/百里将就',
    excel: '/Users/wangheng/Downloads/百里将就.xlsx'
  }
];

async function importAllDramas() {
  console.log('🎬 开始导入五部短剧...\n');

  for (const drama of dramas) {
    console.log(`\n========== 处理: ${drama.name} ==========`);
    
    try {
      // 1. 创建项目
      const [project] = await db
        .insert(hlProjects)
        .values({
          name: drama.name,
          description: `AI训练项目 - ${drama.name}`,
          status: 'created'
        })
        .returning();
      
      console.log(`✅ 项目创建成功: ${project.id}`);

      // 2. 读取Excel标记数据
      const buffer = await readFile(drama.excel);
      const workbook = XLSX.read(buffer, { type: 'buffer' });
      const sheetName = workbook.SheetNames[0];
      const worksheet = workbook.Sheets[sheetName];
      const data = XLSX.utils.sheet_to_json(worksheet, { raw: false });

      console.log(`📊 Excel数据: ${data.length} 条标记`);

      // 3. 导入视频和标记
      for (let i = 1; i <= 10; i++) {
        const videoPath = `${drama.folder}/${i}.mp4`;
        
        // 插入视频记录
        const [video] = await db
          .insert(hlVideos)
          .values({
            projectId: project.id,
            filename: `${i}.mp4`,
            filePath: videoPath,
            fileSize: 0,
            episodeNumber: `第${i}集`,
            durationMs: 0,
            width: 1920,
            height: 1080,
            fps: 30,
            status: 'ready'
          })
          .returning();

        // 查找该集的所有标记
        const episodeMarkings = (data as any[]).filter(row => 
          row['集数'] === `第${i}集`
        );

        for (const row of episodeMarkings) {
          const timeParts = row['时间点'].toString().split(':');
          let seconds = 0;
          if (timeParts.length === 2) {
            seconds = parseInt(timeParts[0]) * 60 + parseInt(timeParts[1]);
          } else if (timeParts.length === 3) {
            seconds = parseInt(timeParts[0]) * 3600 + parseInt(timeParts[1]) * 60 + parseInt(timeParts[2]);
          }

          await db
            .insert(hlMarkings)
            .values({
              projectId: project.id,
              videoId: video.id,
              timestamp: row['时间点'].toString(),
              seconds: seconds,
              type: row['标记类型'] === '高光点' ? '高光点' : '钩子点',
              description: row['描述'] || ''
            });
        }

        console.log(`  第${i}集: ${episodeMarkings.length} 个标记`);
      }

      console.log(`✅ ${drama.name} 导入完成!`);

    } catch (error) {
      console.error(`❌ ${drama.name} 导入失败:`, error);
    }
  }

  console.log('\n🎉 全部导入完成!');
}

importAllDramas().catch(console.error);
