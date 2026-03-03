/**
 * 多轨道音频混合模块
 * Agent 3 - 视频处理核心
 *
 * 提供 4 轨道音频混合功能，用于深度解说模式
 * 支持解说配音、原音、BGM、音效的混合
 */

import { existsSync } from 'fs';
import { execFFmpegWithProgress, ProgressCallback } from './progress';

/**
 * 音频轨道类型
 */
export type AudioTrackType = 'voiceover' | 'original' | 'bgm' | 'sfx';

/**
 * 音频轨道定义
 */
export interface AudioTrack {
  /** 轨道类型 */
  type: AudioTrackType;
  /** 音频文件路径 */
  path: string;
  /** 音量 (0.0-1.0，默认根据类型有不同默认值) */
  volume?: number;
  /** 开始时间（毫秒，默认 0） */
  startMs?: number;
  /** 持续时间（毫秒，默认为整个音频长度） */
  durationMs?: number;
}

/**
 * 多轨道混合选项
 */
export interface MultitrackMixOptions {
  /** 视频文件路径（包含原音轨道） */
  videoPath: string;
  /** 音频轨道列表（最多 4 个轨道） */
  tracks: AudioTrack[];
  /** 输出文件路径 */
  outputPath: string;
  /** 输出视频编码器（默认 copy，不重新编码） */
  videoCodec?: string;
  /** 输出音频编码器（默认 aac） */
  audioCodec?: string;
  /** 音频比特率（默认 192k） */
  audioBitrate?: string;
  /** 总视频时长（秒），用于进度计算 */
  totalDuration?: number;
  /** 进度回调函数 */
  onProgress?: ProgressCallback;
}

/**
 * 混合结果
 */
export interface MixResult {
  /** 输出文件路径 */
  outputPath: string;
  /** 混合的轨道数量 */
  trackCount: number;
  /** 总时长（秒） */
  duration: number;
  /** 文件大小（字节） */
  size: number;
}

/**
 * 默认音量配置
 */
const DEFAULT_VOLUMES: Record<AudioTrackType, number> = {
  voiceover: 1.0,    // 解说配音 100%
  original: 0.15,    // 原始环境音 15%
  bgm: 0.3,          // BGM 30%
  sfx: 0.5           // 音效 50%
};

/**
 * 验证音频轨道
 */
function validateTracks(tracks: AudioTrack[]): void {
  if (tracks.length === 0) {
    throw new Error('至少需要一个音频轨道');
  }

  if (tracks.length > 4) {
    throw new Error('最多支持 4 个音频轨道');
  }

  // 检查类型重复
  const types = tracks.map(t => t.type);
  const uniqueTypes = new Set(types);
  if (types.length !== uniqueTypes.size) {
    throw new Error('音频轨道类型不能重复');
  }

  // 验证文件存在
  for (const track of tracks) {
    if (!existsSync(track.path)) {
      throw new Error(`音频文件不存在: ${track.path}`);
    }
  }
}

/**
 * 构建 FFmpeg filter_complex 字符串
 */
function buildFilterComplex(
  videoPath: string,
  tracks: AudioTrack[]
): string {
  const filters: string[] = [];
  let inputIndex = 0;

  // 添加视频音频作为第一个输入（如果有）
  const hasOriginalAudio = !tracks.some(t => t.type === 'original');

  if (hasOriginalAudio) {
    // 如果没有显式指定 original 轨道，使用视频原音
    filters.push(`[0:a]volume=${DEFAULT_VOLUMES.original}[a0]`);
    inputIndex = 1;
  } else {
    inputIndex = 0;
  }

  // 处理每个音频轨道
  for (let i = 0; i < tracks.length; i++) {
    const track = tracks[i];
    const volume = track.volume ?? DEFAULT_VOLUMES[track.type];
    const outputLabel = `a${inputIndex + i}`;

    // 应用音量调整
    let filter = `[${inputIndex + i}:a]volume=${volume}`;

    // 如果有开始时间或持续时间，添加 atrim 和 asetpts
    if (track.startMs !== undefined || track.durationMs !== undefined) {
      const startSec = (track.startMs ?? 0) / 1000;
      const durationSec = track.durationMs ? track.durationMs / 1000 : undefined;

      if (durationSec) {
        filter += `,atrim=${startSec}:${startSec + durationSec},asetpts=PTS-STARTPTS`;
      } else if (startSec > 0) {
        filter += `,asetpts=PTS-STARTPTS`;
      }
    }

    filters.push(`${filter}[${outputLabel}]`);
  }

  // 构建混合链
  const trackInputs = filters.map(f => f.split('[')[1].split(']')[0]).join('');
  const mixInputs = Array.from({ length: filters.length }, (_, i) => `[a${i}]`).join('');

  // 合并所有过滤器
  let filterComplex = filters.join(';');

  // 添加 amix 滤镜
  filterComplex += `;${mixInputs}amix=inputs=${filters.length}:duration=longest[aout]`;

  return filterComplex;
}

/**
 * 多轨道音频混合
 *
 * @param options 混合选项
 * @returns 混合结果
 *
 * @example
 * ```typescript
 * // 四轨道混合（解说 + 原音 + BGM + 音效）
 * const result = await mixAudioMultitrack({
 *   videoPath: './video.mp4',
 *   tracks: [
 *     { type: 'voiceover', path: './voiceover.mp3', volume: 1.0 },
 *     { type: 'bgm', path: './bgm.mp3', volume: 0.3 },
 *     { type: 'sfx', path: './sfx.mp3', volume: 0.5 }
 *   ],
 *   outputPath: './output.mp4',
 *   totalDuration: 120,
 *   onProgress: (progress) => console.log(`进度: ${progress.toFixed(1)}%`)
 * });
 * ```
 */
export async function mixAudioMultitrack(
  options: MultitrackMixOptions
): Promise<MixResult> {
  const {
    videoPath,
    tracks,
    outputPath,
    videoCodec = 'copy',
    audioCodec = 'aac',
    audioBitrate = '192k',
    totalDuration,
    onProgress,
  } = options;

  console.log('🎵 开始多轨道音频混合...');
  console.log(`   视频文件: ${videoPath}`);
  console.log(`   轨道数量: ${tracks.length}`);
  console.log(`   输出路径: ${outputPath}`);

  // 1. 验证视频文件存在
  if (!existsSync(videoPath)) {
    throw new Error(`视频文件不存在: ${videoPath}`);
  }

  // 2. 验证音频轨道
  validateTracks(tracks);

  // 3. 显示轨道信息
  console.log('\n   音频轨道:');
  tracks.forEach((track, index) => {
    const volume = track.volume ?? DEFAULT_VOLUMES[track.type];
    const typeName = {
      voiceover: '解说配音',
      original: '原始环境音',
      bgm: 'BGM',
      sfx: '音效'
    }[track.type];

    console.log(`   ${index + 1}. ${typeName} - 音量: ${(volume * 100).toFixed(0)}% - ${track.path}`);
  });

  // 4. 构建 FFmpeg 命令
  const inputArgs: string[] = ['-i', videoPath];
  tracks.forEach(track => {
    inputArgs.push('-i', track.path);
  });

  const filterComplex = buildFilterComplex(videoPath, tracks);

  const args = [
    ...inputArgs,
    '-filter_complex', filterComplex,
    '-map', '0:v',  // 使用视频的第一个视频流
    '-map', '[aout]',  // 使用混合后的音频
    `-c:v`, videoCodec,
    `-c:a`, audioCodec,
    `-b:a`, audioBitrate,
    outputPath,
    '-y'
  ];

  // 5. 执行混合
  console.log('\n   正在混合...');
  await execFFmpegWithProgress({
    args,
    totalDuration,
    onProgress,
  });

  // 6. 获取输出文件信息
  const { statSync } = await import('fs');
  const size = statSync(outputPath).size;

  console.log('\n✅ 混合完成！');
  console.log(`   输出文件: ${outputPath}`);
  console.log(`   文件大小: ${(size / 1024 / 1024).toFixed(2)} MB`);

  return {
    outputPath,
    trackCount: tracks.length,
    duration: 0, // TODO: 从输出视频获取时长
    size,
  };
}

/**
 * 创建标准四轨道混合（解说 + 原音 + BGM + 音效）
 *
 * @param options 混合选项
 * @returns 混合结果
 *
 * @example
 * ```typescript
 * // 使用预设的四轨道配置
 * const result = await createStandardMix({
 *   videoPath: './video.mp4',
 *   voiceoverPath: './voiceover.mp3',
 *   bgmPath: './bgm.mp3',
 *   sfxPath: './sfx.mp3',
 *   outputPath: './output.mp4'
 * });
 * ```
 */
export async function createStandardMix(options: {
  videoPath: string;
  voiceoverPath: string;
  bgmPath: string;
  sfxPath?: string;
  outputPath: string;
  voiceoverVolume?: number;
  bgmVolume?: number;
  sfxVolume?: number;
  totalDuration?: number;
  onProgress?: ProgressCallback;
}): Promise<MixResult> {
  const {
    videoPath,
    voiceoverPath,
    bgmPath,
    sfxPath,
    outputPath,
    voiceoverVolume = 1.0,
    bgmVolume = 0.3,
    sfxVolume = 0.5,
    totalDuration,
    onProgress,
  } = options;

  const tracks: AudioTrack[] = [
    { type: 'voiceover', path: voiceoverPath, volume: voiceoverVolume },
    { type: 'bgm', path: bgmPath, volume: bgmVolume },
  ];

  if (sfxPath) {
    tracks.push({ type: 'sfx', path: sfxPath, volume: sfxVolume });
  }

  return mixAudioMultitrack({
    videoPath,
    tracks,
    outputPath,
    totalDuration,
    onProgress,
  });
}

/**
 * 批量混合多个视频
 *
 * @param batches 批次列表
 * @returns 所有混合结果
 */
export async function batchMixAudioMultitrack(
  batches: Array<{
    videoPath: string;
    tracks: AudioTrack[];
    outputPath: string;
    options?: Omit<MultitrackMixOptions, 'videoPath' | 'tracks' | 'outputPath'>;
  }>
): Promise<Map<string, MixResult>> {
  const results = new Map<string, MixResult>();

  for (const batch of batches) {
    const { videoPath, tracks, outputPath, options = {} } = batch;

    try {
      const result = await mixAudioMultitrack({
        videoPath,
        tracks,
        outputPath,
        ...options,
      });

      results.set(outputPath, result);
    } catch (error) {
      console.error(`❌ ${outputPath} 混合失败:`, error);
      throw error;
    }
  }

  return results;
}
