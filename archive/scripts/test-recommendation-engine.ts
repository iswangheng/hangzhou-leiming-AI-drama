/**
 * 推荐引擎测试脚本
 *
 * 用途：验证推荐引擎的基本功能
 * 使用：npm run test:recommendation
 */

import { RecommendationEngine } from '../lib/ai/recommendation-engine';

async function testRecommendationEngine() {
  console.log('==========================================');
  console.log('   推荐引擎功能测试');
  console.log('==========================================\n');

  // 测试配置
  const testCases = [
    {
      name: '正常情况：生成推荐',
      params: {
        analysisId: 1,
        minDurationMs: 90000,  // 90秒
        maxDurationMs: 150000, // 150秒
        maxCombinations: 10,
        allowCrossEpisode: true,
      },
    },
    {
      name: '边界情况：极短时长',
      params: {
        analysisId: 1,
        minDurationMs: 30000,  // 30秒（最小）
        maxDurationMs: 60000,  // 60秒
        maxCombinations: 5,
        allowCrossEpisode: false,
      },
    },
    {
      name: '边界情况：极长时长',
      params: {
        analysisId: 1,
        minDurationMs: 300000, // 5分钟
        maxDurationMs: 600000, // 10分钟
        maxCombinations: 5,
        allowCrossEpisode: true,
      },
    },
  ];

  for (const testCase of testCases) {
    console.log(`\n📊 测试: ${testCase.name}`);
    console.log('────────────────────────────────────────');

    try {
      const startTime = Date.now();

      const results = await RecommendationEngine.generateRecommendations(
        testCase.params
      );

      const duration = Date.now() - startTime;

      console.log(`✅ 成功生成 ${results.length} 个推荐`);
      console.log(`⏱️  耗时: ${duration}ms`);

      if (results.length > 0) {
        console.log('\n🏆 Top 3 推荐:');
        results.slice(0, 3).forEach((result, index) => {
          console.log(`\n  ${index + 1}. ${result.name}`);
          console.log(`     得分: ${result.overallScore.toFixed(1)} (排名: #${result.rank})`);
          console.log(`     时长: ${(result.totalDurationMs / 60000).toFixed(1)} 分钟`);
          console.log(`     评分: 冲突 ${result.conflictScore.toFixed(1)} | ` +
                      `情感 ${result.emotionScore.toFixed(1)} | ` +
                      `悬念 ${result.suspenseScore.toFixed(1)} | ` +
                      `节奏 ${result.rhythmScore.toFixed(1)} | ` +
                      `历史 ${result.historyScore.toFixed(1)}`);
          console.log(`     理由: ${result.reasoning.substring(0, 100)}...`);
        });
      }

    } catch (error) {
      console.error(`❌ 失败: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  console.log('\n==========================================');
  console.log('   测试完成');
  console.log('==========================================\n');
}

// 运行测试
testRecommendationEngine().catch((error) => {
  console.error('测试脚本执行失败:', error);
  process.exit(1);
});
