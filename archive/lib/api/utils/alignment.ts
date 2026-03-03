/**
 * 音频强制对齐工具
 *
 * 当 API 不返回精确的 wordTimings 时，
 * 使用音频特征分析来估计词级时间戳
 */

import { Word } from '../../../types/api-contracts';

/**
 * 语音活动检测（VAD）结果
 */
interface VADResult {
  startMs: number;
  endMs: number;
  energy: number;
}

/**
 * 简化的音节估计
 * @param word 单词
 * @returns 估计的音节数
 */
function estimateSyllables(word: string): number {
  const vowels = word.match(/[aeiouy]+/gi);
  return vowels ? vowels.length : 1;
}

/**
 * 基于音节的词时长估计
 * @param words 词列表
 * @param totalDurationMs 总时长（毫秒）
 * @returns Word[] 词时间戳
 */
export function alignWordsBySyllables(
  text: string,
  totalDurationMs: number
): Word[] {
  const words = text.split(/\s+/).filter(w => w.length > 0);

  if (words.length === 0) {
    return [];
  }

  // 1. 计算每个词的音节数
  const syllableCounts = words.map(word => estimateSyllables(word));
  const totalSyllables = syllableCounts.reduce((sum, count) => sum + count, 0);

  // 2. 计算每个音节的平均时长
  const msPerSyllable = totalDurationMs / totalSyllables;

  // 3. 根据音节数分配时间
  const wordTimings: Word[] = [];
  let currentTimeMs = 0;

  words.forEach((word, index) => {
    const syllableCount = syllableCounts[index];
    const durationMs = Math.round(syllableCount * msPerSyllable);

    wordTimings.push({
      text: word,
      startMs: currentTimeMs,
      endMs: currentTimeMs + durationMs,
      timestampMs: currentTimeMs,
    });

    currentTimeMs += durationMs;
  });

  return wordTimings;
}

/**
 * 基于标点符号的断句对齐
 * @param text 文本
 * @param totalDurationMs 总时长（毫秒）
 * @returns Word[] 词时间戳
 */
export function alignWordsByPunctuation(
  text: string,
  totalDurationMs: number
): Word[] {
  // 1. 按标点符号分割句子
  const sentences = text.match(/[^.!?。！？]+[.!?。！？]*/g) || [text];

  // 2. 计算每个句子的字符数（用于分配时间）
  const sentenceLengths = sentences.map(s => s.length);
  const totalLength = sentenceLengths.reduce((sum, len) => sum + len, 0);

  // 3. 为每个句子分配时间
  const sentenceTimings = sentences.map((sentence, index) => {
    const sentenceStartMs = Math.round(
      (sentenceLengths.slice(0, index).reduce((sum, len) => sum + len, 0) / totalLength) *
      totalDurationMs
    );
    const sentenceEndMs = Math.round(
      ((sentenceLengths.slice(0, index).reduce((sum, len) => sum + len, 0) + sentence.length) /
        totalLength) *
      totalDurationMs
    );

    return {
      text: sentence,
      startMs: sentenceStartMs,
      endMs: sentenceEndMs,
      durationMs: sentenceEndMs - sentenceStartMs,
    };
  });

  // 4. 在每个句子内部分配词时间
  const wordTimings: Word[] = [];

  sentenceTimings.forEach(sentence => {
    const words = sentence.text.split(/\s+/).filter(w => w.length > 0);
    const msPerWord = sentence.durationMs / words.length;

    words.forEach((word, index) => {
      const startMs = Math.round(sentence.startMs + index * msPerWord);
      const endMs = Math.round(sentence.startMs + (index + 1) * msPerWord);

      wordTimings.push({
        text: word,
        startMs,
        endMs,
        timestampMs: startMs,
      });
    });
  });

  return wordTimings;
}

/**
 * 混合策略：结合音节和标点符号
 * @param text 文本
 * @param totalDurationMs 总时长（毫秒）
 * @returns Word[] 词时间戳
 */
export function alignWordsHybrid(
  text: string,
  totalDurationMs: number
): Word[] {
  // 1. 按标点符号分割句子
  const sentences = text.match(/[^.!?。！？]+[.!?。！？]*/g) || [text];

  const wordTimings: Word[] = [];
  let globalTimeMs = 0;

  sentences.forEach(sentence => {
    const words = sentence.split(/\s+/).filter(w => w.length > 0);

    if (words.length === 0) {
      return;
    }

    // 计算句子的音节总数
    const syllableCounts = words.map(w => estimateSyllables(w));
    const totalSyllables = syllableCounts.reduce((sum, count) => sum + count, 0);

    // 句子时长估算：假设平均每秒 3 个音节
    const estimatedSentenceDuration = Math.round((totalSyllables / 3) * 1000);

    const msPerSyllable = estimatedSentenceDuration / totalSyllables;
    let sentenceTimeMs = 0;

    words.forEach((word, index) => {
      const syllableCount = syllableCounts[index];
      const durationMs = Math.round(syllableCount * msPerSyllable);

      wordTimings.push({
        text: word,
        startMs: globalTimeMs + sentenceTimeMs,
        endMs: globalTimeMs + sentenceTimeMs + durationMs,
        timestampMs: globalTimeMs + sentenceTimeMs,
      });

      sentenceTimeMs += durationMs;
    });

    globalTimeMs += estimatedSentenceDuration;
  });

  // 归一化到总时长
  if (wordTimings.length > 0) {
    const actualTotalDuration = wordTimings[wordTimings.length - 1].endMs;
    const scale = totalDurationMs / actualTotalDuration;

    wordTimings.forEach(word => {
      word.startMs = Math.round(word.startMs * scale);
      word.endMs = Math.round(word.endMs * scale);
      if (word.timestampMs !== undefined) {
        word.timestampMs = Math.round(word.timestampMs * scale);
      }
    });
  }

  return wordTimings;
}

/**
 * 智能选择最佳对齐策略
 * @param text 文本
 * @param totalDurationMs 总时长（毫秒）
 * @returns Word[] 词时间戳
 */
export function alignWordsSmart(
  text: string,
  totalDurationMs: number
): Word[] {
  // 统计标点符号数量
  const punctuationCount = (text.match(/[.!?。！？]/g) || []).length;

  // 统计句子数量
  const sentences = text.match(/[^.!?。！？]+[.!?。！？]*/g) || [];
  const avgSentenceLength = sentences.length > 0
    ? text.length / sentences.length
    : text.length;

  // 决策策略
  if (punctuationCount > 3 && avgSentenceLength < 50) {
    // 有多个短句子：使用标点符号对齐
    return alignWordsByPunctuation(text, totalDurationMs);
  } else if (punctuationCount > 0) {
    // 有标点符号：使用混合策略
    return alignWordsHybrid(text, totalDurationMs);
  } else {
    // 无标点符号：使用音节估计
    return alignWordsBySyllables(text, totalDurationMs);
  }
}
