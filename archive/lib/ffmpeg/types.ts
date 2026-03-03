/**
 * FFmpeg 工具类型定义
 */

export interface VideoMetadata {
  durationInSeconds: number;
  width: number;
  height: number;
  fps: number;
}

export interface TrimOptions {
  inputPath: string;
  outputPath: string;
  startTimeMs: number;      // 开始时间（毫秒）
  durationMs?: number;      // 持续时间（毫秒）
  crf?: number;             // CRF 质量值（默认 18）
  preset?: string;          // 编码预设（默认 'fast'）
}

export interface AudioExtractOptions {
  inputPath: string;
  outputPath: string;
  sampleRate?: number;      // 采样率（默认 16000）
}

export interface AudioMixOptions {
  videoPath: string;
  audioPath: string;
  outputPath: string;
  videoVolume?: number;     // 视频原声音量（0-1）
  audioVolume?: number;     // 外部音频音量（0-1）
}

export interface VolumeAdjustOptions {
  inputPath: string;
  outputPath: string;
  volume: number;           // 音量倍数（0.5 = 50%, 1.5 = 150%）
}
