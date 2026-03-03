"use client";

/**
 * 杭州雷鸣 - 导出中心页面
 *
 * 功能：
 * - 选择剪辑组合
 * - 一键导出视频
 * - 查看导出记录
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Download,
  FileVideo,
  Clock,
  HardDrive,
  CheckCircle,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HangzhouLeimingLayout } from "@/components/hangzhou-leiming-layout";

interface ExportRecord {
  id: number;
  combinationId: number;
  outputPath: string | null;
  fileSize: number | null;
  status: string;
  createdAt: Date;
  completedAt: Date | null;
}

export default function ExportCenterPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const [projectId, setProjectId] = useState<number | null>(null);

  // 导出记录
  const [exports, setExports] = useState<ExportRecord[]>([]);
  const [loading, setLoading] = useState(true);

  // 加载projectId
  useEffect(() => {
    params.then((resolvedParams) => {
      setProjectId(parseInt(resolvedParams.id));
    });
  }, [params]);

  // 加载导出记录
  useEffect(() => {
    if (projectId) {
      loadExports();
    }
  }, [projectId]);

  const loadExports = async () => {
    if (!projectId) return;

    try {
      const res = await fetch(
        `/api/hangzhou-leiming/exports?projectId=${projectId}`
      );
      const result = await res.json();
      if (result.success) {
        setExports(result.data || []);
      }
    } catch (error) {
      console.error("加载导出记录失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (!bytes) return "-";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " MB";
    return (bytes / (1024 * 1024)).toFixed(2) + " GB";
  };

  // 下载视频
  const handleDownload = async (exportId: number) => {
    try {
      // 打开下载链接
      window.open(`/api/hangzhou-leiming/exports/${exportId}/download`, "_blank");
    } catch (error) {
      console.error("下载失败:", error);
      alert("下载失败，请稍后重试");
    }
  };

  // 等待projectId
  if (projectId === null) {
    return (
      <HangzhouLeimingLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
        </div>
      </HangzhouLeimingLayout>
    );
  }

  return (
    <HangzhouLeimingLayout projectId={projectId}>
      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
            导出中心
          </h1>
          <p className="text-muted-foreground mt-2">
            一键导出剪辑组合，生成成品视频
          </p>
        </div>
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
          </div>
        ) : exports.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Download className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">暂无导出记录</h3>
              <p className="text-muted-foreground mb-6">
                在智能剪辑中选择组合并导出后，记录将显示在这里
              </p>
              <Button
                onClick={() => router.push(`/hangzhou-leiming/${projectId}/smart-editor`)}
                className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
              >
                前往智能剪辑
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {exports.map((exp) => (
              <Card key={exp.id}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div
                        className={`p-3 rounded-full ${
                          exp.status === "completed"
                            ? "bg-green-100"
                            : exp.status === "processing"
                            ? "bg-blue-100"
                            : "bg-red-100"
                        }`}
                      >
                        {exp.status === "completed" ? (
                          <CheckCircle className="w-6 h-6 text-green-600" />
                        ) : exp.status === "processing" ? (
                          <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                        ) : (
                          <FileVideo className="w-6 h-6 text-red-600" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium">
                          导出 #{exp.id}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {new Date(exp.createdAt).toLocaleString("zh-CN")}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-6 text-sm">
                      <div className="flex items-center gap-2">
                        <HardDrive className="w-4 h-4 text-muted-foreground" />
                        <span>{formatFileSize(exp.fileSize || 0)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-muted-foreground" />
                        <span>
                          {exp.completedAt
                            ? new Date(exp.completedAt).toLocaleString("zh-CN")
                            : "处理中..."}
                        </span>
                      </div>
                      <div
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          exp.status === "completed"
                            ? "bg-green-100 text-green-800"
                            : exp.status === "processing"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {exp.status === "completed"
                          ? "已完成"
                          : exp.status === "processing"
                          ? "处理中"
                          : "失败"}
                      </div>

                      {/* 下载按钮 */}
                      {exp.status === "completed" && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="cursor-pointer"
                          onClick={() => handleDownload(exp.id)}
                        >
                          <Download className="w-4 h-4 mr-2" />
                          下载
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </HangzhouLeimingLayout>
  );
}
