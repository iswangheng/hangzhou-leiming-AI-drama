# Prompts 目录使用指南

本目录包含所有第三方AI API调用的提示词（Prompt）模板。

## 版本更新

### V2.0 - 精确时间戳版本 (2026-03-03)

**核心改进**：
- ✅ 明确高光点定义："从这个时刻开始"
- ✅ 明确钩子点定义："播放到这个时刻结束"
- ✅ 强调"宁缺毋滥"原则
- ✅ 要求返回精确时间戳（preciseSecond）
- ✅ 要求返回置信度评分（confidence）
- ✅ 添加统计规律指导

**关键Prompt变更**：

**V1 - 旧版**：
```
请分析以下视频片段，识别最关键的"钩子点"。
返回JSON格式：
{
  "isHook": true/false,
  "hookType": "类型名"
}
```

**V2 - 新版**：
```
## 高光点定义
从**这个时刻开始**，观众更愿意看下去
返回窗口内**精确的秒数**（不是窗口开始！）

## 钩子点定义
播放到**这个时刻突然结束**，观众想看后续
返回窗口内**精确的秒数**（不是窗口开始！）

## 人工标记统计规律
- 平均每集只有 1.0 个标记
- 宁缺毋滥，只标记最关键的
```

---

## 📁 目录结构

```
prompts/
├── README.md                      # 本文件
│
├── hangzhou-leiming/              # 杭州雷鸣模块Prompts
│   ├── marking/                   # 标记相关
│   │   ├── analyze-marking.md     # 分析单个标记点（为什么是高光/钩子）
│   │   ├── analyze-keyframes.md   # Gemini Vision分析关键帧
│   │   └── marking-with-skill.md  # 使用技能文件标记新视频
│   │
│   └── training/                  # 训练相关
│       ├── generate-skill.md      # 生成技能文件
│       └── extract-patterns.md    # 提取模式规则
│
└── common/                        # 通用Prompts
    └── json-parser.md             # JSON解析容错
```

## 🎯 Prompt设计原则

### 1. **结构清晰**
- 使用Markdown格式，层次分明
- 明确的章节标题
- 清晰的任务说明

### 2. **变量替换**
- 使用 `{{variable_name}}` 格式定义变量
- 代码中使用 `PromptLoader.fill()` 填充

### 3. **输出规范**
- 明确指定输出格式（JSON）
- 提供示例输出
- 定义字段类型和约束

### 4. **上下文完整**
- 提供足够的背景信息
- 给出明确的判断标准
- 包含典型示例

## 📝 使用示例

### TypeScript代码
```typescript
import { PromptLoader } from '@/lib/prompts/loader';

// 加载Prompt模板
const promptTemplate = await PromptLoader.load(
  'hangzhou-leiming/training/analyze-marking.md'
);

// 填充变量
const prompt = PromptLoader.fill(promptTemplate, {
  marking_type: '高光点',
  timestamp: '00:35',
  transcript: '你这个骗子！...',
  frame_analysis: '人物表情愤怒...'
});

// 调用AI API
const response = await geminiClient.callApi(prompt);
```

### Prompt模板
```markdown
# 分析标记点

## 输入数据
- 标记类型: {{marking_type}}
- 时间点: {{timestamp}}

## 分析任务
请分析以下内容：

### 转录文本
{{transcript}}

### 画面分析
{{frame_analysis}}

## 输出要求
请返回JSON格式：
```json
{
  "emotion": "...",
  "reasoning": "..."
}
```
```

## 🔄 更新Prompt

### 开发环境热更新
```typescript
// 清除缓存，重新加载
PromptLoader.clearCache();
const updatedPrompt = await PromptLoader.load('hangzhou-leiming/training/analyze-marking.md');
```

### 版本控制
- 所有Prompt文件纳入Git版本控制
- 重大修改在文件头部记录变更日期和原因
- 使用Git diff追踪Prompt优化历史

## ⚠️ 注意事项

1. **变量名统一**：使用snake_case命名（如 `marking_type`）
2. **示例完整**：提供完整的输入输出示例
3. **约束明确**：明确字段的类型、范围、格式
4. **语言一致**：使用中文Prompt（因为视频内容是中文）
5. **Token控制**：Prompt长度控制在4000 tokens以内

## 📊 Prompt效果监控

建议记录每次AI调用的结果质量：
```typescript
const result = await callAI(prompt);
// 记录到日志
console.log(`[AI调用] Prompt: ${promptName}, Tokens: ${result.usage}, 质量: ${quality}`);
```

## 🔗 相关文档

- [云雾API配置](../../docs/technical/API-SETUP.md)
- [Gemini客户端](../../lib/api/gemini.ts)
- [Prompt加载器](../../lib/prompts/loader.ts)
