"use client";

/**
 * 高光切片视频播放器组件
 *
 * 功能特性：
 * - 支持视频播放控制（播放/暂停/跳转）
 * - 毫秒级精度时间显示（HH:MM:SS.mmm）
 * - 进度条上显示高光时刻标记点
 * - 支持点击标记点快速跳转
 * - 支持拖拽进度条跳转
 * - 支持键盘快捷键控制
 * - 支持外部控制跳转和播放
 */

import { useState, useRef, useEffect, useImperativeHandle, forwardRef } from "react";
import ReactPlayer from "react-player";
import { Play, Pause } from "lucide-react";
import { Button } from "@/components/ui/button";

interface HighlightMarker {
  id: string;
  timeMs: number;      // 高光时刻时间（毫秒）
  label?: string;      // 可选标签
  color?: string;      // 标记颜色（默认为主题色）
}

interface HighlightPlayerProps {
  url: string;                         // 视频URL
  markers?: HighlightMarker[];         // 高光时刻标记
  onMarkerClick?: (marker: HighlightMarker) => void;  // 点击标记回调
  onProgress?: (currentTimeMs: number) => void;       // 进度回调
  onReady?: () => void;                // 播放器就绪回调
  className?: string;                  // 自定义样式类
}

export interface HighlightPlayerRef {
  seekTo: (timeMs: number) => void;
  play: () => void;
  pause: () => void;
  togglePlay: () => void;
}

/**
 * 毫秒转时间字符串（HH:MM:SS.mmm 格式）
 */
export function formatMsToTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const milliseconds = ms % 1000;

  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(milliseconds).padStart(3, "0")}`;
}

/**
 * 高光切片视频播放器
 */
export const HighlightPlayer = forwardRef<HighlightPlayerRef, HighlightPlayerProps>(({
  url,
  markers = [],
  onMarkerClick,
  onProgress,
  onReady,
  className = "",
}, ref) => {
  console.log("🎬🎬🎬 HighlightPlayer 组件开始渲染:", { url, className });

  const playerRef = useRef<any>(null);
  const progressContainerRef = useRef<HTMLDivElement>(null);

  // 播放状态
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeMs, setCurrentTimeMs] = useState(0);
  const [durationMs, setDurationMs] = useState(0);
  const [isSeeking, setIsSeeking] = useState(false);
  const [isReady, setIsReady] = useState(false); // 播放器是否已就绪
  const [loadError, setLoadError] = useState<string | null>(null); // 加载错误

  // 组件挂载时输出日志
  useEffect(() => {
    console.log("🎬✅ HighlightPlayer 组件已挂载:", {
      url,
      markersCount: markers.length,
      hasPlayerRef: !!playerRef.current,
    });
  }, [url, markers]);

  // 暴露方法给父组件
  useImperativeHandle(ref, () => ({
    seekTo: (timeMs: number) => {
      console.log("🎯 HighlightPlayer.seekTo 被调用:", {
        timeMs,
        isReady,
        durationMs,
        hasPlayerRef: !!playerRef.current,
      });
      if (playerRef.current && isReady) {
        const timeInSeconds = timeMs / 1000;
        playerRef.current.seekTo(timeInSeconds, "seconds");
        setCurrentTimeMs(timeMs);
        console.log("✅ seekTo 完成");
      } else {
        console.warn("⚠️ seekTo 失败：播放器未就绪");
      }
    },
    play: () => {
      console.log("▶️ HighlightPlayer.play 被调用:", {
        isReady,
        currentIsPlaying: isPlaying,
      });
      if (isReady) {
        setIsPlaying(true);
        console.log("✅ play 完成，设置 isPlaying = true");
      } else {
        console.warn("⚠️ play 失败：播放器未就绪");
      }
    },
    pause: () => {
      console.log("⏸️ HighlightPlayer.pause 被调用");
      setIsPlaying(false);
    },
    togglePlay: () => {
      if (isReady) {
        setIsPlaying(!isPlaying);
      }
    },
  }));

  /**
   * 处理播放器就绪
   */
  const handleReady = () => {
    console.log("🎬 ReactPlayer handleReady 被调用");
    if (playerRef.current) {
      const duration = playerRef.current.getDuration();
      setDurationMs(duration * 1000);
      setIsReady(true);
      console.log('✅ HighlightPlayer 已就绪:', {
        duration,
        durationMs: duration * 1000,
      });

      // 通知父组件播放器已就绪
      onReady?.();
    } else {
      console.error("❌ playerRef.current 为空");
    }
  };

  /**
   * 处理播放进度更新
   */
  const handleProgress = (state: any) => {
    if (!isSeeking && state?.playedSeconds !== undefined) {
      const currentTimeMs = state.playedSeconds * 1000;
      setCurrentTimeMs(currentTimeMs);
      onProgress?.(currentTimeMs);
    }
  };

  /**
   * 切换播放/暂停
   */
  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  /**
   * 跳转到指定时间（毫秒）
   */
  const seekTo = (timeMs: number) => {
    if (playerRef.current && durationMs > 0) {
      const timeInSeconds = timeMs / 1000;
      playerRef.current.seekTo(timeInSeconds, "seconds");
      setCurrentTimeMs(timeMs);
    }
  };

  /**
   * 处理进度条点击/拖拽
   */
  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!progressContainerRef.current || durationMs === 0) return;

    const rect = progressContainerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, clickX / rect.width));
    const newTimeMs = percentage * durationMs;

    seekTo(newTimeMs);
  };

  /**
   * 处理标记点击
   */
  const handleMarkerClick = (marker: HighlightMarker, e: React.MouseEvent) => {
    e.stopPropagation(); // 防止触发进度条点击
    seekTo(marker.timeMs);
    onMarkerClick?.(marker);
  };

  /**
   * 键盘快捷键
   */
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // 空格键：播放/暂停
      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      }
      // 左右箭头：±5秒
      else if (e.code === "ArrowLeft") {
        seekTo(Math.max(0, currentTimeMs - 5000));
      } else if (e.code === "ArrowRight") {
        seekTo(Math.min(durationMs, currentTimeMs + 5000));
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [currentTimeMs, durationMs]);

  console.log("🎬🎬 HighlightPlayer 即将渲染到DOM:", {
    isPlaying,
    durationMs,
    isReady,
    url,
  });

  return (
    <div className={`relative w-full ${className}`}>
      {/* 视频播放器 */}
      <div className="relative bg-black rounded-lg overflow-hidden">
        {/* ReactPlayer 隐藏原生控件 */}
        <div className="aspect-video max-h-[600px]">
          <ReactPlayer
            ref={playerRef as any}
            {...{ url } as any}
            playing={isPlaying}
            width="100%"
            height="100%"
            onReady={handleReady}
            onProgress={handleProgress as any}
            onError={(e: any) => {
              console.error("❌ ReactPlayer 错误:", e);
              setLoadError(e?.toString?.() || "视频加载失败");
              onReady?.();
            }}
          />
        </div>

        {/* 自定义播放按钮覆盖层 */}
        {!isPlaying && (
          <div
            className="absolute inset-0 flex items-center justify-center cursor-pointer"
            onClick={togglePlay}
          >
            <div className="w-20 h-20 bg-black/50 rounded-full flex items-center justify-center hover:bg-black/60 transition-colors">
              <Play className="w-10 h-10 text-white ml-1" />
            </div>
          </div>
        )}
      </div>

      {/* 控制栏 */}
      <div className="mt-4 space-y-3">
        {/* 进度条 */}
        <div
          ref={progressContainerRef}
          className="relative h-2 bg-muted rounded-full cursor-pointer group"
          onClick={handleProgressClick}
        >
          {/* 已播放进度 */}
          <div
            className="absolute h-full bg-primary rounded-full transition-all"
            style={{
              width: durationMs > 0 ? `${(currentTimeMs / durationMs) * 100}%` : "0%",
            }}
          />

          {/* 高光标记点 */}
          {markers.map((marker) => {
            const percentage = durationMs > 0 ? (marker.timeMs / durationMs) * 100 : 0;
            return (
              <div
                key={marker.id}
                className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-white shadow-lg cursor-pointer hover:scale-125 transition-transform z-10"
                style={{
                  left: `${percentage}%`,
                  marginLeft: "-8px",
                  backgroundColor: marker.color || "hsl(var(--primary))",
                }}
                onClick={(e) => handleMarkerClick(marker, e)}
                title={`${marker.label || formatMsToTime(marker.timeMs)}`}
              />
            );
          })}

          {/* 悬停时显示的时间提示 */}
          <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
            {formatMsToTime(currentTimeMs)}
          </div>
        </div>

        {/* 时间显示和控制按钮 */}
        <div className="flex items-center justify-between">
          {/* 当前时间 / 总时长 */}
          <div className="flex items-center gap-2 font-mono text-sm text-muted-foreground">
            <span>{formatMsToTime(currentTimeMs)}</span>
            <span>/</span>
            <span>{formatMsToTime(durationMs)}</span>
          </div>

          {/* 播放/暂停按钮 */}
          <Button
            variant="outline"
            size="sm"
            onClick={togglePlay}
            className="cursor-pointer"
          >
            {isPlaying ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>

      {/* 快捷键提示 */}
      <div className="mt-2 text-xs text-muted-foreground text-center">
        快捷键：空格 = 播放/暂停 | ←/→ = ±5秒
      </div>
    </div>
  );
});

HighlightPlayer.displayName = "HighlightPlayer";
