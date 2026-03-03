"use client";

/**
 * 杭州雷鸣 - 项目详情：标记管理页面
 *
 * 功能：
 * - 查看项目下的所有标记
 * - 筛选标记（高光点/钩子点）
 * - 删除标记
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Trash2,
  FileText,
  Clock,
  Calendar,
  Filter,
  CheckCircle,
  Loader2,
  Target,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { HangzhouLeimingLayout } from "@/components/hangzhou-leiming-layout";

interface HLMarking {
  id: number;
  projectId: number;
  videoId: number;
  timestamp: string;
  seconds: number;
  type: "高光点" | "钩子点";
  subType: string | null;
  description: string | null;
  score: number | null;
  reasoning: string | null;
  aiEnhanced: boolean;
  emotion: string | null;
  characters: string | null;
  createdAt: Date;
  updatedAt: Date;
}

interface HLVideo {
  id: number;
  episodeNumber: string;
  displayTitle: string;
}

interface HLProject {
  id: number;
  name: string;
  description: string | null;
}

export default function MarkingsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [project, setProject] = useState<HLProject | null>(null);
  const [markings, setMarkings] = useState<HLMarking[]>([]);
  const [videos, setVideos] = useState<HLVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"全部" | "高光点" | "钩子点">("全部");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedMarking, setSelectedMarking] = useState<HLMarking | null>(null);

  // 加载 projectId
  useEffect(() => {
    params.then((resolvedParams) => {
      setProjectId(parseInt(resolvedParams.id));
    });
  }, [params]);

  // 加载数据
  useEffect(() => {
    if (projectId) {
      loadProject();
      loadMarkings();
      loadVideos();
    }
  }, [projectId]);

  const loadProject = async () => {
    if (!projectId) return;

    try {
      const res = await fetch(`/api/hangzhou-leiming/projects/${projectId}`);
      const result = await res.json();

      if (result.success) {
        setProject(result.data);
      }
    } catch (error) {
      console.error("加载项目失败:", error);
    }
  };

  const loadMarkings = async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      const res = await fetch(
        `/api/hangzhou-leiming/markings?projectId=${projectId}`
      );
      const result = await res.json();

      if (result.success) {
        setMarkings(result.data || []);
      }
    } catch (error) {
      console.error("加载标记失败:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadVideos = async () => {
    if (!projectId) return;

    try {
      const res = await fetch(
        `/api/hangzhou-leiming/videos?projectId=${projectId}`
      );
      const result = await res.json();

      if (result.success) {
        setVideos(result.data || []);
      }
    } catch (error) {
      console.error("加载视频失败:", error);
    }
  };

  // 删除标记
  const handleDeleteMarking = async () => {
    if (!selectedMarking) return;

    try {
      const res = await fetch(
        `/api/hangzhou-leiming/markings/${selectedMarking.id}`,
        {
          method: "DELETE",
        }
      );

      const result = await res.json();

      if (result.success) {
        setDeleteDialogOpen(false);
        setSelectedMarking(null);
        await loadMarkings();
      } else {
        alert(`删除失败：${result.message}`);
      }
    } catch (error) {
      console.error("删除标记失败:", error);
      alert("删除标记失败，请稍后重试");
    }
  };

  // 获取视频标题
  const getVideoTitle = (videoId: number) => {
    const video = videos.find((v) => v.id === videoId);
    return video ? `${video.episodeNumber} - ${video.displayTitle}` : "未知视频";
  };

  // 筛选后的标记
  const filteredMarkings =
    filter === "全部"
      ? markings
      : markings.filter((m) => m.type === filter);

  // 统计
  const highlightCount = markings.filter((m) => m.type === "高光点").length;
  const hookCount = markings.filter((m) => m.type === "钩子点").length;

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
            标记管理
          </h1>
          <p className="text-muted-foreground mt-2">
            {project?.name || "加载中..."} - 查看和管理所有标记
          </p>
        </div>
        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                标记总数
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <FileText className="w-8 h-8 text-blue-600" />
                <div className="text-3xl font-bold">{markings.length}</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                高光点
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Zap className="w-8 h-8 text-orange-600" />
                <div className="text-3xl font-bold">{highlightCount}</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                钩子点
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Target className="w-8 h-8 text-green-600" />
                <div className="text-3xl font-bold">{hookCount}</div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 筛选器 */}
        <div className="flex items-center gap-2 mb-6">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <Button
            variant={filter === "全部" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("全部")}
            className="cursor-pointer"
          >
            全部 ({markings.length})
          </Button>
          <Button
            variant={filter === "高光点" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("高光点")}
            className="cursor-pointer"
          >
            高光点 ({highlightCount})
          </Button>
          <Button
            variant={filter === "钩子点" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("钩子点")}
            className="cursor-pointer"
          >
            钩子点 ({hookCount})
          </Button>
        </div>

        {/* 标记列表 */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
          </div>
        ) : filteredMarkings.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FileText className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">暂无标记</h3>
              <p className="text-muted-foreground mb-6">
                {filter === "全部"
                  ? "上传视频并导入Excel标记文件，或使用AI自动标注"
                  : `暂无${filter}标记`}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredMarkings.map((marking) => (
              <Card key={marking.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <div
                          className={`p-2 rounded-full ${
                            marking.type === "高光点"
                              ? "bg-orange-100"
                              : "bg-green-100"
                          }`}
                        >
                          {marking.type === "高光点" ? (
                            <Zap className="w-4 h-4 text-orange-600" />
                          ) : (
                            <Target className="w-4 h-4 text-green-600" />
                          )}
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold">{marking.type}</h3>
                          <p className="text-sm text-muted-foreground">
                            {marking.subType || "未分类"}
                          </p>
                        </div>
                        {marking.aiEnhanced && (
                          <div className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                            AI增强
                          </div>
                        )}
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                        <div className="flex items-center gap-2 text-sm">
                          <Clock className="w-4 h-4 text-muted-foreground" />
                          <span className="text-muted-foreground">时间点：</span>
                          <span className="font-medium">{marking.timestamp}</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                          <FileText className="w-4 h-4 text-muted-foreground" />
                          <span className="text-muted-foreground">得分：</span>
                          <span className="font-medium">
                            {marking.score ?? "-"}
                          </span>
                        </div>
                      </div>

                      {marking.description && (
                        <div className="mb-2">
                          <p className="text-sm text-muted-foreground mb-1">
                            描述：
                          </p>
                          <p className="text-sm">{marking.description}</p>
                        </div>
                      )}

                      {marking.reasoning && (
                        <div className="mb-2">
                          <p className="text-sm text-muted-foreground mb-1">
                            推理：
                          </p>
                          <p className="text-sm">{marking.reasoning}</p>
                        </div>
                      )}

                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>视频：{getVideoTitle(marking.videoId)}</span>
                        <span>
                          创建于：{new Date(marking.createdAt).toLocaleString("zh-CN")}
                        </span>
                      </div>
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      className="cursor-pointer hover:bg-red-50 hover:text-red-600"
                      onClick={() => {
                        setSelectedMarking(marking);
                        setDeleteDialogOpen(true);
                      }}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* 删除确认对话框 */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="确认删除标记"
        description={`确定要删除${selectedMarking?.type}「${selectedMarking?.timestamp}」吗？此操作无法撤销。`}
        confirmText="确认删除"
        cancelText="取消"
        onConfirm={handleDeleteMarking}
        variant="destructive"
      />
    </HangzhouLeimingLayout>
  );
}
