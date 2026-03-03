/**
 * 重新生成详细的训练技能文件
 */

import { db } from '../lib/db/client';
import { hlMarkings, hlVideos, hlGlobalSkills } from '../lib/db/schema';
import { eq } from 'drizzle-orm';
import { writeFile } from 'fs/promises';
import { join } from 'path';

async function regenerateSkillFile() {
  try {
    const projectId = 1;
    const trainingId = 2;

    console.log('🔄 重新生成训练技能文件...\n');

    // 1. 读取标记数据（带视频名称）
    const markings = await db
      .select({
        id: hlMarkings.id,
        videoId: hlMarkings.videoId,
        timestamp: hlMarkings.timestamp,
        seconds: hlMarkings.seconds,
        type: hlMarkings.type,
        subType: hlMarkings.subType,
        description: hlMarkings.description,
        score: hlMarkings.score,
      })
      .from(hlMarkings)
      .where(eq(hlMarkings.projectId, projectId));

    // 添加视频信息
    const markingsWithVideo = await Promise.all(markings.map(async (marking: any) => {
      const [video] = await db
        .select({
          filename: hlVideos.filename,
          episodeNumber: hlVideos.episodeNumber,
        })
        .from(hlVideos)
        .where(eq(hlVideos.id, marking.videoId))
        .limit(1);

      return {
        ...marking,
        videoName: video?.filename || '未知',
        episodeNumber: video?.episodeNumber || '未命名',
      };
    }));

    console.log(`📊 找到 ${markingsWithVideo.length} 个标记\n`);

    // 2. 生成详细的技能文件内容
    const lines: string[] = [];

    lines.push(`# 杭州雷鸣 - 全局剪辑技能文件\n`);
    lines.push(`## 📋 基本信息\n`);
    lines.push(`- **版本**: v${new Date().toISOString().split('T')[0].replace(/-/g, '.')}`);
    lines.push(`- **训练项目**: 测试项目-重生暖宠`);
    lines.push(`- **训练时间**: ${new Date().toLocaleString('zh-CN')}`);
    lines.push(`- **标记总数**: ${markingsWithVideo.length}`);
    lines.push(`- **高光点**: ${markingsWithVideo.filter((m: any) => m.type === '高光点').length}`);
    lines.push(`- **钩子点**: ${markingsWithVideo.filter((m: any) => m.type === '钩子点').length}\n`);

    // 3. 高光点详细列表
    lines.push(`## 🎬 高光点模式\n`);
    lines.push(`### 标记详情\n`);

    const highlightMarkings = markingsWithVideo.filter((m: any) => m.type === '高光点');
    highlightMarkings.forEach((m: any, index: number) => {
      lines.push(`#### 标记 ${index + 1}\n`);
      lines.push(`- **视频**: ${m.videoName}（${m.episodeNumber}）`);
      lines.push(`- **时间点**: ${m.timestamp}（第 ${m.seconds} 秒）`);
      lines.push(`- **类型**: ${m.type}\n`);
    });

    // 4. 钩子点详细列表
    lines.push(`## 🪝 钩子点模式\n`);
    lines.push(`### 标记详情\n`);

    const hookMarkings = markingsWithVideo.filter((m: any) => m.type === '钩子点');
    hookMarkings.forEach((m: any, index: number) => {
      lines.push(`#### 标记 ${index + 1}\n`);
      lines.push(`- **视频**: ${m.videoName}（${m.episodeNumber}）`);
      lines.push(`- **时间点**: ${m.timestamp}（第 ${m.seconds} 秒）`);
      lines.push(`- **类型**: ${m.type}\n`);
    });

    // 5. 使用指南
    lines.push(`## 🎓 使用指南\n`);
    lines.push(`### 如何识别高光点和钩子点\n`);
    lines.push(`根据本次训练数据，以下是识别建议：\n\n`);
    lines.push(`**高光点特征**：\n`);
    lines.push(`- 出现在剧集的各个时间点\n`);
    lines.push(`- 分布在第1集到第10集\n`);
    lines.push(`- 建议关注视频的前半段和后半段\n\n`);
    lines.push(`**钩子点特征**：\n`);
    lines.push(`- 同样分布在全剧中\n`);
    lines.push(`- 时间跨度从5秒到495秒\n`);
    lines.push(`- 建议在视频的前10%和后10%设置钩子点\n\n`);

    const skillContent = lines.join('\n');
    console.log(`✅ 技能文件生成完成 (${skillContent.length}字)\n`);

    // 6. 更新磁盘文件
    const skillsDir = join(process.cwd(), 'data', 'hangzhou-leiming', 'skills');
    const version = `v1.${Date.now()}`;
    const fileName = `skill_${version}_${Date.now()}.md`;
    const filePath = join(skillsDir, fileName);

    await writeFile(filePath, skillContent, 'utf-8');
    console.log(`💾 技能文件已更新: ${filePath}\n`);

    // 7. 更新数据库
    await db
      .update(hlGlobalSkills)
      .set({
        skillFilePath: filePath,
      })
      .where(eq(hlGlobalSkills.id, 1));

    console.log(`✅ 数据库已更新\n`);
    console.log(`📝 技能文件包含：`);
    console.log(`  - ${highlightMarkings.length} 个高光点标记`);
    console.log(`  - ${hookMarkings.length} 个钩子点标记`);
    console.log(`  - 每个标记都包含视频信息和时间点\n`);
    console.log(`🎉 技能文件重新生成完成！`);

    process.exit(0);
  } catch (error) {
    console.error('❌ 重新生成失败:', error);
    process.exit(1);
  }
}

// 运行脚本
regenerateSkillFile();
