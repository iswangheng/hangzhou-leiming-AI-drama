// ============================================
// AI 学习流程测试脚本
// 用于验证学习流程的各个组件
// ============================================

import { startLearning, type LearningConfig } from '../lib/ai/learning-pipeline';
import { extractKeyframes } from '../lib/video/keyframes';
import { transcribeAudio } from '../lib/audio/transcriber';
import { getGeminiClient } from '../lib/api/gemini';
import { db } from '../lib/db/client';
import { hlMarkings, hlVideos, hlProjects } from '../lib/db/schema';
import { eq } from 'drizzle-orm';

/**
 * 测试数据准备
 */
async function testDataPreparation(projectId: number) {
  console.log('\n📊 测试 1: 数据准备\n');

  try {
    // 获取项目信息
    const [project] = await db
      .select()
      .from(hlProjects)
      .where(eq(hlProjects.id, projectId));

    if (!project) {
      console.error('❌ 项目不存在');
      return false;
    }

    console.log(`✅ 项目名称: ${project.name}`);
    console.log(`   状态: ${project.status}`);

    // 获取视频数量
    const videos = await db
      .select()
      .from(hlVideos)
      .where(eq(hlVideos.projectId, projectId));

    console.log(`✅ 视频数量: ${videos.length}`);

    if (videos.length === 0) {
      console.error('❌ 项目没有视频');
      return false;
    }

    // 获取标记数量
    const markings = await db
      .select()
      .from(hlMarkings)
      .where(eq(hlMarkings.projectId, projectId));

    console.log(`✅ 标记数量: ${markings.length}`);

    if (markings.length === 0) {
      console.error('❌ 项目没有标记数据');
      return false;
    }

    // 按类型统计
    const highlightCount = markings.filter((m: any) => m.type === '高光点').length;
    const hookCount = markings.filter((m: any) => m.type === '钩子点').length;

    console.log(`   - 高光点: ${highlightCount}`);
    console.log(`   - 钩子点: ${hookCount}`);

    // 按集数统计
    const episodesMap = new Map<string, number>();
    for (const marking of markings) {
      const video = videos.find((v: any) => v.id === marking.videoId);
      if (video) {
        const episode = video.episodeNumber;
        episodesMap.set(episode, (episodesMap.get(episode) || 0) + 1);
      }
    }

    console.log(`\n📺 标记分布（按集数）:`);
    for (const [episode, count] of episodesMap.entries()) {
      console.log(`   - ${episode}: ${count} 个标记`);
    }

    return true;
  } catch (error) {
    console.error('❌ 数据准备测试失败:', error);
    return false;
  }
}

/**
 * 测试关键帧提取
 */
async function testKeyframeExtraction(videoPath: string) {
  console.log('\n📸 测试 2: 关键帧提取\n');

  try {
    console.log(`视频路径: ${videoPath}`);

    const result = await extractKeyframes({
      videoPath,
      frameCount: 5, // 测试时只提取 5 帧
    });

    console.log(`✅ 提取完成:`);
    console.log(`   - 帧数: ${result.framePaths.length}`);
    console.log(`   - 输出目录: ${result.outputDir}`);
    console.log(`   - 时间戳: ${result.timestamps.slice(0, 3).map(t => `${t}ms`).join(', ')}...`);

    return true;
  } catch (error) {
    console.error('❌ 关键帧提取测试失败:', error);
    return false;
  }
}

/**
 * 测试音频转录
 */
async function testAudioTranscription(audioPath: string) {
  console.log('\n🎙️ 测试 3: 音频转录\n');

  try {
    console.log(`音频路径: ${audioPath}`);

    const result = await transcribeAudio(audioPath, {
      language: 'zh',
      model: 'tiny',
    });

    console.log(`✅ 转录完成:`);
    console.log(`   - 文本长度: ${result.text.length} 字`);
    console.log(`   - 语言: ${result.language}`);
    console.log(`   - 时长: ${result.duration} 秒`);
    console.log(`   - 片段数: ${result.segments.length}`);
    console.log(`\n转录文本预览:`);
    console.log(result.text.substring(0, 200) + '...');

    return true;
  } catch (error) {
    console.error('❌ 音频转录测试失败:', error);
    return false;
  }
}

/**
 * 测试 Gemini 分析
 */
async function testGeminiAnalysis() {
  console.log('\n🤖 测试 4: Gemini 分析\n');

  try {
    const geminiClient = getGeminiClient();

    const testPrompt = `请分析以下短剧场景：

时间点: 00:35
类型: 高光点
关键帧描述:
- 帧1: 人物A愤怒表情特写
- 帧2: 人物A打了人物B一耳光
- 帧3: 周围人震惊表情

转录文本: "你怎么敢这样对我！"

请返回 JSON 格式的高光类型分析。`;

    const response = await geminiClient.callApi(
      testPrompt,
      '你是一位短剧剪辑分析师。'
    );

    if (response.success && response.data) {
      console.log(`✅ Gemini 分析成功:`);
      console.log(`   - 响应长度: ${(response.data as string).length} 字`);
      console.log(`\n响应预览:`);
      console.log((response.data as string).substring(0, 500) + '...');
      return true;
    } else {
      console.error('❌ Gemini 分析失败:', response.error);
      return false;
    }
  } catch (error) {
    console.error('❌ Gemini 分析测试失败:', error);
    return false;
  }
}

/**
 * 测试完整学习流程
 */
async function testFullLearningFlow(projectId: number) {
  console.log('\n🎓 测试 5: 完整学习流程\n');

  try {
    const config: LearningConfig = {
      projectId,
      framesPerMarking: 5, // 测试时使用较少的帧
      skipExistingFrames: false,
      skipExistingTranscript: false,
      onProgress: (progress, message) => {
        console.log(`   [${progress}%] ${message}`);
      },
    };

    console.log('启动学习流程...');
    const result = await startLearning(config);

    console.log('\n✅ 学习流程完成:');
    console.log(`   - 技能文件 ID: ${result.skillId}`);
    console.log(`   - 总标记数: ${result.totalMarkings}`);
    console.log(`   - 成功: ${result.successCount}`);
    console.log(`   - 失败: ${result.failureCount}`);
    console.log(`\n技能文件内容预览:`);
    console.log(result.skillContent.substring(0, 500) + '...');

    return true;
  } catch (error) {
    console.error('❌ 学习流程测试失败:', error);
    return false;
  }
}

/**
 * 主测试函数
 */
async function main() {
  console.log('========================================');
  console.log('  AI 学习流程测试脚本');
  console.log('========================================');

  const args = process.argv.slice(2);
  const command = args[0];
  const projectId = args[1] ? parseInt(args[1]) : 1;

  switch (command) {
    case 'data':
      await testDataPreparation(projectId);
      break;

    case 'keyframes': {
      const videoPath = args[2];
      if (!videoPath) {
        console.error('❌ 请提供视频路径');
        process.exit(1);
      }
      await testKeyframeExtraction(videoPath);
      break;
    }

    case 'transcript': {
      const audioPath = args[2];
      if (!audioPath) {
        console.error('❌ 请提供音频路径');
        process.exit(1);
      }
      await testAudioTranscription(audioPath);
      break;
    }

    case 'gemini':
      await testGeminiAnalysis();
      break;

    case 'full':
      await testFullLearningFlow(projectId);
      break;

    case 'all':
      const dataOk = await testDataPreparation(projectId);
      if (!dataOk) {
        console.error('\n❌ 数据准备测试失败，跳过后续测试');
        process.exit(1);
      }

      await testGeminiAnalysis();
      await testFullLearningFlow(projectId);
      break;

    default:
      console.log(`
用法: npm run test:learning <command> [args]

命令:
  data [projectId]        - 测试数据准备
  keyframes <videoPath>    - 测试关键帧提取
  transcript <audioPath>   - 测试音频转录
  gemini                   - 测试 Gemini 分析
  full [projectId]         - 测试完整学习流程
  all [projectId]          - 运行所有测试

示例:
  npm run test:learning data 1
  npm run test:learning full 1
  npm run test:learning all 1
      `);
  }

  console.log('\n========================================');
  console.log('  测试完成');
  console.log('========================================\n');

  process.exit(0);
}

main();
