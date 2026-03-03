/**
 * 多片段视频组合组件
 * Agent 3 - 视频处理核心
 *
 * 支持多个视频片段的组合、转场效果和字幕叠加
 */

"use client";

import React, { useCallback, useState } from 'react';
import {
  AbsoluteFill,
  Series,
  Sequence,
  Video,
  useVideoConfig,
  useDelayRender,
  cancelRender,
  Composition,
  staticFile,
} from 'remotion';
import { z } from 'zod';
import { getVideoMetadata } from '@remotion/media-utils';
import { KaraokeSentence } from './subtitles/KaraokeSentence';

/**
 * 视频片段定义
 */
export interface VideoClip {
  /** 视频文件路径 */
  src: string;
  /** 开始时间（毫秒），默认 0 */
  startMs?: number;
  /** 持续时间（毫秒），默认为整个视频 */
  durationMs?: number;
  /** 片段字幕 */
  subtitles?: Array<{
    startMs: number;
    endMs: number;
    text: string;
    words?: Array<{
      text: string;
      startMs: number;
      endMs: number;
    }>;
  }>;
}

/**
 * 转场类型
 */
export type TransitionType = 'none' | 'fade' | 'slide' | 'zoom';

/**
 * 多片段组合 Props
 */
export interface MultiClipCompositionProps {
  /** 视频片段列表 */
  clips: VideoClip[];
  /** 转场类型（默认 none） */
  transition?: TransitionType;
  /** 转场持续时间（毫秒，默认 500） */
  transitionDurationMs?: number;
  /** 全局字幕样式 */
  fontSize?: number;
  fontColor?: string;
  highlightColor?: string;
  outlineColor?: string;
  outlineSize?: number;
  subtitleY?: number;
  /** 水印 */
  watermarkUrl?: string | null;
}

/**
 * Schema 定义
 */
export const multiClipCompositionSchema = z.object({
  clips: z.array(z.object({
    src: z.string(),
    startMs: z.number().optional(),
    durationMs: z.number().optional(),
    subtitles: z.array(z.any()).optional(),
  })),
  transition: z.enum(['none', 'fade', 'slide', 'zoom']).optional(),
  transitionDurationMs: z.number().optional(),
  fontSize: z.number().optional(),
  fontColor: z.string().optional(),
  highlightColor: z.string().optional(),
  outlineColor: z.string().optional(),
  outlineSize: z.number().optional(),
  subtitleY: z.number().optional(),
  watermarkUrl: z.string().nullable().optional(),
});

/**
 * 计算视频元数据
 */
export const calculateMultiClipMetadata = async ({
  props,
}: {
  props: MultiClipCompositionProps;
}) => {
  const fps = 30;

  let totalDuration = 0;

  // 计算所有片段的总时长
  for (const clip of props.clips) {
    const metadata = await getVideoMetadata(clip.src);
    const clipDuration = clip.durationMs
      ? clip.durationMs / 1000
      : metadata.durationInSeconds;

    // 如果有转场效果，需要添加转场时间
    if (props.transition && props.transition !== 'none') {
      totalDuration += clipDuration;
    } else {
      totalDuration += clipDuration;
    }
  }

  return {
    fps,
    durationInFrames: Math.floor(totalDuration * fps),
  };
};

/**
 * 转场效果组件
 */
interface TransitionProps {
  type: TransitionType;
  progress: number; // 0-1
  children: React.ReactNode;
}

const Transition: React.FC<TransitionProps> = ({ type, progress, children }) => {
  const style: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
  };

  switch (type) {
    case 'fade':
      return (
        <div
          style={{
            ...style,
            opacity: progress,
          }}
        >
          {children}
        </div>
      );

    case 'slide':
      return (
        <div
          style={{
            ...style,
            transform: `translateX(${(1 - progress) * 100}%)`,
          }}
        >
          {children}
        </div>
      );

    case 'zoom':
      const scale = 0.8 + progress * 0.2; // 0.8 -> 1.0
      return (
        <div
          style={{
            ...style,
            transform: `scale(${scale})`,
          }}
        >
          {children}
        </div>
      );

    default:
      return <>{children}</>;
  }
};

/**
 * 单个片段组件
 */
interface ClipProps {
  clip: VideoClip;
  index: number;
  totalClips: number;
  globalStyle: Pick<
    MultiClipCompositionProps,
    'fontSize' | 'fontColor' | 'highlightColor' | 'outlineColor' | 'outlineSize' | 'subtitleY'
  >;
}

const Clip: React.FC<ClipProps> = ({ clip, index, totalClips, globalStyle }) => {
  const { fps } = useVideoConfig();
  const { delayRender, continueRender } = useDelayRender();
  const [handle] = useState(() => delayRender());

  const [metadata, setMetadata] = useState<{
    durationInSeconds: number;
    width: number;
    height: number;
  } | null>(null);

  // 加载视频元数据
  useCallback(async () => {
    try {
      const meta = await getVideoMetadata(clip.src);
      setMetadata(meta);
      continueRender(handle);
    } catch (error) {
      console.error(`加载视频元数据失败: ${clip.src}`, error);
      cancelRender(`加载视频元数据失败: ${error}`);
    }
  }, [clip.src, handle, continueRender]);

  if (!metadata) {
    return null;
  }

  // 计算片段时长
  const clipDuration = clip.durationMs
    ? clip.durationMs / 1000
    : metadata.durationInSeconds;

  // 调整字幕时间（相对于片段开始）
  const adjustedSubtitles = (clip.subtitles || []).map((subtitle) => ({
    ...subtitle,
    // 字幕时间已经相对于片段，不需要调整
    // 但如果是全局时间轴，需要减去片段开始时间
  }));

  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      {/* 视频层 */}
      <Video
        src={staticFile(clip.src)}
        style={{
          objectFit: 'contain',
        }}
      />

      {/* 字幕层 */}
      {adjustedSubtitles.map((subtitle, idx) => {
        const startFrame = Math.floor((subtitle.startMs / 1000) * fps);
        const endFrame = Math.floor((subtitle.endMs / 1000) * fps);
        const duration = endFrame - startFrame;

        return (
          <Sequence
            key={idx}
            from={startFrame}
            durationInFrames={duration}
          >
            <AbsoluteFill
              style={{
                display: 'flex',
                alignItems: 'flex-end',
                justifyContent: 'center',
                paddingBottom: globalStyle.subtitleY || 80,
              }}
            >
              <KaraokeSentence
                text={subtitle.text}
                words={subtitle.words || []}
                sentenceStartMs={subtitle.startMs}
                fontSize={globalStyle.fontSize || 60}
                fontColor={globalStyle.fontColor || 'white'}
                highlightColor={globalStyle.highlightColor || '#FFE600'}
                outlineColor={globalStyle.outlineColor || 'black'}
                outlineSize={globalStyle.outlineSize || 5}
                subtitleY={globalStyle.subtitleY || 80}
              />
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

/**
 * 多片段组合主组件
 */
export const MultiClipComposition: React.FC<MultiClipCompositionProps> = ({
  clips,
  transition = 'none',
  transitionDurationMs = 500,
  fontSize,
  fontColor,
  highlightColor,
  outlineColor,
  outlineSize,
  subtitleY,
  watermarkUrl,
}) => {
  const { fps } = useVideoConfig();

  const globalStyle = {
    fontSize,
    fontColor,
    highlightColor,
    outlineColor,
    outlineSize,
    subtitleY,
  };

  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      <Series>
        {clips.map((clip, index) => {
          return (
            <Sequence
              key={index}
              // 计算片段在全局时间轴中的位置
              // from={...} // Series 自动处理
            >
              <Clip
                clip={clip}
                index={index}
                totalClips={clips.length}
                globalStyle={globalStyle}
              />
            </Sequence>
          );
        })}
      </Series>

      {/* 水印层 */}
      {watermarkUrl && (
        <AbsoluteFill
          style={{
            pointerEvents: 'none',
          }}
        >
          <img
            src={watermarkUrl}
            alt="水印"
            style={{
              position: 'absolute',
              bottom: 20,
              right: 20,
              width: 100,
              opacity: 0.5,
            }}
          />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
