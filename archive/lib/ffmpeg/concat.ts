/**
 * 视频拼接模块
 * Agent 3 - 视频处理核心
 *
 * 提供视频片段拼接功能，用于将多个视频片段合并为一个完整视频
 * 支持转场效果、音频对齐等高级功能
 */

import { existsSync, unlinkSync, writeFileSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { execFFmpegWithProgress, ProgressCallback } from './progress';

/**
 * 视频片段
 */
export interface VideoSegment {
  /** 视频文件路径 */
  path: string;
  /** 开始时间（毫秒），可选 */
  startMs?: number;
  /** 持续时间（毫秒），可选 */
  durationMs?: number;
}

/**
 * 拼接选项
 */
export interface ConcatOptions {
  /** 视频片段列表 */
  segments: VideoSegment[];
  /** 输出文件路径 */
  outputPath: string;
  /** 转场效果（默认 null，即无转场） */
  transition?: null | 'fade' | 'crossfade';
  /** 转场持续时间（毫秒，默认 500） */
  transitionDurationMs?: number;
  /** 输出视频宽度（默认 1920） */
  width?: number;
  /** 输出视频高度（默认 1080） */
  height?: number;
  /** 输出帧率（默认 30） */
  fps?: number;
  /** 视频编码器（默认 libx264） */
  videoCodec?: string;
  /** CRF 质量（默认 18） */
  crf?: number;
  /** 编码预设（默认 fast） */
  preset?: string;
  /** 音频编码器（默认 aac） */
  audioCodec?: string;
  /** 音频比特率（默认 192k） */
  audioBitrate?: string;
  /** 总视频时长（秒），用于进度计算 */
  totalDuration?: number;
  /** 进度回调函数 */
  onProgress?: ProgressCallback;
}

/**
 * 拼接结果
 */
export interface ConcatResult {
  /** 输出文件路径 */
  outputPath: string;
  /** 总时长（秒） */
  duration: number;
  /** 总大小（字节） */
  size: number;
  /** 拼接的片段数量 */
  segmentCount: number;
}

/**
 * 使用 concat demuxer 拼接视频（推荐方法）
 *
 * 优点：
 * - 快速（使用 -c copy 时）
 * - 无重编码质量损失
 * - 支持不同编码格式
 *
 * 缺点：
 * - 所有片段必须有相同的编码参数
 * - 不支持转场效果
 */
async function concatWithDemuxer(
  segments: VideoSegment[],
  outputPath: string,
  options: ConcatOptions
): Promise<void> {
  const {
    transition,
    videoCodec = 'libx264',
    crf = 18,
    preset = 'fast',
    audioCodec = 'aac',
    audioBitrate = '192k',
    totalDuration,
    onProgress,
  } = options;

  if (transition) {
    throw new Error('concat demuxer 不支持转场效果，请使用 concat filter 方法');
  }

  // 创建临时文件列表
  const listFilePath = join(tmpdir(), `ffmpeg-concat-${Date.now()}.txt`);
  const fileList = segments.map((seg) => `file '${seg.path}'`).join('\n');
  writeFileSync(listFilePath, fileList);

  try {
    // 构建命令
    const args = [
      '-f', 'concat',
      '-safe', '0',
      '-i', listFilePath,
      '-c:v', videoCodec,
      '-preset', preset,
      '-crf', crf.toString(),
      '-c:a', audioCodec,
      '-b:a', audioBitrate,
      outputPath,
      '-y'
    ];

    await execFFmpegWithProgress({
      args,
      totalDuration,
      onProgress,
    });
  } finally {
    // 清理临时文件
    if (existsSync(listFilePath)) {
      unlinkSync(listFilePath);
    }
  }
}

/**
 * 使用 concat filter 拼接视频（高级方法）
 *
 * 优点：
 * - 支持不同分辨率的视频
 * - 支持转场效果
 * - 可以应用复杂滤镜
 *
 * 缺点：
 * - 需要重编码（较慢）
 * - 质量可能有损失
 */
async function concatWithFilter(
  segments: VideoSegment[],
  outputPath: string,
  options: ConcatOptions
): Promise<void> {
  const {
    width = 1920,
    height = 1080,
    fps = 30,
    transition = null,
    transitionDurationMs = 500,
    videoCodec = 'libx264',
    crf = 18,
    preset = 'fast',
    audioCodec = 'aac',
    audioBitrate = '192k',
    totalDuration,
    onProgress,
  } = options;

  // 构建输入参数
  const inputArgs: string[] = [];
  segments.forEach((seg) => {
    inputArgs.push('-i', seg.path);
  });

  // 构建 concat filter
  let filterComplex: string;
  let outputMap: string;

  if (transition && segments.length > 1) {
    // 带转场效果的拼接
    filterComplex = buildTransitionFilter(segments, width, height, transition, transitionDurationMs);
    outputMap = `-map "[vout]" -map "[aout]"`;
  } else {
    // 无转场效果的拼接
    filterComplex = buildSimpleConcatFilter(segments.length, width, height, fps);
    outputMap = `-map "[v]" -map "[a]"`;
  }

  // 构建完整命令
  const args = [
    ...inputArgs,
    '-filter_complex', filterComplex,
    outputMap,
    '-c:v', videoCodec,
    '-preset', preset,
    '-crf', crf.toString(),
    '-c:a', audioCodec,
    '-b:a', audioBitrate,
    outputPath,
    '-y'
  ];

  await execFFmpegWithProgress({
    args,
    totalDuration,
    onProgress,
  });
}

/**
 * 构建带转场效果的 filter
 */
function buildTransitionFilter(
  segments: VideoSegment[],
  width: number,
  height: number,
  transition: string,
  transitionDurationMs: number
): string {
  const transitionDuration = transitionDurationMs / 1000;
  let filterComplex = '';

  // 为每个输入添加缩放和 fps 滤镜
  for (let i = 0; i < segments.length; i++) {
    filterComplex += `[${i}:v]scale=${width}:${height},fps=30[v${i}];`;
    filterComplex += `[${i}:a]asetpts=PTS-STARTPTS[a${i}];`;
  }

  // 构建转场效果
  if (transition === 'fade') {
    // 淡入淡出转场
    let lastVideo = 'v0';
    let lastAudio = 'a0';

    for (let i = 1; i < segments.length; i++) {
      filterComplex += `[${lastVideo}][v${i}]xfade=transition=fade:duration=${transitionDuration}:offset=${i * transitionDuration}[vtmp${i}];`;
      filterComplex += `[${lastAudio}][a${i}]acrossfade=d=${transitionDuration}[atmp${i}];`;

      lastVideo = `vtmp${i}`;
      lastAudio = `atmp${i}`;
    }

    filterComplex += `[${lastVideo}]vtrim=0:1000000[vout];[${lastAudio}]atrim=0:100000000[aout]`;
  } else if (transition === 'crossfade') {
    // 交叉淡入淡出转场（视频 + 音频）
    let lastVideo = 'v0';
    let lastAudio = 'a0';

    for (let i = 1; i < segments.length; i++) {
      filterComplex += `[${lastVideo}][v${i}]xfade=transition=fade:duration=${transitionDuration}:offset=${i * transitionDuration}[vtmp${i}];`;
      filterComplex += `[${lastAudio}][a${i}]amix=inputs=2:dropout_transition=2[atmp${i}];`;

      lastVideo = `vtmp${i}`;
      lastAudio = `atmp${i}`;
    }

    filterComplex += `[${lastVideo}][${lastAudio}]vout;aout`;
  }

  return filterComplex;
}

/**
 * 构建简单 concat filter（无转场）
 */
function buildSimpleConcatFilter(
  segmentCount: number,
  width: number,
  height: number,
  fps: number
): string {
  let filterComplex = '';

  // 为每个输入添加缩放和设置 pts
  for (let i = 0; i < segmentCount; i++) {
    filterComplex += `[${i}:v]scale=${width}:${height},fps=${fps},setpts=PTS-STARTPTS[v${i}];`;
    filterComplex += `[${i}:a]asetpts=PTS-STARTPTS[a${i}];`;
  }

  // 拼接视频和音频
  const videoInputs = Array.from({ length: segmentCount }, (_, i) => `[v${i}]`).join('');
  const audioInputs = Array.from({ length: segmentCount }, (_, i) => `[a${i}]`).join('');

  filterComplex += `${videoInputs}concat=n=${segmentCount}:v=1:a=0[v];`;
  filterComplex += `${audioInputs}concat=n=${segmentCount}:v=0:a=1[a]`;

  return filterComplex;
}

/**
 * 拼接视频片段
 *
 * @param options 拼接选项
 * @returns 拼接结果
 *
 * @example
 * ```typescript
 * // 简单拼接（无转场）
 * const result = await concatVideos({
 *   segments: [
 *     { path: './segment1.mp4' },
 *     { path: './segment2.mp4' },
 *     { path: './segment3.mp4' }
 *   ],
 *   outputPath: './output.mp4',
 *   totalDuration: 180,
 *   onProgress: (progress) => console.log(`进度: ${progress.toFixed(1)}%`)
 * });
 *
 * // 带淡入淡出转场
 * const result2 = await concatVideos({
 *   segments: [...],
 *   outputPath: './output.mp4',
 *   transition: 'fade',
 *   transitionDurationMs: 1000,
 *   totalDuration: 180
 * });
 * ```
 */
export async function concatVideos(options: ConcatOptions): Promise<ConcatResult> {
  const { segments, outputPath, transition } = options;

  console.log('🎬 开始视频拼接...');
  console.log(`   片段数量: ${segments.length}`);
  console.log(`   输出路径: ${outputPath}`);
  console.log(`   转场效果: ${transition || '无'}`);

  // 1. 验证所有文件存在
  for (const seg of segments) {
    if (!existsSync(seg.path)) {
      throw new Error(`视频文件不存在: ${seg.path}`);
    }
  }

  // 2. 根据是否需要转场选择方法
  if (transition) {
    console.log(`   使用方法: concat filter (支持转场)`);
    await concatWithFilter(segments, outputPath, options);
  } else {
    console.log(`   使用方法: concat demuxer (快速)`);
    await concatWithDemuxer(segments, outputPath, options);
  }

  // 3. 获取输出文件信息
  const { statSync } = await import('fs');
  const size = statSync(outputPath).size;

  console.log('\n✅ 拼接完成！');
  console.log(`   输出文件: ${outputPath}`);
  console.log(`   文件大小: ${(size / 1024 / 1024).toFixed(2)} MB`);

  return {
    outputPath,
    duration: 0, // TODO: 从输出视频获取时长
    size,
    segmentCount: segments.length,
  };
}

/**
 * 批量拼接视频
 *
 * @param batches 批次列表，每个批次包含片段列表和输出路径
 * @returns 所有拼接结果
 */
export async function batchConcatVideos(
  batches: Array<{
    segments: VideoSegment[];
    outputPath: string;
    options?: Omit<ConcatOptions, 'segments' | 'outputPath'>;
  }>
): Promise<Map<string, ConcatResult>> {
  const results = new Map<string, ConcatResult>();

  for (const batch of batches) {
    const { segments, outputPath, options = {} } = batch;

    try {
      const result = await concatVideos({
        segments,
        outputPath,
        ...options,
      });

      results.set(outputPath, result);
    } catch (error) {
      console.error(`❌ ${outputPath} 拼接失败:`, error);
      throw error;
    }
  }

  return results;
}
