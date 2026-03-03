// ============================================
// FFmpeg 视频切片工具
// 实现毫秒级精度的视频切割
// ============================================

import { exec } from 'child_process';
import { promisify } from 'util';
import { mkdir, access } from 'fs/promises';
import { join } from 'path';

const execAsync = promisify(exec);

// ============================================
// 类型定义
// ============================================

/**
 * 视频切片选项
 */
export interface TrimOptions {
  inputPath: string;              // 输入视频路径
  outputPath: string;              // 输出视频路径
  startMs: number;                 // 开始时间（毫秒）
  durationMs: number;              // 持续时间（毫秒）
  crf?: number;                    // 质量参数（默认18，高质量）
  preset?: 'ultrafast' | 'superfast' | 'veryfast' | 'faster' | 'fast' | 'medium' | 'slow' | 'slower' | 'veryslow';  // 编码速度（默认fast）
  fps?: number;                    // 输出帧率（默认30）
  onProgress?: (progress: number, message: string) => void;  // 进度回调
}

/**
 * 切片结果
 */
export interface TrimResult {
  success: boolean;
  outputPath?: string;
  duration?: number;
  size?: number;
  error?: string;
}

// ============================================
// 工具函数
// ============================================

/**
 * 确保输出目录存在
 */
async function ensureDir(dir: string): Promise<void> {
  try {
    await access(dir);
  } catch {
    await mkdir(dir, { recursive: true });
  }
}

/**
 * 格式化毫秒为 HH:MM:SS.mmm
 */
function formatMs(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const milliseconds = ms % 1000;

  const pad = (n: number, size: number) => n.toString().padStart(size, '0');

  return `${pad(hours, 2)}:${pad(minutes, 2)}:${pad(seconds, 2)}.${pad(milliseconds, 3)}`;
}

/**
 * 生成唯一的输出文件名
 */
export function generateOutputFilename(videoId: number, highlightId: number): string {
  const timestamp = Date.now();
  return `highlight_${videoId}_${highlightId}_${timestamp}.mp4`;
}

// ============================================
// 核心功能
// ============================================

/**
 * 切割视频（毫秒级精度）
 *
 * 使用 FFmpeg 的 -ss 参数实现精确切割
 *
 * 关键点：
 * 1. -ss 参数放在 -i 之前，使用 seek-to-key 精确定位
 * 2. 使用 -t 参数控制持续时间
 * 3. 重编码（不使用 -c:v copy）确保帧级精度
 * 4. 统一帧率为 30fps
 *
 * @param options 切片选项
 * @returns 切片结果
 */
export async function trimVideo(options: TrimOptions): Promise<TrimResult> {
  const {
    inputPath,
    outputPath,
    startMs,
    durationMs,
    crf = 18,
    preset = 'fast',
    fps = 30,
    onProgress,
  } = options;

  try {
    // 1. 确保输出目录存在
    const outputDir = join(outputPath, '..');
    await ensureDir(outputDir);

    // 2. 验证输入文件
    try {
      await access(inputPath);
    } catch {
      return {
        success: false,
        error: `输入文件不存在: ${inputPath}`,
      };
    }

    // 3. 格式化时间参数
    const startTime = formatMs(startMs);
    const durationSeconds = durationMs / 1000;

    onProgress?.(10, '准备切片...');

    // 4. 构建 FFmpeg 命令
    // 关键：-ss 在 -i 之前，使用精确 seek
    const ffmpegCommand = [
      'ffmpeg',
      '-y', // 覆盖输出文件
      `-ss ${startTime}`, // 精确定位开始时间（在-i之前）
      `-i "${inputPath}"`, // 输入文件
      `-t ${durationSeconds}`, // 持续时间（秒）
      `-c:v libx264`, // 视频编码器
      `-preset ${preset}`, // 编码速度预设
      `-crf ${crf}`, // 质量参数（0-51，越低质量越高，18推荐）
      `-r ${fps}`, // 帧率
      `-c:a aac`, // 音频编码器
      `-b:a 128k`, // 音频比特率
      `-movflags +faststart`, // 优化网络播放
      `"${outputPath}"`, // 输出文件
    ].join(' ');

    console.log(`🎬 执行FFmpeg命令: ${ffmpegCommand}`);

    onProgress?.(20, '开始渲染...');

    // 5. 执行 FFmpeg
    const startTimeMs = Date.now();

    const { stdout, stderr } = await execAsync(ffmpegCommand, {
      maxBuffer: 10 * 1024 * 1024, // 10MB buffer
    });

    const elapsed = Date.now() - startTimeMs;

    // 6. 解析输出获取视频信息
    console.log('FFmpeg stderr:', stderr);

    onProgress?.(90, '完成处理...');

    // 7. 验证输出文件
    try {
      await access(outputPath);
    } catch {
      return {
        success: false,
        error: '输出文件未生成',
      };
    }

    // 8. 获取输出文件信息
    const stats = await import('fs/promises').then(fs => fs.stat(outputPath));

    onProgress?.(100, '完成！');

    console.log(`✅ 切片完成: ${outputPath}`);
    console.log(`   时长: ${durationMs}ms`);
    console.log(`   大小: ${(stats.size / 1024 / 1024).toFixed(2)} MB`);
    console.log(`   耗时: ${elapsed}ms`);

    return {
      success: true,
      outputPath,
      duration: durationMs,
      size: stats.size,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '未知错误';

    console.error('❌ 切片失败:', errorMessage);

    return {
      success: false,
      error: errorMessage,
    };
  }
}

/**
 * 批量切割视频
 *
 * @param optionsArray 切片选项数组
 * @returns 切片结果数组
 */
export async function batchTrimVideos(
  optionsArray: TrimOptions[]
): Promise<TrimResult[]> {
  const results: TrimResult[] = [];

  for (let i = 0; i < optionsArray.length; i++) {
    const options = optionsArray[i];

    console.log(`🎬 处理 ${i + 1}/${optionsArray.length}...`);

    const result = await trimVideo({
      ...options,
      onProgress: (progress, message) => {
        const totalProgress = ((i * 100) + progress) / optionsArray.length;
        options.onProgress?.(totalProgress, `[${i + 1}/${optionsArray.length}] ${message}`);
      },
    });

    results.push(result);

    if (!result.success) {
      console.error(`❌ 切片 ${i + 1} 失败:`, result.error);
    }
  }

  return results;
}

// ============================================
// 导出
// ============================================

export default {
  trimVideo,
  batchTrimVideos,
  generateOutputFilename,
  formatMs,
};
