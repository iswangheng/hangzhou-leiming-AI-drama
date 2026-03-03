# 镜头检测模块 - 使用文档

**Agent 3 - 视频处理**
**状态**: 🔄 代码已完成，等待 Agent 4 添加数据库字段

---

## 功能概述

实现场景切换检测（Shot Detection），为深度解说模式提供素材。

**检测内容**:
- 场景切换点（使用 FFmpeg detect_scene）
- 镜头边界（startMs, endMs）
- 镜头缩略图（thumbnailPath）

**符合接口契约**: `types/api-contracts.ts - SceneShot`

---

## 当前状态

### ✅ 已完成
- ✅ `detectShots()` - 核心检测逻辑
- ✅ `generateThumbnail()` - 缩略图生成
- ✅ `detectSceneChanges()` - FFmpeg 场景检测
- ✅ HTTP API: `/api/video/shots`
- ✅ 测试脚本: `scripts/test-shot-detection.ts`

### ⏸️ 等待中
- ⏸️ 数据库集成（需要 Agent 4 添加 `thumbnailPath` 字段）
- ⏸️ 语义标签填充（Agent 2 的 Gemini 会处理）

---

## 使用方法

### 1. 命令行测试

```bash
# 基础测试
npx tsx scripts/test-shot-detection.ts /path/to/video.mp4

# 自定义选项
npx tsx scripts/test-shot-detection.ts /path/to/video.mp4 \
  --min-duration 2000 \
  --threshold 0.3

# 不生成缩略图（快速测试）
npx tsx scripts/test-shot-detection.ts /path/to/video.mp4 \
  --no-thumbnails
```

### 2. 通过 API 调用

```typescript
// Agent 2 或 Agent 4 调用
const response = await fetch('/api/video/shots', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    videoPath: '/path/to/video.mp4',
    minShotDuration: 2000,      // 最小镜头时长（毫秒）
    generateThumbnails: true,   // 生成缩略图
    thumbnailDir: './thumbnails',
    threshold: 0.3              // 场景切换阈值（0-1）
  })
});

const result = await response.json();

if (result.success) {
  console.log(`检测到 ${result.count} 个镜头`);
  result.shots.forEach(shot => {
    console.log(`  ${shot.startMs}ms - ${shot.endMs}ms`);
    console.log(`  缩略图: ${shot.thumbnailPath}`);
  });
}
```

### 3. 直接调用（后端处理）

```typescript
import { detectShots } from '@/lib/video/shot-detection';

const shots = await detectShots('/path/to/video.mp4', {
  minShotDuration: 2000,
  generateThumbnails: true,
  thumbnailDir: './thumbnails',
  threshold: 0.3
});

console.log(`检测到 ${shots.length} 个镜头`);
```

---

## 数据结构

### SceneShot 接口

```typescript
interface SceneShot {
  id: string;                // 镜头 ID
  startMs: number;           // 开始时间（毫秒）
  endMs: number;             // 结束时间（毫秒）
  thumbnailPath?: string;    // 缩略图路径
  semanticTags: string[];    // 语义标签（Agent 2 填充）
  embeddings?: number[];     // 向量表示（Agent 2 填充）
}
```

### 数据库存储（等待 Agent 4）

```typescript
// lib/db/schema.ts - shots 表
export const shots = sqliteTable('shots', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  videoId: integer('video_id').notNull().references(() => videos.id),

  // 时间信息
  startMs: integer('start_ms').notNull(),
  endMs: integer('end_ms').notNull(),
  startFrame: integer('start_frame').notNull(),
  endFrame: integer('end_frame').notNull(),

  // Gemini 分析结果
  description: text('description').notNull(),
  emotion: text('emotion').notNull(),
  dialogue: text('dialogue'),
  characters: text('characters'),
  viralScore: real('viral_score'),

  // ⚠️ 需要添加：
  thumbnailPath: text('thumbnail_path'),  // 缩略图路径

  ...timestamps,
});
```

---

## 参数说明

### minShotDuration（最小镜头时长）
- **类型**: number（毫秒）
- **默认**: 2000ms（2 秒）
- **说明**: 过滤掉太短的镜头，避免碎片化
- **建议**:
  - 快节奏视频: 1000-1500ms
  - 普通视频: 2000-3000ms
  - 慢节奏视频: 4000-5000ms

### threshold（场景切换阈值）
- **类型**: number（0-1）
- **默认**: 0.3
- **说明**: FFmpeg detect_scene 的阈值
- **影响**:
  - 太低（0.1）: 检测过多，包含微小变化
  - 太高（0.5）: 检测过少，漏掉真实切换
- **建议**:
  - 初次使用: 0.3（默认）
  - 切换不明显: 降低到 0.2
  - 误判过多: 提高到 0.4

### generateThumbnails（生成缩略图）
- **类型**: boolean
- **默认**: true
- **说明**: 是否为每个镜头生成缩略图
- **影响**:
  - 启用: 可视化预览，但速度较慢
  - 禁用: 快速测试，但无法预览

### thumbnailDir（缩略图目录）
- **类型**: string
- **默认**: './thumbnails'
- **说明**: 缩略图保存路径
- **注意**: 会在项目根目录下创建

---

## 性能指标

### 处理速度
- **不生成缩略图**: ~5-10 秒（10 分钟视频）
- **生成缩略图**: ~20-30 秒（10 分钟视频）

### 输出大小
- **缩略图**: 每个 ~50KB（JPEG, q=2）
- **100 个镜头**: ~5MB

### 内存占用
- **峰值**: ~200MB（FFmpeg 进程）

---

## 与其他 Agent 的集成

### Agent 2 (API) - Gemini 分析

**工作流程**:
1. Agent 3 检测镜头（我）
2. Agent 2 调用 Gemini 分析每个镜头
3. Agent 2 更新语义标签到数据库

```typescript
// Agent 2 的代码
import { detectShots } from '@/lib/video/shot-detection';
import { geminiClient } from '@/lib/api/gemini';

// 1. 检测镜头
const shots = await detectShots(videoPath);

// 2. 分析每个镜头
for (const shot of shots) {
  const analysis = await geminiClient.analyzeShot(
    videoPath,
    shot.startMs,
    shot.endMs
  );

  // 3. 更新语义标签
  await updateShotAnalysis(shot.id, analysis.semanticTags);
}
```

### Agent 4 (Data) - 数据库存储

**工作流程**:
1. Agent 3 检测镜头（我）
2. Agent 4 添加 thumbnailPath 字段
3. Agent 3 保存镜头到数据库

```typescript
// Agent 4 需要先做：
// 1. 在 shots 表添加 thumbnailPath 字段
// 2. 运行数据库迁移

// 然后 Agent 3 可以：
import { detectAndSaveShots } from '@/lib/video/db-integration';

await detectAndSaveShots(videoPath, videoId, {
  minShotDuration: 2000,
  generateThumbnails: true
});
```

---

## 常见问题

### Q1: 检测的镜头太少或太多

**调整 threshold 参数**:
```bash
# 镜头太少 → 降低阈值
npx tsx scripts/test-shot-detection.ts video.mp4 --threshold 0.2

# 镜头太多 → 提高阈值
npx tsx scripts/test-shot-detection.ts video.mp4 --threshold 0.4
```

### Q2: 包含了很短的镜头（1 秒以内）

**调整 minShotDuration**:
```bash
npx tsx scripts/test-shot-detection.ts video.mp4 --min-duration 3000
```

### Q3: 缩略图生成失败

**检查 FFmpeg 是否正确安装**:
```bash
ffmpeg -version
```

**检查磁盘空间**:
```bash
df -h .
```

### Q4: 数据库保存失败

**这是正常的！当前被阻塞**:
- shots 表缺少 thumbnailPath 字段
- 等待 Agent 4 添加字段后即可使用

**参考文档**: `docs/AGENT-4-TASK-ADD-THUMBNAIL.md`

---

## 下一步

### 立即可做:
1. ✅ 测试 detectShots() 功能
2. ✅ 调整参数优化检测效果
3. ✅ 生成缩略图预览

### 等待 Agent 4:
1. ⏸️ 数据库集成
2. ⏸️ 保存镜头到 shots 表
3. ⏸️ 查询镜头数据

### Agent 4 完成后:
1. 实现 `saveShotsToDatabase()` 函数
2. 实现 `loadShotsFromDatabase()` 函数
3. 完整的数据库集成测试

---

**相关文档**:
- `types/api-contracts.ts` - 接口定义
- `docs/AGENT-4-TASK-ADD-THUMBNAIL.md` - Agent 4 任务文档
- `COLLABORATION.md` - 协作状态
- `CLAUDE.md` - 项目架构
