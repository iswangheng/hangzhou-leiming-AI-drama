/**
 * API 流式响应工具
 *
 * 支持 Server-Sent Events (SSE) 和 WebSocket 流式推送
 */

export interface StreamChunk {
  text: string;
  done: boolean;
  index: number;
  error?: string;
}

export type StreamCallback = (chunk: StreamChunk) => void | Promise<void>;

/**
 * 流处理器类型 - 接收回调函数并异步处理流
 */
export type StreamProcessor = (callback: StreamCallback) => void | Promise<void>;

/**
 * Server-Sent Events (SSE) 响应格式
 */
export class SSEStream {
  private encoder = new TextEncoder();

  /**
   * 格式化 SSE 数据
   */
  private formatEvent(event: string, data: unknown): Uint8Array {
    const lines = [`event: ${event}`, `data: ${JSON.stringify(data)}`, '', ''];
    return this.encoder.encode(lines.join('\n'));
  }

  /**
   * 创建流式响应
   */
  createStreamResponse(
    onStream: StreamProcessor,
    onComplete?: () => void
  ): ReadableStream<Uint8Array> {
    let index = 0;
    const encoder = this.encoder;
    const formatEvent = this.formatEvent.bind(this);

    return new ReadableStream({
      async start(controller) {
        try {
          await onStream((chunk) => {
            controller.enqueue(formatEvent('message', chunk));

            if (chunk.done) {
              controller.enqueue(formatEvent('done', { index }));
            }
          });

          if (onComplete) {
            onComplete();
          }

          controller.close();
        } catch (error) {
          controller.error(error);
        }
      },
    });
  }
}

/**
 * 流式进度跟踪器
 */
export class StreamProgressTracker {
  private startTime: number = 0;
  private chunksReceived: number = 0;
  private totalCharacters: number = 0;

  start() {
    this.startTime = Date.now();
    this.chunksReceived = 0;
    this.totalCharacters = 0;
  }

  update(chunk: StreamChunk) {
    this.chunksReceived++;
    this.totalCharacters += chunk.text.length;
  }

  getStats() {
    const elapsedMs = Date.now() - this.startTime;
    const chunksPerSecond = elapsedMs > 0
      ? (this.chunksReceived / (elapsedMs / 1000)).toFixed(2)
      : '0';

    return {
      chunksReceived: this.chunksReceived,
      totalCharacters: this.totalCharacters,
      elapsedMs,
      chunksPerSecond: parseFloat(chunksPerSecond),
    };
  }
}

/**
 * 流式响应包装器
 * 用于将非流式 API 转换为流式
 */
export async function* createMockStream(
  text: string,
  chunkSize: number = 10,
  delayMs: number = 50
): AsyncGenerator<StreamChunk> {
  const chunks: string[] = [];

  for (let i = 0; i < text.length; i += chunkSize) {
    chunks.push(text.slice(i, i + chunkSize));
  }

  for (let i = 0; i < chunks.length; i++) {
    await new Promise(resolve => setTimeout(resolve, delayMs));

    yield {
      text: chunks[i],
      done: i === chunks.length - 1,
      index: i,
    };
  }
}

/**
 * Next.js API Route 流式响应辅助函数
 */
export function createStreamResponseHelper(
  onStream: StreamProcessor,
  onComplete?: () => void
): Response {
  const stream = new SSEStream().createStreamResponse(onStream, onComplete);

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
