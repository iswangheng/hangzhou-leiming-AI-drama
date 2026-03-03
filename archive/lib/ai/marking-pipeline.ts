// ============================================
// 杭州雷鸣 - 智能标记流程
// 根据技能文件自动标记视频的高光点和钩子点
// ============================================

import { readFile } from 'fs/promises';
import { join } from 'path';
import { extractKeyframes } from '../video/keyframes';
import { transcribeAudio } from '../audio/transcriber';
import { getGeminiClient } from '../api/gemini';
import { db } from '../db/client';
import { hlAiMarkings, hlAnalysisResults, hlVideos } from '../db/schema';
import { eq, and } from 'drizzle-orm';
import { wsServer } from '../ws/server';
import type { HLAnalysisResult, HLAiMarking, HLVideo, HLSkill } from '../db/schema';

// ============================================
// 类型定义
// ============================================

export interface MarkingPipelineOptions {
  /** 分析结果 ID */
  analysisId: number;
  /** 视频对象 */
  video: HLVideo;
  /** 技能文件内容（可选，不提供则使用默认） */
  skillContent?: string;
  /** 最小时长（毫秒） */
  minDurationMs?: number;
  /** 最大时长（毫秒） */
  maxDurationMs?: number;
  /** 进度回调 */
  onProgress?: (progress: number, step: string, found: number) => void;
}

export interface SegmentAnalysis {
  startMs: number;
  endMs: number;
  frameDescriptions: string;
  transcript: string;
}

export interface MarkingResult {
  highlights: Array<{
    timeMs: number;
    type: string;
    confidence: number;
    reasoning: string;
  }>;
  hooks: Array<{
    timeMs: number;
    type: string;
    confidence: number;
    reasoning: string;
  }>;
}

// ============================================
// 默认技能文件内容
// ============================================

const DEFAULT_SKILL_CONTENT = `
# 短剧剪辑技能标准

## 高光点定义
- **高能冲突**: 人物之间的激烈对抗、争吵、打斗场面
- **身份揭露**: 真实身份的揭示、秘密的曝光
- **情感高潮**: 角色情感爆发的时刻（痛哭、愤怒、震惊）
- **反转时刻**: 剧情发生突变的节点

## 钩子点定义
- **悬念结尾**: 在关键时刻截断，引发观众好奇
- **反转预告**: 暗示即将发生的剧情反转
- **疑问设置**: 通过对话或画面提出问题
- **冲突预告**: 预示即将爆发的矛盾冲突

## 评分标准
- 情绪强度: 0-10分
- 戏剧冲突: 0-10分
- 观众吸引力: 0-10分
`;

// ============================================
// 标记流程类
// ============================================

export class MarkingPipeline {
  private geminiClient = getGeminiClient();
  private jobId: string;

  constructor(private options: MarkingPipelineOptions) {
    this.jobId = `marking-${options.analysisId}-${Date.now()}`;
  }

  /**
   * 执行完整的标记流程
   */
  async execute(): Promise<HLAiMarking[]> {
    const { video, analysisId, onProgress } = this.options;

    console.log(`🎬 [智能标记] 开始处理视频: ${video.filename}`);
    this.sendProgress(0, '准备中...', 0);

    try {
      // ========================================
      // 步骤 1: 上下文加载
      // ========================================
      this.sendProgress(5, '加载技能文件...', 0);
      const skillContent = this.options.skillContent || DEFAULT_SKILL_CONTENT;

      // ========================================
      // 步骤 2: 视频预处理
      // ========================================
      this.sendProgress(10, '提取关键帧...', 0);
      const keyframesResult = await this.extractKeyframes();

      this.sendProgress(30, '转录音频...', 0);
      const transcriptResult = await this.transcribeAudio();

      // ========================================
      // 步骤 3: 分段分析
      // ========================================
      this.sendProgress(50, '分析视频内容...', 0);
      const markingResults = await this.analyzeSegments(
        keyframesResult,
        transcriptResult,
        skillContent
      );

      // ========================================
      // 步骤 4: 结果聚合
      // ========================================
      this.sendProgress(80, '聚合标记结果...', 0);
      const aggregatedMarkings = this.aggregateResults(markingResults);

      // ========================================
      // 步骤 5: 保存到数据库
      // ========================================
      this.sendProgress(90, '保存标记数据...', 0);
      const savedMarkings = await this.saveMarkings(aggregatedMarkings);

      // ========================================
      // 步骤 6: 更新分析结果
      // ========================================
      await this.updateAnalysisResults(aggregatedMarkings);

      this.sendProgress(100, '分析完成', aggregatedMarkings.length);
      this.sendComplete({
        totalMarkings: aggregatedMarkings.length,
        highlights: aggregatedMarkings.filter(m => m.type === '高光点').length,
        hooks: aggregatedMarkings.filter(m => m.type === '钩子点').length,
      });

      console.log(`✅ [智能标记] 完成! 共找到 ${aggregatedMarkings.length} 个标记`);
      return savedMarkings;

    } catch (error) {
      console.error('❌ [智能标记] 失败:', error);
      this.sendError(error instanceof Error ? error.message : '未知错误');
      throw error;
    }
  }

  /**
   * 步骤 2.1: 提取关键帧
   */
  private async extractKeyframes() {
    const { video } = this.options;

    console.log(`📸 [关键帧提取] 开始提取关键帧...`);

    // 检查是否已经提取过
    if (video.frameDir) {
      console.log(`✅ [关键帧提取] 已存在关键帧目录: ${video.frameDir}`);

      // 读取现有关键帧
      const fs = await import('fs/promises');
      const { readdir } = fs;

      try {
        const files = await readdir(video.frameDir);
        const frameFiles = files.filter(f => f.startsWith('keyframe') && (f.endsWith('.jpg') || f.endsWith('.png')));

        if (frameFiles.length > 0) {
          console.log(`✅ [关键帧提取] 找到 ${frameFiles.length} 个现有关键帧，跳过重新提取`);

          // 读取帧文件并排序
          const framePaths = frameFiles
            .sort()
            .map(f => `${video.frameDir}/${f}`);

          // 从文件名提取时间戳（如果可能）
          const timestamps: number[] = framePaths.map(() => 0); // 简化处理，实际可以从文件名解析

          return {
            framePaths,
            timestamps,
            outputDir: video.frameDir,
          };
        }
      } catch (error) {
        console.warn(`⚠️  [关键帧提取] 读取现有关键帧失败: ${error}，将重新提取`);
      }
    }

    // 提取关键帧（5fps，约2秒一帧）
    const result = await extractKeyframes({
      videoPath: video.filePath,
      frameCount: 30, // 30帧，保证足够密度
      filenamePrefix: `frame_${video.id}`,
    });

    console.log(`✅ [关键帧提取] 完成! 提取了 ${result.framePaths.length} 帧`);

    // 更新视频记录
    await db.update(hlVideos)
      .set({ frameDir: result.outputDir })
      .where(eq(hlVideos.id, video.id));

    return result;
  }

  /**
   * 步骤 2.2: 转录音频
   */
  private async transcribeAudio() {
    const { video } = this.options;

    console.log(`🎙️  [音频转录] 开始转录音频...`);

    // 检查是否已经转录过
    if (video.asrResultPath) {
      console.log(`✅ [音频转录] 已存在转录结果: ${video.asrResultPath}`);
      try {
        const result = JSON.parse(await readFile(video.asrResultPath, 'utf-8'));
        return result;
      } catch {
        console.warn('⚠️  [音频转录] 无法读取现有转录结果，重新转录');
      }
    }

    // 提取音频并转录
    const result = await transcribeAudio(
      video.filePath,
      { model: 'tiny', language: 'zh' }
    );

    console.log(`✅ [音频转录] 完成! 文本长度: ${result.text.length} 字`);

    // 保存转录结果
    const asrResultPath = join(process.cwd(), 'data', 'asr', `${video.id}.json`);
    await import('fs/promises').then(({ mkdir, writeFile }) => {
      mkdir(join(process.cwd(), 'data', 'asr'), { recursive: true });
      writeFile(asrResultPath, JSON.stringify(result, null, 2));
    });

    // 更新视频记录
    await db.update(hlVideos)
      .set({ asrResultPath })
      .where(eq(hlVideos.id, video.id));

    return result;
  }

  /**
   * 步骤 3: 分段分析
   */
  private async analyzeSegments(
    keyframesResult: { framePaths: string[]; timestamps: number[] },
    transcriptResult: { text: string; segments: any[] },
    skillContent: string
  ): Promise<MarkingResult[]> {
    const { video, minDurationMs = 30000, maxDurationMs = 180000 } = this.options;

    console.log(`🔍 [分段分析] 开始分段分析...`);

    // 计算分段数量（每段2-3分钟）
    const segmentDuration = 150000; // 2.5分钟
    const totalDuration = video.durationMs;
    const segmentCount = Math.ceil(totalDuration / segmentDuration);

    console.log(`   - 总时长: ${(totalDuration / 1000 / 60).toFixed(1)} 分钟`);
    console.log(`   - 分段数量: ${segmentCount} 段`);

    const results: MarkingResult[] = [];

    // 逐段分析
    for (let i = 0; i < segmentCount; i++) {
      const startMs = i * segmentDuration;
      const endMs = Math.min((i + 1) * segmentDuration, totalDuration);

      console.log(`\n📝 分析第 ${i + 1}/${segmentCount} 段 (${(startMs / 1000).toFixed(0)}s - ${(endMs / 1000).toFixed(0)}s)`);

      // 准备分段数据
      const segmentData = await this.prepareSegmentData(
        startMs,
        endMs,
        keyframesResult,
        transcriptResult
      );

      // 调用 Gemini 分析
      const result = await this.callGeminiForSegment(
        segmentData,
        skillContent,
        i + 1,
        segmentCount
      );

      if (result) {
        results.push(result);
        const foundCount = (result.highlights?.length || 0) + (result.hooks?.length || 0);
        console.log(`✅ 第 ${i + 1} 段分析完成，找到 ${foundCount} 个标记`);
      }

      // 更新进度
      const progress = 50 + Math.floor((i + 1) / segmentCount * 30);
      this.sendProgress(progress, `分析第 ${i + 1}/${segmentCount} 段`, results.reduce((sum, r) => sum + (r.highlights?.length || 0) + (r.hooks?.length || 0), 0));
    }

    console.log(`\n✅ [分段分析] 完成! 共分析 ${segmentCount} 段`);
    return results;
  }

  /**
   * 准备分段数据
   */
  private async prepareSegmentData(
    startMs: number,
    endMs: number,
    keyframesResult: { framePaths: string[]; timestamps: number[] },
    transcriptResult: { text: string; segments: any[] }
  ): Promise<SegmentAnalysis> {
    // 筛选时间段内的关键帧
    const segmentFrames = keyframesResult.timestamps
      .map((ts, index) => ({ timestamp: ts, path: keyframesResult.framePaths[index] }))
      .filter(f => f.timestamp >= startMs && f.timestamp <= endMs);

    // 生成关键帧描述（简化版，实际应该用 Gemini Vision）
    const frameDescriptions = segmentFrames.map(f => {
      const timeSec = (f.timestamp / 1000).toFixed(0);
      return `[${timeSec}s] ${f.path.split('/').pop()}`;
    }).join('\n');

    // 筛选时间段内的转录文本
    const segmentSegments = transcriptResult.segments.filter((s: any) => {
      const start = s.start * 1000;
      return start >= startMs && start <= endMs;
    });

    const transcript = segmentSegments.map((s: any) => s.text).join(' ');

    return {
      startMs,
      endMs,
      frameDescriptions,
      transcript: transcript || '（无对白）',
    };
  }

  /**
   * 调用 Gemini 分析单段
   */
  private async callGeminiForSegment(
    segmentData: SegmentAnalysis,
    skillContent: string,
    segmentIndex: number,
    totalSegments: number
  ): Promise<MarkingResult | null> {
    const { video } = this.options;
    const durationMin = ((segmentData.endMs - segmentData.startMs) / 1000 / 60).toFixed(1);

    // 读取 Prompt 模板
    const promptTemplate = await readFile(
      join(process.cwd(), 'prompts', 'hl-marking.md'),
      'utf-8'
    );

    // 填充 Prompt 变量
    const prompt = promptTemplate
      .replace('{{skill_content}}', skillContent)
      .replace('{{video_name}}', video.filename)
      .replace('{{start_ms}}', segmentData.startMs.toString())
      .replace('{{end_ms}}', segmentData.endMs.toString())
      .replace('{{duration_min}}', durationMin)
      .replace('{{frame_count}}', segmentData.frameDescriptions.split('\n').length.toString())
      .replace('{{frame_descriptions}}', segmentData.frameDescriptions)
      .replace('{{transcript}}', segmentData.transcript);

    // 调用 Gemini API
    const response = await this.geminiClient.callApi(prompt);

    if (!response.success || !response.data) {
      console.error(`❌ Gemini API 调用失败: ${response.error}`);
      return null;
    }

    // 解析 JSON 响应
    const result = this.parseGeminiResponse(response.data as string);

    if (result) {
      console.log(`✅ Gemini 分析成功: ${result.highlights.length} 高光 + ${result.hooks.length} 钩子`);
    }

    return result;
  }

  /**
   * 解析 Gemini 响应
   */
  private parseGeminiResponse(text: string): MarkingResult | null {
    try {
      // 尝试提取 JSON
      let jsonText = text;

      // 模式 1: markdown json 代码块
      const jsonMatch = text.match(/```json\n([\s\S]*?)\n```/);
      if (jsonMatch) {
        jsonText = jsonMatch[1];
      } else {
        // 模式 2: 普通代码块
        const codeMatch = text.match(/```\n([\s\S]*?)\n```/);
        if (codeMatch) {
          jsonText = codeMatch[1];
        } else {
          // 模式 3: 查找第一个 { 和最后一个 }
          const firstBrace = text.indexOf('{');
          const lastBrace = text.lastIndexOf('}');
          if (firstBrace !== -1 && lastBrace !== -1) {
            jsonText = text.substring(firstBrace, lastBrace + 1);
          }
        }
      }

      const parsed = JSON.parse(jsonText.trim()) as MarkingResult;

      // 验证数据结构
      if (!parsed.highlights || !Array.isArray(parsed.highlights)) {
        console.warn('⚠️  响应缺少 highlights 字段');
        parsed.highlights = [];
      }

      if (!parsed.hooks || !Array.isArray(parsed.hooks)) {
        console.warn('⚠️  响应缺少 hooks 字段');
        parsed.hooks = [];
      }

      return parsed;
    } catch (error) {
      console.error('❌ JSON 解析失败:', error);
      console.error('原始响应:', text.substring(0, 500));
      return null;
    }
  }

  /**
   * 步骤 4: 结果聚合和去重
   */
  private aggregateResults(results: MarkingResult[]): HLAiMarking[] {
    console.log(`\n📊 [结果聚合] 开始聚合 ${results.length} 个分段的结果...`);

    const allMarkings: HLAiMarking[] = [];
    const { analysisId, video } = this.options;

    // 收集所有标记
    results.forEach((result, segmentIndex) => {
      // 添加高光点
      result.highlights.forEach((h: any) => {
        allMarkings.push({
          id: 0, // 临时 ID，插入时会自动生成
          analysisId,
          videoId: video.id,
          startMs: h.timeMs,
          endMs: null, // 高光点是单点时刻
          type: '高光点',
          subType: h.type,
          score: h.confidence,
          reasoning: h.reasoning,
          emotion: null,
          intensity: null,
          isConfirmed: false,
          customStartMs: null,
          customEndMs: null,
          createdAt: new Date(),
          updatedAt: new Date(),
        });
      });

      // 添加钩子点
      result.hooks.forEach((h: any) => {
        allMarkings.push({
          id: 0, // 临时 ID，插入时会自动生成
          analysisId,
          videoId: video.id,
          startMs: h.timeMs,
          endMs: null,
          type: '钩子点',
          subType: h.type,
          score: h.confidence,
          reasoning: h.reasoning,
          emotion: null,
          intensity: null,
          isConfirmed: false,
          customStartMs: null,
          customEndMs: null,
          createdAt: new Date(),
          updatedAt: new Date(),
        });
      });
    });

    // 去重：时间接近的标记合并（5秒内）
    const deduplicatedMarkings = this.deduplicateMarkings(allMarkings, 5000);

    // 过滤：置信度 < 7.0 的标记
    const filteredMarkings = deduplicatedMarkings.filter(m => m.score >= 7.0);

    // 按置信度排序
    filteredMarkings.sort((a, b) => b.score - a.score);

    console.log(`✅ [结果聚合] 完成!`);
    console.log(`   - 原始标记: ${allMarkings.length}`);
    console.log(`   - 去重后: ${deduplicatedMarkings.length}`);
    console.log(`   - 过滤后(≥7.0): ${filteredMarkings.length}`);

    return filteredMarkings;
  }

  /**
   * 标记去重
   */
  private deduplicateMarkings(markings: HLAiMarking[], timeThresholdMs: number): HLAiMarking[] {
    const result: HLAiMarking[] = [];

    // 按时间排序
    const sorted = [...markings].sort((a, b) => a.startMs - b.startMs);

    sorted.forEach(marking => {
      // 查找是否有接近的标记
      const duplicate = result.find(existing => {
        const timeDiff = Math.abs(existing.startMs - marking.startMs);
        const sameType = existing.type === marking.type;
        return sameType && timeDiff < timeThresholdMs;
      });

      // 如果没有重复，添加
      if (!duplicate) {
        result.push(marking);
      } else {
        // 如果重复，保留置信度更高的
        if (marking.score > duplicate.score) {
          const index = result.indexOf(duplicate);
          result[index] = marking;
        }
      }
    });

    return result;
  }

  /**
   * 步骤 5: 保存标记到数据库
   */
  private async saveMarkings(markings: HLAiMarking[]): Promise<HLAiMarking[]> {
    console.log(`💾 [保存标记] 保存 ${markings.length} 个标记到数据库...`);

    // 批量插入
    const saved = await db.insert(hlAiMarkings).values(markings).returning();

    console.log(`✅ [保存标记] 完成! 保存了 ${saved.length} 个标记`);

    return saved;
  }

  /**
   * 步骤 6: 更新分析结果
   */
  private async updateAnalysisResults(markings: HLAiMarking[]) {
    const { analysisId } = this.options;

    const highlightsCount = markings.filter(m => m.type === '高光点').length;
    const hooksCount = markings.filter(m => m.type === '钩子点').length;

    console.log(`📊 [更新分析] 更新分析结果...`);

    await db.update(hlAnalysisResults)
      .set({
        status: 'completed',
        progress: 100,
        highlightsFound: highlightsCount,
        hooksFound: hooksCount,
        updatedAt: new Date(),
      })
      .where(eq(hlAnalysisResults.id, analysisId));

    console.log(`✅ [更新分析] 完成! ${highlightsCount} 高光 + ${hooksCount} 钩子`);
  }

  /**
   * 发送进度更新
   */
  private sendProgress(progress: number, step: string, found: number) {
    this.options.onProgress?.(progress, step, found);
    wsServer.sendProgress(this.jobId, progress, `${step} - 已发现 ${found} 个标记`);
  }

  /**
   * 发送错误
   */
  private sendError(error: string) {
    wsServer.sendError(this.jobId, error);
  }

  /**
   * 发送完成通知
   */
  private sendComplete(result: Record<string, unknown>) {
    wsServer.sendComplete(this.jobId, result);
  }
}

// ============================================
// 导出工厂函数
// ============================================

export async function runMarkingPipeline(options: MarkingPipelineOptions): Promise<HLAiMarking[]> {
  const pipeline = new MarkingPipeline(options);
  return pipeline.execute();
}
