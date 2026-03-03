/**
 * 镜头检测模块
 * Agent 3 - 视频处理
 *
 * 实现场景切换检测和镜头片段提取
 * 符合 types/api-contracts.ts 接口契约
 */

import { execSync } from 'child_process';
import { existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import type { SceneShot } from '@/types/api-contracts';

/**
 * FFmpeg detect_scene 输出解析
 */
interface SceneChange {
  frame: number;      // 帧号
  pts_time: number;   // 时间戳（秒）
  score: number;      // 切换分数（0-1）
}

/**
 * 使用 FFmpeg detect_scene 检测场景切换
 *
 * @param videoPath 视频文件路径
 * @param threshold 切换阈值（0-1，默认 0.3）
 * @returns 场景切换点数组
 */
function detectSceneChanges(
  videoPath: string,
  threshold = 0.3
): SceneChange[] {
  // 使用双引号包裹整个 filter_complex 参数，避免引号嵌套问题
  // 添加 2>&1 将 stderr 重定向到 stdout（FFmpeg 的 showinfo 输出到 stderr）
  const command = `ffmpeg -i "${videoPath}" -filter_complex "[0:v]select='gt(scene,${threshold})',showinfo" -f null - 2>&1`;

  try {
    const output = execSync(command, {
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'pipe']  // 只返回 stdout（通过 2>&1 已经包含 stderr）
    });

    // 解析 FFmpeg 输出
    const lines = output.split('\n');
    const sceneChanges: SceneChange[] = [];

    for (const line of lines) {
      // 查找包含 scene 切换信息的行（支持整数和小数格式）
      const match = line.match(/pts_time:(\d+\.?\d*)/);
      if (match) {
        sceneChanges.push({
          frame: 0, // FFmpeg 没有直接提供帧号
          pts_time: parseFloat(match[1]),
          score: threshold
        });
      }
    }

    return sceneChanges;
  } catch (error) {
    console.error('场景检测失败:', error);
    throw new Error(`场景检测失败: ${error}`);
  }
}

/**
 * 生成镜头缩略图
 *
 * @param videoPath 视频文件路径
 * @param timeMs 时间点（毫秒）
 * @param outputPath 输出路径
 * @returns 缩略图路径
 */
async function generateThumbnail(
  videoPath: string,
  timeMs: number,
  outputPath: string
): Promise<string> {
  // 确保输出目录存在
  const dir = outputPath.substring(0, outputPath.lastIndexOf('/'));
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  // 将毫秒转换为 HH:MM:SS.mmm 格式
  const totalSeconds = timeMs / 1000;
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const timeStr = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${seconds.toFixed(3)}`;

  // FFmpeg 提取单帧作为缩略图
  const command = `ffmpeg -ss ${timeStr} -i "${videoPath}" -vframes 1 -q:v 2 "${outputPath}" -y`;

  try {
    execSync(command, { stdio: ['ignore', 'inherit', 'inherit'] });
    return outputPath;
  } catch (error) {
    console.error('生成缩略图失败:', error);
    throw new Error(`缩略图生成失败: ${error}`);
  }
}

/**
 * 检测场景镜头
 *
 * @param videoPath 视频文件路径
 * @param options 选项
 * @returns SceneShot 数组
 *
 * @example
 * ```typescript
 * const shots = await detectShots('/path/to/video.mp4', {
 *   minShotDuration: 2000,  // 最小镜头时长 2 秒
 *   generateThumbnails: true
 * });
 * ```
 */
export async function detectShots(
  videoPath: string,
  options?: {
    minShotDuration?: number;  // 最小镜头时长（毫秒），默认 2000ms
    generateThumbnails?: boolean; // 是否生成缩略图，默认 true
    thumbnailDir?: string;      // 缩略图目录，默认 './thumbnails'
    threshold?: number;         // 场景切换阈值（0-1），默认 0.3
  }
): Promise<SceneShot[]> {
  const {
    minShotDuration = 2000,
    generateThumbnails = true,
    thumbnailDir = './thumbnails',
    threshold = 0.3
  } = options || {};

  // 1. 验证文件存在
  if (!existsSync(videoPath)) {
    throw new Error(`视频文件不存在: ${videoPath}`);
  }

  // 2. 检测场景切换点
  console.log('🎬 检测场景切换...');
  const sceneChanges = detectSceneChanges(videoPath, threshold);

  // 添加视频开始点
  const allPoints = [
    { pts_time: 0, score: 1.0 },
    ...sceneChanges
  ];

  // 3. 构建镜头片段
  const shots: SceneShot[] = [];
  const videoId = Buffer.from(videoPath).toString('base64').substring(0, 8);

  for (let i = 0; i < allPoints.length - 1; i++) {
    const startPoint = allPoints[i];
    const endPoint = allPoints[i + 1];

    const startMs = Math.floor(startPoint.pts_time * 1000);
    const endMs = Math.floor(endPoint.pts_time * 1000);
    const durationMs = endMs - startMs;

    // 过滤掉太短的镜头
    if (durationMs < minShotDuration) {
      continue;
    }

    const shotId = `${videoId}-${i}`;
    const thumbnailPath = generateThumbnails
      ? join(thumbnailDir, `${shotId}.jpg`)
      : undefined;

    // 生成缩略图
    if (generateThumbnails && thumbnailPath) {
      await generateThumbnail(videoPath, startMs, thumbnailPath);
    }

    shots.push({
      id: shotId,
      startMs,
      endMs,
      thumbnailPath,
      semanticTags: [],  // Agent 2 的 Gemini 会填充
      embeddings: undefined  // Agent 2 的 Gemini 会填充
    });

    console.log(`  ✅ 镜头 ${i + 1}: ${formatDuration(startMs)} - ${formatDuration(endMs)}`);
  }

  console.log(`🎬 检测完成，共 ${shots.length} 个镜头`);

  return shots;
}

/**
 * 格式化时长为可读格式
 */
function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const milliseconds = ms % 1000;

  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(milliseconds).padStart(3, '0')}`;
}

/**
 * 估算帧号（需要 fps）
 *
 * @param timeMs 时间（毫秒）
 * @param fps 帧率
 * @returns 帧号
 */
export function timeToFrame(timeMs: number, fps: number): number {
  return Math.floor((timeMs / 1000) * fps);
}

/**
 * 帧号转时间
 *
 * @param frame 帧号
 * @param fps 帧率
 * @returns 时间（毫秒）
 */
export function frameToTime(frame: number, fps: number): number {
  return Math.floor((frame / fps) * 1000);
}
