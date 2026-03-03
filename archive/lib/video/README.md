# 视频处理模块 - 使用文档

**Agent 3 - 视频处理核心**
**状态**: ✅ 已完成（2025-02-08）

---

## 📦 模块概览

视频处理模块提供完整的视频处理能力，支持从原始视频到最终产出的全流程处理。

### 核心功能

| 功能 | 文件 | 状态 |
|------|------|------|
| 视频元数据提取 | `metadata.ts` | ✅ 完成 |
| 镜头检测 | `shot-detection.ts` | ✅ 完成 |
| 关键帧采样 | `sampling.ts` | ✅ 完成 |
| 数据库集成 | `db-integration.ts` | ✅ 完成 |

### FFmpeg 工具库

| 功能 | 文件 | 状态 |
|------|------|------|
| 基础工具（裁剪、混音） | `ffmpeg/utils.ts` | ✅ 完成 |
| 进度监控 | `ffmpeg/progress.ts` | ✅ 完成 |
| 视频拼接 | `ffmpeg/concat.ts` | ✅ 完成 |
| 多轨道音频混合 | `ffmpeg/multitrack-audio.ts` | ✅ 完成 |

### Remotion 渲染

| 功能 | 文件 | 状态 |
|------|------|------|
| 渲染客户端 | `remotion/renderer.ts` | ✅ 完成 |
| 多片段组合组件 | `components/remotion/MultiClipComposition.tsx` | ✅ 完成 |

---

## 🎯 快速开始

### 1. 视频元数据提取

```typescript
import { getMetadata } from '@/lib/video/metadata';

const metadata = await getMetadata('/path/to/video.mp4');
console.log(metadata.duration);   // 120.5 (秒)
console.log(metadata.width);      // 1920
console.log(metadata.height);     // 1080
console.log(metadata.fps);        // 29.97
```

### 2. 关键帧采样

```typescript
import { sampleKeyFrames } from '@/lib/video/sampling';

// 均匀采样 30 帧
const result = await sampleKeyFrames({
  videoPath: './video.mp4',
  outputDir: './frames',
  frameCount: 30,
  strategy: 'uniform'
});

console.log(result.frames);  // ['帧1.jpg', '帧2.jpg', ...]
```

### 3. 视频拼接

```typescript
import { concatVideos } from '@/lib/ffmpeg/concat';

// 简单拼接
await concatVideos({
  segments: [
    { path: './seg1.mp4' },
    { path: './seg2.mp4' }
  ],
  outputPath: './output.mp4',
  totalDuration: 180,
  onProgress: (progress) => console.log(`${progress.toFixed(1)}%`)
});
```

### 4. 多轨道音频混合

```typescript
import { createStandardMix } from '@/lib/ffmpeg/multitrack-audio';

// 四轨道混合（解说 + 原音 + BGM + 音效）
await createStandardMix({
  videoPath: './video.mp4',
  voiceoverPath: './voiceover.mp3',
  bgmPath: './bgm.mp3',
  sfxPath: './sfx.mp3',
  outputPath: './output.mp4',
  totalDuration: 180
});
```

### 5. Remotion 渲染

```typescript
import { renderCaptionedVideo } from '@/lib/remotion/renderer';

// 渲染带字幕的视频
const result = await renderCaptionedVideo({
  videoPath: './video.mp4',
  subtitles: subtitleData,
  outputPath: './output.mp4',
  onProgress: (progress) => console.log(`${progress.toFixed(1)}%`)
});
```

---

## 📚 详细文档

每个功能都有独立的详细文档：

| 功能 | 文档 | 说明 |
|------|------|------|
| 关键帧采样 | [docs/KEY-FRAME-SAMPLING.md](../docs/KEY-FRAME-SAMPLING.md) | 降低 Gemini Token 90%+ |
| FFmpeg 进度监控 | [docs/FFMPEG-PROGRESS.md](../docs/FFMPEG-PROGRESS.md) | 实时进度反馈 |
| 视频拼接 | [docs/VIDEO-CONCAT.md](../docs/VIDEO-CONCAT.md) | concat demuxer/filter |
| 多轨道音频混合 | [docs/MULTITRACK-AUDIO.md](../docs/MULTITRACK-AUDIO.md) | 四轨道混音 |
| Remotion 渲染客户端 | [docs/REMOTION-RENDERER.md](../docs/REMOTION-RENDERER.md) | 程序化渲染 |
| 多片段组合 | [docs/MULTICLIP-COMPOSITION.md](../docs/MULTICLIP-COMPOSITION.md) | Remotion 组件 |

---

## 🧪 测试脚本

每个功能都有对应的测试脚本：

```bash
# 测试关键帧采样
npx tsx scripts/test-sampling.ts ./video.mp4

# 测试 FFmpeg 进度监控
npx tsx scripts/test-ffmpeg-progress.ts ./video.mp4 trim

# 测试视频拼接
npx tsx scripts/test-concat.ts ./seg1.mp4 ./seg2.mp4

# 测试多轨道音频混合
npx tsx scripts/test-multitrack-audio.ts ./video.mp4 \
  --voiceover ./voiceover.mp3 --bgm ./bgm.mp3

# 测试 Remotion 渲染
npx tsx scripts/test-remotion-renderer.ts ./video.mp4 ./subtitles.json

# 测试多片段组合
npx tsx scripts/test-multiclip.ts ./clip1.mp4 ./clip2.mp4 --transition fade
```

---

## 🔧 API 集成

### 与 Gemini API 集成

```typescript
import { sampleKeyFrames } from '@/lib/video/sampling';
import { geminiClient } from '@/lib/api/gemini';

// 1. 采样关键帧
const { frames } = await sampleKeyFrames({
  videoPath: './video.mp4',
  outputDir: './frames',
  frameCount: 30
});

// 2. 转换为 Base64
const frameBase64Array = frames.map(framePath => {
  const buffer = readFileSync(framePath);
  return buffer.toString('base64');
});

// 3. 调用 Gemini 分析
const analysis = await geminiClient.analyzeVideo(
  './video.mp4',
  frameBase64Array
);
```

### 与 ElevenLabs TTS 集成

```typescript
import { createStandardMix } from '@/lib/ffmpeg/multitrack-audio';
import { elevenlabsClient } from '@/lib/api/elevenlabs';

// 1. TTS 生成配音
const { audioBuffer } = await elevenlabsClient.textToSpeech({
  text: '这是解说文案',
  voiceId: 'your_voice_id'
});

// 2. 保存音频文件
writeFileSync('./voiceover.mp3', audioBuffer);

// 3. 四轨道混音
await createStandardMix({
  videoPath: './video.mp4',
  voiceoverPath: './voiceover.mp3',
  bgmPath: './bgm.mp3',
  outputPath: './output.mp4'
});
```

---

## 📊 性能基准

### 关键帧采样

| 视频时长 | 采样帧数 | 耗时 | Token 节省 |
|---------|---------|------|-----------|
| 2 分钟 | 30 帧 | ~10秒 | 90%+ |
| 10 分钟 | 30 帧 | ~15秒 | 90%+ |

### 视频拼接

| 片段数 | 总时长 | 方法 | 耗时 |
|-------|-------|------|------|
| 2 片段 | 5分钟 | demuxer | ~5秒 |
| 2 片段 | 5分钟 | filter + fade | ~35秒 |

### 多轨道音频混合

| 轨道数 | 视频时长 | 耗时 |
|-------|---------|------|
| 2 轨道 | 5分钟 | ~10秒 |
| 4 轨道 | 5分钟 | ~15秒 |

### Remotion 渲染

| 视频时长 | 分辨率 | 预设 | 渲染耗时 |
|---------|-------|------|---------|
| 30 秒 | 1080x1920 | ultrafast | ~15秒 |
| 60 秒 | 1080x1920 | ultrafast | ~30秒 |

---

## 🎓 技术细节

### 依赖项

```json
{
  "dependencies": {
    "@remotion/media-utils": "^latest",
    "fluent-ffmpeg": "^2.1.2",
    "@remotion/bundler": "^latest",
    "@remotion/renderer": "^latest"
  }
}
```

### FFmpeg 要求

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# 验证安装
ffmpeg -version
```

---

## 🚀 后续计划

- [ ] 支持更多视频格式（MKV, AVI）
- [ ] 添加视频质量评估
- [ ] 实现智能采样（AI 选择关键帧）
- [ ] 支持多线程批量处理

---

**相关文档**:
- [IMPLEMENTATION.md](../IMPLEMENTATION.md) - 实施进度
- [ROADMAP.md](../ROADMAP.md) - 项目路线图
- [docs/](../docs/) - 功能文档目录

---

**最后更新**: 2025-02-08
**Agent**: Agent 3 (视频处理核心)
