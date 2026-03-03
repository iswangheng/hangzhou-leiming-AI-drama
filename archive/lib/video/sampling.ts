/**
 * 关键帧采样模块
 * Agent 3 - 视频处理
 *
 * 从视频中采样关键帧，用于 Gemini 视频分析
 * 目标：降低 Token 消耗，同时保留足够的视觉信息
 */

import { execSync } from 'child_process';
import { existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { getMetadata } from './metadata';

/**
 * 采样策略
 */
export type SamplingStrategy = 'uniform' | 'scene-based';

/**
 * 关键帧采样选项
 */
export interface KeyFrameSamplingOptions {
  /** 视频文件路径 */
  videoPath: string;
  /** 输出目录 */
  outputDir: string;
  /** 采样帧数（默认 30） */
  frameCount?: number;
  /** 采样策略 */
  strategy?: SamplingStrategy;
  /** JPEG 质量 (1-31，默认 5，数值越小质量越高) */
  quality?: number;
  /** 代理分辨率宽度（默认 640，用于降低存储和 Token 消耗） */
  proxyWidth?: number;
  /** 是否生成缩略图（默认 false） */
  generateThumbnail?: boolean;
  /** 最小镜头时长（毫秒），仅用于 scene-based 策略 */
  minShotDuration?: number;
}

/**
 * 采样结果
 */
export interface SamplingResult {
  /** 采样帧文件路径数组 */
  frames: string[];
  /** 采样策略 */
  strategy: SamplingStrategy;
  /** 总帧数 */
  totalFrames: number;
  /** 输出目录 */
  outputDir: string;
}

/**
 * 均匀采样关键帧
 * 按固定时间间隔采样
 */
async function sampleUniformly(
  videoPath: string,
  outputDir: string,
  frameCount: number,
  quality: number,
  proxyWidth: number,
  generateThumbnail: boolean
): Promise<string[]> {
  console.log('📸 均匀采样模式...');

  // 1. 获取视频元数据
  const metadata = await getMetadata(videoPath);
  const durationMs = metadata.duration * 1000;

  // 2. 计算采样间隔
  const intervalMs = durationMs / (frameCount + 1);

  console.log(`   视频时长: ${(durationMs / 1000).toFixed(1)}秒`);
  console.log(`   采样间隔: ${intervalMs.toFixed(0)}ms`);
  console.log(`   目标帧数: ${frameCount}`);

  // 3. 采样每一帧
  const frames: string[] = [];

  for (let i = 0; i < frameCount; i++) {
    const timestampMs = intervalMs * (i + 1);
    const framePath = join(outputDir, `frame_${String(i + 1).padStart(3, '0')}.jpg`);

    // 提取单帧
    await extractFrame(videoPath, timestampMs, framePath, quality, proxyWidth);
    frames.push(framePath);

    console.log(`   ✅ 帧 ${i + 1}/${frameCount}: ${formatTime(timestampMs)}`);
  }

  // 4. 生成封面缩略图（第一帧）
  if (generateThumbnail) {
    const thumbnailPath = join(outputDir, 'thumbnail.jpg');
    await extractFrame(videoPath, 0, thumbnailPath, quality, proxyWidth);
    console.log(`   🖼️  封面: ${thumbnailPath}`);
  }

  return frames;
}

/**
 * 基于场景采样关键帧
 * 使用镜头检测结果，从每个镜头中选择代表性帧
 */
async function sampleByScenes(
  videoPath: string,
  outputDir: string,
  frameCount: number,
  quality: number,
  proxyWidth: number,
  minShotDuration: number
): Promise<string[]> {
  console.log('🎬 基于场景采样模式...');

  // 1. 先检测镜头
  const { detectShots } = await import('./shot-detection');
  const shots = await detectShots(videoPath, {
    minShotDuration,
    generateThumbnails: false, // 我们自己生成
    threshold: 0.3
  });

  console.log(`   检测到 ${shots.length} 个镜头`);

  // 2. 从每个镜头中选择代表性帧
  const frames: string[] = [];
  const framesPerShot = Math.ceil(frameCount / shots.length);

  for (let shotIndex = 0; shotIndex < shots.length; shotIndex++) {
    const shot = shots[shotIndex];
    const shotDuration = shot.endMs - shot.startMs;

    // 从镜头中选择 framesPerShot 个关键帧
    const interval = shotDuration / (framesPerShot + 1);

    for (let i = 0; i < framesPerShot && frames.length < frameCount; i++) {
      const timestampMs = shot.startMs + interval * (i + 1);
      const framePath = join(outputDir, `shot_${shotIndex + 1}_frame_${i + 1}.jpg`);

      await extractFrame(videoPath, timestampMs, framePath, quality, proxyWidth);
      frames.push(framePath);

      console.log(`   ✅ 镜头 ${shotIndex + 1} 帧 ${i + 1}: ${formatTime(timestampMs)}`);
    }
  }

  return frames;
}

/**
 * 提取单帧
 */
async function extractFrame(
  videoPath: string,
  timestampMs: number,
  outputPath: string,
  quality: number,
  width: number
): Promise<void> {
  const timeStr = msToFFmpegTime(timestampMs);

  const command = [
    'ffmpeg',
    '-ss', timeStr,
    '-i', videoPath,
    '-vframes', '1',
    '-q:v', quality.toString(),
    '-vf', `scale=${width}:-1`,  // 保持宽高比
    '-y',
    outputPath
  ].join(' ');

  try {
    execSync(command, {
      stdio: ['ignore', 'pipe', 'pipe']  // 只捕获错误输出
    });
  } catch (error) {
    throw new Error(`提取帧失败 (${outputPath}): ${error}`);
  }
}

/**
 * 将毫秒转换为 FFmpeg 时间格式
 */
function msToFFmpegTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

/**
 * 格式化时间为可读格式
 */
function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const milliseconds = ms % 1000;

  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(milliseconds).padStart(3, '0')}`;
}

/**
 * 采样关键帧
 *
 * @param options 采样选项
 * @returns 采样结果
 *
 * @example
 * ```typescript
 * // 均匀采样 30 帧
 * const result = await sampleKeyFrames({
 *   videoPath: '/path/to/video.mp4',
 *   outputDir: './frames',
 *   frameCount: 30,
 *   strategy: 'uniform'
 * });
 *
 * // 基于场景采样 50 帧
 * const result2 = await sampleKeyFrames({
 *   videoPath: '/path/to/video.mp4',
 *   outputDir: './frames',
 *   frameCount: 50,
 *   strategy: 'scene-based',
 *   minShotDuration: 2000
 * });
 * ```
 */
export async function sampleKeyFrames(
  options: KeyFrameSamplingOptions
): Promise<SamplingResult> {
  const {
    videoPath,
    outputDir,
    frameCount = 30,
    strategy = 'uniform',
    quality = 5,
    proxyWidth = 640,
    generateThumbnail = false,
    minShotDuration = 2000
  } = options;

  console.log('🎬 开始关键帧采样...');
  console.log(`   视频: ${videoPath}`);
  console.log(`   输出目录: ${outputDir}`);
  console.log(`   采样策略: ${strategy}`);

  // 1. 验证文件存在
  if (!existsSync(videoPath)) {
    throw new Error(`视频文件不存在: ${videoPath}`);
  }

  // 2. 创建输出目录
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true });
    console.log(`📁 创建输出目录: ${outputDir}`);
  }

  // 3. 根据策略采样
  let frames: string[];

  if (strategy === 'uniform') {
    frames = await sampleUniformly(
      videoPath,
      outputDir,
      frameCount,
      quality,
      proxyWidth,
      generateThumbnail
    );
  } else if (strategy === 'scene-based') {
    frames = await sampleByScenes(
      videoPath,
      outputDir,
      frameCount,
      quality,
      proxyWidth,
      minShotDuration
    );
  } else {
    throw new Error(`不支持的采样策略: ${strategy}`);
  }

  const result: SamplingResult = {
    frames,
    strategy,
    totalFrames: frames.length,
    outputDir
  };

  console.log(`\n✅ 采样完成，共 ${frames.length} 帧`);
  console.log(`📁 输出目录: ${outputDir}`);

  return result;
}

/**
 * 批量采样多个视频
 *
 * @param videos 视频列表和采样选项
 * @returns 所有采样结果
 */
export async function batchSampleKeyFrames(
  videos: Array<{
    videoPath: string;
    options?: Omit<KeyFrameSamplingOptions, 'videoPath' | 'outputDir'>;
  }>
): Promise<Map<string, SamplingResult>> {
  const results = new Map<string, SamplingResult>();

  for (const { videoPath, options = {} } of videos) {
    const outputDir = `./frames/${Buffer.from(videoPath).toString('base64').substring(0, 8)}`;

    try {
      const result = await sampleKeyFrames({
        videoPath,
        outputDir,
        ...options
      });

      results.set(videoPath, result);
    } catch (error) {
      console.error(`❌ ${videoPath} 采样失败:`, error);
      throw error;
    }
  }

  return results;
}
