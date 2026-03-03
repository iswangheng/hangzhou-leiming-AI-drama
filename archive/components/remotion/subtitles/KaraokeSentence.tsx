"use client";

import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { TheBoldFont } from "../utils/load-font";
import { SubtitleProps, Word } from "./types";

const fontFamily = TheBoldFont;

const container: React.CSSProperties = {
  justifyContent: "center",
  alignItems: "center",
  top: undefined,
  bottom: 150,
  height: 300,
  paddingLeft: 100,
  paddingRight: 100,
};

interface KaraokeSentenceProps extends SubtitleProps {
  text: string;
  words: Word[];
  sentenceStartMs: number;
}

/**
 * 卡拉OK风格字幕组件
 * 支持单词级别的高亮动画
 * 用于抖音爆款风格的字幕效果
 */
export const KaraokeSentence: React.FC<KaraokeSentenceProps> = ({
  text,
  words,
  sentenceStartMs,
  fontSize = 60,
  fontColor = "white",
  highlightColor = "#FFE600",  // 亮黄色，抖音爆款风格
  outlineColor = "black",
  outlineSize = 5,
  subtitleY = 80,
  subtitleBgEnabled,
  subtitleBgColor = "#7B8793",
  subtitleBgRadius = 25,
  subtitleBgPadX = 10,
  subtitleBgPadY = 5,
  subtitleBgOpacity = 0.4
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 计算当前绝对时间（毫秒）
  const currentAbsoluteTimeMs = sentenceStartMs + (frame / fps) * 1000;

  const dynamicContainer: React.CSSProperties = {
    ...container,
    top: `${subtitleY}%`,
    bottom: undefined,
    transform: 'translateY(-50%)',
  };

  return (
    <AbsoluteFill style={dynamicContainer}>
      <div
        style={{
          fontFamily,
          fontSize: fontSize,
          color: fontColor,
          textAlign: "center",
          lineHeight: 1.4,
          textShadow: "0px 2px 8px rgba(0,0,0,0.8)",
          WebkitTextStroke: `${outlineSize}px ${outlineColor}`,
          paintOrder: "stroke",
          display: "inline-flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "15px",
          backgroundColor: subtitleBgEnabled
            ? (() => {
                const hex = subtitleBgColor.replace("#", "");
                const r = parseInt(hex.substring(0, 2), 16);
                const g = parseInt(hex.substring(2, 4), 16);
                const b = parseInt(hex.substring(4, 6), 16);
                return `rgba(${r},${g},${b},${subtitleBgOpacity})`;
              })()
            : "transparent",
          borderRadius: subtitleBgEnabled ? subtitleBgRadius : 0,
          padding: subtitleBgEnabled ? `${subtitleBgPadY}px ${subtitleBgPadX}px` : 0,
        }}
      >
        {words.length > 0 ? (
          words.map((word, i) => {
            // 判断当前单词是否应该高亮
            const isActive =
              currentAbsoluteTimeMs >= word.startMs && currentAbsoluteTimeMs <= word.endMs;

            return (
              <span
                key={i}
                style={{
                  color: isActive ? highlightColor : fontColor,
                  transform: isActive ? "scale(1.1)" : "scale(1)",
                  transition: "transform 0.1s, color 0.1s",
                  display: "inline-block",
                }}
              >
                {word.text}
              </span>
            );
          })
        ) : (
          <span>{text}</span>
        )}
      </div>
    </AbsoluteFill>
  );
};
