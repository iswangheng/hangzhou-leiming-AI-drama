import { execSync } from "child_process";
import { existsSync, statSync } from "fs";
import {
  TrimOptions,
  AudioExtractOptions,
  AudioMixOptions,
  VolumeAdjustOptions,
} from "./types";

/**
 * 将毫秒转换为 FFmpeg 时间格式
 * @param ms 毫秒
 * @returns HH:MM:SS.mmm 格式
 */
export function msToTime(ms: number): string {
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
export function msToSeconds(ms: number): number {
  return ms / 1000;
}

/**
 * 验证文件是否存在
 * @param filePath 文件路径
 * @throws 如果文件不存在
 */
export function validateFileExists(filePath: string): void {
  if (!existsSync(filePath)) {
    throw new Error(`文件不存在: ${filePath}`);
  }
}

/**
 * 毫秒级精度视频裁剪
 *
 * ⚠️ 重要：不使用 -vcodec copy，因为它只能跳转到 I 帧，不精确
 * 必须重编码以实现毫秒级准确切割
 *
 * @param options 裁剪选项
 */
export function trimVideo(options: TrimOptions): void {
  const {
    inputPath,
    outputPath,
    startTimeMs,
    durationMs,
    crf = 18,
    preset = "fast"
  } = options;

  validateFileExists(inputPath);

  const startTime = msToTime(startTimeMs);
  const duration = durationMs ? msToSeconds(durationMs) : undefined;

  let command = `npx remotion ffmpeg -ss ${startTime} -i "${inputPath}"`;

  if (duration) {
    command += ` -t ${duration}`;
  }

  // 重编码以实现精确裁剪
  command += ` -c:v libx264 -preset ${preset} -crf ${crf} -c:a aac -b:a 192k "${outputPath}" -y`;

  console.log(`执行视频裁剪: ${command}`);

  try {
    execSync(command, {
      stdio: ["ignore", "inherit", "inherit"],
    });
  } catch (error) {
    throw new Error(`视频裁剪失败: ${error}`);
  }
}

/**
 * 提取音频为 WAV 文件
 * 用于 Whisper 转录或其他音频处理
 *
 * @param options 音频提取选项
 */
export function extractAudio(options: AudioExtractOptions): void {
  const {
    inputPath,
    outputPath,
    sampleRate = 16000
  } = options;

  validateFileExists(inputPath);

  const command = `npx remotion ffmpeg -i "${inputPath}" -ar ${sampleRate} "${outputPath}" -y`;

  console.log(`执行音频提取: ${command}`);

  try {
    execSync(command, {
      stdio: ["ignore", "inherit", "inherit"],
    });
  } catch (error) {
    throw new Error(`音频提取失败: ${error}`);
  }
}

/**
 * 混合音频和视频
 * 用于将解说配音与原视频混合
 *
 * @param options 音频混合选项
 */
export function mixAudio(options: AudioMixOptions): void {
  const {
    videoPath,
    audioPath,
    outputPath,
    videoVolume = 0.15,    // 原音降至 15%
    audioVolume = 1.0      // 解说音量 100%
  } = options;

  validateFileExists(videoPath);
  validateFileExists(audioPath);

  // 使用 amix 滤镜混合两个音频
  const command = `npx remotion ffmpeg -i "${videoPath}" -i "${audioPath}" \
    -filter_complex "[0:a]volume=${videoVolume}[a0];[1:a]volume=${audioVolume}[a1];[a0][a1]amix=inputs=2:duration=first" \
    -c:v copy -c:a aac -b:a 192k "${outputPath}" -y`;

  console.log(`执行音频混合: ${command}`);

  try {
    execSync(command, {
      stdio: ["ignore", "inherit", "inherit"],
      shell: "/bin/bash",  // 使用 bash 支持多行命令
    });
  } catch (error) {
    throw new Error(`音频混合失败: ${error}`);
  }
}

/**
 * 调整视频音量
 *
 * @param options 音量调整选项
 */
export function adjustVolume(options: VolumeAdjustOptions): void {
  const {
    inputPath,
    outputPath,
    volume
  } = options;

  validateFileExists(inputPath);

  const command = `npx remotion ffmpeg -i "${inputPath}" -filter:a "volume=${volume}" -c:v copy "${outputPath}" -y`;

  console.log(`执行音量调整: ${command}`);

  try {
    execSync(command, {
      stdio: ["ignore", "inherit", "inherit"],
    });
  } catch (error) {
    throw new Error(`音量调整失败: ${error}`);
  }
}

/**
 * 帧率对齐
 * 将视频转换为统一的 30fps，确保毫秒计算与帧号匹配
 *
 * @param inputPath 输入路径
 * @param outputPath 输出路径
 * @param fps 目标帧率（默认 30）
 */
export function normalizeFrameRate(inputPath: string, outputPath: string, fps = 30): void {
  validateFileExists(inputPath);

  const command = `npx remotion ffmpeg -i "${inputPath}" -filter:v "fps=${fps}" -c:v libx264 -preset fast -crf 18 -c:a aac -b:a 192k "${outputPath}" -y`;

  console.log(`执行帧率对齐: ${command}`);

  try {
    execSync(command, {
      stdio: ["ignore", "inherit", "inherit"],
    });
  } catch (error) {
    throw new Error(`帧率对齐失败: ${error}`);
  }
}

/**
 * 提取关键帧
 * 每隔指定秒数提取一帧，用于 Gemini 分析
 *
 * @param inputPath 输入视频路径
 * @param outputDir 输出目录
 * @param intervalSeconds 提取间隔（秒），默认 3 秒
 * @returns 提取的关键帧信息数组
 */
export interface ExtractKeyframeResult {
  framePath: string;
  timestampMs: number;
  frameNumber: number;
  fileSize: number;
}

export function extractKeyframes(
  inputPath: string,
  outputDir: string,
  intervalSeconds = 3
): ExtractKeyframeResult[] {
  validateFileExists(inputPath);

  // 创建输出目录
  execSync(`mkdir -p "${outputDir}"`);

  // 使用 FFmpeg 提取关键帧
  // -vf fps=1/3 表示每 3 秒提取一帧
  // frame_%05d.jpg 表示文件名格式（frame_00001.jpg）
  const command = `npx remotion ffmpeg -i "${inputPath}" -vf "fps=1/${intervalSeconds}" "${outputDir}/frame_%05d.jpg" -y`;

  console.log(`执行关键帧提取: ${command}`);

  try {
    execSync(command, {
      stdio: ["ignore", "inherit", "inherit"],
    });
  } catch (error) {
    throw new Error(`关键帧提取失败: ${error}`);
  }

  // 获取视频时长（毫秒）
  const durationCommand = `npx remotion ffmpeg -i "${inputPath}" 2>&1 | grep "Duration" | cut -d ' ' -f 4 | head -n 1`;
  const durationOutput = execSync(durationCommand, { encoding: 'utf-8' });
  const durationMatch = durationOutput.match(/(\d{2}):(\d{2}):(\d{2}\.\d{2})/);

  if (!durationMatch) {
    throw new Error('无法获取视频时长');
  }

  const [, hours, minutes, seconds] = durationMatch;
  const durationMs = (parseInt(hours) * 3600 + parseInt(minutes) * 60 + parseFloat(seconds)) * 1000;

  // 获取帧率
  const fpsCommand = `npx remotion ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "${inputPath}"`;
  const fpsOutput = execSync(fpsCommand, { encoding: 'utf-8' }).trim();
  const fps = fpsOutput.split('/')[0] ? parseFloat(eval(fpsOutput)) : 30; // 评估分数形式

  // 收集提取的关键帧信息
  const results: ExtractKeyframeResult[] = [];
  let frameNumber = 1;
  for (let timestampMs = 0; timestampMs < durationMs; timestampMs += intervalSeconds * 1000) {
    const framePath = `${outputDir}/frame_${String(frameNumber).padStart(5, '0')}.jpg`;

    // 检查文件是否存在
    if (existsSync(framePath)) {
      const stats = statSync(framePath);
      const fileSize = stats.size;

      results.push({
        framePath,
        timestampMs,
        frameNumber,
        fileSize,
      });

      frameNumber++;
    }
  }

  console.log(`✅ 成功提取 ${results.length} 个关键帧`);

  return results;
}
