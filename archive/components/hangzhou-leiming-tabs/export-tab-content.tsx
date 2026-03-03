"use client";

import { useState, useEffect } from "react";
import { Download, Loader2, FileVideo, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ExportTabContentProps {
  projectId: number;
  projectName: string;
}

interface ClipCombination {
  id: number;
  name: string;
  totalDurationMs: number;
  overallScore: number;
  clips: Array<{
    videoName: string;
    startMs: number;
    endMs: number;
  }>;
  createdAt: Date;
  exportPath: string | null;
}

export function ExportTabContent({ projectId, projectName }: ExportTabContentProps) {
  const [combinations, setCombinations] = useState<ClipCombination[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<number | null>(null);

  useEffect(() => {
    loadCombinations();
  }, [projectId]);

  const loadCombinations = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/hangzhou-leiming/projects/${projectId}/recommend`);
      const result = await res.json();
      if (result.success) {
        setCombinations(result.data?.combinations || []);
      }
    } catch (error) {
      console.error("加载推荐失败:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (combinationId: number) => {
    setExporting(combinationId);
    try {
      const res = await fetch("/api/hangzhou-leiming/exports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ projectId, combinationId }),
      });
      const result = await res.json();
      if (result.success) {
        alert("导出任务已创建");
        loadCombinations();
      } else {
        alert("导出失败: " + result.message);
      }
    } catch (error) {
      alert("导出失败");
    } finally {
      setExporting(null);
    }
  };

  const formatDuration = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}分${remainingSeconds}秒`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">导出中心</h2>
          <p className="text-muted-foreground text-sm mt-1">{projectName} - 导出成品视频</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-orange-600" /></div>
      ) : combinations.length === 0 ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">暂无推荐组合，请先运行AI分析</CardContent></Card>
      ) : (
        <div className="space-y-4">
          {combinations.map((combo, index) => (
            <Card key={combo.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">
                      #{index + 1} {combo.name}
                    </CardTitle>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant="secondary">得分: {combo.overallScore}</Badge>
                      <Badge variant="outline">
                        <Clock className="w-3 h-3 mr-1" />
                        {formatDuration(combo.totalDurationMs)}
                      </Badge>
                      {combo.exportPath && (
                        <Badge className="bg-green-100 text-green-800">
                          已导出
                        </Badge>
                      )}
                    </div>
                  </div>
                  <Button
                    onClick={() => handleExport(combo.id)}
                    disabled={exporting === combo.id || !!combo.exportPath}
                    className="bg-gradient-to-r from-green-500 to-emerald-500"
                  >
                    {exporting === combo.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : combo.exportPath ? (
                      "已导出"
                    ) : (
                      <>
                        <Download className="w-4 h-4 mr-2" />
                        导出视频
                      </>
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">片段列表:</p>
                  {combo.clips.map((clip, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm bg-muted p-2 rounded">
                      <FileVideo className="w-4 h-4" />
                      <span className="flex-1">{clip.videoName}</span>
                      <span className="text-muted-foreground">
                        {formatDuration(clip.endMs - clip.startMs)}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
