/**
 * FFmpeg 进度监控模块
 * Agent 3 - 视频处理核心
 *
 * 提供实时进度监控功能，用于长时间视频处理任务
 * 通过解析 FFmpeg stderr 输出中的 time= 字段计算进度
 */

import { spawn } from 'child_process';

/**
 * 进度回调函数类型
 * @param progress 当前进度 (0-100)
 * @param currentTime 当前处理时间（秒）
 * @param totalTime 总时长（秒）
 */
export type ProgressCallback = (
  progress: number,
  currentTime: number,
  totalTime: number
) => void;

/**
 * FFmpeg 进度选项
 */
export interface FFmpegProgressOptions {
  /** 命令行参数数组 */
  args: string[];
  /** 总视频时长（秒），用于计算进度百分比 */
  totalDuration?: number;
  /** 进度回调函数 */
  onProgress?: ProgressCallback;
  /** 是否显示实时输出（默认 false） */
  verbose?: boolean;
}

/**
 * FFmpeg 进度信息
 */
export interface FFmpegProgress {
  /** 当前帧号 */
  frame: number;
  /** fps */
  fps: number;
  /** 当前处理时间（秒） */
  time: number;
  /** 比特率 */
  bitrate: string;
  /** 总大小（字节） */
  size: number;
  /** 进度百分比 (0-100) */
  progress?: number;
}

/**
 * 解析 FFmpeg stderr 输出行，提取进度信息
 *
 * FFmpeg 输出示例：
 * frame=  123 fps= 25 q=28.0 size=    1234kB time=00:00:05.12 bitrate= 1234.5kbits/s speed=1.23x
 *
 * @param line FFmpeg stderr 输出行
 * @returns 解析后的进度信息，如果解析失败返回 null
 */
export function parseFFmpegProgress(line: string): FFmpegProgress | null {
  // 匹配时间字段 time=HH:MM:SS.mm
  const timeMatch = line.match(/time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})/);
  if (!timeMatch) return null;

  // 解析时间
  const hours = parseInt(timeMatch[1], 10);
  const minutes = parseInt(timeMatch[2], 10);
  const seconds = parseInt(timeMatch[3], 10);
  const centiseconds = parseInt(timeMatch[4], 10);
  const timeInSeconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100;

  // 解析帧号
  const frameMatch = line.match(/frame=\s*(\d+)/);
  const frame = frameMatch ? parseInt(frameMatch[1], 10) : 0;

  // 解析 fps
  const fpsMatch = line.match(/fps=\s*([\d.]+)/);
  const fps = fpsMatch ? parseFloat(fpsMatch[1]) : 0;

  // 解析比特率
  const bitrateMatch = line.match(/bitrate=\s*([\d.]+)kbits\/s/);
  const bitrate = bitrateMatch ? `${bitrateMatch[1]}kbits/s` : '0kbits/s';

  // 解析大小
  const sizeMatch = line.match(/size=\s*(\d+)kB/);
  const size = sizeMatch ? parseInt(sizeMatch[1], 10) * 1024 : 0;

  return {
    frame,
    fps,
    time: timeInSeconds,
    bitrate,
    size,
  };
}

/**
 * 执行 FFmpeg 命令并监控进度
 *
 * @param options FFmpeg 进度选项
 * @returns Promise，当命令完成时 resolve
 *
 * @example
 * ```typescript
 * await execFFmpegWithProgress({
 *   args: ['-i', 'input.mp4', '-c:v', 'libx264', 'output.mp4'],
 *   totalDuration: 120, // 2分钟视频
 *   onProgress: (progress, currentTime, totalTime) => {
 *     console.log(`进度: ${progress.toFixed(1)}% (${currentTime.toFixed(1)}s / ${totalTime}s)`);
 *   }
 * });
 * ```
 */
export function execFFmpegWithProgress(options: FFmpegProgressOptions): Promise<void> {
  const { args, totalDuration, onProgress, verbose = false } = options;

  return new Promise((resolve, reject) => {
    // 启动 FFmpeg 进程
    const ffmpeg = spawn('npx', ['remotion', 'ffmpeg', ...args], {
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stderr = '';

    // 监听 stderr 输出
    ffmpeg.stderr.on('data', (data) => {
      const line = data.toString();

      if (verbose) {
        process.stderr.write(line);
      }

      stderr += line;

      // 解析进度
      const progressInfo = parseFFmpegProgress(line);

      if (progressInfo && totalDuration) {
        const progress = Math.min((progressInfo.time / totalDuration) * 100, 100);

        if (onProgress) {
          onProgress(progress, progressInfo.time, totalDuration);
        }
      }
    });

    // 监听 stdout 输出（一般 FFmpeg 输出到 stderr）
    ffmpeg.stdout.on('data', (data) => {
      if (verbose) {
        process.stdout.write(data);
      }
    });

    // 监听进程退出
    ffmpeg.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`FFmpeg 进程异常退出，退出码: ${code}\n${stderr}`));
      }
    });

    // 监听错误
    ffmpeg.on('error', (error) => {
      reject(new Error(`FFmpeg 启动失败: ${error.message}`));
    });
  });
}

/**
 * 带进度监控的视频裁剪
 *
 * ⚠️ 重要：不使用 -vcodec copy，因为它只能跳转到 I 帧，不精确
 * 必须重编码以实现毫秒级准确切割
 *
 * @param options 裁剪选项和进度回调
 */
export async function trimVideoWithProgress(options: {
  inputPath: string;
  outputPath: string;
  startTimeMs: number;
  durationMs?: number;
  crf?: number;
  preset?: string;
  totalDuration?: number;
  onProgress?: ProgressCallback;
}): Promise<void> {
  const {
    inputPath,
    outputPath,
    startTimeMs,
    durationMs,
    crf = 18,
    preset = 'fast',
    totalDuration,
    onProgress,
  } = options;

  const startTime = msToTime(startTimeMs);
  const duration = durationMs ? msToSeconds(durationMs) : undefined;

  const args = [
    '-ss', startTime,
    '-i', inputPath,
  ];

  if (duration) {
    args.push('-t', duration.toString());
  }

  args.push(
    '-c:v', 'libx264',
    '-preset', preset,
    '-crf', crf.toString(),
    '-c:a', 'aac',
    '-b:a', '192k',
    outputPath,
    '-y'
  );

  await execFFmpegWithProgress({
    args,
    totalDuration,
    onProgress,
  });
}

/**
 * 带进度监控的音频混合
 *
 * @param options 音频混合选项和进度回调
 */
export async function mixAudioWithProgress(options: {
  videoPath: string;
  audioPath: string;
  outputPath: string;
  videoVolume?: number;
  audioVolume?: number;
  totalDuration?: number;
  onProgress?: ProgressCallback;
}): Promise<void> {
  const {
    videoPath,
    audioPath,
    outputPath,
    videoVolume = 0.15,
    audioVolume = 1.0,
    totalDuration,
    onProgress,
  } = options;

  const args = [
    '-i', videoPath,
    '-i', audioPath,
    '-filter_complex',
    `[0:a]volume=${videoVolume}[a0];[1:a]volume=${audioVolume}[a1];[a0][a1]amix=inputs=2:duration=first`,
    '-c:v', 'copy',
    '-c:a', 'aac',
    '-b:a', '192k',
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
 * 带进度监控的帧率对齐
 *
 * @param options 帧率对齐选项和进度回调
 */
export async function normalizeFrameRateWithProgress(options: {
  inputPath: string;
  outputPath: string;
  fps?: number;
  totalDuration?: number;
  onProgress?: ProgressCallback;
}): Promise<void> {
  const {
    inputPath,
    outputPath,
    fps = 30,
    totalDuration,
    onProgress,
  } = options;

  const args = [
    '-i', inputPath,
    '-filter:v', `fps=${fps}`,
    '-c:v', 'libx264',
    '-preset', 'fast',
    '-crf', '18',
    '-c:a', 'aac',
    '-b:a', '192k',
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
 * 将毫秒转换为 FFmpeg 时间格式
 * @param ms 毫秒
 * @returns HH:MM:SS.mmm 格式
 */
function msToTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const milliseconds = ms % 1000;

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(milliseconds).padStart(3, '0')}`;
}

/**
 * 将毫秒转换为秒
 * @param ms 毫秒
 * @returns 秒
 */
function msToSeconds(ms: number): number {
  return ms / 1000;
}
