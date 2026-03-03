/**
 * 字幕数据类型定义
 * 用于视频字幕渲染
 */

export interface Word {
  text: string;          // 单词内容
  startMs: number;       // 开始时间（毫秒）
  endMs: number;         // 结束时间（毫秒）
  timestampMs?: number;  // 时间戳
}

export interface Caption {
  startMs: number;       // 开始时间（毫秒）
  endMs: number;         // 结束时间（毫秒）
  timestampMs: number;   // 时间戳
  text: string;          // 字幕内容
  confidence?: number;   // 置信度
  words?: Word[];        // 词级信息（可选，用于卡拉OK效果）
}

export interface SubtitleProps {
  fontSize?: number;              // 字体大小
  fontColor?: string;             // 字体颜色
  highlightColor?: string;        // 高亮颜色（卡拉OK效果）
  outlineColor?: string;          // 描边颜色
  outlineSize?: number;           // 描边大小
  subtitleY?: number;             // 字幕垂直位置（百分比）
  subtitleBgEnabled?: boolean;    // 是否启用背景
  subtitleBgColor?: string;       // 背景颜色
  subtitleBgRadius?: number;      // 背景圆角
  subtitleBgPadX?: number;        // 背景水平内边距
  subtitleBgPadY?: number;        // 背景垂直内边距
  subtitleBgOpacity?: number;     // 背景透明度
}

export interface CaptionedVideoProps extends SubtitleProps {
  src: string;                    // 视频源地址
  subtitles?: Caption[];          // 字幕数据
  originalVolume?: number;        // 原始音量（0-1）
  watermarkUrl?: string | null;   // 水印图片地址
  watermarkOpacity?: number;      // 水印透明度
  watermarkSize?: number;         // 水印大小（百分比）
  watermarkX?: number;            // 水印X位置（百分比）
  watermarkY?: number;            // 水印Y位置（百分比）
}
