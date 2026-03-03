// ============================================
// 杭州雷鸣 - AI 学习流程
// 从历史标记数据自动生成剪辑技能文件
// ============================================

import { readFile } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';
import { extractKeyframes } from '../video/keyframes';
import { transcribeAudio } from '../audio/transcriber';
import { getGeminiClient } from '../api/gemini';
import { db } from '../db/client';
import { hlMarkings, hlVideos, hlProjects, hlSkills } from '../db/schema';
import { eq, and } from 'drizzle-orm';
import wsServer from '../ws/server';

// ============================================
// 类型定义
// ============================================

export interface LearningConfig {
  /** 项目 ID */
  projectId: number;
  /** 每个标记点提取关键帧的数量（前后各提取几帧） */
  framesPerMarking?: number;
  /** 是否跳过已提取关键帧的视频 */
  skipExistingFrames?: boolean;
  /** 是否跳过已转录的视频 */
  skipExistingTranscript?: boolean;
  /** 进度回调 */
  onProgress?: (progress: number, message: string) => void;
}

export interface MarkingWithVideo {
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

export interface LearningResult {
  /** 生成的技能文件 ID */
  skillId: number;
  /** 分析的标记数量 */
  totalMarkings: number;
  /** 成功分析的标记数量 */
  successCount: number;
  /** 失败的标记数量 */
  failureCount: number;
  /** 生成的技能内容（Markdown） */
  skillContent: string;
  /** 技能元数据（JSON） */
  skillMetadata: {
    highlight_types: HighlightType[];
    hook_types: HookType[];
    editing_rules: EditingRule[];
    reasoning: string;
  };
}

export interface HighlightType {
  name: string;
  description: string;
  visual_features: string[];
  audio_features: string[];
  examples: Array<{
    timestamp: string;
    context: string;
  }>;
}

export interface HookType {
  name: string;
  description: string;
  visual_features: string[];
  audio_features: string[];
  examples: Array<{
    timestamp: string;
    context: string;
  }>;
}

export interface EditingRule {
  scenario: string;
  duration: string;
  rhythm: string;
  combination: string;
  cut_in: string;
  cut_out: string;
}

// ============================================
// 学习流程类
// ============================================

export class LearningPipeline {
  private geminiClient = getGeminiClient();
  private jobId: string;

  constructor(private config: LearningConfig) {
    this.jobId = `learning-${config.projectId}-${Date.now()}`;
  }

  /**
   * 执行完整的学习流程
   */
  async execute(): Promise<LearningResult> {
    console.log(`🎓 [学习流程] 开始执行项目 ${this.config.projectId} 的学习任务`);
    this.sendProgress(0, '初始化学习流程...');

    try {
      // 1. 数据准备
      this.sendProgress(5, '读取项目数据和标记信息...');
      const markings = await this.prepareData();

      if (markings.length === 0) {
        throw new Error('项目没有标记数据，无法进行学习');
      }

      console.log(`📊 [学习流程] 找到 ${markings.length} 个标记数据`);

      // 2. 多模态提取（关键帧 + 音频转录）
      this.sendProgress(10, '提取关键帧和转录音频...');
      const enrichedMarkings = await this.extractMultimodal(markings);

      // 3. Gemini 分析（归纳类型和规则）
      this.sendProgress(50, 'AI 分析中，归纳剪辑规律...');
      const analysisResult = await this.analyzeWithGemini(enrichedMarkings);

      // 4. 生成技能文件
      this.sendProgress(80, '生成剪辑技能文件...');
      const skill = await this.generateSkillFile(analysisResult);

      // 5. 完成
      this.sendProgress(100, '学习完成！');
      wsServer.sendComplete(this.jobId, {
        skillId: skill.id,
        projectId: this.config.projectId,
      });

      console.log(`✅ [学习流程] 学习完成！技能文件 ID: ${skill.id}`);

      return {
        skillId: skill.id,
        totalMarkings: markings.length,
        successCount: enrichedMarkings.filter(m => m.success).length,
        failureCount: enrichedMarkings.filter(m => !m.success).length,
        skillContent: skill.content,
        skillMetadata: analysisResult,
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '未知错误';
      console.error(`❌ [学习流程] 失败:`, errorMsg);
      wsServer.sendError(this.jobId, errorMsg);
      throw error;
    }
  }

  /**
   * 步骤 1: 数据准备
   */
  private async prepareData(): Promise<MarkingWithVideo[]> {
    // 1.1 获取项目信息
    const [project] = await db
      .select()
      .from(hlProjects)
      .where(eq(hlProjects.id, this.config.projectId));

    if (!project) {
      throw new Error(`项目 ${this.config.projectId} 不存在`);
    }

    // 1.2 获取项目的所有标记数据（关联视频信息）
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
      .where(eq(hlMarkings.projectId, this.config.projectId))
      .orderBy(hlMarkings.seconds);

    console.log(`📊 [数据准备] 项目 "${project.name}" 包含 ${markings.length} 个标记数据`);

    return markings as MarkingWithVideo[];
  }

  /**
   * 步骤 2: 多模态提取
   */
  private async extractMultimodal(markings: MarkingWithVideo[]) {
    console.log(`🎬 [多模态提取] 开始提取关键帧和转录音频...`);

    // 按视频分组，避免重复处理
    const videosMap = new Map<number, MarkingWithVideo[]>();
    for (const marking of markings) {
      if (!videosMap.has(marking.videoId)) {
        videosMap.set(marking.videoId, []);
      }
      videosMap.get(marking.videoId)!.push(marking);
    }

    console.log(`📹 [多模态提取] 涉及 ${videosMap.size} 个视频文件`);

    const enrichedMarkings: Array<MarkingWithVideo & {
      frameDescriptions?: string[];
      transcript?: string;
      success: boolean;
      error?: string;
    }> = [];

    let processedVideos = 0;
    let totalFramesExtracted = 0;
    let totalTranscripts = 0;

    // 处理每个视频
    for (const [videoId, videoMarkings] of videosMap.entries()) {
      const video = videoMarkings[0].video;
      const progressBase = 10 + (processedVideos / videosMap.size) * 40;

      this.sendProgress(
        progressBase,
        `处理第 ${video.episodeNumber} 集 (${processedVideos + 1}/${videosMap.size})...`
      );

      console.log(`\n📹 [视频 ${video.episodeNumber}] 处理 ${videoMarkings.length} 个标记点...`);

      try {
        // 2.1 提取关键帧（如果需要）
        let frameDescriptions: string[] = [];

        // 检查是否已有帧目录
        const frameDir = join(process.cwd(), 'public', 'keyframes', `hl-${videoId}`);

        if (existsSync(frameDir) && this.config.skipExistingFrames) {
          console.log(`  ✅ 关键帧已存在，跳过提取`);
          // 这里可以加载已有的帧描述，暂时跳过
        } else {
          // 提取关键帧（固定 30 帧，均匀分布）
          console.log(`  📸 提取关键帧...`);
          const keyframesResult = await extractKeyframes({
            videoPath: video.filePath,
            outputDir: frameDir,
            frameCount: 30,
          });

          totalFramesExtracted += keyframesResult.framePaths.length;

          // 生成帧描述（简化版：基于时间戳）
          frameDescriptions = keyframesResult.timestamps.map((ts, index) => {
            const seconds = Math.floor(ts / 1000);
            const minutes = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `帧 ${index + 1}: ${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
          });

          console.log(`  ✅ 提取了 ${keyframesResult.framePaths.length} 帧`);
        }

        // 2.2 转录音频（如果需要）
        let transcript = '';

        // 检查是否已有转录文件
        const transcriptPath = video.filePath.replace(/\.[^.]+$/, '-transcript.json');

        if (existsSync(transcriptPath) && this.config.skipExistingTranscript) {
          console.log(`  ✅ 转录文件已存在，跳过转录`);
          try {
            const transcriptData = JSON.parse(await readFile(transcriptPath, 'utf-8'));
            transcript = transcriptData.text || '';
            totalTranscripts++;
          } catch (error) {
            console.warn(`  ⚠️ 转录文件读取失败，将重新转录`);
          }
        }

        if (!transcript) {
          console.log(`  🎙️ 转录音频...`);

          // 提取音频（使用 FFmpeg，如果是视频文件）
          const audioPath = video.filePath.replace(/\.[^.]+$/, '.wav');

          // 如果音频不存在，先提取
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
          const transcriptionResult = await transcribeAudio(audioPath, {
            language: 'zh',
            model: 'tiny',
          });

          transcript = transcriptionResult.text;
          totalTranscripts++;

          // 保存转录结果
          await writeFile(transcriptPath, JSON.stringify(transcriptionResult, null, 2));

          console.log(`  ✅ 转录完成（${transcriptionResult.text.length} 字）`);

          // 清理临时音频文件
          const { unlink } = await import('fs/promises');
          try {
            await unlink(audioPath);
          } catch {}
        }

        // 为每个标记点分配数据
        for (const marking of videoMarkings) {
          // 找到最接近标记时间的关键帧
          const markingMs = marking.seconds * 1000;

          // 简化版：只提供转录文本，不提取特定帧
          enrichedMarkings.push({
            ...marking,
            transcript,
            success: true,
          });
        }

      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : '未知错误';
        console.error(`  ❌ 视频 ${video.episodeNumber} 处理失败:`, errorMsg);

        // 标记所有标记点为失败
        for (const marking of videoMarkings) {
          enrichedMarkings.push({
            ...marking,
            success: false,
            error: errorMsg,
          });
        }
      }

      processedVideos++;
    }

    console.log(`\n📊 [多模态提取] 完成:`);
    console.log(`   - 处理视频: ${processedVideos}/${videosMap.size}`);
    console.log(`   - 提取帧数: ${totalFramesExtracted}`);
    console.log(`   - 转录音频: ${totalTranscripts}`);
    console.log(`   - 成功标记: ${enrichedMarkings.filter(m => m.success).length}/${enrichedMarkings.length}`);

    return enrichedMarkings;
  }

  /**
   * 步骤 3: Gemini 分析
   */
  private async analyzeWithGemini(markings: Array<MarkingWithVideo & {
    transcript?: string;
    success: boolean;
  }>) {
    console.log(`\n🤖 [Gemini 分析] 开始分析 ${markings.length} 个标记点...`);

    // 过滤成功的标记
    const successMarkings = markings.filter(m => m.success);

    if (successMarkings.length === 0) {
      throw new Error('没有成功提取的标记数据，无法进行分析');
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

    console.log(`📺 [Gemini 分析] 涉及 ${episodesMap.size} 集视频`);

    // 读取 Prompt 模板
    const promptTemplate = await readFile(
      join(process.cwd(), 'prompts', 'hl-learning.md'),
      'utf-8'
    );

    // 构建分析请求
    const systemInstruction = `你是一位专业的短剧剪辑分析师，擅长从历史标记数据中总结剪辑技能和规律。
你需要基于真实的关键帧和转录文本进行分析，不要编造不存在的情节。
返回的 JSON 必须严格遵循指定的 schema。`;

    // 为每个标记点构建分析上下文
    const markingContexts = successMarkings.slice(0, 10).map((marking, index) => {
      const timeMin = Math.floor(marking.seconds / 60);
      const timeSec = marking.seconds % 60;
      const timestamp = `${timeMin.toString().padStart(2, '0')}:${timeSec.toString().padStart(2, '0')}`;

      // 提取转录文本中的相关片段（前后 5 秒）
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

    console.log(`📝 [Gemini 分析] 发送分析请求...`);

    // 调用 Gemini
    const response = await this.geminiClient.callApi(prompt, systemInstruction);

    if (!response.success || !response.data) {
      throw new Error(`Gemini 分析失败: ${response.error || '未知错误'}`);
    }

    // 解析 JSON 响应
    const jsonMatch = (response.data as string).match(/```json\n([\s\S]*?)\n```/);
    const jsonText = jsonMatch ? jsonMatch[1] : response.data as string;

    let analysisResult: {
      highlight_types: HighlightType[];
      hook_types: HookType[];
      editing_rules: EditingRule[];
      reasoning: string;
    };

    try {
      analysisResult = JSON.parse(jsonText);
      console.log(`✅ [Gemini 分析] 分析完成`);
      console.log(`   - 高光类型: ${analysisResult.highlight_types.length} 个`);
      console.log(`   - 钩子类型: ${analysisResult.hook_types.length} 个`);
      console.log(`   - 剪辑规则: ${analysisResult.editing_rules.length} 个`);
    } catch (error) {
      console.error(`❌ [Gemini 分析] JSON 解析失败:`, error);
      console.error(`响应内容:`, jsonText.substring(0, 500));
      throw new Error('Gemini 返回的 JSON 格式不正确');
    }

    return analysisResult;
  }

  /**
   * 步骤 4: 生成技能文件
   */
  private async generateSkillFile(analysisResult: {
    highlight_types: HighlightType[];
    hook_types: HookType[];
    editing_rules: EditingRule[];
    reasoning: string;
  }) {
    console.log(`\n📄 [技能生成] 生成技能文件...`);

    // 生成 Markdown 内容
    const markdown = this.generateSkillMarkdown(analysisResult);

    // 保存到数据库
    const [skill] = await db
      .insert(hlSkills)
      .values({
        projectId: this.config.projectId,
        name: `技能文件 v1.0`,
        version: 'v1.0',
        content: markdown,
        highlightTypes: JSON.stringify(analysisResult.highlight_types),
        hookTypes: JSON.stringify(analysisResult.hook_types),
        editingRules: JSON.stringify(analysisResult.editing_rules),
        generatedFrom: 'ai_learning',
        totalMarkings: 0, // 稍后更新
      })
      .returning();

    console.log(`✅ [技能生成] 技能文件已保存 (ID: ${skill.id})`);

    return skill;
  }

  /**
   * 生成技能 Markdown 内容
   */
  private generateSkillMarkdown(analysisResult: {
    highlight_types: HighlightType[];
    hook_types: HookType[];
    editing_rules: EditingRule[];
    reasoning: string;
  }): string {
    const lines: string[] = [];

    lines.push('# 剪辑技能文件\n');
    lines.push('> 本文件由 AI 学习自动生成，基于历史标记数据归纳剪辑规律。\n');
    lines.push('---\n');

    // 1. 分析推理
    lines.push('## 📊 分析推理\n');
    lines.push(analysisResult.reasoning);
    lines.push('\n---\n');

    // 2. 高光类型
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

    // 3. 钩子类型
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

    // 4. 剪辑规则
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

    return lines.join('');
  }

  /**
   * 发送进度更新
   */
  private sendProgress(progress: number, message: string) {
    console.log(`📊 [进度] ${progress}% - ${message}`);
    wsServer.sendProgress(this.jobId, progress, message);
    this.config.onProgress?.(progress, message);
  }
}

// ============================================
// 辅助函数
// ============================================

async function writeFile(filePath: string, content: string) {
  const { writeFile: fsWriteFile } = await import('fs/promises');
  await fsWriteFile(filePath, content, 'utf-8');
}

// ============================================
// 导出
// ============================================

export async function startLearning(config: LearningConfig): Promise<LearningResult> {
  const pipeline = new LearningPipeline(config);
  return pipeline.execute();
}
