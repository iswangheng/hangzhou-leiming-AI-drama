"use client";

/**
 * 杭州雷鸣 - 项目详情：视频管理页面
 *
 * 功能：
 * - 查看项目下的所有视频
 * - 上传新视频
 * - 删除视频
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Upload,
  Trash2,
  Video,
  Clock,
  Calendar,
  CheckCircle,
  Loader2,
  FileVideo,
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

interface HLVideo {
  id: number;
  projectId: number;
  filename: string;
  filePath: string;
  fileSize: number;
  episodeNumber: string;
  displayTitle: string;
  sortOrder: number;
  durationMs: number;
  width: number;
  height: number;
  fps: number;
  status: "uploading" | "processing" | "ready" | "error";
  createdAt: Date;
}

interface HLProject {
  id: number;
  name: string;
  description: string | null;
}

export default function VideosPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [project, setProject] = useState<HLProject | null>(null);
  const [videos, setVideos] = useState<HLVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<HLVideo | null>(null);
  const [playVideoDialogOpen, setPlayVideoDialogOpen] = useState(false);
  const [playingVideo, setPlayingVideo] = useState<HLVideo | null>(null);

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

  const loadVideos = async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      const res = await fetch(
        `/api/hangzhou-leiming/videos?projectId=${projectId}`
      );
      const result = await res.json();

      if (result.success) {
        setVideos(result.data || []);
      }
    } catch (error) {
      console.error("加载视频失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 上传视频
  const handleUpload = async (files: FileList | null) => {
    if (!files || !projectId) return;

    setUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append("file", file);
        formData.append("projectId", projectId.toString());

        // 可以添加集数和显示标题
        const episodeNumber = prompt(`请输入「${file.name}」的集数（如：第1集）`, `第${videos.length + i + 1}集`);
        if (episodeNumber) {
          formData.append("episodeNumber", episodeNumber);
          formData.append("displayTitle", episodeNumber);
        }

        const res = await fetch("/api/hangzhou-leiming/videos", {
          method: "POST",
          body: formData,
        });

        const result = await res.json();

        if (!result.success) {
          alert(`上传 ${file.name} 失败：${result.message}`);
        }
      }

      await loadVideos();
    } catch (error) {
      console.error("上传视频失败:", error);
      alert("上传视频失败，请稍后重试");
    } finally {
      setUploading(false);
    }
  };

  // 删除视频
  const handleDeleteVideo = async () => {
    if (!selectedVideo) return;

    try {
      const res = await fetch(
        `/api/hangzhou-leiming/videos/${selectedVideo.id}`,
        {
          method: "DELETE",
        }
      );

      const result = await res.json();

      if (result.success) {
        setDeleteDialogOpen(false);
        setSelectedVideo(null);
        await loadVideos();
      } else {
        alert(`删除失败：${result.message}`);
      }
    } catch (error) {
      console.error("删除视频失败:", error);
      alert("删除视频失败，请稍后重试");
    }
  };

  // 播放视频
  const handlePlayVideo = (video: HLVideo) => {
    setPlayingVideo(video);
    setPlayVideoDialogOpen(true);
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (!bytes) return "-";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + " MB";
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
  };

  // 格式化时长
  const formatDuration = (ms: number) => {
    if (!ms) return "-";
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  };

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
        {/* 页面标题和操作按钮 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
              视频管理
            </h1>
            <p className="text-muted-foreground mt-2">
              {project?.name || "加载中..."} - 管理项目下的所有视频
            </p>
          </div>
          <Button
            onClick={() => document.getElementById('video-upload')?.click()}
            className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
            disabled={uploading}
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                上传中...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                上传视频
              </>
            )}
          </Button>
          <input
            id="video-upload"
            type="file"
            accept="video/*"
            multiple
            className="hidden"
            onChange={(e) => handleUpload(e.target.files)}
          />
        </div>
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
          </div>
        ) : videos.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FileVideo className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">暂无视频</h3>
              <p className="text-muted-foreground mb-6">
                上传视频文件开始使用杭州雷鸣
              </p>
              <Button
                onClick={() => document.getElementById('video-upload-empty')?.click()}
                className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
              >
                <Upload className="w-4 h-4 mr-2" />
                上传视频
              </Button>
              <input
                id="video-upload-empty"
                type="file"
                accept="video/*"
                multiple
                className="hidden"
                onChange={(e) => handleUpload(e.target.files)}
              />
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {videos.map((video) => (
              <Card
                key={video.id}
                className="hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => handlePlayVideo(video)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg mb-1">
                        {video.displayTitle || video.filename}
                      </CardTitle>
                      <CardDescription className="text-xs">
                        {video.episodeNumber}
                      </CardDescription>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="cursor-pointer hover:bg-red-50 hover:text-red-600"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedVideo(video);
                        setDeleteDialogOpen(true);
                      }}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm">
                      <Video className="w-4 h-4 text-muted-foreground" />
                      <span className="text-muted-foreground">文件：</span>
                      <span className="truncate flex-1">{video.filename}</span>
                    </div>

                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="w-4 h-4 text-muted-foreground" />
                      <span className="text-muted-foreground">时长：</span>
                      <span>{formatDuration(video.durationMs)}</span>
                    </div>

                    <div className="flex items-center gap-2 text-sm">
                      <FileVideo className="w-4 h-4 text-muted-foreground" />
                      <span className="text-muted-foreground">大小：</span>
                      <span>{formatFileSize(video.fileSize)}</span>
                    </div>

                    <div className="flex items-center gap-2 text-sm">
                      <Calendar className="w-4 h-4 text-muted-foreground" />
                      <span className="text-muted-foreground">上传时间：</span>
                      <span>{new Date(video.createdAt).toLocaleString("zh-CN")}</span>
                    </div>

                    <div className="pt-3 border-t">
                      <div
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                          video.status === "ready"
                            ? "bg-green-100 text-green-800"
                            : video.status === "processing"
                            ? "bg-blue-100 text-blue-800"
                            : video.status === "error"
                            ? "bg-red-100 text-red-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {video.status === "ready" ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : null}
                        {
                          {
                            uploading: "上传中",
                            processing: "处理中",
                            ready: "就绪",
                            error: "错误",
                          }[video.status]
                        }
                      </div>
                    </div>
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
        title="确认删除视频"
        description={`确定要删除视频「${selectedVideo?.displayTitle || selectedVideo?.filename}」吗？此操作将删除视频文件和相关标记数据，且无法恢复。`}
        confirmText="确认删除"
        cancelText="取消"
        onConfirm={handleDeleteVideo}
        variant="destructive"
      />

      {/* 视频播放对话框 */}
      <Dialog
        open={playVideoDialogOpen}
        onOpenChange={(open) => {
          setPlayVideoDialogOpen(open);
          if (!open) {
            setPlayingVideo(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-[800px]">
          <DialogHeader>
            <DialogTitle>
              {playingVideo?.displayTitle || playingVideo?.filename}
            </DialogTitle>
            <DialogDescription>
              {playingVideo?.episodeNumber} · {formatDuration(playingVideo?.durationMs || 0)} · {formatFileSize(playingVideo?.fileSize || 0)}
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4">
            {playingVideo && (
              <video
                key={playingVideo.id}
                src={`/api/hangzhou-leiming/videos/${playingVideo.id}/stream`}
                controls
                autoPlay
                className="w-full rounded-lg"
                style={{ maxHeight: '60vh' }}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </HangzhouLeimingLayout>
  );
}
