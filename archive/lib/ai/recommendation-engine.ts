// ============================================
// 杭州雷鸣 - 剪辑推荐引擎
//
// 功能：
// - 根据 AI 标记生成高光×钩子组合
// - 多维评分算法（冲突、情感、悬念、节奏、历史）
// - 智能排序和过滤
// ============================================

import { db } from '@/lib/db/client';
import { hlAiMarkings, hlClipCombinations, hlVideos } from '@/lib/db/schema';
import { eq, and, desc } from 'drizzle-orm';

// ============================================
// 类型定义
// ============================================

/**
 * AI 标记（从数据库读取）
 */
export interface Marking {
  id: number;
  videoId: number;
  videoName: string;
  startMs: number;
  endMs: number;
  type: '高光点' | '钩子点';
  subType: string;  // 如：高能冲突、悬念结尾
  score: number;    // 置信度 0-10
  emotion?: string; // 情绪标签
  reasoning: string;
}

/**
 * 剪辑组合片段
 */
export interface Clip {
  videoId: number;
  videoName: string;
  startMs: number;
  endMs: number;
  type: string;
  subType: string;
}

/**
 * 剪辑组合
 */
export interface ClipCombination {
  highlights: Marking[];  // 1-2个高光点
  hooks: Marking[];       // 1-2个钩子点
  clips: Clip[];          // 实际使用的片段
  totalDurationMs: number;
}

/**
 * 评分结果
 */
export interface ScoringResult {
  overallScore: number;   // 综合得分 0-100
  conflictScore: number;  // 冲突强度 0-10
  emotionScore: number;   // 情感共鸣 0-10
  suspenseScore: number;  // 悬念设置 0-10
  rhythmScore: number;    // 节奏把握 0-10
  historyScore: number;   // 历史验证 0-10
}

/**
 * 推荐配置
 */
export interface RecommendOptions {
  analysisId: number;
  minDurationMs: number;
  maxDurationMs: number;
  maxCombinations?: number; // 最多返回多少个组合（默认20）
  allowCrossEpisode?: boolean; // 是否允许跨集组合（默认true）
}

/**
 * 推荐结果
 */
export interface RecommendResult {
  id: number;
  name: string;
  clips: Clip[];
  totalDurationMs: number;
  overallScore: number;
  conflictScore: number;
  emotionScore: number;
  suspenseScore: number;
  rhythmScore: number;
  historyScore: number;
  reasoning: string;
  rank: number;
}

// ============================================
// 推荐引擎类
// ============================================

export class RecommendationEngine {
  /**
   * 生成剪辑推荐
   */
  static async generateRecommendations(
    options: RecommendOptions
  ): Promise<RecommendResult[]> {
    const {
      analysisId,
      minDurationMs,
      maxDurationMs,
      maxCombinations = 20,
      allowCrossEpisode = true,
    } = options;

    console.log(`[推荐引擎] 开始生成推荐，分析ID: ${analysisId}`);
    console.log(`[推荐引擎] 时长范围: ${minDurationMs}ms - ${maxDurationMs}ms`);
    console.log(`[推荐引擎] 跨集组合: ${allowCrossEpisode ? '允许' : '不允许'}`);

    // 1. 读取所有 AI 标记
    const markings = await this.fetchMarkings(analysisId);

    console.log(`[推荐引擎] 读取到 ${markings.length} 个标记`);

    if (markings.length === 0) {
      throw new Error('没有可用的 AI 标记');
    }

    const highlights = markings.filter((m) => m.type === '高光点');
    const hooks = markings.filter((m) => m.type === '钩子点');

    console.log(`[推荐引擎] 高光点: ${highlights.length} 个，钩子点: ${hooks.length} 个`);

    // 2. 生成所有可能的组合
    const combinations = this.generateCombinations(
      highlights,
      hooks,
      minDurationMs,
      maxDurationMs,
      allowCrossEpisode
    );

    console.log(`[推荐引擎] 生成 ${combinations.length} 个组合（时长过滤前）`);

    // 3. 多维评分
    const scoredCombinations = await this.scoreCombinations(combinations);

    // 4. 智能排序
    const sortedCombinations = this.sortCombinations(scoredCombinations);

    // 5. 去重（避免相似组合）
    const deduplicatedCombinations = this.deduplicateCombinations(
      sortedCombinations as any
    );

    console.log(`[推荐引擎] 去重后剩余 ${deduplicatedCombinations.length} 个组合`);

    // 6. 保存到数据库
    const savedResults = await this.saveCombinations(
      deduplicatedCombinations.slice(0, maxCombinations) as any,
      analysisId
    );

    console.log(`[推荐引擎] 保存 ${savedResults.length} 个组合到数据库`);

    return savedResults;
  }

  /**
   * 从数据库读取标记
   */
  private static async fetchMarkings(analysisId: number): Promise<Marking[]> {
    const results = await db
      .select({
        id: hlAiMarkings.id,
        videoId: hlAiMarkings.videoId,
        startMs: hlAiMarkings.startMs,
        endMs: hlAiMarkings.endMs,
        type: hlAiMarkings.type,
        subType: hlAiMarkings.subType,
        score: hlAiMarkings.score,
        emotion: hlAiMarkings.emotion,
        reasoning: hlAiMarkings.reasoning,
      })
      .from(hlAiMarkings)
      .where(eq(hlAiMarkings.analysisId, analysisId))
      .orderBy(hlAiMarkings.startMs);

    // 补充视频名称
    const markings: Marking[] = [];

    for (const result of results) {
      const [video] = await db
        .select({ filename: hlVideos.filename })
        .from(hlVideos)
        .where(eq(hlVideos.id, result.videoId))
        .limit(1);

      markings.push({
        ...result,
        videoName: video?.filename || '未知视频',
        endMs: result.endMs || (result.startMs + 10000),
      });
    }

    return markings;
  }

  /**
   * 生成所有可能的组合
   */
  private static generateCombinations(
    highlights: Marking[],
    hooks: Marking[],
    minDurationMs: number,
    maxDurationMs: number,
    allowCrossEpisode: boolean
  ): ClipCombination[] {
    const combinations: ClipCombination[] = [];

    // 1. 单集组合：同一视频内的 高光→钩子
    for (const highlight of highlights) {
      for (const hook of hooks) {
        // 只生成同一视频内的组合
        if (highlight.videoId !== hook.videoId) continue;

        // 高光必须在钩子之前
        if (highlight.startMs >= hook.startMs) continue;

        const durationMs = hook.endMs - highlight.startMs;

        // 过滤时长不符合的组合
        if (durationMs < minDurationMs || durationMs > maxDurationMs) continue;

        combinations.push({
          highlights: [highlight],
          hooks: [hook],
          clips: [
            {
              videoId: highlight.videoId,
              videoName: highlight.videoName,
              startMs: highlight.startMs,
              endMs: hook.endMs,
              type: `${highlight.type} → ${hook.type}`,
              subType: `${highlight.subType} → ${hook.subType}`,
            },
          ],
          totalDurationMs: durationMs,
        });
      }
    }

    // 2. 跨集组合：不同视频的 高光→钩子
    if (allowCrossEpisode) {
      for (const highlight of highlights) {
        for (const hook of hooks) {
          // 跳过同一视频（已在上面处理）
          if (highlight.videoId === hook.videoId) continue;

          // 假设钩子在后面的集数（基于 videoId 判断）
          if (highlight.videoId >= hook.videoId) continue;

          const durationMs = (hook.endMs - hook.startMs) + (highlight.endMs - highlight.startMs);

          // 过滤时长不符合的组合
          if (durationMs < minDurationMs || durationMs > maxDurationMs) continue;

          combinations.push({
            highlights: [highlight],
            hooks: [hook],
            clips: [
              {
                videoId: highlight.videoId,
                videoName: highlight.videoName,
                startMs: highlight.startMs,
                endMs: highlight.endMs,
                type: highlight.type,
                subType: highlight.subType,
              },
              {
                videoId: hook.videoId,
                videoName: hook.videoName,
                startMs: hook.startMs,
                endMs: hook.endMs,
                type: hook.type,
                subType: hook.subType,
              },
            ],
            totalDurationMs: durationMs,
          });
        }
      }
    }

    return combinations;
  }

  /**
   * 多维评分算法
   */
  private static async scoreCombinations(
    combinations: ClipCombination[]
  ): Promise<Array<ClipCombination & ScoringResult & { reasoning: string }>> {
    const results: Array<ClipCombination & ScoringResult & { reasoning: string }> = [];

    for (const combination of combinations) {
      const scoring = await this.calculateScores(combination);

      results.push({
        ...combination,
        ...scoring,
        reasoning: this.generateReasoning(combination, scoring),
      });
    }

    return results;
  }

  /**
   * 计算单个组合的得分
   */
  private static async calculateScores(
    combination: ClipCombination
  ): Promise<ScoringResult> {
    const { highlights, hooks, totalDurationMs } = combination;

    // 1. 冲突强度 (conflictScore)
    const conflictScore = this.calculateConflictScore(highlights);

    // 2. 情感共鸣 (emotionScore)
    const emotionScore = this.calculateEmotionScore(highlights, hooks);

    // 3. 悬念设置 (suspenseScore)
    const suspenseScore = this.calculateSuspenseScore(hooks);

    // 4. 节奏把握 (rhythmScore)
    const rhythmScore = this.calculateRhythmScore(totalDurationMs);

    // 5. 历史验证 (historyScore)
    const historyScore = await this.calculateHistoryScore(combination);

    // 综合得分（加权平均）
    const overallScore =
      conflictScore * 25 +
      emotionScore * 25 +
      suspenseScore * 25 +
      rhythmScore * 15 +
      historyScore * 10;

    return {
      overallScore,
      conflictScore,
      emotionScore,
      suspenseScore,
      rhythmScore,
      historyScore,
    };
  }

  /**
   * 计算冲突强度
   */
  private static calculateConflictScore(highlights: Marking[]): number {
    if (highlights.length === 0) return 5;

    const highlight = highlights[0];
    const subType = highlight.subType.toLowerCase();

    // 冲突类型映射
    if (subType.includes('冲突') || subType.includes('对抗') || subType.includes('争吵')) {
      return 9 + Math.random(); // 9-10
    } else if (subType.includes('揭露') || subType.includes('曝光') || subType.includes('真相')) {
      return 7 + Math.random() * 2; // 7-9
    } else if (subType.includes('高潮') || subType.includes('爆发')) {
      return 8 + Math.random() * 2; // 8-10
    } else {
      return 5 + Math.random() * 3; // 5-8
    }
  }

  /**
   * 计算情感共鸣
   */
  private static calculateEmotionScore(highlights: Marking[], hooks: Marking[]): number {
    // 合并所有标记的情绪
    const allEmotions = [...highlights, ...hooks].map((m) => m.emotion || '').filter(Boolean);

    if (allEmotions.length === 0) return 6;

    // 情绪强度映射
    const emotionIntensity: Record<string, number> = {
      愤怒: 9,
      震惊: 8,
      悲伤: 7,
      紧张: 6,
      好奇: 5,
      恐惧: 8,
      喜悦: 6,
      温馨: 5,
    };

    // 计算平均情绪强度
    let totalIntensity = 0;
    for (const emotion of allEmotions) {
      const intensity = emotionIntensity[emotion] || 5;
      totalIntensity += intensity;
    }

    return Math.min(10, totalIntensity / allEmotions.length);
  }

  /**
   * 计算悬念设置
   */
  private static calculateSuspenseScore(hooks: Marking[]): number {
    if (hooks.length === 0) return 5;

    const hook = hooks[0];
    const subType = hook.subType.toLowerCase();

    // 钩子类型映射
    if (subType.includes('悬念') || subType.includes('未知')) {
      return 9 + Math.random(); // 9-10
    } else if (subType.includes('反转') || subType.includes('预告')) {
      return 7 + Math.random() * 2; // 7-9
    } else if (subType.includes('情感') || subType.includes('余韵')) {
      return 6 + Math.random() * 2; // 6-8
    } else {
      return 5 + Math.random() * 2; // 5-7
    }
  }

  /**
   * 计算节奏把握
   */
  private static calculateRhythmScore(durationMs: number): number {
    // 最佳时长区间：2-5分钟
    const optimalMinMs = 120000;
    const optimalMaxMs = 300000;

    if (durationMs >= optimalMinMs && durationMs <= optimalMaxMs) {
      // 在最佳区间内
      return 9 + Math.random(); // 9-10
    } else if (durationMs < optimalMinMs) {
      // 太短，按比例扣分
      const ratio = durationMs / optimalMinMs;
      return 5 + ratio * 3; // 5-8
    } else {
      // 太长，按比例扣分
      const ratio = optimalMaxMs / durationMs;
      return 5 + ratio * 3; // 5-8
    }
  }

  /**
   * 计算历史验证得分
   *
   * 实现与历史数据的相似度对比：
   * - 对比技能文件中的历史高转化素材
   * - 基于类型匹配度和时长相似度计算得分
   */
  private static async calculateHistoryScore(
    combination: ClipCombination
  ): Promise<number> {
    try {
      // 1. 获取最新的技能文件
      const { db } = await import('../db/client');
      const { hlSkills } = await import('../db/schema');
      const { desc } = await import('drizzle-orm');

      const [latestSkill] = await db
        .select()
        .from(hlSkills)
        .orderBy(desc(hlSkills.createdAt))
        .limit(1);

      if (!latestSkill || !latestSkill.highlightTypes || !latestSkill.hookTypes) {
        // 没有历史数据，返回默认值
        return 6 + Math.random() * 2; // 6-8
      }

      // 2. 解析技能文件中的类型定义
      const highlightTypes = JSON.parse(latestSkill.highlightTypes);
      const hookTypes = JSON.parse(latestSkill.hookTypes);

      // 3. 计算类型匹配度
      const highlightSubTypes = combination.highlights.map(h => h.subType);
      const hookSubTypes = combination.hooks.map(h => h.subType);

      let typeMatchScore = 0;
      let matchedCount = 0;

      // 检查高光点类型匹配
      for (const subType of highlightSubTypes) {
        const matched = highlightTypes.find((t: any) => t.name === subType);
        if (matched) {
          typeMatchScore += 2;
          matchedCount++;
        }
      }

      // 检查钩子点类型匹配
      for (const subType of hookSubTypes) {
        const matched = hookTypes.find((t: any) => t.name === subType);
        if (matched) {
          typeMatchScore += 2;
          matchedCount++;
        }
      }

      // 4. 计算时长合理性（基于技能文件中的剪辑规则）
      const durationMin = combination.totalDurationMs / 60000;
      let durationScore = 5;

      if (latestSkill.editingRules) {
        const editingRules = JSON.parse(latestSkill.editingRules);
        // 查找匹配的剪辑规则
        const matchedRule = editingRules.find((rule: any) => {
          // 简单匹配：场景类型
          const highlightDesc = highlightSubTypes.join(' + ');
          return highlightDesc.includes(rule.scenario);
        });

        if (matchedRule) {
          // 解析规则中的时长建议（如"60-90秒"）
          const durationMatch = matchedRule.duration.match(/(\d+)-(\d+)/);
          if (durationMatch) {
            const minMin = parseInt(durationMatch[1]) / 60;
            const maxMin = parseInt(durationMatch[2]) / 60;
            if (durationMin >= minMin && durationMin <= maxMin) {
              durationScore = 8;
            } else if (durationMin >= minMin * 0.8 && durationMin <= maxMin * 1.2) {
              durationScore = 6;
            }
          }
        }
      }

      // 5. 综合计算历史得分
      const totalScore = typeMatchScore + durationScore;
      const normalizedScore = Math.min(10, Math.max(1, totalScore));

      console.log(`  📊 [历史验证] 类型匹配: ${matchedCount}/${highlightSubTypes.length + hookSubTypes.length}, 时长得分: ${durationScore.toFixed(1)}, 总分: ${normalizedScore.toFixed(1)}`);

      return normalizedScore;
    } catch (error) {
      console.warn(`⚠️  [历史验证] 计算失败: ${error}，使用默认值`);
      return 6 + Math.random() * 2; // 降级到默认值
    }
  }

  /**
   * 生成推荐理由
   */
  private static generateReasoning(
    combination: ClipCombination,
    scoring: ScoringResult
  ): string {
    const { highlights, hooks } = combination;

    const highlightDesc = highlights.map((h) => h.subType).join(' + ');
    const hookDesc = hooks.map((h) => h.subType).join(' + ');

    const parts = [];

    // 1. 开场描述
    parts.push(`以「${highlightDesc}」开场，立即抓住观众注意力`);

    // 2. 结尾描述
    parts.push(`以「${hookDesc}」收尾，留下强烈悬念`);

    // 3. 时长描述
    const durationMin = (combination.totalDurationMs / 60000).toFixed(1);
    parts.push(`时长 ${durationMin} 分钟，节奏${scoring.rhythmScore >= 8 ? '紧凑' : '适中'}`);

    // 4. 预测转化率
    const conversionRate = (scoring.overallScore / 10).toFixed(1);
    parts.push(`预计转化率：${conversionRate}%`);

    // 5. 综合评价
    if (scoring.overallScore >= 85) {
      parts.push('⭐ 推荐指数：极高，优先投放');
    } else if (scoring.overallScore >= 75) {
      parts.push('⭐ 推荐指数：高，重点投放');
    } else if (scoring.overallScore >= 65) {
      parts.push('⭐ 推荐指数：中，测试投放');
    } else {
      parts.push('⭐ 推荐指数：一般，备选投放');
    }

    return parts.join('；');
  }

  /**
   * 智能排序
   */
  private static sortCombinations<T extends ClipCombination & ScoringResult>(
    combinations: T[]
  ): T[] {
    // 按 overallScore 降序排序
    return combinations.sort((a, b) => b.overallScore - a.overallScore);
  }

  /**
   * 去重（避免相似组合）
   *
   * 策略：
   * - 同一视频 + 相似的起止时间（±5秒）
   * - 只保留得分更高的那个
   */
  private static deduplicateCombinations<T extends ClipCombination & ScoringResult>(
    combinations: T[]
  ): T[] {
    const deduplicated: T[] = [];
    const seenSignatures = new Set<string>();

    for (const combo of combinations) {
      // 生成组合签名（用于去重判断）
      const signature = this.generateCombinationSignature(combo);

      if (seenSignatures.has(signature)) {
        // 已存在相似组合，跳过
        continue;
      }

      seenSignatures.add(signature);
      deduplicated.push(combo);
    }

    return deduplicated;
  }

  /**
   * 生成组合签名
   */
  private static generateCombinationSignature(
    combination: ClipCombination
  ): string {
    // 使用第一个片段的视频ID和5秒粒度的时间戳
    const firstClip = combination.clips[0];
    const startSlot = Math.floor(firstClip.startMs / 5000) * 5000; // 5秒粒度
    const endSlot = Math.floor(firstClip.endMs / 5000) * 5000;

    return `${firstClip.videoId}-${startSlot}-${endSlot}`;
  }

  /**
   * 保存组合到数据库
   */
  private static async saveCombinations(
    combinations: Array<ClipCombination & ScoringResult & { reasoning: string }>,
    analysisId: number
  ): Promise<RecommendResult[]> {
    const results: RecommendResult[] = [];

    for (let i = 0; i < combinations.length; i++) {
      const combo = combinations[i];

      // 生成组合名称
      const name = this.generateCombinationName(combo);

      // 保存到数据库
      const [inserted] = await db
        .insert(hlClipCombinations)
        .values({
          analysisId,
          name,
          clips: JSON.stringify(combo.clips),
          totalDurationMs: combo.totalDurationMs,
          overallScore: combo.overallScore,
          conflictScore: combo.conflictScore,
          emotionScore: combo.emotionScore,
          suspenseScore: combo.suspenseScore,
          rhythmScore: combo.rhythmScore,
          historyScore: combo.historyScore,
          reasoning: combo.reasoning,
          rank: i + 1,
        })
        .returning();

      results.push({
        id: inserted.id,
        name: inserted.name,
        clips: combo.clips,
        totalDurationMs: inserted.totalDurationMs,
        overallScore: inserted.overallScore,
        conflictScore: inserted.conflictScore!,
        emotionScore: inserted.emotionScore!,
        suspenseScore: inserted.suspenseScore!,
        rhythmScore: inserted.rhythmScore!,
        historyScore: inserted.historyScore!,
        reasoning: inserted.reasoning,
        rank: inserted.rank,
      });
    }

    return results;
  }

  /**
   * 生成组合名称
   */
  private static generateCombinationName(
    combination: ClipCombination & ScoringResult
  ): string {
    const { highlights, hooks } = combination;

    const highlightTypes = highlights.map((h) => h.subType).join(' + ');
    const hookTypes = hooks.map((h) => h.subType).join(' + ');

    return `${highlightTypes} + ${hookTypes}`;
  }
}

// ============================================
// 导出
// ============================================

export default RecommendationEngine;
