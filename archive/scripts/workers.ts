// ============================================
// DramaCut AI 队列 Worker 启动脚本
// 在独立的进程中运行任务队列 Worker
// ============================================

import * as dotenv from 'dotenv';
import * as path from 'path';

// 加载环境变量
const envPath = path.resolve(process.cwd(), '.env.local');
const result = dotenv.config({ path: envPath });

if (result.error) {
  console.warn('⚠️  警告: .env.local 加载失败，使用系统环境变量');
} else {
  console.log('✅ 环境变量已加载:', envPath);
}

import { queueManager, QUEUE_NAMES } from '../lib/queue/bullmq';
import { videoJobProcessor } from '../lib/queue/workers';
import { wsServer } from '../lib/ws/server';

/**
 * 启动所有 Worker
 */
async function startWorkers() {
  console.log('🚀 启动 DramaCut AI 队列 Workers...\n');

  // 1. 启动视频处理 Worker（镜头检测）
  queueManager.createWorker(QUEUE_NAMES.videoProcessing, videoJobProcessor);
  console.log(`✅ 视频处理 Worker 已启动: ${QUEUE_NAMES.videoProcessing}`);

  // 2. 启动 Gemini 分析 Worker
  queueManager.createWorker(QUEUE_NAMES.geminiAnalysis, videoJobProcessor);
  console.log(`✅ Gemini 分析 Worker 已启动: ${QUEUE_NAMES.geminiAnalysis}`);

  // 3. 启动 TTS 生成 Worker
  queueManager.createWorker(QUEUE_NAMES.ttsGeneration, videoJobProcessor);
  console.log(`✅ TTS 生成 Worker 已启动: ${QUEUE_NAMES.ttsGeneration}`);

  // 4. 启动视频渲染 Worker
  queueManager.createWorker(QUEUE_NAMES.videoRender, videoJobProcessor);
  console.log(`✅ 视频渲染 Worker 已启动: ${QUEUE_NAMES.videoRender}`);

  // 5. 监听队列事件（可选）
  queueManager.listenQueueEvents(QUEUE_NAMES.videoProcessing, {
    onWaiting: (jobId) => {
      console.log(`⏳ 视频处理任务等待中: ${jobId}`);
    },
    onActive: (jobId) => {
      console.log(`🔄 视频处理任务进行中: ${jobId}`);
    },
    onCompleted: (jobId) => {
      console.log(`✅ 视频处理任务完成: ${jobId}`);
    },
    onFailed: (jobId, error) => {
      console.error(`❌ 视频处理任务失败: ${jobId}`, error);
    },
  });

  queueManager.listenQueueEvents(QUEUE_NAMES.geminiAnalysis, {
    onWaiting: (jobId) => {
      console.log(`⏳ Gemini 分析任务等待中: ${jobId}`);
    },
    onActive: (jobId) => {
      console.log(`🔄 Gemini 分析任务进行中: ${jobId}`);
    },
    onCompleted: (jobId) => {
      console.log(`✅ Gemini 分析任务完成: ${jobId}`);
    },
    onFailed: (jobId, error) => {
      console.error(`❌ Gemini 分析任务失败: ${jobId}`, error);
    },
  });

  console.log('\n✨ 所有 Workers 已启动，等待任务...\n');

  // 优雅关闭处理
  const shutdown = async () => {
    console.log('\n🛑 正在关闭 Workers...');
    await queueManager.close();
    console.log('✅ Workers 已关闭');
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

// 启动 Workers
startWorkers().catch((error) => {
  console.error('❌ 启动 Workers 失败:', error);
  process.exit(1);
});
