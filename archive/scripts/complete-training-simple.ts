/**
 * 手动完成训练并保存技能文件到数据库
 */

import { db } from '../lib/db/client';
import { hlTrainingHistory, hlGlobalSkills, hlMarkings, hlProjects } from '../lib/db/schema';
import { eq } from 'drizzle-orm';
import { mkdir, writeFile, readdir, stat } from 'fs/promises';
import { join } from 'path';

async function completeTraining() {
  try {
    const trainingId = 2; // 训练记录ID
    const projectId = 1; // 项目ID（简化处理）

    console.log(`🔄 手动完成训练，ID: ${trainingId}\n`);

    // 1. 检查训练记录
    const [training] = await db
      .select()
      .from(hlTrainingHistory)
      .where(eq(hlTrainingHistory.id, trainingId));

    if (!training) {
      console.error('❌ 训练记录不存在');
      process.exit(1);
    }

    console.log(`📋 训练项目ID: ${projectId}`);
    console.log(`📊 当前状态: ${training.status}, 进度: ${training.progress}%\n`);

    // 2. 读取标记数据和项目信息
    const [project] = await db
      .select()
      .from(hlProjects)
      .where(eq(hlProjects.id, projectId));

    if (!project) {
      console.error('❌ 项目不存在');
      process.exit(1);
    }

    const allMarkings = await db
      .select()
      .from(hlMarkings)
      .where(eq(hlMarkings.projectId, projectId));

    console.log(`📋 项目名称: ${project.name}`);
    console.log(`📊 标记总数: ${allMarkings.length}\n`);

    if (allMarkings.length === 0) {
      console.error('❌ 没有找到标记数据');
      process.exit(1);
    }

    // 3. 生成技能文件内容
    console.log(`📝 生成技能文件内容...`);

    const highlightMarkings = allMarkings.filter((m: any) => m.type === '高光点');
    const hookMarkings = allMarkings.filter((m: any) => m.type === '钩子点');

    // 生成Markdown内容
    const lines: string[] = [];

    lines.push(`# 杭州雷鸣 - 全局剪辑技能文件\n`);
    lines.push(`## 📋 基本信息\n`);
    lines.push(`- **版本**: v${new Date().toISOString().split('T')[0].replace(/-/g, '.')}`);
    lines.push(`- **训练项目**: ${project.name}`);
    lines.push(`- **训练时间**: ${new Date().toLocaleString('zh-CN')}`);
    lines.push(`- **标记总数**: ${allMarkings.length}`);
    lines.push(`- **高光点**: ${highlightMarkings.length}`);
    lines.push(`- **钩子点**: ${hookMarkings.length}\n`);

    // 高光点示例
    lines.push(`## 🎬 高光点模式\n`);
    const highlightSubTypes = highlightMarkings.reduce((acc: any, m: any) => {
      const subType = m.subType || m.description || '未分类';
      acc[subType] = (acc[subType] || 0) + 1;
      return acc;
    }, {});

    Object.entries(highlightSubTypes).forEach(([subType, count]) => {
      lines.push(`### ${subType} (${count}个)\n`);
      const examples = highlightMarkings
        .filter((m: any) => (m.subType || m.description) === subType)
        .slice(0, 3);
      examples.forEach((m: any) => {
        lines.push(`- **时间点**: ${m.timestamp}（第${m.videoId}集）`);
        lines.push(`  - **描述**: ${m.description || '无'}`);
        lines.push(`  - **得分**: ${m.score || '无'}\n`);
      });
    });

    // 钩子点示例
    lines.push(`## 🪝 钩子点模式\n`);
    const hookSubTypes = hookMarkings.reduce((acc: any, m: any) => {
      const subType = m.subType || m.description || '未分类';
      acc[subType] = (acc[subType] || 0) + 1;
      return acc;
    }, {});

    Object.entries(hookSubTypes).forEach(([subType, count]) => {
      lines.push(`### ${subType} (${count}个)\n`);
      const examples = hookMarkings
        .filter((m: any) => (m.subType || m.description) === subType)
        .slice(0, 3);
      examples.forEach((m: any) => {
        lines.push(`- **时间点**: ${m.timestamp}（第${m.videoId}集）`);
        lines.push(`  - **描述**: ${m.description || '无'}\n`);
      });
    });

    const skillContent = lines.join('\n');
    console.log(`  ✅ 技能文件生成完成 (${skillContent.length}字)\n`);

    // 4. 保存技能文件到磁盘
    const skillsDir = join(process.cwd(), 'data', 'hangzhou-leiming', 'skills');
    await mkdir(skillsDir, { recursive: true });

    const version = `v1.${Date.now()}`;
    const fileName = `skill_${version}_${Date.now()}.md`;
    const filePath = join(skillsDir, fileName);

    await writeFile(filePath, skillContent, 'utf-8');

    console.log(`💾 技能文件已保存: ${filePath}`);
    console.log(`📌 版本: ${version}\n`);

    // 5. 保存技能到数据库
    const [newSkill] = await db
      .insert(hlGlobalSkills)
      .values({
        version,
        skillFilePath: filePath,
        totalProjects: 1,
        totalVideos: 0,
        totalMarkings: allMarkings.length,
        trainingProjectIds: JSON.stringify([projectId]),
        status: 'ready',
      })
      .returning();

    console.log(`✅ 技能已保存到数据库，ID: ${newSkill.id}\n`);

    // 6. 更新训练历史
    await db
      .update(hlTrainingHistory)
      .set({
        status: 'completed',
        progress: 100,
        currentStep: '训练完成',
        skillVersion: version,
        skillId: newSkill.id,
        completedAt: new Date(),
      })
      .where(eq(hlTrainingHistory.id, trainingId));

    console.log(`✅ 训练历史已更新\n`);
    console.log(`🎉 手动训练完成！`);
    console.log(`\n📊 技能统计:`);
    console.log(`  - 版本: ${version}`);
    console.log(`  - 标记数: ${allMarkings.length}`);
    console.log(`  - 高光点: ${highlightMarkings.length}`);
    console.log(`  - 钩子点: ${hookMarkings.length}`);

    process.exit(0);
  } catch (error) {
    console.error('❌ 手动训练失败:', error);
    process.exit(1);
  }
}

// 运行脚本
completeTraining();
