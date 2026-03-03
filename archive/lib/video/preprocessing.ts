/**
 * 杭州雷鸣 - 视频预处理工具
 *
 * 功能：
 * - 抽帧：5fps 抽取视频关键帧
 * - 缩略图生成：为每个镜头生成缩略图
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { mkdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';

const execAsync = promisify(exec);

export interface FrameExtractionResult {
  frameDir: string;
  frameCount: number;
  frames: string[];
}

/**
 * 从视频中抽取关键帧（5fps）
 * @param videoPath 视频文件路径
 * @param outputDir 输出目录
 * @returns 抽取结果
 */
export async function extractFrames(
  videoPath: string,
  outputDir: string
): Promise<FrameExtractionResult> {
  // 确保输出目录存在
  if (!existsSync(outputDir)) {
    await mkdir(outputDir, { recursive: true });
  }

  console.log(`[抽帧] 开始从视频中提取关键帧: ${videoPath}`);

  // 使用 ffmpeg 抽帧（5fps）
  const command = `ffmpeg -i "${videoPath}" -vf "fps=5" -q:v 2 "${outputDir}/frame_%04d.jpg"`;

  try {
    await execAsync(command);
    console.log(`[抽帧] 完成，输出目录: ${outputDir}`);

    // 列出所有生成的帧
    const { stdout } = await execAsync(`ls "${outputDir}"/*.jpg | wc -l`);
    const frameCount = parseInt(stdout.trim());

    return {
      frameDir: outputDir,
      frameCount,
      frames: Array.from({ length: frameCount }, (_, i) =>
        join(outputDir, `frame_${String(i).padStart(4, '0')}.jpg`)
      ),
    };
  } catch (error) {
    console.error('[抽帧] 失败:', error);
    throw new Error(`视频抽帧失败: ${error}`);
  }
}

/**
 * 获取视频时长（秒）
 * @param videoPath 视频文件路径
 * @returns 时长（秒）
 */
export async function getVideoDuration(videoPath: string): Promise<number> {
  const command = `ffprobe -v error -select_streams v:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1 "${videoPath}"`;

  try {
    const { stdout } = await execAsync(command);
    const duration = parseFloat(stdout.trim());
    return duration;
  } catch (error) {
    console.error('[获取时长] 失败:', error);
    throw new Error(`获取视频时长失败: ${error}`);
  }
}

/**
 * 提取音频为 WAV 格式（用于 Whisper 转录）
 * @param videoPath 视频文件路径
 * @param audioPath 输出音频路径
 */
export async function extractAudio(
  videoPath: string,
  audioPath: string
): Promise<void> {
  const command = `ffmpeg -i "${videoPath}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "${audioPath}"`;

  try {
    await execAsync(command);
    console.log(`[音频提取] 完成: ${audioPath}`);
  } catch (error) {
    console.error('[音频提取] 失败:', error);
    throw new Error(`音频提取失败: ${error}`);
  }
}
