/**
 * Remotion 字幕组件
 * 从 remotion-ai-subtitle-generation 项目适配而来
 * 支持抖音爆款风格的卡拉OK字幕效果
 */

export { CaptionedVideo } from "./CaptionedVideo";
export { Word } from "./Word";
export { KaraokeSentence } from "./KaraokeSentence";
export { captionedVideoSchema, calculateCaptionedVideoMetadata } from "./CaptionedVideo";

// 类型导出
export type { Caption, Word as WordType, SubtitleProps, CaptionedVideoProps } from "./types";
