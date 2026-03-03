// ============================================
// DramaCut AI 统一配置管理
// ============================================

// 加载环境变量（必须在所有其他代码之前）
import * as dotenv from 'dotenv';
import path from 'path';

// 加载 .env.local 文件
const envPath = path.join(process.cwd(), '.env.local');
const result = dotenv.config({ path: envPath });

if (result.error) {
  console.warn('⚠️  [config] 警告: 无法加载 .env.local 文件:', result.error.message);
}

/**
 * 环境变量验证辅助函数
 * @throws 当必需的环境变量未定义时抛出错误
 */
function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

/**
 * 安全获取环境变量，提供默认值
 */
function getEnv(key: string, defaultValue: string): string {
  return process.env[key] || defaultValue;
}

/**
 * 解析布尔值环境变量
 */
function getBooleanEnv(key: string, defaultValue: boolean = false): boolean {
  const value = process.env[key];
  if (value === undefined) return defaultValue;
  return value === 'true' || value === '1';
}

/**
 * 解析数字环境变量
 */
function getNumberEnv(key: string, defaultValue: number): number {
  const value = process.env[key];
  if (!value) return defaultValue;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
}

// ============================================
// 应用配置
// ============================================
export const config = {
  // 基础配置
  env: getEnv('NODE_ENV', 'development') as 'development' | 'production' | 'test',
  port: getNumberEnv('PORT', 3000),
  appUrl: getEnv('NEXT_PUBLIC_APP_URL', 'http://localhost:3000'),
  isDev: getEnv('NODE_ENV', 'development') === 'development',
  isProd: getEnv('NODE_ENV', 'development') === 'production',

  // 调试模式
  debug: getBooleanEnv('DEBUG', true),
  logLevel: getEnv('LOG_LEVEL', 'info'),
  logDir: getEnv('LOG_DIR', './logs'),
  logMaxFiles: getNumberEnv('LOG_MAX_FILES', 7),
  logMaxSize: getEnv('LOG_MAX_SIZE', '10M'),

  // 安全配置
  jwtSecret: getEnv('JWT_SECRET', 'change-this-secret-in-production'),
  rateLimitMaxRequests: getNumberEnv('RATE_LIMIT_MAX_REQUESTS', 100),
  rateLimitWindowMs: getNumberEnv('RATE_LIMIT_WINDOW_MS', 60000),
} as const;

// ============================================
// Gemini API 配置
// ============================================
export const geminiConfig = {
  // API 密钥
  apiKey: process.env.GEMINI_API_KEY || process.env.YUNWU_API_KEY,

  // API 端点
  endpoint: process.env.YUNWU_API_ENDPOINT,

  // 模型配置
  model: getEnv('GEMINI_MODEL', 'gemini-2.5-flash-exp'),
  temperature: getNumberEnv('GEMINI_TEMPERATURE', 7) / 10,
  maxTokens: getNumberEnv('GEMINI_MAX_TOKENS', 8192),

  // 视频分析配置
  videoMaxDurationSeconds: getNumberEnv('GEMINI_VIDEO_MAX_DURATION_SECONDS', 600),
  videoSampleFrameCount: getNumberEnv('GEMINI_VIDEO_SAMPLE_FRAME_COUNT', 30),

  // 请求超时配置（毫秒）
  timeout: 600000, // 10 分钟（视频分析需要更长时间）
  retryAttempts: 3,
  retryDelay: 2000,
} as const;

// ============================================
// ElevenLabs API 配置
// ============================================
export const elevenlabsConfig = {
  // API 密钥
  apiKey: process.env.ELEVENLABS_API_KEY,
  endpoint: getEnv('ELEVENLABS_API_ENDPOINT', 'https://api.elevenlabs.io/v1'),

  // 默认语音配置
  defaultVoice: getEnv('ELEVENLABS_DEFAULT_VOICE', 'eleven_multilingual_v2'),
  defaultModel: getEnv('ELEVENLABS_DEFAULT_MODEL', 'eleven_multilingual_v2'),

  // 音频输出配置
  outputFormat: getEnv('ELEVENLABS_OUTPUT_FORMAT', 'mp3_44100_128'),
  stability: getNumberEnv('ELEVENLABS_STABILITY', 5) / 10,
  similarityBoost: getNumberEnv('ELEVENLABS_SIMILARITY_BOOST', 75) / 100,

  // 请求超时配置（毫秒）
  timeout: 60000, // 1 分钟
  retryAttempts: 3,
  retryDelay: 1000,
} as const;

// ============================================
// 数据库配置
// ============================================
export const dbConfig = {
  url: getEnv('DATABASE_URL', './data/database.sqlite'),

  // 连接池配置
  maxConnections: 10,
  idleTimeout: 30000, // 30 秒

  // WAL 模式（提升并发性能）
  enableWal: true,
} as const;

// ============================================
// 文件存储配置
// ============================================
export const storageConfig = {
  // 目录配置
  uploadDir: getEnv('UPLOAD_DIR', './uploads'),
  rawAssetsDir: getEnv('RAW_ASSETS_DIR', './raw_assets'),
  processedDir: getEnv('PROCESSED_DIR', './processed'),
  outputDir: getEnv('OUTPUT_DIR', './outputs'),
  tempDir: getEnv('TEMP_DIR', './temp'),

  // 文件大小限制（字节）
  maxFileSize: 2 * 1024 * 1024 * 1024, // 2GB
  maxVideoDuration: 3600, // 1 小时（秒）

  // 允许的视频格式
  allowedVideoFormats: ['.mp4', '.mov', '.avi', '.mkv', '.webm'],

  // 允许的音频格式
  allowedAudioFormats: ['.mp3', '.wav', '.aac', '.m4a'],
} as const;

// ============================================
// FFmpeg 配置
// ============================================
export const ffmpegConfig = {
  // FFmpeg 路径
  ffmpegPath: process.env.FFMPEG_PATH || 'ffmpeg',
  ffprobePath: process.env.FFPROBE_PATH || 'ffprobe',

  // 视频处理默认配置
  defaultFps: getNumberEnv('DEFAULT_VIDEO_FPS', 30),
  defaultCrf: getNumberEnv('DEFAULT_VIDEO_CRF', 18),
  defaultPreset: getEnv('DEFAULT_VIDEO_PRESET', 'fast'),
  defaultAudioBitrate: getEnv('DEFAULT_AUDIO_BITRATE', '128k'),

  // 编码配置
  videoCodec: 'libx264',
  audioCodec: 'aac',

  // 质量配置
  crfRange: {
    min: 18,
    max: 28,
  },

  // 处理超时（毫秒）
  processingTimeout: 600000, // 10 分钟
} as const;

// ============================================
// 任务队列配置（BullMQ + Redis）
// ============================================
export const queueConfig = {
  // Redis 配置
  redis: {
    host: getEnv('REDIS_HOST', 'localhost'),
    port: getNumberEnv('REDIS_PORT', 6379),
    password: process.env.REDIS_PASSWORD || undefined,
    db: getNumberEnv('REDIS_DB', 0),
  },

  // 任务并发配置
  maxConcurrentJobs: getNumberEnv('MAX_CONCURRENT_JOBS', 2),  // ✅ 限制并发数为 2，防止资源耗尽
  retryAttempts: getNumberEnv('JOB_RETRY_ATTEMPTS', 3),
  retryDelay: getNumberEnv('JOB_RETRY_DELAY', 5000),

  // 速率限制配置（防止 API 滥用）
  rateLimit: {
    max: 10,       // 每分钟最多 10 个任务
    duration: 60000,  // 60 秒
  },

  // 队列名称
  queues: {
    videoProcessing: 'video-processing',
    geminiAnalysis: 'gemini-analysis',
    ttsGeneration: 'tts-generation',
    videoRender: 'video-render',
  } as const,

  // 任务超时配置（毫秒）
  jobTimeouts: {
    videoProcessing: 600000, // 10 分钟
    geminiAnalysis: 180000, // 3 分钟
    ttsGeneration: 120000, // 2 分钟
    videoRender: 900000, // 15 分钟
  } as const,
} as const;

// ============================================
// WebSocket 配置
// ============================================
export const wsConfig = {
  port: getNumberEnv('WS_PORT', 3001),
  heartbeatInterval: getNumberEnv('WS_HEARTBEAT_INTERVAL', 30000),

  // 连接配置
  maxConnections: 100,
  messageQueueSize: 100,
} as const;

// ============================================
// 第三方服务配置
// ============================================
export const thirdPartyConfig = {
  // 阿里云 OSS
  aliyunOss: {
    enabled: getBooleanEnv('ALIYUN_OSS_ENABLED', false),
    region: getEnv('ALIYUN_OSS_REGION', 'oss-cn-hangzhou'),
    accessKeyId: process.env.ALIYUN_OSS_ACCESS_KEY_ID,
    accessKeySecret: process.env.ALIYUN_OSS_ACCESS_KEY_SECRET,
    bucket: process.env.ALIYUN_OSS_BUCKET,
  },

  // CDN
  cdn: {
    enabled: getBooleanEnv('CDN_ENABLED', false),
    domain: getEnv('CDN_DOMAIN', ''),
  },
} as const;

// ============================================
// Remotion 配置
// ============================================
export const remotionConfig = {
  studioPort: getNumberEnv('REMOTION_STUDIO_PORT', 3002),
  outputDir: storageConfig.outputDir,
  inputProps: {
    // 默认字幕配置
    fontSize: 60,
    fontColor: 'white',
    highlightColor: '#FFE600', // 抖音爆款黄色
    outlineColor: 'black',
    outlineSize: 5,
    subtitleY: 80,
  },
} as const;

// ============================================
// 开发工具配置
// ============================================
export const devConfig = {
  hotReload: getBooleanEnv('DEV_HOT_RELOAD', true),
  remotionStudioPort: getNumberEnv('REMOTION_STUDIO_PORT', 3002),
} as const;

// ============================================
// 配置导出（默认导出）
// ============================================
export default config;
