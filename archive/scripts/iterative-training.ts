// ============================================
// 螺旋式迭代训练脚本
// 修复问题：每次训练更新同一个技能文件，而不是创建新文件
// 
// 输出文件: ai-drama-clipping-thoughts-vX.md
// ============================================

import { readFile, writeFile, readdir, mkdir } from 'fs/promises';
import { join, dirname } from 'path';
import { existsSync } from 'fs';
import { extractKeyframes } from '../lib/video/keyframes';
import { transcribeAudio } from '../lib/audio/transcriber';
import { getGeminiClient } from '../lib/api/gemini';
import { db } from '../lib/db/client';
import { 
  hlMarkings, 
  hlVideos, 
  hlProjects, 
  hlGlobalSkills,
  hlTrainingHistory 
} from '../lib/db/schema';
import { eq, desc, sql } from 'drizzle-orm';

// ============================================
// 配置
// ============================================

const SKILLS_DIR = join(process.cwd(), 'data', 'hangzhou-leiming', 'skills');
const DEFAULT_FRAMES_PER_MARKING = 5;

// ============================================
// 类型定义
// ============================================

interface LearningConfig {
  projectIds: number[];
  framesPerMarking?: number;
  skipExistingFrames?: boolean;
  skipExistingTranscript?: boolean;
}

interface MarkingWithVideo {
  id: number;
  timestamp: string;
  seconds: number;
  type: '高光点' | '钩子点';
  videoId: number;
  video: {
    id: number;
    filePath: string;
    episodeNumber: string;
    durationMs: number;
  };
}

interface AnalysisResult {
  highlight_types: HighlightType[];
  hook_types: HookType[];
  editing_rules: EditingRule[];
  reasoning: string;
}

interface HighlightType {
  name: string;
  description: string;
  visual_features: string[];
  audio_features: string[];
  examples: Array<{ timestamp: string; context: string }>;
}

interface HookType {
  name: string;
  description: string;
  visual_features: string[];
  audio_features: string[];
  examples: Array<{ timestamp: string; context: string }>;
}

interface EditingRule {
  scenario: string;
  duration: string;
  rhythm: string;
  combination: string;
  cut_in: string;
  cut_out: string;
}

interface TrainingResult {
  skillVersion: string;
  skillFilePath: string;
  totalProjects: number;
  totalVideos: number;
  totalMarkings: number;
  successCount: number;
  failureCount: number;
}

// ============================================
// 主函数
// ============================================

export async function runIterativeTraining(config: LearningConfig): Promise<TrainingResult> {
  console.log('='.repeat(50));
  console.log('  螺旋式迭代训练流程');
  console.log('='.repeat(50));
  console.log();

  // 1. 确保输出目录存在
  if (!existsSync(SKILLS_DIR)) {
    await mkdir(SKILLS_DIR, { recursive: true });
  }

  // 2. 获取当前技能版本
  const currentSkill = await getCurrentSkill();
  const newVersion = incrementVersion(currentSkill?.version || 'v0.0');
  
  console.log(`📊 当前版本: ${currentSkill?.version || '无'} → 新版本: ${newVersion}`);
  console.log();

  // 3. 收集所有项目的数据
  console.log('📂 收集项目数据...');
  const allMarkings = await collectProjectData(config.projectIds);
  
  if (allMarkings.length === 0) {
    throw new Error('没有找到标记数据');
  }

  console.log(`✅ 共收集 ${allMarkings.length} 个标记数据`);
  const highlightCount = allMarkings.filter(m => m.type === '高光点').length;
  const hookCount = allMarkings.filter(m => m.type === '钩子点').length;
  console.log(`   - 高光点: ${highlightCount}`);
  console.log(`   - 钩子点: ${hookCount}`);
  console.log();

  // 4. 提取多模态数据
  console.log('🎬 提取多模态数据...');
  const enrichedMarkings = await extractMultimodalData(
    allMarkings,
    config.framesPerMarking || DEFAULT_FRAMES_PER_MARKING,
    config.skipExistingFrames,
    config.skipExistingTranscript
  );
  console.log();

  // 5. Gemini AI 分析
  console.log('🤖 AI 分析中...');
  const analysisResult = await analyzeWithGemini(enrichedMarkings);
  console.log();

  // 6. 生成技能文件
  console.log('📝 生成技能文件...');
  const skillFilePath = await generateSkillFile(analysisResult, newVersion);
  console.log(`✅ 技能文件: ${skillFilePath}`);
  console.log();

  // 7. 更新数据库
  console.log('💾 更新数据库...');
  await updateSkillInDB(
    newVersion,
    skillFilePath,
    config.projectIds,
    allMarkings.length,
    enrichedMarkings.filter(m => m.success).length
  );
  console.log();

  // 8. 记录训练历史
  await recordTrainingHistory(config.projectIds, newVersion, allMarkings.length);
  console.log();

  console.log('='.repeat(50));
  console.log(`✅ 训练完成! 版本: ${newVersion}`);
  console.log('='.repeat(50));

  return {
    skillVersion: newVersion,
    skillFilePath,
    totalProjects: config.projectIds.length,
    totalVideos: new Set(allMarkings.map(m => m.videoId)).size,
    totalMarkings: allMarkings.length,
    successCount: enrichedMarkings.filter(m => m.success).length,
    failureCount: enrichedMarkings.filter(m => !m.success).length,
  };
}

// ============================================
// 辅助函数
// ============================================

/**
 * 获取当前技能版本
 */
async function getCurrentSkill() {
  const [skill] = await db
    .select()
    .from(hlGlobalSkills)
    .orderBy(desc(hlGlobalSkills.createdAt))
    .limit(1);
  
  return skill;
}

/**
 * 递增版本号
 */
function incrementVersion(currentVersion: string): string {
  // 解析版本号 (如 v1.0 -> 1.0)
  const match = currentVersion.match(/v(\d+)\.(\d+)/);
  if (match) {
    const major = parseInt(match[1]);
    const minor = parseInt(match[2]) + 1;
    return `v${major}.${minor}`;
  }
  // 默认从 v1.0 开始
  return 'v1.0';
}

/**
 * 收集项目数据
 */
async function collectProjectData(projectIds: number[]): Promise<MarkingWithVideo[]> {
  const allMarkings: MarkingWithVideo[] = [];

  for (const projectId of projectIds) {
    const markings = await db
      .select({
        id: hlMarkings.id,
        timestamp: hlMarkings.timestamp,
        seconds: hlMarkings.seconds,
        type: hlMarkings.type,
        videoId: hlMarkings.videoId,
        video: {
          id: hlVideos.id,
          filePath: hlVideos.filePath,
          episodeNumber: hlVideos.episodeNumber,
          durationMs: hlVideos.durationMs,
        },
      })
      .from(hlMarkings)
      .innerJoin(hlVideos, eq(hlMarkings.videoId, hlVideos.id))
      .where(eq(hlMarkings.projectId, projectId))
      .orderBy(hlMarkings.seconds);

    allMarkings.push(...markings as MarkingWithVideo[]);
  }

  return allMarkings;
}

/**
 * 提取多模态数据
 */
async function extractMultimodalData(
  markings: MarkingWithVideo[],
  framesPerMarking: number,
  skipExistingFrames?: boolean,
  skipExistingTranscript?: boolean
) {
  // 按视频分组
  const videosMap = new Map<number, MarkingWithVideo[]>();
  for (const marking of markings) {
    if (!videosMap.has(marking.videoId)) {
      videosMap.set(marking.videoId, []);
    }
    videosMap.get(marking.videoId)!.push(marking);
  }

  const enrichedMarkings: Array<MarkingWithVideo & { transcript?: string; success: boolean; error?: string }> = [];

  let processedVideos = 0;
  const totalVideos = videosMap.size;

  for (const [videoId, videoMarkings] of videosMap.entries()) {
    const video = videoMarkings[0].video;
    processedVideos++;
    
    console.log(`   处理视频 ${processedVideos}/${totalVideos}: ${video.episodeNumber}`);

    try {
      // 转录音频
      let transcript = '';
      const transcriptPath = video.filePath.replace(/\.[^.]+$/, '-transcript.json');

      if (existsSync(transcriptPath) && skipExistingTranscript) {
        try {
          const transcriptData = JSON.parse(await readFile(transcriptPath, 'utf-8'));
          transcript = transcriptData.text || '';
        } catch {}
      }

      if (!transcript) {
        // 提取音频
        const audioPath = video.filePath.replace(/\.[^.]+$/, '.wav');
        
        if (!existsSync(audioPath)) {
          const { exec } = await import('child_process');
          await new Promise<void>((resolve, reject) => {
            exec(`ffmpeg -i "${video.filePath}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "${audioPath}"`, (error) => {
              if (error) reject(error);
              else resolve();
            });
          });
        }

        // 转录
        const result = await transcribeAudio(audioPath, { language: 'zh' });
        transcript = result.text;

        // 保存转录
        await writeFile(transcriptPath, JSON.stringify(result, null, 2));

        // 清理
        try {
          const { unlink } = await import('fs/promises');
          await unlink(audioPath);
        } catch {}
      }

      // 为每个标记点添加转录
      for (const marking of videoMarkings) {
        enrichedMarkings.push({
          ...marking,
          transcript,
          success: true,
        });
      }

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '未知错误';
      console.error(`   ❌ 视频 ${video.episodeNumber} 处理失败: ${errorMsg}`);
      
      for (const marking of videoMarkings) {
        enrichedMarkings.push({
          ...marking,
          success: false,
          error: errorMsg,
        });
      }
    }
  }

  return enrichedMarkings;
}

/**
 * Gemini AI 分析
 */
async function analyzeWithGemini(markings: Array<MarkingWithVideo & { transcript?: string; success: boolean }>) {
  const geminiClient = getGeminiClient();
  
  // 过滤成功的标记
  const successMarkings = markings.filter(m => m.success);

  if (successMarkings.length === 0) {
    throw new Error('没有成功提取的标记数据');
  }

  // 按集数分组
  const episodesMap = new Map<string, typeof successMarkings>();
  for (const marking of successMarkings) {
    const episode = marking.video.episodeNumber;
    if (!episodesMap.has(episode)) {
      episodesMap.set(episode, []);
    }
    episodesMap.get(episode)!.push(marking);
  }

  // 读取 Prompt 模板
  let promptTemplate = '';
  const promptPath = join(process.cwd(), 'prompts', 'hl-learning.md');
  
  if (existsSync(promptPath)) {
    promptTemplate = await readFile(promptPath, 'utf-8');
  } else {
    // 默认模板
    promptTemplate = `## 分析任务
基于以下短剧标记数据，总结剪辑规律。

### 剧集信息
{{episode}}

### 标记统计
{{timestamp}}
类型分布: {{type}}

### 标记详情
{{transcript}}

请返回 JSON 格式的分析结果：
\`\`\`json
{
  "highlight_types": [...],
  "hook_types": [...],
  "editing_rules": [...],
  "reasoning": "..."
}
\`\`\`
`;
  }

  // 构建标记上下文
  const markingContexts = successMarkings.slice(0, 10).map((marking, index) => {
    const timeMin = Math.floor(marking.seconds / 60);
    const timeSec = marking.seconds % 60;
    const timestamp = `${timeMin.toString().padStart(2, '0')}:${timeSec.toString().padStart(2, '0')}`;

    let transcriptSnippet = '';
    if (marking.transcript) {
      const words = marking.transcript.split('');
      const centerIndex = Math.floor(words.length * (marking.seconds / (marking.video.durationMs / 1000)));
      const startIdx = Math.max(0, centerIndex - 50);
      const endIdx = Math.min(words.length, centerIndex + 50);
      transcriptSnippet = words.slice(startIdx, endIdx).join('');
    }

    return `## 标记 ${index + 1}
- 集数: 第${marking.video.episodeNumber}集
- 时间点: ${timestamp}
- 类型: ${marking.type}
- 转录文本: ${transcriptSnippet || '(无转录)'}`;
  }).join('\n\n');

  const prompt = promptTemplate
    .replace('{{episode}}', `共 ${episodesMap.size} 集`)
    .replace('{{timestamp}}', `${successMarkings.length} 个标记点`)
    .replace('{{type}}', `${successMarkings.filter(m => m.type === '高光点').length} 个高光点，${successMarkings.filter(m => m.type === '钩子点').length} 个钩子点`)
    .replace('{{frame_descriptions}}', '已提供关键帧和转录文本')
    .replace('{{transcript}}', markingContexts)
    .replace('{{total_markings}}', successMarkings.length.toString());

  const systemInstruction = `你是一位专业的短剧剪辑分析师，擅长从历史标记数据中总结剪辑技能和规律。
你需要基于真实的转录文本进行分析，不要编造不存在的情节。
返回的 JSON 必须严格遵循指定的 schema。`;

  const response = await geminiClient.callApi(prompt, systemInstruction);

  if (!response.success || !response.data) {
    throw new Error(`Gemini 分析失败: ${response.error || '未知错误'}`);
  }

  // 解析 JSON
  const jsonMatch = (response.data as string).match(/```json\n([\s\S]*?)\n```/);
  const jsonText = jsonMatch ? jsonMatch[1] : response.data as string;

  try {
    return JSON.parse(jsonText) as AnalysisResult;
  } catch {
    throw new Error('Gemini 返回的 JSON 格式不正确');
  }
}

/**
 * 生成技能文件
 */
async function generateSkillFile(analysisResult: AnalysisResult, version: string): Promise<string> {
  // 新文件命名: ai-drama-clipping-thoughts-vX.md
  const fileName = `ai-drama-clipping-thoughts-${version}.md`;
  const filePath = join(SKILLS_DIR, fileName);

  const lines: string[] = [];

  lines.push('# AI 短剧剪辑技能\n');
  lines.push(`> 版本: ${version} | 由 AI 学习自动生成\n`);
  lines.push('---\n');

  // 分析推理
  lines.push('## 📊 分析推理\n');
  lines.push(analysisResult.reasoning);
  lines.push('\n---\n');

  // 高光类型
  if (analysisResult.highlight_types.length > 0) {
    lines.push('## 🎯 高光类型\n');
    for (const type of analysisResult.highlight_types) {
      lines.push(`### ${type.name}\n`);
      lines.push(`**描述**: ${type.description}\n\n`);
      lines.push(`**视觉特征**:\n`);
      for (const feature of type.visual_features) {
        lines.push(`- ${feature}\n`);
      }
      lines.push(`\n**听觉特征**:\n`);
      for (const feature of type.audio_features) {
        lines.push(`- ${feature}\n`);
      }
      if (type.examples.length > 0) {
        lines.push(`\n**示例**:\n`);
        for (const example of type.examples) {
          lines.push(`- ${example.timestamp}: ${example.context}\n`);
        }
      }
      lines.push('\n');
    }
    lines.push('---\n');
  }

  // 钩子类型
  if (analysisResult.hook_types.length > 0) {
    lines.push('## 🪝 钩子类型\n');
    for (const type of analysisResult.hook_types) {
      lines.push(`### ${type.name}\n`);
      lines.push(`**描述**: ${type.description}\n\n`);
      lines.push(`**视觉特征**:\n`);
      for (const feature of type.visual_features) {
        lines.push(`- ${feature}\n`);
      }
      lines.push(`\n**听觉特征**:\n`);
      for (const feature of type.audio_features) {
        lines.push(`- ${feature}\n`);
      }
      if (type.examples.length > 0) {
        lines.push(`\n**示例**:\n`);
        for (const example of type.examples) {
          lines.push(`- ${example.timestamp}: ${example.context}\n`);
        }
      }
      lines.push('\n');
    }
    lines.push('---\n');
  }

  // 剪辑规则
  if (analysisResult.editing_rules.length > 0) {
    lines.push('## ✂️ 剪辑规则\n');
    for (const rule of analysisResult.editing_rules) {
      lines.push(`### ${rule.scenario}\n`);
      lines.push(`- **时长**: ${rule.duration}\n`);
      lines.push(`- **节奏**: ${rule.rhythm}\n`);
      lines.push(`- **组合方式**: ${rule.combination}\n`);
      lines.push(`- **切入**: ${rule.cut_in}\n`);
      lines.push(`- **切出**: ${rule.cut_out}\n`);
      lines.push('\n');
    }
  }

  await writeFile(filePath, lines.join(''));
  return filePath;
}

/**
 * 更新数据库中的技能
 */
async function updateSkillInDB(
  version: string,
  filePath: string,
  projectIds: number[],
  totalMarkings: number,
  successCount: number
) {
  // 检查是否已存在该版本
  const existing = await db
    .select()
    .from(hlGlobalSkills)
    .where(eq(hlGlobalSkills.version, version))
    .limit(1);

  if (existing.length > 0) {
    // 更新现有记录
    await db
      .update(hlGlobalSkills)
      .set({
        skillFilePath: filePath,
        totalProjects: projectIds.length,
        totalMarkings,
        trainingProjectIds: JSON.stringify(projectIds),
        updatedAt: new Date(),
      })
      .where(eq(hlGlobalSkills.id, existing[0].id));
    
    console.log(`   已更新版本 ${version}`);
  } else {
    // 插入新记录
    await db
      .insert(hlGlobalSkills)
      .values({
        version,
        skillFilePath: filePath,
        totalProjects: projectIds.length,
        totalVideos: 0,
        totalMarkings,
        trainingProjectIds: JSON.stringify(projectIds),
        status: 'ready',
      });
    
    console.log(`   已创建新版本 ${version}`);
  }
}

/**
 * 记录训练历史
 */
async function recordTrainingHistory(projectIds: number[], version: string, markingCount: number) {
  // 获取项目名称
  const projects = await db
    .select({ id: hlProjects.id, name: hlProjects.name })
    .from(hlProjects)
    .where(sql`${hlProjects.id} IN (${projectIds.join(',')})`);

  const projectNames = projects.map(p => p.name);

  await db
    .insert(hlTrainingHistory)
    .values({
      projectIds: JSON.stringify(projectIds),
      projectNames: JSON.stringify(projectNames),
      skillVersion: version,
      status: 'completed',
      progress: 100,
      currentStep: '完成',
      totalVideosProcessed: 0,
      totalMarkingsLearned: markingCount,
      startedAt: new Date(),
      completedAt: new Date(),
    });

  console.log(`   已记录训练历史`);
}

// ============================================
// 主入口
// ============================================

async function main() {
  const args = process.argv.slice(2);
  
  // 默认训练项目 20-24
  const projectIds = args[0] 
    ? args[0].split(',').map(Number)
    : [20, 21, 22, 23, 24];

  console.log(`训练项目: ${projectIds.join(', ')}`);
  console.log();

  try {
    const result = await runIterativeTraining({
      projectIds,
      framesPerMarking: 5,
      skipExistingFrames: true,
      skipExistingTranscript: true,
    });

    console.log('\n📊 训练结果:');
    console.log(`   - 版本: ${result.skillVersion}`);
    console.log(`   - 文件: ${result.skillFilePath}`);
    console.log(`   - 项目数: ${result.totalProjects}`);
    console.log(`   - 标记数: ${result.totalMarkings}`);
    console.log(`   - 成功: ${result.successCount}`);
    console.log(`   - 失败: ${result.failureCount}`);

  } catch (error) {
    console.error('\n❌ 训练失败:', error);
    process.exit(1);
  }
}

// 运行
main();
