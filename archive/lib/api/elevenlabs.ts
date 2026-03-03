// ============================================
// ElevenLabs API 客户端
// 用于 TTS 语音合成和音频生成
// ============================================

import { elevenlabsConfig } from '../config';
import { withRetry, type RetryOptions } from './utils/retry';
import { alignWordsSmart } from './utils/alignment';

// ============================================
// 类型定义
// ============================================

/**
 * ElevenLabs API 响应基础接口
 */
export interface ElevenLabsResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

/**
 * 语音信息
 */
export interface Voice {
  voice_id: string;
  name: string;
  category?: 'generated' | 'cloned' | 'premade' | 'professional' | 'famous' | 'high_quality';
  labels?: Record<string, string>;
  description?: string;
  preview_url?: string;
  available_for_tiers?: string[];
  language?: string;
  gender?: string;
  age?: string;
  accent?: string;
}

/**
 * 共享语音信息
 */
export interface SharedVoice {
  voice_id: string;
  name: string;
  accent: string;
  gender: string;
  age: string;
  descriptive: string;
  use_case: string;
  category: 'generated' | 'cloned' | 'premade' | 'professional' | 'famous' | 'high_quality';
  language: string;
  description: string;
  preview_url: string;
  image_url?: string;
  featured: boolean;
  free_users_allowed: boolean;
}

/**
 * TTS 生成选项
 */
export interface TTSOptions {
  text: string;
  voiceId?: string;
  modelId?: string;
  outputFormat?: string;
  stability?: number;
  similarityBoost?: number;
}

/**
 * TTS 生成结果
 */
export interface TTSResult {
  audioBuffer: Buffer; // 音频数据
  format: string; // 音频格式
}

/**
 * 语音模型
 */
export interface Model {
  model_id: string;
  name: string;
  can_do_text_to_speech: boolean;
  can_do_voice_conversion: boolean;
  can_do_style_transfer: boolean;
  description?: string;
}

// ============================================
// ElevenLabs 客户端类
// ============================================

export class ElevenLabsClient {
  private apiKey: string;
  private endpoint: string;
  private timeout: number;
  private defaultModel: string;
  private retryOptions: RetryOptions; // 添加重试配置

  constructor(retryOptions?: RetryOptions) {
    // 验证必需的配置
    if (!elevenlabsConfig.apiKey) {
      throw new Error('ElevenLabs API key is not configured. Please set ELEVENLABS_API_KEY in .env');
    }

    this.apiKey = elevenlabsConfig.apiKey;
    this.endpoint = elevenlabsConfig.endpoint;
    this.timeout = elevenlabsConfig.timeout;
    this.defaultModel = elevenlabsConfig.defaultModel;

    // 配置重试选项
    this.retryOptions = {
      maxRetries: retryOptions?.maxRetries || 3,
      initialDelay: retryOptions?.initialDelay || 1000,
      maxDelay: retryOptions?.maxDelay || 10000,
      backoffMultiplier: retryOptions?.backoffMultiplier || 2,
      onRetry: (attempt, error) => {
        console.warn(`⚠️  ElevenLabs API 请求失败，第 ${attempt} 次重试...`, error.message);
      },
    };
  }

  /**
   * 内部请求执行方法（用于重试）
   */
  private async executeRequest<T>(
    path: string,
    options: RequestInit = {},
    controller?: AbortController
  ): Promise<{ data: T; response: Response }> {
    const response = await fetch(`${this.endpoint}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'xi-api-key': this.apiKey,
        ...options.headers,
      },
      signal: controller?.signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      const error = new Error(`ElevenLabs API error: ${response.status} - ${errorText}`) as any;
      error.statusCode = response.status;
      throw error;
    }

    const data = await response.json();
    return { data, response };
  }

  /**
   * 通用 HTTP 请求方法（带重试机制，用于 JSON 响应）
   */
  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<ElevenLabsResponse<T>> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      // 使用 withRetry 包装请求
      const result = await withRetry(
        async () => {
          return await this.executeRequest<T>(path, options, controller);
        },
        this.retryOptions
      );

      clearTimeout(timeoutId);

      return {
        success: true,
        data: result.data,
      };
    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          return {
            success: false,
            error: `ElevenLabs API timeout after ${this.timeout}ms`,
          };
        }
        return {
          success: false,
          error: error.message,
        };
      }
      return {
        success: false,
        error: 'Unknown error occurred',
      };
    }
  }

  /**
   * 获取用户语音列表
   */
  async getVoices(): Promise<ElevenLabsResponse<{ voices: Voice[] }>> {
    return this.request<{ voices: Voice[] }>('/voices');
  }

  /**
   * 获取共享语音库
   */
  async getSharedVoices(options?: {
    pageSize?: number;
    category?: 'professional' | 'famous' | 'high_quality';
    gender?: string;
    age?: string;
    accent?: string;
    language?: string;
    search?: string;
    featured?: boolean;
  }): Promise<ElevenLabsResponse<{ voices: SharedVoice[]; has_more: boolean }>> {
    const params = new URLSearchParams();

    if (options?.pageSize) params.append('page_size', options.pageSize.toString());
    if (options?.category) params.append('category', options.category);
    if (options?.gender) params.append('gender', options.gender);
    if (options?.age) params.append('age', options.age);
    if (options?.accent) params.append('accent', options.accent);
    if (options?.language) params.append('language', options.language);
    if (options?.search) params.append('search', options.search);
    if (options?.featured !== undefined) params.append('featured', options.featured.toString());

    const queryString = params.toString();
    const path = queryString ? `/shared-voices?${queryString}` : '/shared-voices';

    return this.request<{ voices: SharedVoice[]; has_more: boolean }>(path);
  }

  /**
   * 获取可用的模型列表
   */
  async getModels(): Promise<ElevenLabsResponse<Model[]>> {
    return this.request<Model[]>('/models');
  }

  /**
   * 内部 TTS 执行方法（用于重试）
   */
  private async executeTextToSpeech(
    text: string,
    voiceId: string,
    modelId: string,
    outputFormat: string,
    stability: number,
    similarityBoost: number,
    controller?: AbortController,
    includeTimestamps: boolean = true
  ): Promise<{ audioBuffer: Buffer; format: string; alignment?: any }> {
    // 构建 URL
    const url = new URL(`${this.endpoint}/text-to-speech/${voiceId}`);
    if (outputFormat) {
      url.searchParams.append('output_format', outputFormat);
    }

    // 构建请求体
    const requestBody: any = {
      text,
      model_id: modelId,
      voice_settings: {
        stability,
        similarity_boost: similarityBoost,
      },
    };

    // 尝试启用 timestamps（ElevenLabs 可能需要特殊参数）
    if (includeTimestamps) {
      // ElevenLabs 可能的参数（需要根据实际 API 文档调整）
      // requestBody.return_timestamps = true;
      // requestBody.prosody = { alignment: true };
    }

    // 发送 TTS 请求
    const response = await fetch(url.toString(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'xi-api-key': this.apiKey,
      },
      body: JSON.stringify(requestBody),
      signal: controller?.signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      const error = new Error(`TTS generation failed: ${response.status} - ${errorText}`) as any;
      error.statusCode = response.status;
      throw error;
    }

    // 尝试从响应头获取 alignment 信息
    let alignment;
    const alignmentHeader = response.headers.get('X-ElevenLabs-Alignment');
    if (alignmentHeader) {
      try {
        alignment = JSON.parse(alignmentHeader);
      } catch (e) {
        // 忽略解析错误
      }
    }

    // 获取音频二进制数据
    const arrayBuffer = await response.arrayBuffer();
    const audioBuffer = Buffer.from(arrayBuffer);

    // 解析音频格式
    const format = this.parseAudioFormat(outputFormat);

    return { audioBuffer, format, alignment };
  }

  /**
   * 文本转语音（TTS，带重试机制）
   * 返回音频二进制数据
   */
  async textToSpeech(options: TTSOptions): Promise<ElevenLabsResponse<TTSResult>> {
    try {
      const {
        text,
        voiceId = '21m00Tcm4TlvDq8ikWAM', // 默认使用 "Rachel" 语音
        modelId = this.defaultModel,
        outputFormat = elevenlabsConfig.outputFormat,
        stability = elevenlabsConfig.stability,
        similarityBoost = elevenlabsConfig.similarityBoost,
      } = options;

      // 验证输入
      if (!text || text.trim().length === 0) {
        return {
          success: false,
          error: 'Text is required for TTS generation',
        };
      }

      // 文本长度限制（ElevenLabs 限制）
      if (text.length > 5000) {
        return {
          success: false,
          error: 'Text is too long. Maximum length is 5000 characters.',
        };
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      // 使用 withRetry 包装 TTS 请求
      const result = await withRetry(
        async () => {
          return await this.executeTextToSpeech(
            text,
            voiceId,
            modelId,
            outputFormat,
            stability,
            similarityBoost,
            controller,
            true // 尝试获取 timestamps
          );
        },
        this.retryOptions
      );

      clearTimeout(timeoutId);

      return {
        success: true,
        data: {
          audioBuffer: result.audioBuffer,
          format: result.format,
        },
      };
    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          return {
            success: false,
            error: `TTS generation timeout after ${this.timeout}ms`,
          };
        }
        return {
          success: false,
          error: error.message,
        };
      }
      return {
        success: false,
        error: 'Unknown error occurred during TTS generation',
      };
    }
  }

  /**
   * 批量文本转语音
   */
  async batchTextToSpeech(
    paragraphs: string[],
    options?: Omit<TTSOptions, 'text'>
  ): Promise<ElevenLabsResponse<TTSResult[]>> {
    const results: TTSResult[] = [];

    for (let i = 0; i < paragraphs.length; i++) {
      const paragraph = paragraphs[i].trim();
      if (!paragraph) continue;

      const response = await this.textToSpeech({
        ...options,
        text: paragraph,
      });

      if (!response.success || !response.data) {
        return {
          success: false,
          error: `Failed to generate audio for paragraph ${i + 1}: ${response.error}`,
        };
      }

      results.push(response.data);
    }

    return {
      success: true,
      data: results,
    };
  }

  /**
   * 获取语音预览音频
   */
  async getVoicePreview(voiceId: string): Promise<ElevenLabsResponse<Buffer>> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(`${this.endpoint}/voices/${voiceId}/preview`, {
        method: 'GET',
        headers: {
          'xi-api-key': this.apiKey,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        return {
          success: false,
          error: `Failed to fetch voice preview: ${response.status}`,
        };
      }

      const arrayBuffer = await response.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);

      return {
        success: true,
        data: buffer,
      };
    } catch (error) {
      if (error instanceof Error) {
        return {
          success: false,
          error: error.message,
        };
      }
      return {
        success: false,
        error: 'Unknown error occurred',
      };
    }
  }

  /**
   * 解析音频格式
   */
  private parseAudioFormat(outputFormat: string): string {
    // mp3_44100_128 -> mp3
    // pcm_16000 -> wav
    // wav_44100 -> wav
    const match = outputFormat.match(/^(mp3|pcm|wav|opus)/);
    return match ? match[1] : 'mp3';
  }

  /**
   * 生成语音解说（符合 IElevenLabsAPI 接口契约）
   * 将文本转换为语音并保存为文件，提取词语时间戳
   *
   * @param text 文案内容
   * @param options 选项
   * @returns TTSResult 包含 audioPath, durationMs, wordTimings
   */
  async generateNarration(
    text: string,
    options?: {
      voice?: string;      // 默认: eleven_multilingual_v2
      model?: string;      // 默认: eleven_multilingual_v2
      stability?: number;  // 0-1
      outputPath?: string;  // 输出文件路径
    }
  ): Promise<ElevenLabsResponse<{
    audioPath: string;
    durationMs: number;
    wordTimings: import('../../types/api-contracts').Word[];
    format: string;
  }>> {
    const {
      voice = 'eleven_multilingual_v2',
      model = 'eleven_multilingual_v2',
      stability = 0.5,
      outputPath: initialOutputPath
    } = options || {};

    let outputPath = initialOutputPath;

    try {
      // 1. 调用 TTS 生成音频
      const response = await this.textToSpeech({
        text,
        voiceId: voice,
        modelId: model,
        stability,
      });

      if (!response.success || !response.data) {
        return {
          success: false,
          error: response.error || 'TTS generation failed',
        };
      }

      // 2. 生成输出文件路径（如果未指定）
      if (!outputPath) {
        const timestamp = Date.now();
        const format = this.parseAudioFormat(elevenlabsConfig.outputFormat);
        outputPath = `./outputs/voiceover_${timestamp}.${format}`;
      }

      // 3. 确保输出目录存在
      const dir = outputPath.substring(0, outputPath.lastIndexOf('/'));
      if (dir && !require('fs').existsSync(dir)) {
        require('fs').mkdirSync(dir, { recursive: true });
      }

      // 4. 保存音频文件
      const { execSync } = require('child_process');
      const fs = require('fs');

      fs.writeFileSync(outputPath, response.data.audioBuffer);

      console.log(`✅ TTS 音频已保存: ${outputPath}`);
      console.log(`   大小: ${(response.data.audioBuffer.length / 1024).toFixed(2)} KB`);

      // 5. 获取音频时长（使用 ffprobe）
      let durationMs = 0;
      try {
        const ffprobeOutput = execSync(
          `ffprobe -v quiet -show_entries -of json "${outputPath}"`,
          { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'pipe'] }
        );
        const metadata = JSON.parse(ffprobeOutput);
        durationMs = Math.round(parseFloat(metadata.format.duration) * 1000);
      } catch (error) {
        console.warn('⚠️  无法获取音频时长，使用估算值');
        // 根据文本长度估算（假设平均语速）
        const estimatedWordsPerSecond = 3;
        const wordCount = text.split(/\s+/).length;
        durationMs = Math.round((wordCount / estimatedWordsPerSecond) * 1000);
      }

      // 6. 提取 wordTimings
      // 优先尝试从 API 获取真实的 timestamps
      // 如果不可用，则使用智能对齐算法

      let wordTimings: import('../../types/api-contracts').Word[];

      // TODO: 如果 ElevenLabs 返回了 alignment 数据，优先使用
      // if (result.alignment && result.alignment.chars) {
      //   wordTimings = this.parseElevenLabsAlignment(result.alignment, text);
      // } else {
      //   // 使用智能对齐算法
      //   wordTimings = alignWordsSmart(text, durationMs);
      // }

      // 当前使用智能对齐算法（改进版）
      wordTimings = this.extractWordTimingsFromText(text, durationMs, true);

      const format = this.parseAudioFormat(elevenlabsConfig.outputFormat);

      return {
        success: true,
        data: {
          audioPath: outputPath,
          durationMs,
          wordTimings,
          format,
        },
      };
    } catch (error) {
      if (error instanceof Error) {
        return {
          success: false,
          error: error.message,
        };
      }
      return {
        success: false,
        error: 'Unknown error occurred',
      };
    }
  }

  /**
   * 从文本提取 wordTimings（改进版）
   *
   * @param text 文本内容
   * @param totalDurationMs 总时长（毫秒）
   * @param useSmartAlignment 是否使用智能对齐算法（默认 false 以保持向后兼容）
   * @returns Word[] 词时间戳数组
   */
  private extractWordTimingsFromText(
    text: string,
    totalDurationMs: number,
    useSmartAlignment: boolean = false
  ): import('../../types/api-contracts').Word[] {
    if (useSmartAlignment) {
      // 使用智能对齐算法（基于音节和标点符号）
      return alignWordsSmart(text, totalDurationMs);
    }

    // 简单平均分割（保持向后兼容）
    const words = text.split(/\s+/).filter(w => w.length > 0);
    const msPerWord = totalDurationMs / words.length;

    return words.map((word, index) => {
      const startMs = Math.floor(index * msPerWord);
      const endMs = Math.floor((index + 1) * msPerWord);

      return {
        text: word,
        startMs,
        endMs,
        timestampMs: startMs,
      };
    });
  }

  /**
   * 解析 ElevenLabs API 返回的 alignment 数据
   * （预留方法，等待 API 支持）
   */
  private parseElevenLabsAlignment(
    alignment: any,
    text: string
  ): import('../../types/api-contracts').Word[] {
    // TODO: 实现 ElevenLabs alignment 数据解析
    // 这取决于 API 实际返回的数据格式
    return [];
  }
}

// ============================================
// 导出单例实例（懒加载）
// ============================================

let clientInstance: ElevenLabsClient | null = null;

export function getElevenLabsClient(): ElevenLabsClient {
  if (!clientInstance) {
    clientInstance = new ElevenLabsClient();
  }
  return clientInstance;
}

// 向后兼容：导出一个 getter
export const elevenlabsClient = new Proxy({} as ElevenLabsClient, {
  get(target, prop) {
    const client = getElevenLabsClient();
    return client[prop as keyof ElevenLabsClient];
  }
});
