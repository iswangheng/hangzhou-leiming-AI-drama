/**
 * FFmpeg 工具库
 *
 * 提供视频处理的核心功能，包括：
 * - 毫秒级精度视频裁剪
 * - 音频提取
 * - 音频混合
 * - 音量调整
 * - 帧率对齐
 * - 进度监控
 *
 * 所有时间轴操作均使用毫秒作为单位
 */

export {
  trimVideo,
  extractAudio,
  mixAudio,
  adjustVolume,
  normalizeFrameRate,
  extractKeyframes,
  msToTime,
  msToSeconds,
  validateFileExists,
} from "./utils";

export {
  parseFFmpegProgress,
  execFFmpegWithProgress,
  trimVideoWithProgress,
  mixAudioWithProgress,
  normalizeFrameRateWithProgress,
} from "./progress";

export {
  concatVideos,
  batchConcatVideos,
} from "./concat";

export {
  mixAudioMultitrack,
  createStandardMix,
  batchMixAudioMultitrack,
} from "./multitrack-audio";

export type {
  VideoMetadata,
  TrimOptions,
  AudioExtractOptions,
  AudioMixOptions,
  VolumeAdjustOptions,
} from "./types";

export type {
  ProgressCallback,
  FFmpegProgressOptions,
  FFmpegProgress,
} from "./progress";

export type {
  VideoSegment,
  ConcatOptions,
  ConcatResult,
} from "./concat";

export type {
  AudioTrack,
  AudioTrackType,
  MultitrackMixOptions,
  MixResult,
} from "./multitrack-audio";
