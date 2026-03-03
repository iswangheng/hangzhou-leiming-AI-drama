"use client";

import { useEffect, useRef, useState } from "react";
import { Scroll } from "lucide-react";

interface LogEntry {
  id: string;
  trainingId: number;
  level: 'info' | 'success' | 'warning' | 'error';
  timestamp: Date;
  message: string;
  step?: string;
  progress?: number;
}

interface TrainingLogsProps {
  trainingId: number | null;
  isTraining: boolean;
}

export function TrainingLogs({ trainingId, isTraining }: TrainingLogsProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  // WebSocket连接
  useEffect(() => {
    if (!trainingId || !isTraining) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
        setIsConnected(false);
      }
      return;
    }

    // 连接WebSocket
    const wsUrl = `ws://localhost:3001`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket连接成功');
      setIsConnected(true);

      // 订阅训练日志
      ws.send(JSON.stringify({
        type: 'subscribe',
        channel: 'training_log',
      }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'training_log' && data.data.trainingId === trainingId) {
          const newLog: LogEntry = {
            id: `${Date.now()}-${Math.random()}`,
            trainingId: data.data.trainingId,
            level: data.data.level,
            timestamp: new Date(data.data.timestamp),
            message: data.data.message,
            step: data.data.step,
            progress: data.data.progress,
          };

          setLogs((prev) => [...prev, newLog]);
        }
      } catch (error) {
        console.error('解析WebSocket消息失败:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket连接关闭');
      setIsConnected(false);
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [trainingId, isTraining]);

  // 清空日志
  useEffect(() => {
    if (!isTraining) {
      setLogs([]);
    }
  }, [isTraining]);

  // 获取日志样式
  const getLogStyle = (level: LogEntry['level']) => {
    const styles = {
      info: 'text-blue-600',
      success: 'text-green-600',
      warning: 'text-yellow-600',
      error: 'text-red-600',
    };
    return styles[level];
  };

  const getLogIcon = (level: LogEntry['level']) => {
    const icons = {
      info: 'ℹ️',
      success: '✅',
      warning: '⚠️',
      error: '❌',
    };
    return icons[level];
  };

  // 格式化时间
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { hour12: false });
  };

  if (!isTraining || logs.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 border rounded-lg bg-slate-950 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Scroll className="w-4 h-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">训练日志</h3>
          <span className="text-xs text-slate-500">
            ({logs.length} 条)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-xs text-slate-500">
            {isConnected ? '已连接' : '未连接'}
          </span>
        </div>
      </div>

      {/* Logs */}
      <div className="p-4 h-96 overflow-y-auto font-mono text-sm">
        <div className="space-y-1">
          {logs.map((log) => (
            <div
              key={log.id}
              className={`flex items-start gap-2 ${getLogStyle(log.level)}`}
            >
              <span className="flex-shrink-0">{getLogIcon(log.level)}</span>
              <span className="flex-shrink-0 text-slate-500">
                [{formatTime(log.timestamp)}]
              </span>
              {log.step && (
                <span className="flex-shrink-0 px-1.5 py-0.5 bg-slate-800 rounded text-xs text-slate-400">
                  {log.step}
                </span>
              )}
              <span className="flex-1 text-slate-300">{log.message}</span>
              {log.progress !== undefined && (
                <span className="flex-shrink-0 text-slate-500">
                  ({log.progress}%)
                </span>
              )}
            </div>
          ))}
        </div>
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}
