/**
 * API 重试工具
 * 支持指数退避策略的自动重试机制
 */

/**
 * 可重试的错误类型
 */
export interface RetryableError extends Error {
  code?: string;
  statusCode?: number;
}

/**
 * 重试配置选项
 */
export interface RetryOptions {
  maxRetries?: number;        // 最大重试次数（默认：3）
  initialDelay?: number;      // 初始延迟（毫秒，默认：1000）
  maxDelay?: number;          // 最大延迟（毫秒，默认：10000）
  backoffMultiplier?: number; // 退避乘数（默认：2）
  retryableErrors?: string[]; // 可重试的错误代码
  retryableStatusCodes?: number[]; // 可重试的 HTTP 状态码
  onRetry?: (attempt: number, error: Error) => void; // 重试回调
}

/**
 * 默认重试配置
 */
const defaultRetryOptions: Required<Omit<RetryOptions, 'onRetry'>> = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
  retryableErrors: [
    'NETWORK_ERROR',
    'TIMEOUT',
    'ECONNRESET',
    'ECONNREFUSED',
    'ETIMEDOUT',
    'ENOTFOUND',
  ],
  retryableStatusCodes: [408, 429, 500, 502, 503, 504],
};

/**
 * 计算退避延迟时间
 * @param attempt 当前尝试次数（从 0 开始）
 * @param options 重试配置
 * @returns 延迟时间（毫秒）
 */
function calculateBackoff(
  attempt: number,
  options: Required<Omit<RetryOptions, 'onRetry'>>
): number {
  const exponentialDelay = options.initialDelay * Math.pow(options.backoffMultiplier, attempt);
  return Math.min(exponentialDelay, options.maxDelay);
}

/**
 * 判断错误是否可重试
 * @param error 错误对象
 * @param options 重试配置
 * @returns 是否可重试
 */
function isRetryableError(
  error: RetryableError,
  options: Required<Omit<RetryOptions, 'onRetry'>>
): boolean {
  // 检查错误代码
  if (error.code && options.retryableErrors.includes(error.code)) {
    return true;
  }

  // 检查 HTTP 状态码
  if (error.statusCode && options.retryableStatusCodes.includes(error.statusCode)) {
    return true;
  }

  // 检查错误消息中的关键字
  const errorMessage = error.message.toLowerCase();
  const retryableKeywords = ['timeout', 'network', 'econn', 'etimed', 'enotfound'];

  return retryableKeywords.some(keyword => errorMessage.includes(keyword));
}

/**
 * 延迟函数
 * @param ms 延迟时间（毫秒）
 * @returns Promise
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 带重试的异步函数执行器
 * @param fn 要执行的异步函数
 * @param options 重试配置
 * @returns Promise<T>
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const mergedOptions = { ...defaultRetryOptions, ...options };

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= mergedOptions.maxRetries; attempt++) {
    try {
      // 尝试执行函数
      const result = await fn();

      // 如果成功，返回结果
      return result;
    } catch (error) {
      lastError = error as Error;

      // 如果是最后一次尝试，抛出错误
      if (attempt === mergedOptions.maxRetries) {
        break;
      }

      // 判断是否可重试
      const retryable = isRetryableError(lastError as RetryableError, mergedOptions);

      if (!retryable) {
        // 不可重试的错误，直接抛出
        throw lastError;
      }

      // 计算退避延迟
      const backoffDelay = calculateBackoff(attempt, mergedOptions);

      // 调用重试回调
      if (mergedOptions.onRetry) {
        mergedOptions.onRetry(attempt + 1, lastError);
      }

      // 等待后重试
      console.warn(
        `⚠️  请求失败，${backoffDelay}ms 后进行第 ${attempt + 1} 次重试...`,
        lastError.message
      );

      await delay(backoffDelay);
    }
  }

  // 所有重试都失败，抛出最后一个错误
  throw new Error(
    `请求失败，已重试 ${mergedOptions.maxRetries} 次。最后错误: ${lastError?.message}`
  );
}

/**
 * 创建一个带重试的 API 客户端包装器
 * @param apiCall 原 API 调用函数
 * @param options 重试配置
 * @returns 带重试功能的 API 调用函数
 */
export function createRetryableAPI<T extends (...args: any[]) => Promise<any>>(
  apiCall: T,
  options: RetryOptions = {}
): T {
  return (async (...args: Parameters<T>) => {
    return withRetry(() => apiCall(...args), options);
  }) as T;
}
