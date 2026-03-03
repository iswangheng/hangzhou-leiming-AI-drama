"use client";

import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TheBoldFont } from "../utils/load-font";
import { makeTransform, scale, translateY } from "@remotion/animation-utils";
import { SubtitleProps } from "./types";

const fontFamily = TheBoldFont;

const container: React.CSSProperties = {
  justifyContent: "center",
  alignItems: "center",
  top: undefined,
  bottom: 350,
  height: 150,
};

interface WordProps extends SubtitleProps {
  text: string;
}

/**
 * 单词级字幕组件
 * 支持弹跳动画和自定义样式
 */
export const Word: React.FC<WordProps> = ({
  text,
  fontSize = 100,
  fontColor = "white",
  outlineColor = "black",
  outlineSize,
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

  const enter = spring({
    frame,
    fps,
    config: {
      damping: 200,
    },
    durationInFrames: 5,
  });

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
          textTransform: "uppercase",
          textAlign: "center",
          WebkitTextStroke: `${outlineSize ?? fontSize * 0.1}px ${outlineColor}`,
          paintOrder: "stroke",
          transform: makeTransform([
            scale(interpolate(enter, [0, 1], [0.5, 1])),
            translateY(interpolate(enter, [0, 1], [50, 0])),
          ]),
        }}
      >
        <span
          style={{
            transform: makeTransform([
                scale(interpolate(enter, [0, 1], [0.5, 1])),
                translateY(interpolate(enter, [0, 1], [50, 0])),
            ]),
          }}
        >
          <span
            style={{
              display: "inline-block",
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
            {text}
          </span>
        </span>
      </div>
    </AbsoluteFill>
  );
};
