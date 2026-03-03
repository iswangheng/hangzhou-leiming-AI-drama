// ============================================
// DramaCut AI 数据库查询工具
// 封装常用的数据库操作
// ============================================

import { db } from './client';
import * as schema from './schema';
import { eq, desc, and, sql, like, asc } from 'drizzle-orm';
import type {
  Project,
  Video,
  Shot,
  Storyline,
  StorylineSegment,
  ProjectAnalysis,
  Highlight,
  RecapTask,
  RecapSegment,
  AudioTranscription,
  Keyframe,
} from './schema';

// ============================================
// 项目相关查询 (projects)
// ============================================

export const projectQueries = {
  /**
   * 创建项目
   */
  async create(data: typeof schema.projects.$inferInsert) {
    const [project] = await db.insert(schema.projects).values(data).returning();
    return project;
  },

  /**
   * 根据 ID 获取项目
   */
  async getById(id: number) {
    const [project] = await db.select().from(schema.projects).where(eq(schema.projects.id, id));
    return project;
  },

  /**
   * 获取所有项目列表
   */
  async list(limit = 50, offset = 0) {
    const projects = await db
      .select()
      .from(schema.projects)
      .orderBy(desc(schema.projects.createdAt))
      .limit(limit)
      .offset(offset);
    return projects;
  },

  /**
   * 搜索项目（按名称）
   */
  async search(keyword: string, limit = 50) {
    const projects = await db
      .select()
      .from(schema.projects)
      .where(like(schema.projects.name, `%${keyword}%`))
      .orderBy(desc(schema.projects.createdAt))
      .limit(limit);
    return projects;
  },

  /**
   * 更新项目
   */
  async update(id: number, data: Partial<typeof schema.projects.$inferInsert>) {
    const [project] = await db
      .update(schema.projects)
      .set({
        ...data,
        updatedAt: new Date(),
      })
      .where(eq(schema.projects.id, id))
      .returning();
    return project;
  },

  /**
   * 更新项目状态和进度
   */
  async updateProgress(id: number, progress: number, currentStep?: string) {
    const [project] = await db
      .update(schema.projects)
      .set({
        progress,
        currentStep,
        status: progress === 100 ? 'ready' : 'processing',
        updatedAt: new Date(),
      })
      .where(eq(schema.projects.id, id))
      .returning();
    return project;
  },

  /**
   * 删除项目（级联删除关键帧文件）
   */
  async delete(id: number) {
    // ✅ 步骤 1: 获取项目的所有视频（在删除前）
    const videos = await db
      .select()
      .from(schema.videos)
      .where(eq(schema.videos.projectId, id));

    console.log(`🗑️ 准备删除项目 ${id}，包含 ${videos.length} 个视频`);

    // ✅ 步骤 2: 删除每个视频的关键帧文件
    const fs = await import('fs/promises');
    const path = await import('path');

    let cleanedKeyframesCount = 0;
    let freedSpaceBytes = 0;

    for (const video of videos) {
      const keyframesDir = path.join(process.cwd(), 'public', 'keyframes', video.id.toString());

      try {
        // 检查目录是否存在
        const { stat } = await import('fs/promises');

        // 计算目录大小
        let totalSize = 0;
        try {
          const files = await fs.readdir(keyframesDir, { recursive: true });
          for (const file of files) {
            const filePath = path.join(keyframesDir, file);
            try {
              const stats = await stat(filePath);
              if (stats.isFile()) {
                totalSize += stats.size;
                cleanedKeyframesCount++;
              }
            } catch {}
          }
        } catch {}

        // 删除目录
        await fs.rm(keyframesDir, { recursive: true, force: true });

        freedSpaceBytes += totalSize;

        console.log(`  🗑️  已清理视频 ${video.id} 的关键帧目录 (${totalSize > 0 ? (totalSize / 1024 / 1024).toFixed(2) + 'MB' : '空目录'})`);
      } catch (error) {
        console.warn(`  ⚠️ 清理视频 ${video.id} 的关键帧目录失败:`, error);
      }
    }

    // ✅ 步骤 3: 删除数据库记录（会级联删除所有关联数据）
    const [project] = await db
      .delete(schema.projects)
      .where(eq(schema.projects.id, id))
      .returning();

    console.log(`✅ 项目 ${id} 删除完成，清理了 ${cleanedKeyframesCount} 个关键帧文件，释放了 ${(freedSpaceBytes / 1024 / 1024).toFixed(2)}MB 磁盘空间`);

    return project;
  },

  /**
   * 获取项目及其视频统计信息
   */
  async getWithStats(id: number) {
    const [project] = await db.select().from(schema.projects).where(eq(schema.projects.id, id));
    if (!project) return null;

    const videos = await db
      .select()
      .from(schema.videos)
      .where(eq(schema.videos.projectId, id));

    const videoCount = videos.length;
    const totalDurationMs = videos.reduce((sum: number, v: any) => sum + v.durationMs, 0);
    const totalDuration = `${Math.floor(totalDurationMs / 60000)} 分钟`;

    return {
      ...project,
      videoCount,
      totalDuration,
    };
  },
};

// ============================================
// 视频相关查询 (videos)
// ============================================

export const videoQueries = {
  /**
   * 创建视频记录
   */
  async create(data: typeof schema.videos.$inferInsert) {
    const [video] = await db.insert(schema.videos).values(data).returning();
    return video;
  },

  /**
   * 根据项目 ID 获取所有视频
   */
  async getByProjectId(projectId: number) {
    const videos = await db
      .select()
      .from(schema.videos)
      .where(eq(schema.videos.projectId, projectId))
      .orderBy(desc(schema.videos.createdAt));
    return videos;
  },

  /**
   * 根据 ID 获取视频
   */
  async getById(id: number) {
    const [video] = await db.select().from(schema.videos).where(eq(schema.videos.id, id));
    return video;
  },

  /**
   * 更新视频状态
   */
  async updateStatus(id: number, status: Video['status'], errorMessage?: string) {
    const [video] = await db
      .update(schema.videos)
      .set({
        status,
        errorMessage,
        updatedAt: new Date(),
      })
      .where(eq(schema.videos.id, id))
      .returning();
    return video;
  },

  /**
   * 标记视频错误状态
   */
  async updateError(id: number, errorMessage: string) {
    return this.updateStatus(id, 'error', errorMessage);
  },

  /**
   * 更新视频 AI 分析结果
   */
  async updateAnalysis(id: number, data: { summary?: string; viralScore?: number }) {
    const [video] = await db
      .update(schema.videos)
      .set({
        ...data,
        status: 'ready',
        updatedAt: new Date(),
      })
      .where(eq(schema.videos.id, id))
      .returning();
    return video;
  },

  /**
   * 获取所有视频列表
   */
  async list(limit = 50, offset = 0) {
    const videos = await db
      .select()
      .from(schema.videos)
      .orderBy(desc(schema.videos.createdAt))
      .limit(limit)
      .offset(offset);
    return videos;
  },

  /**
   * 根据状态获取视频列表
   */
  async getByStatus(status: Video['status']) {
    const videos = await db
      .select()
      .from(schema.videos)
      .where(eq(schema.videos.status, status))
      .orderBy(desc(schema.videos.createdAt));
    return videos;
  },

  /**
   * 删除视频（级联删除关键帧文件）
   */
  async delete(id: number) {
    console.log(`🗑️ 准备删除视频 ${id}`);

    // ✅ 步骤 1: 删除该视频的关键帧文件
    const fs = await import('fs/promises');
    const path = await import('path');

    const keyframesDir = path.join(process.cwd(), 'public', 'keyframes', id.toString());

    try {
      // 检查目录是否存在
      const { stat } = await import('fs/promises');

      // 计算目录大小
      let totalSize = 0;
      let keyframesCount = 0;
      try {
        const files = await fs.readdir(keyframesDir, { recursive: true });
        for (const file of files) {
          const filePath = path.join(keyframesDir, file);
          try {
            const stats = await stat(filePath);
            if (stats.isFile()) {
              totalSize += stats.size;
              keyframesCount++;
            }
          } catch {}
        }
      } catch {}

      // 删除目录
      await fs.rm(keyframesDir, { recursive: true, force: true });

      console.log(`  🗑️  已清理视频 ${id} 的关键帧目录 (${keyframesCount} 个文件, ${(totalSize / 1024 / 1024).toFixed(2)}MB)`);
    } catch (error) {
      console.warn(`  ⚠️ 清理视频 ${id} 的关键帧目录失败:`, error);
    }

    // ✅ 步骤 2: 删除数据库记录（会级联删除关联数据）
    const [video] = await db
      .delete(schema.videos)
      .where(eq(schema.videos.id, id))
      .returning();

    console.log(`✅ 视频 ${id} 删除完成`);

    return video;
  },
};

// ============================================
// 镜头切片相关查询 (shots)
// ============================================

export const shotQueries = {
  /**
   * 批量创建镜头记录
   */
  async createMany(data: typeof schema.shots.$inferInsert[]) {
    return db.insert(schema.shots).values(data);
  },

  /**
   * 删除指定视频的所有镜头（防止重复累积）
   */
  async deleteByVideoId(videoId: number) {
    await db.delete(schema.shots).where(eq(schema.shots.videoId, videoId));
  },

  /**
   * 根据视频 ID 获取所有镜头
   */
  async getByVideoId(videoId: number) {
    const shots = await db
      .select()
      .from(schema.shots)
      .where(eq(schema.shots.videoId, videoId))
      .orderBy(schema.shots.startMs);
    return shots;
  },

  /**
   * 根据时间段获取镜头
   */
  async getByTimeRange(videoId: number, startMs: number, endMs: number) {
    const shots = await db
      .select()
      .from(schema.shots)
      .where(
        and(
          eq(schema.shots.videoId, videoId),
          sql`${schema.shots.startMs} <= ${endMs}`,
          sql`${schema.shots.endMs} >= ${startMs}`
        )
      )
      .orderBy(schema.shots.startMs);
    return shots;
  },

  /**
   * 获取高爆款分数的镜头
   */
  async getTopViral(videoId: number, limit = 10) {
    const shots = await db
      .select()
      .from(schema.shots)
      .where(eq(schema.shots.videoId, videoId))
      .orderBy(desc(schema.shots.viralScore))
      .limit(limit);
    return shots;
  },
};

// ============================================
// 故事线相关查询 (storylines)
// ============================================

export const storylineQueries = {
  /**
   * 创建故事线
   */
  async create(data: typeof schema.storylines.$inferInsert) {
    const [storyline] = await db.insert(schema.storylines).values(data).returning();
    return storyline;
  },

  /**
   * 批量创建故事线
   */
  async createMany(data: typeof schema.storylines.$inferInsert[]) {
    const storylines = await db.insert(schema.storylines).values(data).returning();
    return storylines;
  },

  /**
   * 根据 ID 获取故事线
   */
  async getById(id: number) {
    const [storyline] = await db
      .select()
      .from(schema.storylines)
      .where(eq(schema.storylines.id, id));
    return storyline;
  },

  /**
   * 根据项目 ID 获取所有故事线（新增：storylines 现在属于项目）
   */
  async getByProjectId(projectId: number) {
    const storylines = await db
      .select()
      .from(schema.storylines)
      .where(eq(schema.storylines.projectId, projectId))
      .orderBy(desc(schema.storylines.attractionScore));
    return storylines;
  },

  /**
   * 根据视频 ID 获取所有故事线（保留兼容性，现在会查询该项目下的所有 storylines）
   * @deprecated 建议使用 getByProjectId
   */
  async getByVideoId(videoId: number) {
    // 通过 video 找到 projectId，然后查询该项目的所有 storylines
    const [video] = await db
      .select({ projectId: schema.videos.projectId })
      .from(schema.videos)
      .where(eq(schema.videos.id, videoId));

    if (!video) return [];

    return this.getByProjectId(video.projectId);
  },

  /**
   * 根据项目 ID 获取故事线及其片段（包含 segments）
   */
  async getWithSegments(projectId: number) {
    const storylines = await this.getByProjectId(projectId);

    // 为每个 storyline 加载它的 segments
    const result = await Promise.all(
      storylines.map(async (storyline: any) => {
        const segments = await db
          .select()
          .from(schema.storylineSegments)
          .where(eq(schema.storylineSegments.storylineId, storyline.id))
          .orderBy(asc(schema.storylineSegments.segmentOrder));

        return {
          ...storyline,
          segments,
        };
      })
    );

    return result;
  },

  /**
   * 更新故事线
   */
  async update(id: number, data: Partial<typeof schema.storylines.$inferInsert>) {
    const [storyline] = await db
      .update(schema.storylines)
      .set({
        ...data,
        updatedAt: new Date(),
      })
      .where(eq(schema.storylines.id, id))
      .returning();
    return storyline;
  },
};

// ============================================
// 故事线片段相关查询 (storyline_segments) - 新增
// ============================================

export const storylineSegmentQueries = {
  /**
   * 创建故事线片段
   */
  async create(data: typeof schema.storylineSegments.$inferInsert) {
    const [segment] = await db.insert(schema.storylineSegments).values(data).returning();
    return segment;
  },

  /**
   * 批量创建故事线片段
   */
  async createMany(data: typeof schema.storylineSegments.$inferInsert[]) {
    const segments = await db.insert(schema.storylineSegments).values(data).returning();
    return segments;
  },

  /**
   * 根据 ID 获取片段
   */
  async getById(id: number) {
    const [segment] = await db
      .select()
      .from(schema.storylineSegments)
      .where(eq(schema.storylineSegments.id, id));
    return segment;
  },

  /**
   * 根据 storyline ID 获取所有片段
   */
  async getByStorylineId(storylineId: number) {
    const segments = await db
      .select()
      .from(schema.storylineSegments)
      .where(eq(schema.storylineSegments.storylineId, storylineId))
      .orderBy(asc(schema.storylineSegments.segmentOrder));
    return segments;
  },

  /**
   * 根据 storyline ID 删除所有片段
   */
  async deleteByStorylineId(storylineId: number) {
    const segments = await db
      .delete(schema.storylineSegments)
      .where(eq(schema.storylineSegments.storylineId, storylineId))
      .returning();
    return segments;
  },
};

// ============================================
// 项目级分析相关查询 (project_analysis) - 新增
// ============================================

export const projectAnalysisQueries = {
  /**
   * 创建或更新项目分析
   */
  async upsert(data: typeof schema.projectAnalysis.$inferInsert) {
    const existing = await db
      .select()
      .from(schema.projectAnalysis)
      .where(eq(schema.projectAnalysis.projectId, data.projectId));

    if (existing.length > 0) {
      // 更新
      const [analysis] = await db
        .update(schema.projectAnalysis)
        .set({
          ...data,
          updatedAt: new Date(),
        })
        .where(eq(schema.projectAnalysis.projectId, data.projectId))
        .returning();
      return analysis;
    } else {
      // 创建
      const [analysis] = await db.insert(schema.projectAnalysis).values(data).returning();
      return analysis;
    }
  },

  /**
   * 根据 ID 获取项目分析
   */
  async getById(id: number) {
    const [analysis] = await db
      .select()
      .from(schema.projectAnalysis)
      .where(eq(schema.projectAnalysis.id, id));
    return analysis;
  },

  /**
   * 根据项目 ID 获取分析结果
   */
  async getByProjectId(projectId: number) {
    const [analysis] = await db
      .select()
      .from(schema.projectAnalysis)
      .where(eq(schema.projectAnalysis.projectId, projectId));
    return analysis;
  },

  /**
   * 删除项目分析
   */
  async delete(projectId: number) {
    const [analysis] = await db
      .delete(schema.projectAnalysis)
      .where(eq(schema.projectAnalysis.projectId, projectId))
      .returning();
    return analysis;
  },
};

// ============================================
// 高光候选相关查询 (highlights)
// ============================================

export const highlightQueries = {
  /**
   * 批量创建高光候选
   */
  async createMany(data: typeof schema.highlights.$inferInsert[]) {
    const highlights = await db.insert(schema.highlights).values(data).returning();
    return highlights;
  },

  /**
   * 删除指定视频的所有高光（防止重复累积）
   */
  async deleteByVideoId(videoId: number) {
    await db.delete(schema.highlights).where(eq(schema.highlights.videoId, videoId));
  },

  /**
   * 根据 ID 获取高光
   */
  async getById(id: number) {
    const [highlight] = await db
      .select()
      .from(schema.highlights)
      .where(eq(schema.highlights.id, id));
    return highlight;
  },

  /**
   * 根据视频 ID 获取高光列表
   */
  async getByVideoId(videoId: number) {
    const highlights = await db
      .select()
      .from(schema.highlights)
      .where(eq(schema.highlights.videoId, videoId))
      .orderBy(desc(schema.highlights.viralScore));
    return highlights;
  },

  /**
   * 获取用户已确认的高光
   */
  async getConfirmed(videoId: number) {
    const highlights = await db
      .select()
      .from(schema.highlights)
      .where(and(eq(schema.highlights.videoId, videoId), eq(schema.highlights.isConfirmed, true)))
      .orderBy(desc(schema.highlights.viralScore));
    return highlights;
  },

  /**
   * 更新高光的时间范围（用户微调）
   */
  async updateTimeRange(id: number, customStartMs: number, customEndMs: number) {
    const [highlight] = await db
      .update(schema.highlights)
      .set({
        customStartMs,
        customEndMs,
        updatedAt: new Date(),
      })
      .where(eq(schema.highlights.id, id))
      .returning();
    return highlight;
  },

  /**
   * 确认高光（用户确认后导出）
   */
  async confirm(id: number, customStartMs?: number, customEndMs?: number) {
    const [highlight] = await db
      .update(schema.highlights)
      .set({
        isConfirmed: true,
        customStartMs: customStartMs ?? undefined,
        customEndMs: customEndMs ?? undefined,
        updatedAt: new Date(),
      })
      .where(eq(schema.highlights.id, id))
      .returning();
    return highlight;
  },

  /**
   * 更新导出路径
   */
  async updateExportPath(id: number, exportedPath: string) {
    const [highlight] = await db
      .update(schema.highlights)
      .set({
        exportedPath,
        updatedAt: new Date(),
      })
      .where(eq(schema.highlights.id, id))
      .returning();
    return highlight;
  },
};

// ============================================
// 解说任务相关查询 (recap_tasks)
// ============================================

export const recapTaskQueries = {
  /**
   * 创建解说任务
   */
  async create(data: typeof schema.recapTasks.$inferInsert) {
    const [task] = await db.insert(schema.recapTasks).values(data).returning();
    return task;
  },

  /**
   * 根据 ID 获取任务
   */
  async getById(id: number) {
    const [task] = await db.select().from(schema.recapTasks).where(eq(schema.recapTasks.id, id));
    return task;
  },

  /**
   * 根据故事线 ID 获取所有任务
   */
  async getByStorylineId(storylineId: number) {
    const tasks = await db
      .select()
      .from(schema.recapTasks)
      .where(eq(schema.recapTasks.storylineId, storylineId))
      .orderBy(desc(schema.recapTasks.createdAt));
    return tasks;
  },

  /**
   * 更新任务状态
   */
  async updateStatus(id: number, status: RecapTask['status'], errorMessage?: string) {
    const [task] = await db
      .update(schema.recapTasks)
      .set({
        status,
        errorMessage,
        updatedAt: new Date(),
      })
      .where(eq(schema.recapTasks.id, id))
      .returning();
    return task;
  },

  /**
   * 更新任务输出路径
   */
  async updateOutput(id: number, outputPath: string, audioPath?: string) {
    const [task] = await db
      .update(schema.recapTasks)
      .set({
        outputPath,
        audioPath,
        status: 'ready',
        updatedAt: new Date(),
      })
      .where(eq(schema.recapTasks.id, id))
      .returning();
    return task;
  },
};

// ============================================
// 解说词片段相关查询 (recap_segments)
// ============================================

export const recapSegmentQueries = {
  /**
   * 批量创建解说词片段
   */
  async createMany(data: typeof schema.recapSegments.$inferInsert[]) {
    return db.insert(schema.recapSegments).values(data);
  },

  /**
   * 根据任务 ID 获取所有片段
   */
  async getByTaskId(taskId: number) {
    const segments = await db
      .select()
      .from(schema.recapSegments)
      .where(eq(schema.recapSegments.taskId, taskId))
      .orderBy(schema.recapSegments.order);
    return segments;
  },

  /**
   * 更新片段的画面匹配
   */
  async updateMatch(id: number, matchedShotId: number, isManuallySet = true) {
    const [segment] = await db
      .update(schema.recapSegments)
      .set({
        matchedShotId,
        isManuallySet,
        updatedAt: new Date(),
      })
      .where(eq(schema.recapSegments.id, id))
      .returning();
    return segment;
  },
};

// ============================================
// 任务队列相关查询 (queue_jobs)
// ============================================

export const queueJobQueries = {
  /**
   * 创建任务记录
   */
  async create(data: typeof schema.queueJobs.$inferInsert) {
    const [job] = await db.insert(schema.queueJobs).values(data).returning();
    return job;
  },

  /**
   * 根据 Job ID 获取任务
   */
  async getByJobId(jobId: string) {
    const [job] = await db.select().from(schema.queueJobs).where(eq(schema.queueJobs.jobId, jobId));
    return job;
  },

  /**
   * 更新任务状态
   */
  async updateStatus(jobId: string, status: typeof schema.queueJobs.$inferInsert.status) {
    const [job] = await db
      .update(schema.queueJobs)
      .set({
        status,
        processedAt: status === 'active' ? new Date() : undefined,
        updatedAt: new Date(),
      })
      .where(eq(schema.queueJobs.jobId, jobId))
      .returning();
    return job;
  },

  /**
   * 标记任务完成
   */
  async markComplete(jobId: string, result?: Record<string, unknown>) {
    const [job] = await db
      .update(schema.queueJobs)
      .set({
        status: 'completed',
        completedAt: new Date(),
        result: result ? JSON.stringify(result) : undefined,
        updatedAt: new Date(),
      })
      .where(eq(schema.queueJobs.jobId, jobId))
      .returning();
    return job;
  },

  /**
   * 标记任务失败
   */
  async markFailed(jobId: string, error: string) {
    const [job] = await db
      .update(schema.queueJobs)
      .set({
        status: 'failed',
        error,
        completedAt: new Date(),
        updatedAt: new Date(),
      })
      .where(eq(schema.queueJobs.jobId, jobId))
      .returning();
    return job;
  },

  /**
   * 更新任务进度
   */
  async updateProgress(jobId: string, progress: number) {
    const [job] = await db
      .update(schema.queueJobs)
      .set({
        progress,
        updatedAt: new Date(),
      })
      .where(eq(schema.queueJobs.jobId, jobId))
      .returning();
    return job;
  },
};

// ============================================
// 统计相关查询
// ============================================

export const statsQueries = {
  /**
   * 获取数据库统计信息
   */
  async getOverview() {
    const [projectStats] = await db
      .select({
        total: sql<number>`COUNT(*)`,
        ready: sql<number>`SUM(CASE WHEN status = 'ready' THEN 1 ELSE 0 END)`,
        processing: sql<number>`SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END)`,
        error: sql<number>`SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END)`,
      })
      .from(schema.projects);

    const [videoStats] = await db
      .select({
        total: sql<number>`COUNT(*)`,
        uploading: sql<number>`SUM(CASE WHEN status = 'uploading' THEN 1 ELSE 0 END)`,
        processing: sql<number>`SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END)`,
        analyzing: sql<number>`SUM(CASE WHEN status = 'analyzing' THEN 1 ELSE 0 END)`,
        ready: sql<number>`SUM(CASE WHEN status = 'ready' THEN 1 ELSE 0 END)`,
        error: sql<number>`SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END)`,
      })
      .from(schema.videos);

    const [highlightStats] = await db
      .select({
        total: sql<number>`COUNT(*)`,
        confirmed: sql<number>`SUM(CASE WHEN is_confirmed = 1 THEN 1 ELSE 0 END)`,
        exported: sql<number>`SUM(CASE WHEN exported_path IS NOT NULL THEN 1 ELSE 0 END)`,
      })
      .from(schema.highlights);

    const [recapStats] = await db
      .select({
        total: sql<number>`COUNT(*)`,
        pending: sql<number>`SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END)`,
        generating: sql<number>`SUM(CASE WHEN status = 'generating' THEN 1 ELSE 0 END)`,
        ready: sql<number>`SUM(CASE WHEN status = 'ready' THEN 1 ELSE 0 END)`,
      })
      .from(schema.recapTasks);

    return {
      projects: projectStats,
      videos: videoStats,
      highlights: highlightStats,
      recaps: recapStats,
    };
  },
};

// ============================================
// 音频转录查询 (audio_transcriptions)
// ============================================

export const audioTranscriptionQueries = {
  /**
   * 创建转录记录
   */
  async create(data: {
    videoId: number;
    text: string;
    language: string;
    duration: number;
    segments: string;
    model: string;
    processingTimeMs?: number;
  }) {
    const [result] = await db.insert(schema.audioTranscriptions).values(data).returning();
    return result;
  },

  /**
   * 根据 videoId 获取转录记录
   */
  async getByVideoId(videoId: number) {
    const [result] = await db
      .select()
      .from(schema.audioTranscriptions)
      .where(eq(schema.audioTranscriptions.videoId, videoId))
      .limit(1);
    return result || null;
  },

  /**
   * 更新转录记录
   */
  async update(id: number, data: Partial<{ text: string; segments: string }>) {
    const [result] = await db
      .update(schema.audioTranscriptions)
      .set({ ...data, updatedAt: new Date() })
      .where(eq(schema.audioTranscriptions.id, id))
      .returning();
    return result;
  },

  /**
   * 删除转录记录
   */
  async delete(id: number) {
    await db.delete(schema.audioTranscriptions).where(eq(schema.audioTranscriptions.id, id));
  },
};

// ============================================
// 杭州雷鸣音频转录查询 (hl_audio_transcriptions)
// ============================================

export const hlAudioTranscriptionQueries = {
  /**
   * 创建转录记录
   */
  async create(data: {
    videoId: number;
    text: string;
    language: string;
    duration: number;
    segments: string;
    model: string;
    processingTimeMs?: number;
  }) {
    const [result] = await db.insert(schema.hlAudioTranscriptions).values(data).returning();
    return result;
  },

  /**
   * 根据 videoId 获取转录记录
   */
  async getByVideoId(videoId: number) {
    const [result] = await db
      .select()
      .from(schema.hlAudioTranscriptions)
      .where(eq(schema.hlAudioTranscriptions.videoId, videoId))
      .limit(1);
    return result || null;
  },

  /**
   * 更新转录记录
   */
  async update(id: number, data: Partial<{ text: string; segments: string }>) {
    const [result] = await db
      .update(schema.hlAudioTranscriptions)
      .set({ ...data, updatedAt: new Date() })
      .where(eq(schema.hlAudioTranscriptions.id, id))
      .returning();
    return result;
  },

  /**
   * 删除转录记录
   */
  async delete(id: number) {
    await db.delete(schema.hlAudioTranscriptions).where(eq(schema.hlAudioTranscriptions.id, id));
  },

  /**
   * 根据 projectId 获取所有转录记录
   */
  async getByProjectId(projectId: number) {
    const results = await db
      .select({
        transcription: schema.hlAudioTranscriptions,
        video: schema.hlVideos,
      })
      .from(schema.hlAudioTranscriptions)
      .innerJoin(schema.hlVideos, eq(schema.hlAudioTranscriptions.videoId, schema.hlVideos.id))
      .where(eq(schema.hlVideos.projectId, projectId))
      .orderBy(schema.hlAudioTranscriptions.createdAt);
    return results;
  },

  /**
   * 检查视频是否已有转录记录
   */
  async existsByVideoId(videoId: number): Promise<boolean> {
    const [result] = await db
      .select({ count: sql<number>`COUNT(*)` })
      .from(schema.hlAudioTranscriptions)
      .where(eq(schema.hlAudioTranscriptions.videoId, videoId));
    return (result?.count || 0) > 0;
  },
};

// ============================================
// 杭州雷鸣关键帧查询 (hl_keyframes)
// ============================================

export const hlKeyframeQueries = {
  /**
   * 创建关键帧记录
   */
  async create(data: {
    videoId: number;
    framePath: string;
    timestampMs: number;
    frameNumber: number;
    fileSize?: number;
  }) {
    const [result] = await db
      .insert(schema.hlKeyframes)
      .values({ ...data, extractedAt: new Date() })
      .returning();
    return result;
  },

  /**
   * 根据 videoId 获取所有关键帧
   */
  async getByVideoId(videoId: number) {
    const results = await db
      .select()
      .from(schema.hlKeyframes)
      .where(eq(schema.hlKeyframes.videoId, videoId))
      .orderBy(schema.hlKeyframes.timestampMs);
    return results;
  },

  /**
   * 批量创建关键帧记录
   */
  async createBatch(frames: Array<{
    videoId: number;
    framePath: string;
    timestampMs: number;
    frameNumber: number;
    fileSize?: number;
  }>) {
    const results = await db
      .insert(schema.hlKeyframes)
      .values(frames.map(f => ({ ...f, extractedAt: new Date() })))
      .returning();
    return results;
  },

  /**
   * 删除指定视频的所有关键帧
   */
  async deleteByVideoId(videoId: number) {
    await db.delete(schema.hlKeyframes).where(eq(schema.hlKeyframes.videoId, videoId));
  },

  /**
   * 获取指定视频的关键帧数量
   */
  async getFrameCount(videoId: number) {
    const [result] = await db
      .select({ count: sql<number>`COUNT(*)` })
      .from(schema.hlKeyframes)
      .where(eq(schema.hlKeyframes.videoId, videoId));
    return result?.count || 0;
  },

  /**
   * 根据时间范围获取关键帧
   */
  async getByTimeRange(videoId: number, startMs: number, endMs: number) {
    const results = await db
      .select()
      .from(schema.hlKeyframes)
      .where(
        and(
          eq(schema.hlKeyframes.videoId, videoId),
          sql`${schema.hlKeyframes.timestampMs} >= ${startMs}`,
          sql`${schema.hlKeyframes.timestampMs} <= ${endMs}`
        )
      )
      .orderBy(schema.hlKeyframes.timestampMs);
    return results;
  },

  /**
   * 根据 projectId 获取所有关键帧
   */
  async getByProjectId(projectId: number) {
    const results = await db
      .select({
        keyframe: schema.hlKeyframes,
        video: schema.hlVideos,
      })
      .from(schema.hlKeyframes)
      .innerJoin(schema.hlVideos, eq(schema.hlKeyframes.videoId, schema.hlVideos.id))
      .where(eq(schema.hlVideos.projectId, projectId))
      .orderBy(schema.hlKeyframes.timestampMs);
    return results;
  },

  /**
   * 检查视频是否已提取关键帧
   */
  async existsByVideoId(videoId: number): Promise<boolean> {
    const count = await this.getFrameCount(videoId);
    return count > 0;
  },
};

// ============================================
// 关键帧查询 (keyframes) - 通用系统
// ============================================

export const keyframeQueries = {
  /**
   * 创建关键帧记录
   */
  async create(data: {
    videoId: number;
    framePath: string;
    timestampMs: number;
    frameNumber: number;
    fileSize?: number;
  }) {
    const [result] = await db
      .insert(schema.keyframes)
      .values({ ...data, extractedAt: new Date() })
      .returning();
    return result;
  },

  /**
   * 根据 videoId 获取所有关键帧
   */
  async getByVideoId(videoId: number) {
    const results = await db
      .select()
      .from(schema.keyframes)
      .where(eq(schema.keyframes.videoId, videoId))
      .orderBy(schema.keyframes.timestampMs);
    return results;
  },

  /**
   * 批量创建关键帧记录
   */
  async createBatch(frames: Array<{
    videoId: number;
    framePath: string;
    timestampMs: number;
    frameNumber: number;
    fileSize?: number;
  }>) {
    const results = await db
      .insert(schema.keyframes)
      .values(frames.map(f => ({ ...f, extractedAt: new Date() })))
      .returning();
    return results;
  },

  /**
   * 删除指定视频的所有关键帧
   */
  async deleteByVideoId(videoId: number) {
    await db.delete(schema.keyframes).where(eq(schema.keyframes.videoId, videoId));
  },

  /**
   * 获取指定视频的关键帧数量
   */
  async getFrameCount(videoId: number) {
    const [result] = await db
      .select({ count: sql<number>`COUNT(*)` })
      .from(schema.keyframes)
      .where(eq(schema.keyframes.videoId, videoId));
    return result?.count || 0;
  },

  /**
   * 清理过期的关键帧（根据项目创建时间）
   * @param daysToKeep 保留天数（默认 7 天）
   * @returns 清理统计信息
   */
  async cleanupOldKeyframes(daysToKeep: number = 7) {
    const { lt } = await import('drizzle-orm');
    const path = await import('path');
    const fs = await import('fs/promises');

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysToKeep);

    // 查找过期项目（通过 videos 表关联）
    const oldVideos = await db
      .select({ id: schema.videos.id, projectId: schema.videos.projectId })
      .from(schema.videos)
      .where(lt(schema.videos.createdAt, cutoffDate));

    let cleanedCount = 0;
    let freedSpaceBytes = 0;
    const cleanedProjects = new Set<number>();

    for (const video of oldVideos) {
      // 删除数据库记录
      const deletedKeyframes = await db
        .delete(schema.keyframes)
        .where(eq(schema.keyframes.videoId, video.id))
        .returning();

      if (deletedKeyframes.length > 0) {
        cleanedCount += deletedKeyframes.length;
        cleanedProjects.add(video.projectId);

        // 删除文件系统中的关键帧目录
        const keyframesDir = path.join(process.cwd(), 'public', 'keyframes', video.id.toString());

        try {
          const { stat, readdir } = await import('fs/promises');

          // 计算目录大小
          let totalSize = 0;
          try {
            const files = await readdir(keyframesDir, { recursive: true });
            for (const file of files) {
              const filePath = path.join(keyframesDir, file);
              try {
                const stats = await stat(filePath);
                if (stats.isFile()) {
                  totalSize += stats.size;
                }
              } catch {}
            }
          } catch {}

          // 删除目录
          await fs.rm(keyframesDir, { recursive: true, force: true });
          freedSpaceBytes += totalSize;

          console.log(`🗑️ 已清理视频 ${video.id} 的关键帧:` +
                      `${deletedKeyframes.length} 帧, ${(totalSize / 1024 / 1024).toFixed(2)}MB`);
        } catch (error) {
          console.warn(`⚠️ 清理关键帧目录失败: ${keyframesDir}`, error);
        }
      }
    }

    return {
      cleanedVideos: oldVideos.length,
      cleanedProjects: cleanedProjects.size,
      cleanedKeyframes: cleanedCount,
      freedSpaceMB: (freedSpaceBytes / 1024 / 1024).toFixed(2),
    };
  },
};

// ============================================
// 导出所有查询
// ============================================

export const queries = {
  project: projectQueries,
  video: videoQueries,
  shot: shotQueries,
  storyline: storylineQueries,
  storylineSegment: storylineSegmentQueries,
  projectAnalysis: projectAnalysisQueries,
  highlight: highlightQueries,
  recapTask: recapTaskQueries,
  recapSegment: recapSegmentQueries,
  audioTranscription: audioTranscriptionQueries,
  keyframe: keyframeQueries,
  hlAudioTranscription: hlAudioTranscriptionQueries,
  hlKeyframe: hlKeyframeQueries,
  queueJob: queueJobQueries,
  stats: statsQueries,
};

export default queries;
