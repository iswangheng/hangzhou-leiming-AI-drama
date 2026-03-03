// ============================================
// DramaCut AI 数据库查询测试
// Agent 4 - 集成测试
// ============================================

import { describe, it, expect, beforeAll, afterAll, beforeEach } from '@jest/globals';
import { dbClient, queries } from '../index';
import type { NewVideo, NewShot } from '../schema';

describe('Database Queries - 视频管理', () => {
  let testVideoId: number;

  beforeAll(async () => {
    // 初始化数据库
    await dbClient.init();
  });

  afterAll(async () => {
    // 清理并关闭数据库
    await dbClient.close();
  });

  beforeEach(async () => {
    // 每个测试前确保数据库是干净的
    // 注意：在实际项目中，你可能想要使用测试数据库
  });

  describe('视频管理', () => {
    it('应该能够创建视频记录', async () => {
      const videoData: NewVideo = {
        filename: 'test-video.mp4',
        filePath: '/tmp/test-video.mp4',
        fileSize: 1024000,
        durationMs: 60000,
        width: 1920,
        height: 1080,
        fps: 30,
        projectId: 1, // 添加必需的 projectId
        status: 'uploading',
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      const video = await queries.video.create(videoData);

      expect(video).toBeDefined();
      expect(video.id).toBeDefined();
      expect(video.filename).toBe('test-video.mp4');
      expect(video.status).toBe('uploading');

      testVideoId = video.id;
    });

    it('应该能够根据 ID 获取视频', async () => {
      const video = await queries.video.getById(testVideoId);

      expect(video).toBeDefined();
      expect(video?.id).toBe(testVideoId);
      expect(video?.filename).toBe('test-video.mp4');
    });

    it('应该能够更新视频状态', async () => {
      const updatedVideo = await queries.video.updateStatus(testVideoId, 'processing');

      expect(updatedVideo).toBeDefined();
      expect(updatedVideo?.status).toBe('processing');
    });

    it('应该能够更新视频分析结果', async () => {
      const updatedVideo = await queries.video.updateAnalysis(testVideoId, {
        summary: '这是一个测试视频',
        viralScore: 8.5,
      });

      expect(updatedVideo).toBeDefined();
      expect(updatedVideo?.summary).toBe('这是一个测试视频');
      expect(updatedVideo?.viralScore).toBe(8.5);
    });
  });

  describe('镜头切片管理', () => {
    it('应该能够批量创建镜头', async () => {
      const shotsData: NewShot[] = [
        {
          videoId: testVideoId,
          startMs: 0,
          endMs: 5000,
          description: '开场场景',
          emotion: '平静',
          startFrame: 0,
          endFrame: 150,
          createdAt: new Date(),
          updatedAt: new Date(),
        },
        {
          videoId: testVideoId,
          startMs: 5000,
          endMs: 10000,
          description: '冲突场景',
          emotion: '紧张',
          startFrame: 150,
          endFrame: 300,
          createdAt: new Date(),
          updatedAt: new Date(),
        },
      ];

      await queries.shot.createMany(shotsData);

      const shots = await queries.shot.getByVideoId(testVideoId);
      expect(shots).toHaveLength(2);
      expect(shots[0].description).toBe('开场场景');
      expect(shots[1].emotion).toBe('紧张');
    });

    it('应该能够获取时间段内的镜头', async () => {
      const shots = await queries.shot.getByTimeRange(testVideoId, 0, 7500);

      expect(shots).toHaveLength(1);
      expect(shots[0].endMs).toBeLessThanOrEqual(7500);
    });
  });

  describe('高光管理', () => {
    it('应该能够批量创建高光候选', async () => {
      const highlightsData = [
        {
          videoId: testVideoId,
          startMs: 2000,
          endMs: 8000,
          durationMs: 6000,
          reason: '精彩的打斗场面',
          viralScore: 9.0,
          category: 'conflict' as const,
          isConfirmed: false,
          createdAt: new Date(),
          updatedAt: new Date(),
        },
        {
          videoId: testVideoId,
          startMs: 15000,
          endMs: 25000,
          durationMs: 10000,
          reason: '情感爆发',
          viralScore: 8.5,
          category: 'emotional' as const,
          isConfirmed: false,
          createdAt: new Date(),
          updatedAt: new Date(),
        },
      ];

      const highlights = await queries.highlight.createMany(highlightsData);

      expect(highlights).toHaveLength(2);
      expect(highlights[0].reason).toBe('精彩的打斗场面');
    });

    it('应该能够确认高光', async () => {
      const highlights = await queries.highlight.getByVideoId(testVideoId);
      const highlightId = highlights[0].id;

      const confirmed = await queries.highlight.confirm(highlightId);

      expect(confirmed.isConfirmed).toBe(true);
    });
  });

  describe('统计查询', () => {
    it('应该能够获取数据库统计信息', async () => {
      const stats = await queries.stats.getOverview();

      expect(stats).toBeDefined();
      expect(stats.videos).toBeDefined();
      expect(stats.highlights).toBeDefined();
      expect(typeof stats.videos.total).toBe('number');
    });
  });
});

describe('Database Queries - 解说管理', () => {
  let testVideoId: number;
  let testStorylineId: number;

  beforeAll(async () => {
    await dbClient.init();

    // 创建测试视频
    const video = await queries.video.create({
      filename: 'recap-test.mp4',
      filePath: '/tmp/recap-test.mp4',
      fileSize: 2048000,
      durationMs: 120000,
      width: 1920,
      height: 1080,
      fps: 30,
      projectId: 1, // 添加必需的 projectId
      status: 'ready',
      createdAt: new Date(),
      updatedAt: new Date(),
    });

    testVideoId = video.id;

    // 创建测试故事线
    const storyline = await queries.storyline.create({
      videoId: testVideoId,
      name: '复仇主线',
      description: '女主从被陷害到成功复仇的故事',
      attractionScore: 9.5,
      shotIds: '[]',
      category: 'revenge',
      createdAt: new Date(),
      updatedAt: new Date(),
    });

    testStorylineId = storyline.id;
  });

  afterAll(async () => {
    await dbClient.close();
  });

  it('应该能够创建解说任务', async () => {
    const task = await queries.recapTask.create({
      storylineId: testStorylineId,
      style: 'hook',
      title: '你敢信？这个穷小子竟然是亿万富翁！',
      estimatedDurationMs: 90000,
      status: 'pending',
      createdAt: new Date(),
      updatedAt: new Date(),
    });

    expect(task).toBeDefined();
    expect(task.style).toBe('hook');
    expect(task.title).toContain('亿万富翁');
  });

  it('应该能够更新任务状态', async () => {
    const tasks = await queries.recapTask.getByStorylineId(testStorylineId);
    const taskId = tasks[0].id;

    const updated = await queries.recapTask.updateStatus(taskId, 'generating');

    expect(updated.status).toBe('generating');
  });
});
