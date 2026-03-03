// ============================================
// API 客户端统一导出
// ============================================

// 只导出类，不导出单例（避免启动时初始化）
export { GeminiClient } from './gemini';
export { ElevenLabsClient } from './elevenlabs';
export { projectsApi, videosApi } from './projects';

// 导出类型
export type {
  // Gemini 类型
  GeminiResponse,
  Scene,
  VideoAnalysis,
  HighlightMoment,
  ViralMoment,  // 添加 ViralMoment 别名
  Storyline,
  RecapScript,
  // ElevenLabs 类型
  ElevenLabsResponse,
  WordTimestamp,
  TTSOptions,
  TTSResult,
  Voice,
  Model,
  // 通用错误类型
  APIError,
  NetworkError,
  TimeoutError,
  AuthenticationError,
  RateLimitError,
} from './types';

// 项目管理 API 类型
export type { ProjectWithStats, ApiResponse } from './projects';

// 数据库类型（重新导出）
export type {
  Video,
  NewVideo,
  Project,
  NewProject,
} from '@/lib/db';
