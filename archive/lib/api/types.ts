// ============================================
// API 类型定义统一导出
// ============================================

// ------------------------------------------
// Gemini 类型
// ------------------------------------------
export interface GeminiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface Scene {
  startMs: number;
  endMs: number;
  description: string;
  emotion: string;
  dialogue?: string;
  characters?: string[];
  viralScore?: number;
}

export interface VideoAnalysis {
  summary: string;
  scenes: Scene[];
  storylines: string[];
  viralScore: number;
  highlights: number[];
  durationMs: number;
}

/**
 * 病毒式传播时刻（高光候选点）
 * 符合 types/api-contracts.ts 接口契约
 */
export interface HighlightMoment {
  timestampMs: number;     // 时间戳（毫秒）
  type: "plot_twist" | "reveal" | "conflict" | "emotional" | "climax"; // 匹配接口契约
  confidence: number;      // 置信度 (0-1)
  description: string;     // 描述（对应原来的 reason）
  suggestedStartMs: number; // 建议开始时间（毫秒）
  suggestedEndMs: number;   // 建议结束时间（毫秒）

  // 保留原有字段以兼容现有代码
  viralScore?: number;     // 爆款分数
  category?: 'conflict' | 'emotional' | 'reversal' | 'climax' | 'other'; // 原分类
  suggestedDuration?: number; // 原建议时长（秒），可转换计算 EndMs
}

/**
 * ViralMoment 类型别名
 * 完全符合 types/api-contracts.ts 接口契约
 */
export type ViralMoment = HighlightMoment;

export interface Storyline {
  id: string;
  name: string;
  description: string;
  scenes: Scene[];
  attractionScore: number;
}

export interface RecapScript {
  storylineId: string;
  style: 'hook' | 'roast' | 'suspense' | 'emotional' | 'humorous';
  title: string;
  paragraphs: {
    text: string;
    videoCues: string[];
  }[];
  estimatedDurationMs: number;
}

// ------------------------------------------
// ElevenLabs 类型
// ------------------------------------------
export interface ElevenLabsResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface WordTimestamp {
  word: string;
  startMs: number;
  endMs: number;
  confidence?: number;
}

export interface TTSOptions {
  text: string;
  voiceId?: string;
  modelId?: string;
  stability?: number;
  similarityBoost?: number;
  outputFormat?: string;
}

export interface TTSResult {
  audioBuffer: Buffer;
  durationMs: number;
  wordTimestamps: WordTimestamp[];
  format: string;
  sampleRate: number;
}

export interface Voice {
  voice_id: string;
  name: string;
  category: string;
  labels?: Record<string, string>;
  preview_url?: string;
}

export interface Model {
  model_id: string;
  name: string;
}

// ------------------------------------------
// 通用 API 错误类型
// ------------------------------------------
export class APIError extends Error {
  constructor(
    message: string,
    public code?: string,
    public statusCode?: number
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class NetworkError extends APIError {
  constructor(message: string) {
    super(message, 'NETWORK_ERROR');
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends APIError {
  constructor(message: string) {
    super(message, 'TIMEOUT');
    this.name = 'TimeoutError';
  }
}

export class AuthenticationError extends APIError {
  constructor(message: string) {
    super(message, 'AUTH_ERROR', 401);
    this.name = 'AuthenticationError';
  }
}

export class RateLimitError extends APIError {
  constructor(message: string) {
    super(message, 'RATE_LIMIT', 429);
    this.name = 'RateLimitError';
  }
}
