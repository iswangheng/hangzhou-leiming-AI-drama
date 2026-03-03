/**
 * 视频元数据提取模块
 * Agent 3 - 视频处理
 *
 * 提供视频元数据获取功能，符合 types/api-contracts.ts 接口契约
 */

import { execSync } from 'child_process';
import { existsSync, statSync } from 'fs';
import type { VideoMetadata } from '@/types/api-contracts';

/**
 * 从 ffprobe 输出解析视频元数据
 */
interface FFProbeOutput {
  streams: Array<{
    codec_type: string;
    codec_name: string;
    width?: number;
    height?: number;
    r_frame_rate?: string;
    bit_rate?: string;
    duration?: string;
  }>;
  format: {
    duration: string;
    size: string;
    bit_rate: string;
  };
}

/**
 * 使用 ffprobe 获取详细视频信息
 */
function getFFProbeMetadata(videoPath: string): FFProbeOutput {
  const command = `ffprobe -v quiet -print_format json -show_streams -show_format "${videoPath}"`;

  try {
    const output = execSync(command, { encoding: 'utf-8' });
    return JSON.parse(output) as FFProbeOutput;
  } catch (error) {
    console.error('FFprobe 执行失败:', error);
    throw new Error(`无法读取视频元数据: ${error}`);
  }
}

/**
 * 获取视频元数据
 *
 * @param videoPath 视频文件路径
 * @returns VideoMetadata 符合接口契约的视频元数据
 *
 * @example
 * ```typescript
 * const metadata = await getMetadata('/path/to/video.mp4');
 * console.log(metadata.duration); // 120.5 (秒)
 * console.log(metadata.width);    // 1920
 * console.log(metadata.height);   // 1080
 * ```
 */
export async function getMetadata(videoPath: string): Promise<VideoMetadata> {
  // 1. 验证文件存在
  if (!existsSync(videoPath)) {
    throw new Error(`视频文件不存在: ${videoPath}`);
  }

  // 2. 使用 ffprobe 获取详细信息（包括比特率）
  const ffprobeData = getFFProbeMetadata(videoPath);

  // 4. 提取视频流信息
  const videoStream = ffprobeData.streams.find(
    (stream) => stream.codec_type === 'video'
  );

  if (!videoStream) {
    throw new Error('未找到视频流');
  }

  // 5. 解析帧率（ffprobe 返回 "30000/1001" 格式）
  let fps = 30; // 默认帧率
  if (videoStream.r_frame_rate) {
    const [numerator, denominator] = videoStream.r_frame_rate.split('/');
    fps = parseFloat(numerator) / parseFloat(denominator);
  }

  // 6. 获取文件大小
  const size = statSync(videoPath).size;

  // 7. 解析时长（ffprobe 返回秒数）
  const duration = parseFloat(ffprobeData.format.duration);

  // 8. 组装完整的元数据对象（符合接口契约）
  const metadata: VideoMetadata = {
    duration,
    width: videoStream.width || 1920,
    height: videoStream.height || 1080,
    fps,
    bitrate: parseInt(ffprobeData.format.bit_rate) || 0,
    codec: videoStream.codec_name,
    size,
  };

  return metadata;
}

/**
 * 批量获取多个视频的元数据
 * 用于项目初始化时批量处理
 *
 * @param videoPaths 视频文件路径数组
 * @returns VideoMetadata 数组
 */
export async function getBatchMetadata(
  videoPaths: string[]
): Promise<VideoMetadata[]> {
  const results = await Promise.allSettled(
    videoPaths.map((path) => getMetadata(path))
  );

  return results.map((result, index) => {
    if (result.status === 'fulfilled') {
      return result.value;
    } else {
      console.error(`视频 ${videoPaths[index]} 元数据获取失败:`, result.reason);
      throw result.reason;
    }
  });
}

/**
 * 验证视频是否符合处理要求
 *
 * @param metadata 视频元数据
 * @returns 验证结果和错误信息
 */
export function validateVideoMetadata(metadata: VideoMetadata): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // 检查时长（至少 1 秒）
  if (metadata.duration < 1) {
    errors.push(`视频时长过短: ${metadata.duration}秒`);
  }

  // 检查分辨率（最小 720p）
  if (metadata.width < 1280 || metadata.height < 720) {
    errors.push(`分辨率过低: ${metadata.width}x${metadata.height}，建议至少 1280x720`);
  }

  // 检查帧率（建议 25-60 fps）
  if (metadata.fps < 25 || metadata.fps > 60) {
    errors.push(`帧率异常: ${metadata.fps}fps，建议 25-60fps`);
  }

  // 检查编码格式
  const supportedCodecs = ['h264', 'h265', 'hevc', 'vp9', 'av1'];
  if (!supportedCodecs.includes(metadata.codec.toLowerCase())) {
    errors.push(`编码格式可能不支持: ${metadata.codec}`);
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * 格式化元数据为人类可读格式
 * 用于调试和日志
 */
export function formatMetadata(metadata: VideoMetadata): string {
  const durationMinutes = Math.floor(metadata.duration / 60);
  const durationSeconds = (metadata.duration % 60).toFixed(1);

  return `
视频元数据
---------
时长: ${durationMinutes}分${durationSeconds}秒
分辨率: ${metadata.width}x${metadata.height}
帧率: ${metadata.fps.toFixed(2)} fps
编码: ${metadata.codec.toUpperCase()}
比特率: ${(metadata.bitrate / 1000000).toFixed(2)} Mbps
文件大小: ${(metadata.size / 1024 / 1024).toFixed(2)} MB
  `.trim();
}
