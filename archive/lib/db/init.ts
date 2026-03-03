// ============================================
// DramaCut AI 初始化脚本
// 用于在应用启动时初始化数据库和任务队列
// ============================================

import { dbClient } from './client';
import { queueManager } from '../queue/bullmq';
import { wsServer } from '../ws/server';
import { geminiClient } from '../api/gemini';
import { elevenlabsClient } from '../api/elevenlabs';

/**
 * 初始化应用基础设施
 */
export async function initializeApp() {
  console.log('🚀 正在初始化 DramaCut AI...');

  try {
    // 1. 初始化数据库
    console.log('📦 初始化数据库...');
    await dbClient.init();

    // 健康检查
    const isHealthy = dbClient.healthCheck();
    if (!isHealthy) {
      throw new Error('数据库健康检查失败');
    }
    console.log('✅ 数据库初始化完成');

    // 2. 启动 WebSocket 服务器
    console.log('🔌 启动 WebSocket 服务器...');
    wsServer.start();
    console.log('✅ WebSocket 服务器启动完成');

    // 3. 测试 AI 服务连接
    console.log('🤖 测试 AI 服务连接...');
    try {
      // 测试 Gemini API Key 是否配置
      if (!process.env.GEMINI_API_KEY && !process.env.YUNWU_API_KEY) {
        console.warn('⚠️  Gemini API Key 未配置，AI 分析功能将不可用');
      } else {
        console.log('✅ Gemini API 已配置');
      }

      // 测试 ElevenLabs API Key 是否配置
      if (!process.env.ELEVENLABS_API_KEY) {
        console.warn('⚠️  ElevenLabs API Key 未配置，TTS 功能将不可用');
      } else {
        console.log('✅ ElevenLabs API 已配置');
      }
    } catch (error) {
      console.warn('⚠️  AI 服务连接测试失败:', error);
    }

    // 4. 测试 Redis 连接
    console.log('🔴 测试 Redis 连接...');
    try {
      // 尝试获取一个队列来测试 Redis 连接
      queueManager.getQueue('test');
      console.log('✅ Redis 连接成功');
    } catch (error) {
      console.warn('⚠️  Redis 连接失败，任务队列功能将不可用:', error);
    }

    // 5. 启动任务队列 Workers
    console.log('👷 启动任务队列 Workers...');
    try {
      // 启动视频处理 Worker
      await queueManager.createVideoWorker();

      // 启动深度解说渲染 Worker
      queueManager.createWorker('recap-render', async (job) => {
        // 动态导入深度解说渲染处理器
        const { processRecapRenderJob } = await import('../queue/workers/recap-render');
        return await processRecapRenderJob(job);
      });

      console.log('✅ 任务队列 Workers 启动完成');
    } catch (error) {
      console.warn('⚠️  启动 Workers 失败:', error);
    }

    console.log('🎉 DramaCut AI 初始化完成！');

    // 打印统计信息
    const stats = await dbClient.getStats();
    console.log('📊 数据库统计:', stats);

  } catch (error) {
    console.error('❌ 初始化失败:', error);
    throw error;
  }
}

/**
 * 清理应用资源
 */
export async function cleanupApp() {
  console.log('🧹 正在清理 DramaCut AI...');

  try {
    // 关闭队列管理器
    await queueManager.close();

    // 关闭 WebSocket 服务器
    wsServer.close();

    // 关闭数据库连接
    dbClient.close();

    console.log('✅ 清理完成');
  } catch (error) {
    console.error('❌ 清理失败:', error);
    throw error;
  }
}

// 优雅退出处理
if (typeof process !== 'undefined') {
  process.on('SIGINT', async () => {
    console.log('\n收到 SIGINT 信号，正在优雅退出...');
    await cleanupApp();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    console.log('\n收到 SIGTERM 信号，正在优雅退出...');
    await cleanupApp();
    process.exit(0);
  });
}
