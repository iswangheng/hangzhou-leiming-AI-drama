// ============================================
// DramaCut AI 数据库 Schema 定义
// 使用 Drizzle ORM + SQLite
// ============================================

import { sqliteTable, text, integer, real } from 'drizzle-orm/sqlite-core';

// ============================================
// 通用字段类型
// ============================================

/**
 * 创建时间戳字段
 */
const timestamps = {
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull().$defaultFn(() => new Date()),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull().$defaultFn(() => new Date()),
};

// ============================================
// 1. 项目表 (projects)
// ============================================
export const projects = sqliteTable('projects', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  name: text('name').notNull(),                           // 项目名称
  description: text('description'),                       // 项目描述

  // 处理状态
  status: text('status', {
    enum: ['ready', 'processing', 'error']
  }).notNull().default('ready'),                          // 处理状态

  // 进度信息（用于 UI 显示）
  progress: integer('progress').notNull().default(0),    // 整体进度 (0-100)
  currentStep: text('current_step'),                     // 当前处理步骤描述

  // 错误信息
  errorMessage: text('error_message'),                    // 错误消息

  ...timestamps,
});

// ============================================
// 2. 视频素材表 (videos)
// ============================================
export const videos = sqliteTable('videos', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  projectId: integer('project_id').notNull().references(() => projects.id, { onDelete: 'cascade' }),  // 所属项目

  filename: text('filename').notNull(),                    // 原始文件名
  filePath: text('file_path').notNull(),                   // 存储路径
  fileSize: integer('file_size').notNull(),                // 文件大小（字节）

  // 视频元数据
  durationMs: integer('duration_ms').notNull(),            // 时长（毫秒）
  width: integer('width').notNull(),                       // 视频宽度
  height: integer('height').notNull(),                     // 视频高度
  fps: integer('fps').notNull(),                           // 帧率

  // 处理状态
  status: text('status', { enum: ['uploading', 'processing', 'analyzing', 'ready', 'error'] })
    .notNull()
    .default('uploading'),                                  // 处理状态

  // 集数信息（新增）
  episodeNumber: integer('episode_number'),               // 第几集（用户输入）
  displayTitle: text('display_title'),                     // 显示标题（如：第1集：午夜凶铃）
  sortOrder: integer('sort_order').notNull().default(0),  // 排序顺序

  // AI 分析结果
  summary: text('summary'),                                // 剧情梗概（旧版，50字以内）
  enhancedSummary: text('enhanced_summary'),               // 增强剧情梗概（JSON 格式，包含连贯性信息）
  keyframesExtracted: integer('keyframes_extracted').notNull().default(0),  // 是否已提取关键帧（0=否，1=是）
  viralScore: real('viral_score'),                         // 爆款分数 (0-10)

  // 错误信息
  errorMessage: text('error_message'),                     // 错误消息

  ...timestamps,
});

// ============================================
// 2. 镜头切片表 (shots)
// ============================================
export const shots = sqliteTable('shots', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  videoId: integer('video_id').notNull().references(() => videos.id, { onDelete: 'cascade' }),

  // 时间信息
  startMs: integer('start_ms').notNull(),                  // 开始时间（毫秒）
  endMs: integer('end_ms').notNull(),                      // 结束时间（毫秒）

  // Gemini 分析结果
  description: text('description').notNull(),              // 场景描述
  emotion: text('emotion').notNull(),                      // 情绪标签
  dialogue: text('dialogue'),                              // 核心台词
  characters: text('characters'),                          // 角色（JSON 数组）
  viralScore: real('viral_score'),                         // 爆款分数 (0-10)

  // 帧信息（用于快速定位）
  startFrame: integer('start_frame').notNull(),            // 起始帧号
  endFrame: integer('end_frame').notNull(),                // 结束帧号

  // Agent 3 需求：缩略图和语义标签
  thumbnailPath: text('thumbnail_path'),                   // 缩略图路径（相对路径或完整路径）
  semanticTags: text('semantic_tags'),                      // 语义标签（JSON 数组，由 Agent 2 填充）
  embeddings: text('embeddings'),                          // 向量表示（JSON 数组，由 Agent 2 填充）

  ...timestamps,
});

// ============================================
// 3. 故事线表 (storylines) - 重新设计：属于项目层级
// ============================================
export const storylines = sqliteTable('storylines', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  projectId: integer('project_id').notNull().references(() => projects.id, { onDelete: 'cascade' }),  // 属于项目

  // 故事线信息
  name: text('name').notNull(),                            // 故事线名称（如："复仇线"、"身份谜团线"）
  description: text('description').notNull(),              // 详细描述（如："女主从受辱到成功复仇的完整历程"）
  attractionScore: real('attraction_score').notNull(),     // 吸引力分数 (0-10)

  // 全局信息
  episodeCount: integer('episode_count').notNull().default(1),  // 跨越几集
  totalDurationMs: integer('total_duration_ms'),           // 总时长（毫秒）

  // 故事线类型
  category: text('category', {
    enum: ['revenge', 'romance', 'identity', 'mystery', 'power', 'family', 'suspense', 'other']
  }).notNull().default('other'),

  ...timestamps,
});

// ============================================
// 4. 高光候选表 (highlights) - 模式 A
// ============================================
export const highlights = sqliteTable('highlights', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  videoId: integer('video_id').notNull().references(() => videos.id, { onDelete: 'cascade' }),

  // 时间信息
  startMs: integer('start_ms').notNull(),                  // 开始时间（毫秒）
  endMs: integer('end_ms'),                                // 结束时间（毫秒，可选）
  durationMs: integer('duration_ms'),                      // 持续时间（毫秒）

  // AI 分析结果
  reason: text('reason').notNull(),                        // 推荐理由
  viralScore: real('viral_score').notNull(),               // 爆款分数 (0-10)
  category: text('category', {
    enum: ['conflict', 'emotional', 'reversal', 'climax', 'other']
  }).notNull().default('other'),

  // 用户操作
  isConfirmed: integer('is_confirmed', { mode: 'boolean' }).notNull().default(false),  // 用户是否确认
  customStartMs: integer('custom_start_ms'),               // 用户自定义开始时间
  customEndMs: integer('custom_end_ms'),                   // 用户自定义结束时间

  // 导出状态
  exportedPath: text('exported_path'),                     // 导出文件路径

  ...timestamps,
});

// ============================================
// 3.5. 故事线片段表 (storyline_segments) - 新增
// ============================================
export const storylineSegments = sqliteTable('storyline_segments', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  storylineId: integer('storyline_id').notNull().references(() => storylines.id, { onDelete: 'cascade' }),  // 属于哪个 storyline
  videoId: integer('video_id').notNull().references(() => videos.id, { onDelete: 'cascade' }),  // 来自哪一集

  // 时间信息
  startMs: integer('start_ms').notNull(),                  // 开始时间（毫秒）
  endMs: integer('end_ms').notNull(),                      // 结束时间（毫秒）

  // 该片段在 storyline 中的顺序
  segmentOrder: integer('segment_order').notNull(),       // 顺序（1, 2, 3...）

  // 片段描述
  description: text('description').notNull(),              // 片段描述（如："婉清受辱，发誓复仇"）

  // 关联的镜头（可选：如果需要更细粒度）
  shotIds: text('shot_ids'),                               // 使用的镜头ID列表（JSON数组）

  ...timestamps,
});

// ============================================
// 5. 解说任务表 (recap_tasks) - 模式 B
// ============================================
export const recapTasks = sqliteTable('recap_tasks', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  storylineId: integer('storyline_id').notNull().references(() => storylines.id, { onDelete: 'cascade' }),

  // 任务配置
  style: text('style', {
    enum: ['hook', 'roast', 'suspense', 'emotional', 'humorous']
  }).notNull(),                                            // 解说风格

  // AI 生成结果
  title: text('title').notNull(),                          // 黄金 3 秒钩子标题
  estimatedDurationMs: integer('estimated_duration_ms').notNull(),  // 预估时长

  // 处理状态
  status: text('status', {
    enum: ['pending', 'generating', 'tts', 'matching', 'ready', 'error']
  }).notNull().default('pending'),                          // 处理状态

  // 导出信息
  outputPath: text('output_path'),                         // 最终导出路径
  audioPath: text('audio_path'),                           // TTS 音频路径

  // 错误信息
  errorMessage: text('error_message'),                     // 错误消息

  ...timestamps,
});

// ============================================
// 6. 解说词片段表 (recap_segments)
// ============================================
export const recapSegments = sqliteTable('recap_segments', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  taskId: integer('task_id').notNull().references(() => recapTasks.id, { onDelete: 'cascade' }),

  // 文案内容
  text: text('text').notNull(),                            // 解说文本
  order: integer('order').notNull(),                       // 段落顺序

  // 时间信息
  startMs: integer('start_ms').notNull(),                  // 开始时间（毫秒）
  endMs: integer('end_ms').notNull(),                      // 结束时间（毫秒）
  durationMs: integer('duration_ms').notNull(),            // 持续时间（毫秒）

  // TTS 信息
  audioOffsetMs: integer('audio_offset_ms').notNull(),     // 在音频中的偏移量
  wordTimestamps: text('word_timestamps').notNull(),       // 词级时间戳（JSON）

  // 画面匹配
  videoCues: text('video_cues'),                           // AI 建议的画面描述（JSON 数组）
  matchedShotId: integer('matched_shot_id'),               // 匹配的镜头 ID
  isManuallySet: integer('is_manually_set', { mode: 'boolean' }).notNull().default(false),  // 是否手动设置

  ...timestamps,
});

// ============================================
// 7. 音频转录表 (audio_transcriptions)
// ============================================
export const audioTranscriptions = sqliteTable('audio_transcriptions', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  videoId: integer('video_id').notNull().references(() => videos.id, { onDelete: 'cascade' }),  // 关联视频

  // 转录结果
  text: text('text').notNull(),                              // 完整转录文本
  language: text('language').notNull(),                       // 检测到的语言（如 'zh', 'en'）
  duration: integer('duration').notNull(),                    // 音频时长（秒）

  // 分段信息（JSON 格式）
  segments: text('segments').notNull(),                       // 转录分段（JSON 数组）

  // 元数据
  model: text('model').notNull(),                              // 使用的 Whisper 模型
  processingTimeMs: integer('processing_time_ms'),            // 处理耗时（毫秒）

  ...timestamps,
});

// ============================================
// 8. 关键帧表 (keyframes)
// ============================================
export const keyframes = sqliteTable('keyframes', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  videoId: integer('video_id').notNull().references(() => videos.id, { onDelete: 'cascade' }),  // 关联视频

  // 关键帧信息
  framePath: text('frame_path').notNull(),                   // 关键帧文件路径
  timestampMs: integer('timestamp_ms').notNull(),             // 时间戳（毫秒）
  frameNumber: integer('frame_number').notNull(),             // 帧序号
  fileSize: integer('file_size'),                             // 文件大小（字节）

  // 元数据
  extractedAt: integer('extracted_at', { mode: 'timestamp' }).notNull(),  // 提取时间

  ...timestamps,
});

// ============================================
// 9. 任务队列表 (queue_jobs) - 用于跟踪 BullMQ 任务
// ============================================
export const queueJobs = sqliteTable('queue_jobs', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  jobId: text('job_id').notNull().unique(),                // BullMQ Job ID

  // 任务信息
  queueName: text('queue_name').notNull(),                 // 队列名称
  jobType: text('job_type').notNull(),                     // 任务类型
  payload: text('payload').notNull(),                      // 任务参数（JSON）

  // 状态
  status: text('status', {
    enum: ['waiting', 'active', 'completed', 'failed', 'delayed']
  }).notNull().default('waiting'),                          // 任务状态

  // 进度和断点续传
  progress: integer('progress').default(0),                // 任务进度（0-100）
  checkpoint: text('checkpoint'),                          // 断点信息（JSON）
  retryCount: integer('retry_count').default(0),           // 重试次数

  // 结果
  result: text('result'),                                  // 执行结果（JSON）
  error: text('error'),                                    // 错误信息

  // 时间
  processedAt: integer('processed_at', { mode: 'timestamp' }),  // 处理时间
  completedAt: integer('completed_at', { mode: 'timestamp' }),  // 完成时间

  ...timestamps,
});

// ============================================
// 8. 项目级分析表 (project_analysis) - 新增
// ============================================
export const projectAnalysis = sqliteTable('project_analysis', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  projectId: integer('project_id').notNull().references(() => projects.id, { onDelete: 'cascade' }),  // 关联项目

  // 全局剧情理解
  mainPlot: text('main_plot'),                             // 主线剧情梗概
  subplotCount: integer('subplot_count').default(0),       // 支线数量

  // 人物关系图谱（JSON）
  characterRelationships: text('character_relationships'),  // 人物关系变化
  // 例子：{"ep1": {"婉清": ["受欺负", "隐忍"]}, "ep3": {"婉清": ["觉醒", "反击"]}}

  // 跨集伏笔（JSON）
  foreshadowings: text('foreshadowings'),                   // 伏笔设置与揭晓
  // 例子：[{"set_up": "ep1-15:00", "payoff": "ep5-10:00", "description": "骨血灯秘密"}]

  // 跨集高光候选（JSON）
  crossEpisodeHighlights: text('cross_episode_highlights'), // 跨越多集的精彩片段
  // 例子：[{"start_ep": 1, "start_ms": 85000, "end_ep": 2, "end_ms": 15000, "description": "从昏迷到逃生的完整情节"}]

  // 分析时间
  analyzedAt: integer('analyzed_at', { mode: 'timestamp' }),

  ...timestamps,
});

// ============================================
// 类型导出
// ============================================

export type Project = typeof projects.$inferSelect;
export type NewProject = typeof projects.$inferInsert;

export type Video = typeof videos.$inferSelect;
export type NewVideo = typeof videos.$inferInsert;

export type Shot = typeof shots.$inferSelect;
export type NewShot = typeof shots.$inferInsert;

export type Storyline = typeof storylines.$inferSelect;
export type NewStoryline = typeof storylines.$inferInsert;

export type StorylineSegment = typeof storylineSegments.$inferSelect;
export type NewStorylineSegment = typeof storylineSegments.$inferInsert;

export type ProjectAnalysis = typeof projectAnalysis.$inferSelect;
export type NewProjectAnalysis = typeof projectAnalysis.$inferInsert;

export type Highlight = typeof highlights.$inferSelect;
export type NewHighlight = typeof highlights.$inferInsert;

export type RecapTask = typeof recapTasks.$inferSelect;
export type NewRecapTask = typeof recapTasks.$inferInsert;

export type RecapSegment = typeof recapSegments.$inferSelect;
export type NewRecapSegment = typeof recapSegments.$inferInsert;

export type AudioTranscription = typeof audioTranscriptions.$inferSelect;
export type NewAudioTranscription = typeof audioTranscriptions.$inferInsert;

export type Keyframe = typeof keyframes.$inferSelect;
export type NewKeyframe = typeof keyframes.$inferInsert;

export type QueueJob = typeof queueJobs.$inferSelect;
export type NewQueueJob = typeof queueJobs.$inferInsert;

// ============================================
// 杭州雷鸣模块专用表
// ============================================

// ============================================
// HL 1. 杭州雷鸣项目表 (hl_projects)
// ============================================
export const hlProjects = sqliteTable('hl_projects', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  name: text('name').notNull(),                           // 项目名称
  description: text('description'),                       // 项目描述

  // 技能文件关联
  skillFilePath: text('skill_file_path'),                 // 技能文件路径（Markdown）

  // 处理状态
  status: text('status', {
    enum: ['created', 'training', 'ready', 'analyzing', 'error']
  }).notNull().default('created'),                         // 处理状态

  // 训练信息
  trainedAt: integer('trained_at', { mode: 'timestamp' }),  // 训练完成时间

  // 统计信息
  videoCount: integer('video_count').notNull().default(0),  // 视频数量
  markingCount: integer('marking_count').notNull().default(0),  // 标记数量

  ...timestamps,
});

// ============================================
// HL 2. 杭州雷鸣视频表 (hl_videos)
// ============================================
export const hlVideos = sqliteTable('hl_videos', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  projectId: integer('project_id').notNull().references(() => hlProjects.id, { onDelete: 'cascade' }),  // 所属项目

  filename: text('filename').notNull(),                    // 原始文件名
  filePath: text('file_path').notNull(),                   // 存储路径
  fileSize: integer('file_size').notNull(),                // 文件大小（字节）

  // 集数信息
  episodeNumber: text('episode_number').notNull(),         // 集数（如：第1集）
  displayTitle: text('display_title'),                     // 显示标题
  sortOrder: integer('sort_order').notNull().default(0),  // 排序顺序

  // 视频元数据
  durationMs: integer('duration_ms').notNull(),            // 时长（毫秒）
  width: integer('width').notNull(),                       // 视频宽度
  height: integer('height').notNull(),                     // 视频高度
  fps: integer('fps').notNull(),                           // 帧率

  // 处理状态
  status: text('status', { enum: ['uploading', 'processing', 'ready', 'error'] })
    .notNull()
    .default('uploading'),                                  // 处理状态

  // 临时文件路径（用于AI分析）
  frameDir: text('frame_dir'),                             // 抽帧目录
  audioPath: text('audio_path'),                           // 音频路径（WAV）
  asrResultPath: text('asr_result_path'),                  // ASR转录结果（JSON）

  // 错误信息
  errorMessage: text('error_message'),                     // 错误消息

  ...timestamps,
});

// ============================================
// HL 3. 历史标记数据表 (hl_markings) - 来自Excel导入
// ============================================
export const hlMarkings = sqliteTable('hl_markings', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  projectId: integer('project_id').notNull().references(() => hlProjects.id, { onDelete: 'cascade' }),  // 所属项目
  videoId: integer('video_id').notNull().references(() => hlVideos.id, { onDelete: 'cascade' }),  // 关联视频

  // 标记信息
  timestamp: text('timestamp').notNull(),                  // 时间点（如：00:35、01:20）
  seconds: integer('seconds').notNull(),                   // 时间点（秒）
  type: text('type', {
    enum: ['高光点', '钩子点']
  }).notNull(),                                            // 标记类型

  // 详细信息
  subType: text('sub_type'),                               // 子类型（如：高能冲突、悬念结尾）
  description: text('description'),                       // 描述信息
  score: integer('score'),                                 // 得分（0-100）
  reasoning: text('reasoning'),                            // 推理说明

  // AI 分析增强信息
  aiEnhanced: integer('ai_enhanced', { mode: 'boolean' }).notNull().default(false),  // 是否被AI增强分析
  emotion: text('emotion'),                                // 情绪标签
  characters: text('characters'),                          // 涉及角色（JSON数组）

  ...timestamps,
});

// ============================================
// HL 4. 技能文件表 (hl_skills)
// ============================================
export const hlSkills = sqliteTable('hl_skills', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  projectId: integer('project_id').notNull().references(() => hlProjects.id, { onDelete: 'cascade' }),  // 所属项目

  // 技能文件信息
  name: text('name').notNull(),                            // 技能名称
  version: text('version').notNull().default('v1.0'),     // 版本号

  // Markdown 内容
  content: text('content').notNull(),                      // Markdown 格式内容

  // 技能分类（JSON）
  highlightTypes: text('highlight_types'),                 // 高光类型定义（JSON）
  hookTypes: text('hook_types'),                           // 钩子类型定义（JSON）
  editingRules: text('editing_rules'),                     // 剪辑规则（JSON）

  // 生成信息
  generatedFrom: text('generated_from', {
    enum: ['manual', 'ai_learning', 'ai_enhanced']
  }).notNull().default('manual'),                           // 生成方式

  // 统计信息
  totalMarkings: integer('total_markings').notNull().default(0),  // 基于多少标记数据生成

  // 使用统计
  usedCount: integer('used_count').notNull().default(0),  // 被使用次数

  ...timestamps,
});

// ============================================
// HL 5. AI 分析结果表 (hl_analysis_results)
// ============================================
export const hlAnalysisResults = sqliteTable('hl_analysis_results', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  projectId: integer('project_id').notNull().references(() => hlProjects.id, { onDelete: 'cascade' }),  // 所属项目
  videoId: integer('video_id').notNull().references(() => hlVideos.id, { onDelete: 'cascade' }),  // 关联视频

  // 分析配置
  skillId: integer('skill_id').references(() => hlSkills.id),  // 使用的技能文件
  minDurationMs: integer('min_duration_ms'),               // 最小时长（毫秒）
  maxDurationMs: integer('max_duration_ms'),               // 最大时长（毫秒）

  // 分析状态
  status: text('status', {
    enum: ['pending', 'analyzing', 'completed', 'error']
  }).notNull().default('pending'),                          // 分析状态

  // 分析进度
  currentStep: text('current_step'),                       // 当前步骤
  progress: integer('progress').notNull().default(0),    // 进度（0-100）

  // 分析结果摘要
  highlightsFound: integer('highlights_found').default(0),  // 找到的高光数量
  hooksFound: integer('hooks_found').default(0),           // 找到的钩子数量

  // 错误信息
  errorMessage: text('error_message'),                     // 错误消息

  ...timestamps,
});

// ============================================
// HL 6. AI 标记表 (hl_ai_markings) - AI 自动标记的结果
// ============================================
export const hlAiMarkings = sqliteTable('hl_ai_markings', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  analysisId: integer('analysis_id').notNull().references(() => hlAnalysisResults.id, { onDelete: 'cascade' }),  // 关联分析任务
  videoId: integer('video_id').notNull().references(() => hlVideos.id, { onDelete: 'cascade' }),  // 关联视频

  // 时间信息
  startMs: integer('start_ms').notNull(),                  // 开始时间（毫秒）
  endMs: integer('end_ms'),                                // 结束时间（毫秒）

  // 标记信息
  type: text('type', {
    enum: ['高光点', '钩子点']
  }).notNull(),                                            // 标记类型
  subType: text('sub_type'),                               // 子类型（如：高能冲突、身份揭露、悬念结尾）

  // AI 分析结果
  score: real('score').notNull(),                          // 得分（0-10）
  reasoning: text('reasoning').notNull(),                  // 推理说明

  // 情感分析
  emotion: text('emotion'),                                // 情绪标签
  intensity: real('intensity'),                            // 强度（0-10）

  // 用户操作
  isConfirmed: integer('is_confirmed', { mode: 'boolean' }).notNull().default(false),  // 用户是否确认
  customStartMs: integer('custom_start_ms'),               // 用户自定义开始时间
  customEndMs: integer('custom_end_ms'),                   // 用户自定义结束时间

  ...timestamps,
});

// ============================================
// HL 7. 剪辑组合推荐表 (hl_clip_combinations)
// ============================================
export const hlClipCombinations = sqliteTable('hl_clip_combinations', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  analysisId: integer('analysis_id').notNull().references(() => hlAnalysisResults.id, { onDelete: 'cascade' }),  // 关联分析任务

  // 组合信息
  name: text('name').notNull(),                            // 组合名称（如：冲突开场 + 悬念结尾）

  // 组合片段（JSON数组）
  clips: text('clips').notNull(),                          // 片段列表
  // 格式：[{"video_id": 1, "video_name": "ep01.mp4", "start_ms": 80000, "end_ms": 140000, "type": "高光点"}]

  // 时长信息
  totalDurationMs: integer('total_duration_ms').notNull(), // 总时长（毫秒）

  // 评分和排序
  overallScore: real('overall_score').notNull(),           // 综合得分（0-100）
  conflictScore: real('conflict_score'),                   // 冲突强度（0-10）
  emotionScore: real('emotion_score'),                    // 情感共鸣（0-10）
  suspenseScore: real('suspense_score'),                  // 悬念设置（0-10）
  rhythmScore: real('rhythm_score'),                      // 节奏把握（0-10）
  historyScore: real('history_score'),                    // 历史验证（0-10）

  // 推荐理由
  reasoning: text('reasoning').notNull(),                  // 推荐理由

  // 排序
  rank: integer('rank').notNull(),                         // 排名（1, 2, 3...）

  // 用户操作
  isSelected: integer('is_selected', { mode: 'boolean' }).notNull().default(false),  // 是否被用户选择

  ...timestamps,
});

// ============================================
// HL 8. 导出记录表 (hl_exports)
// ============================================
export const hlExports = sqliteTable('hl_exports', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  projectId: integer('project_id').notNull().references(() => hlProjects.id, { onDelete: 'cascade' }),  // 所属项目
  combinationId: integer('combination_id').notNull().references(() => hlClipCombinations.id, { onDelete: 'cascade' }),  // 关联组合

  // 导出配置
  outputFormat: text('output_format', {
    enum: ['mp4', 'mov', 'avi']
  }).notNull().default('mp4'),                             // 输出格式

  // 导出状态
  status: text('status', {
    enum: ['pending', 'processing', 'completed', 'error']
  }).notNull().default('pending'),                          // 导出状态

  // 进度信息
  progress: integer('progress').notNull().default(0),    // 进度（0-100）
  currentStep: text('current_step'),                       // 当前步骤

  // 输出文件
  outputPath: text('output_path'),                         // 输出文件路径
  fileSize: integer('file_size'),                          // 文件大小（字节）

  // FFmpeg 命令（用于调试）
  ffmpegCommand: text('ffmpeg_command'),                   // FFmpeg 命令

  // 错误信息
  errorMessage: text('error_message'),                     // 错误消息

  // 完成时间
  completedAt: integer('completed_at', { mode: 'timestamp' }),  // 完成时间

  ...timestamps,
});

// ============================================
// HL 9. 全局技能表 (hl_global_skills)
// ============================================
/**
 * 全局技能文件表（独立于项目）
 *
 * 用途：存储训练中心生成的全局剪辑技能
 * 特点：每次训练都是增量更新（并集）
 */
export const hlGlobalSkills = sqliteTable('hl_global_skills', {
  id: integer('id').primaryKey({ autoIncrement: true }),

  // 技能文件信息
  version: text('version').notNull().unique(),               // 版本号（如：v1.0, v1.1）
  skillFilePath: text('skill_file_path').notNull(),          // 技能文件路径（Markdown）

  // 统计信息
  totalProjects: integer('total_projects').notNull().default(0),  // 训练项目数量
  totalVideos: integer('total_videos').notNull().default(0),      // 覆盖视频数量
  totalMarkings: integer('total_markings').notNull().default(0),  // 学习标记数量

  // 训练信息
  trainingProjectIds: text('training_project_ids').notNull(),     // 训练项目ID列表（JSON数组）

  // 性能指标（可选，用于评估技能质量）
  accuracy: real('accuracy'),                                // 准确率（0-1）
  precision: real('precision'),                              // 精确率（0-1）
  recall: real('recall'),                                    // 召回率（0-1）

  // 状态
  status: text('status', {
    enum: ['training', 'ready', 'deprecated']
  }).notNull().default('ready'),                             // 技能状态

  ...timestamps,
});

// ============================================
// HL 10. 训练历史表 (hl_training_history)
// ============================================
/**
 * 训练历史记录表
 *
 * 用途：记录每次训练的详细信息
 */
export const hlTrainingHistory = sqliteTable('hl_training_history', {
  id: integer('id').primaryKey({ autoIncrement: true }),

  // 训练配置
  projectIds: text('project_ids').notNull(),                 // 训练项目ID列表（JSON数组）
  projectNames: text('project_names').notNull(),             // 训练项目名称列表（JSON数组）

  // 输出技能
  skillVersion: text('skill_version').notNull(),             // 生成的技能版本
  skillId: integer('skill_id').references(() => hlGlobalSkills.id),  // 关联的技能文件

  // 训练状态
  status: text('status', {
    enum: ['pending', 'training', 'completed', 'failed']
  }).notNull().default('pending'),                           // 训练状态
  progress: integer('progress').notNull().default(0),        // 训练进度 (0-100)
  currentStep: text('current_step'),                         // 当前训练步骤

  // 训练结果
  totalVideosProcessed: integer('total_videos_processed').notNull().default(0),  // 处理的视频数量
  totalMarkingsLearned: integer('total_markings_learned').notNull().default(0),  // 学习的标记数量

  // 错误信息
  errorMessage: text('error_message'),                       // 错误消息

  // 时间信息
  startedAt: integer('started_at', { mode: 'timestamp' }),   // 开始时间
  completedAt: integer('completed_at', { mode: 'timestamp' }), // 完成时间

  ...timestamps,
});

// ============================================
// HL 11. 杭州雷鸣关键帧表 (hl_keyframes)
// ============================================
/**
 * 关键帧表 - 杭州雷鸣专用
 *
 * 用途：存储视频的关键帧信息，用于 AI 分析
 */
export const hlKeyframes = sqliteTable('hl_keyframes', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  videoId: integer('video_id').notNull().references(() => hlVideos.id, { onDelete: 'cascade' }),  // 关联杭州雷鸣视频

  // 关键帧信息
  framePath: text('frame_path').notNull(),                   // 关键帧文件路径
  timestampMs: integer('timestamp_ms').notNull(),             // 时间戳（毫秒）
  frameNumber: integer('frame_number').notNull(),             // 帧序号
  fileSize: integer('file_size'),                             // 文件大小（字节）

  // 元数据
  extractedAt: integer('extracted_at', { mode: 'timestamp' }).notNull(),  // 提取时间

  ...timestamps,
});

// ============================================
// HL 12. 杭州雷鸣音频转录表 (hl_audio_transcriptions)
// ============================================
/**
 * 音频转录表 - 杭州雷鸣专用
 *
 * 用途：存储 Whisper 转录结果，用于训练分析
 */
export const hlAudioTranscriptions = sqliteTable('hl_audio_transcriptions', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  videoId: integer('video_id').notNull().references(() => hlVideos.id, { onDelete: 'cascade' }),  // 关联杭州雷鸣视频

  // 转录结果
  text: text('text').notNull(),                              // 完整转录文本
  language: text('language').notNull(),                       // 检测到的语言（如 'zh', 'en'）
  duration: integer('duration').notNull(),                    // 音频时长（秒）

  // 分段信息（JSON 格式）
  segments: text('segments').notNull(),                       // 转录分段（JSON 数组）

  // 元数据
  model: text('model').notNull(),                              // 使用的 Whisper 模型
  processingTimeMs: integer('processing_time_ms'),            // 处理耗时（毫秒）

  ...timestamps,
});

// ============================================
// 杭州雷鸣类型导出
// ============================================

export type HLProject = typeof hlProjects.$inferSelect;
export type NewHLProject = typeof hlProjects.$inferInsert;

export type HLVideo = typeof hlVideos.$inferSelect;
export type NewHLVideo = typeof hlVideos.$inferInsert;

export type HLMarking = typeof hlMarkings.$inferSelect;
export type NewHLMarking = typeof hlMarkings.$inferInsert;

export type HLSkill = typeof hlSkills.$inferSelect;
export type NewHLSkill = typeof hlSkills.$inferInsert;

export type HLAnalysisResult = typeof hlAnalysisResults.$inferSelect;
export type NewHLAnalysisResult = typeof hlAnalysisResults.$inferInsert;

export type HLAiMarking = typeof hlAiMarkings.$inferSelect;
export type NewHLAiMarking = typeof hlAiMarkings.$inferInsert;

export type HLClipCombination = typeof hlClipCombinations.$inferSelect;
export type NewHLClipCombination = typeof hlClipCombinations.$inferInsert;

export type HLExport = typeof hlExports.$inferSelect;
export type NewHLExport = typeof hlExports.$inferInsert;

export type HLGlobalSkill = typeof hlGlobalSkills.$inferSelect;
export type NewHLGlobalSkill = typeof hlGlobalSkills.$inferInsert;

export type HLTrainingHistory = typeof hlTrainingHistory.$inferSelect;
export type NewHLTrainingHistory = typeof hlTrainingHistory.$inferInsert;

export type HLKeyframe = typeof hlKeyframes.$inferSelect;
export type NewHLKeyframe = typeof hlKeyframes.$inferInsert;

export type HLAudioTranscription = typeof hlAudioTranscriptions.$inferSelect;
export type NewHLAudioTranscription = typeof hlAudioTranscriptions.$inferInsert;

// ============================================
// Schema 对象统一导出
// ============================================
export const schema = {
  // 原有表
  projects,
  videos,
  shots,
  storylines,
  storylineSegments,
  projectAnalysis,
  highlights,
  recapTasks,
  recapSegments,
  audioTranscriptions,
  keyframes,
  queueJobs,

  // 杭州雷鸣表
  hlProjects,
  hlVideos,
  hlMarkings,
  hlSkills,
  hlAnalysisResults,
  hlAiMarkings,
  hlClipCombinations,
  hlExports,
  hlGlobalSkills,
  hlTrainingHistory,
  hlKeyframes,
  hlAudioTranscriptions,
};
