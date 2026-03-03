"use client";

import { useState, useEffect } from "react";
import { Wand2, Loader2, Play, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface SmartEditorTabContentProps {
  projectId: number;
  projectName: string;
  onUpdate?: () => void;
}

export function SmartEditorTabContent({ projectId, projectName, onUpdate }: SmartEditorTabContentProps) {
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState<string>("");
  const [lastAnalysis, setLastAnalysis] = useState<any>(null);

  useEffect(() => {
    checkAnalysisStatus();
  }, [projectId]);

  const checkAnalysisStatus = async () => {
    try {
      const res = await fetch(`/api/hangzhou-leiming/projects/${projectId}/analyze`);
      const result = await res.json();
      if (result.success && result.data) {
        setLastAnalysis(result.data);
      }
    } catch (error) {
      console.error("检查分析状态失败:", error);
    }
  };

  const startAnalysis = async () => {
    if (!confirm("确定要开始AI智能分析吗？这可能需要几分钟时间。")) return;

    setAnalyzing(true);
    setAnalysisStatus("正在启动AI分析...");

    try {
      const res = await fetch(`/api/hangzhou-leiming/projects/${projectId}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skillId: null }),
      });

      const result = await res.json();
      if (result.success) {
        setAnalysisStatus("分析任务已创建，正在处理...");
        // 轮询状态
        const interval = setInterval(async () => {
          const statusRes = await fetch(`/api/hangzhou-leiming/projects/${projectId}/analyze`);
          const statusResult = await statusRes.json();
          if (statusResult.data?.status === "completed") {
            clearInterval(interval);
            setAnalyzing(false);
            setAnalysisStatus("分析完成！");
            onUpdate?.();
          } else if (statusResult.data?.status === "error") {
            clearInterval(interval);
            setAnalyzing(false);
            setAnalysisStatus("分析失败: " + statusResult.data?.error);
          }
        }, 3000);
      } else {
        setAnalyzing(false);
        setAnalysisStatus("启动失败: " + result.message);
      }
    } catch (error) {
      setAnalyzing(false);
      setAnalysisStatus("启动失败");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">智能剪辑</h2>
          <p className="text-muted-foreground text-sm mt-1">{projectName} - AI自动标注和剪辑</p>
        </div>
        <Button onClick={startAnalysis} disabled={analyzing} className="bg-gradient-to-r from-purple-500 to-pink-500">
          {analyzing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Wand2 className="w-4 h-4 mr-2" />}
          {analyzing ? "分析中..." : "开始AI分析"}
        </Button>
      </div>

      {analysisStatus && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              {analyzing && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{analysisStatus}</span>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">功能说明</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>• 自动识别高光时刻和悬念钩子</p>
            <p>• 智能生成剪辑推荐组合</p>
            <p>• 支持技能文件训练</p>
          </CardContent>
        </Card>

        {lastAnalysis && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">最近分析</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant={lastAnalysis.status === "completed" ? "default" : "secondary"}>
                    {lastAnalysis.status}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {new Date(lastAnalysis.createdAt).toLocaleString("zh-CN")}
                  </span>
                </div>
                {lastAnalysis.status === "completed" && (
                  <div className="text-sm">
                    <p>找到高光: {lastAnalysis.highlightsFound} 个</p>
                    <p>找到钩子: {lastAnalysis.hooksFound} 个</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
