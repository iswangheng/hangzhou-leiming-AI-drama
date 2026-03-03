// ============================================
// 高光切片数据转换工具
// 连接 AI 分析、数据库存储和前端展示
// ============================================

import type { ViralMoment } from '@/types/api-contracts';
import type { GeminiClient } from './gemini';

// ============================================
// 类型定义
// ============================================

/**
 * 数据库 Highlight 记录（对应 schema.highlights）
 */
export interface HighlightRecord {
  videoId: number;
  startMs: number;
  endMs?: number;
  durationMs?: number;
  reason: string;
  viralScore: number;
  category: 'conflict' | 'emotional' | 'reversal' | 'climax' | 'other';
  isConfirmed?: boolean;
  customStartMs?: number;
  customEndMs?: number;
  exportedPath?: string;
}

/**
 * 前端 HighlightClip 数据（对应 app/highlight/page.tsx）
 */
export interface HighlightClip {
  id: string;
  name: string;
  sourceVideoId: string;
  sourceVideoName: string;
  sourceEpisodeNumber?: number;
  highlightMomentMs: number;           // AI 检测到的高光时刻（毫秒）
  originalDurationMs: number;
  startMs: number;
  endMs: number;
  finalDurationMs: number;
  crossesEpisode: boolean;
  endVideoId?: string;
  endVideoName?: string;
  source: "ai" | "manual";
  viralScore?: number;
  reason?: string;
  status: "pending" | "in_queue" | "rendering" | "completed" | "failed";
  errorMessage?: string;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * 数据库 Highlight（带ID）
 */
export interface HighlightWithId extends HighlightRecord {
  id: number;
  createdAt: Date;
  updatedAt: Date;
}

// ============================================
// 转换函数
// ============================================

/**
 * 映射 ViralMoment.type 到 Highlight.category
 */
function mapTypeToCategory(
  type: ViralMoment['type']
): HighlightRecord['category'] {
  const mapping: Record<ViralMoment['type'], HighlightRecord['category']> = {
    'plot_twist': 'reversal',
    'reveal': 'climax',
    'conflict': 'conflict',
    'emotional': 'emotional',
    'climax': 'climax',
  };

  return mapping[type] || 'other';
}

/**
 * 将 ViralMoment 转换为 HighlightRecord（用于数据库插入）
 *
 * @param moment - Gemini 返回的病毒时刻
 * @param videoId - 视频 ID
 * @returns HighlightRecord
 */
export function viralMomentToHighlightRecord(
  moment: ViralMoment,
  videoId: number
): HighlightRecord {
  const startMs = moment.suggestedStartMs;
  const endMs = moment.suggestedEndMs;
  const durationMs = endMs - startMs;

  // 转换 confidence (0-1) 到 viralScore (0-10)
  const viralScore = moment.confidence * 10;

  return {
    videoId,
    startMs,
    endMs,
    durationMs,
    reason: moment.description,
    viralScore,
    category: mapTypeToCategory(moment.type),
    isConfirmed: false,
  };
}

/**
 * 将数据库 Highlight 转换为前端 HighlightClip
 *
 * @param highlight - 数据库记录
 * @param videoName - 视频名称（可选）
 * @returns HighlightClip
 */
export function highlightToClip(
  highlight: HighlightWithId,
  videoName?: string
): HighlightClip {
  const startMs = highlight.customStartMs ?? highlight.startMs;
  const endMs = highlight.customEndMs ?? highlight.endMs ?? highlight.startMs + (highlight.durationMs || 60000);

  return {
    id: highlight.id.toString(),
    name: `高光 #${highlight.id}`,
    sourceVideoId: highlight.videoId.toString(),
    sourceVideoName: videoName || `视频 #${highlight.videoId}`,
    sourceEpisodeNumber: undefined,
    highlightMomentMs: highlight.startMs,
    originalDurationMs: highlight.durationMs || (endMs - startMs),
    startMs,
    endMs,
    finalDurationMs: endMs - startMs,
    crossesEpisode: false,
    source: 'ai',
    viralScore: highlight.viralScore,
    reason: highlight.reason,
    status: highlight.isConfirmed ? 'pending' : 'pending', // 根据业务逻辑调整
    createdAt: highlight.createdAt,
    updatedAt: highlight.updatedAt,
  };
}

/**
 * 批量转换 ViralMoment[] 为 HighlightRecord[]
 *
 * @param moments - Gemini 返回的病毒时刻数组
 * @param videoId - 视频 ID
 * @returns HighlightRecord[]
 */
export function viralMomentsToHighlightRecords(
  moments: ViralMoment[],
  videoId: number
): HighlightRecord[] {
  return moments.map((moment) => viralMomentToHighlightRecord(moment, videoId));
}

/**
 * 批量转换数据库 Highlight[] 为前端 HighlightClip[]
 *
 * @param highlights - 数据库记录数组
 * @param videoNames - 视频 ID 到名称的映射（可选）
 * @returns HighlightClip[]
 */
export function highlightsToClips(
  highlights: HighlightWithId[],
  videoNames?: Record<number, string>
): HighlightClip[] {
  return highlights.map((highlight) =>
    highlightToClip(highlight, videoNames?.[highlight.videoId])
  );
}

// ============================================
// 工具函数
// ============================================

/**
 * 格式化毫秒为可读时间
 *
 * @param ms - 毫秒数
 * @returns 格式化的时间字符串 (HH:MM:SS.mmm)
 */
export function formatMs(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const milliseconds = ms % 1000;

  const pad = (n: number, size: number) => n.toString().padStart(size, '0');

  if (hours > 0) {
    return `${pad(hours, 2)}:${pad(minutes, 2)}:${pad(seconds, 2)}.${pad(milliseconds, 3)}`;
  }

  return `${pad(minutes, 2)}:${pad(seconds, 2)}.${pad(milliseconds, 3)}`;
}

/**
 * 计算高光的描述性名称
 *
 * @param highlight - 高光记录
 * @returns 描述性名称
 */
export function getHighlightName(highlight: HighlightRecord | HighlightWithId): string {
  const categoryLabels: Record<HighlightRecord['category'], string> = {
    conflict: '冲突',
    emotional: '情感',
    reversal: '反转',
    climax: '高潮',
    other: '其他',
  };

  const categoryLabel = categoryLabels[highlight.category];
  const timeLabel = formatMs(highlight.startMs);

  return `${categoryLabel}时刻 @ ${timeLabel}`;
}
