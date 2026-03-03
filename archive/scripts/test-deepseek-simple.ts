/**
 * 测试 DeepSeek API 连接（简化版）
 * 通过 yunwu.ai 代理调用 DeepSeek
 */

import { config } from 'dotenv';

// 加载环境变量
config({ path: '.env.local' });

async function testDeepSeek() {
  console.log('🧪 测试 DeepSeek API（通过 yunwu.ai）\n');

  // 读取配置
  const apiKey = process.env.GEMINI_API_KEY || process.env.YUNWU_API_KEY;
  const endpoint = process.env.YUNWU_API_ENDPOINT || 'https://yunwu.ai';

  if (!apiKey) {
    console.error('❌ API Key 未配置');
    console.log('请设置环境变量 GEMINI_API_KEY 或 YUNWU_API_KEY');
    process.exit(1);
  }

  console.log(`✅ 配置: ${endpoint}`);
  console.log(`   API Key: ${apiKey.substring(0, 10)}...${apiKey.substring(apiKey.length - 4)}\n`);

  // 测试用的台词
  const testTranscript = `你这个骗子！我根本不认识你！滚！`;
  console.log(`📝 测试台词: "${testTranscript}"\n`);

  // 方式1: 使用 ?key= 参数
  console.log(`📌 尝试方式1: URL 参数传递 API Key\n`);

  try {
    const apiUrl1 = `${endpoint}/v1/chat/completions?key=${apiKey}`;
    const response1 = await fetch(apiUrl1, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'deepseek-chat',
        messages: [{ role: 'user', content: `分析这段台词的情绪和特征：${testTranscript}` }],
        temperature: 0.7,
        max_tokens: 200,
      }),
    });

    console.log(`   状态: ${response1.status}`);

    if (response1.ok) {
      const result1 = await response1.json();
      console.log(`✅ 成功！模型: deepseek-chat`);
      console.log(`\n响应: ${result1.choices?.[0]?.message?.content}\n`);
      process.exit(0);
    }

    const error1 = await response1.text();
    console.log(`   错误: ${error1}\n`);
  } catch (error) {
    console.log(`   失败: ${error}\n`);
  }

  // 方式2: 使用 Authorization header
  console.log(`📌 尝试方式2: Authorization header\n`);

  try {
    const apiUrl2 = `${endpoint}/v1/chat/completions`;
    const response2 = await fetch(apiUrl2, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'deepseek-chat',
        messages: [{ role: 'user', content: `分析这段台词的情绪和特征：${testTranscript}` }],
        temperature: 0.7,
        max_tokens: 200,
      }),
    });

    console.log(`   状态: ${response2.status}`);

    if (response2.ok) {
      const result2 = await response2.json();
      console.log(`✅ 成功！模型: deepseek-chat`);
      console.log(`\n响应: ${result2.choices?.[0]?.message?.content}\n`);
      process.exit(0);
    }

    const error2 = await response2.text();
    console.log(`   错误: ${error2}\n`);
  } catch (error) {
    console.log(`   失败: ${error}\n`);
  }

  console.log(`❌ 所有方式都失败了\n`);
  console.log(`💡 可能的原因:`);
  console.log(`   1. yunwu.ai 可能不支持 DeepSeek`);
  console.log(`   2. API Key 格式不对`);
  console.log(`   3. 模型名称错误`);
  console.log(`\n🔧 建议: 访问 https://yunwu.ai 查看支持的模型列表\n`);

  process.exit(1);
}

testDeepSeek();
