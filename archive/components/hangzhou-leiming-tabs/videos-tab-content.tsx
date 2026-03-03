"use client";

import { useEffect, useState } from "react";
import {
  Upload,
  Trash2,
  Video,
  Clock,
  Calendar,
  CheckCircle,
  Loader2,
  FileVideo,
  Images,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ConfirmDialog } from "@/components/confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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

interface VideosTabContentProps {
  projectId: number;
  projectName: string;
  onUpdate?: () => void;
}

export function VideosTabContent({
  projectId,
  projectName,
  onUpdate,
}: VideosTabContentProps) {
  const [videos, setVideos] = useState<HLVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<HLVideo | null>(null);
  const [playVideoDialogOpen, setPlayVideoDialogOpen] = useState(false);
  const [playingVideo, setPlayingVideo] = useState<HLVideo | null>(null);
  const [mediaDataDialogOpen, setMediaDataDialogOpen] = useState(false);
  const [mediaData, setMediaData] = useState<any>(null);
  const [loadingMediaData, setLoadingMediaData] = useState(false);

  // 关键帧hover浮窗状态
  const [hoverPreview, setHoverPreview] = useState<{
    show: boolean;
    imageUrl: string;
    x: number;
    y: number;
  }>({
    show: false,
    imageUrl: '',
    x: 0,
    y: 0,
  });

  useEffect(() => {
    loadVideos();
  }, [projectId]);

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

  const handleUpload = async (files: FileList | null) => {
    if (!files || !projectId) return;

    setUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append("file", file);
        formData.append("projectId", projectId.toString());

        const episodeNumber = prompt(
          `请输入「${file.name}」的集数（如：第1集）`,
          `第${videos.length + i + 1}集`
        );
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
      onUpdate?.();
    } catch (error) {
      console.error("上传视频失败:", error);
      alert("上传视频失败，请稍后重试");
    } finally {
      setUploading(false);
    }
  };

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
        onUpdate?.();
      } else {
        alert(`删除失败：${result.message}`);
      }
    } catch (error) {
      console.error("删除视频失败:", error);
      alert("删除视频失败，请稍后重试");
    }
  };

  const handlePlayVideo = (video: HLVideo) => {
    setPlayingVideo(video);
    setPlayVideoDialogOpen(true);
  };

  const handleViewMediaData = async () => {
    if (!projectId) return;

    try {
      setLoadingMediaData(true);
      setMediaDataDialogOpen(true);

      // 添加时间戳参数避免浏览器缓存
      const cacheBuster = Date.now();
      const res = await fetch(
        `/api/hangzhou-leiming/projects/${projectId}/media-data?_=${cacheBuster}`
      );
      const result = await res.json();

      if (result.success) {
        setMediaData(result.data);
      } else {
        alert(`加载素材数据失败：${result.message}`);
        setMediaDataDialogOpen(false);
      }
    } catch (error) {
      console.error("加载素材数据失败:", error);
      alert("加载素材数据失败，请稍后重试");
      setMediaDataDialogOpen(false);
    } finally {
      setLoadingMediaData(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (!bytes) return "-";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + " MB";
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
  };

  const formatDuration = (ms: number) => {
    if (!ms) return "-";
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  };

  // 关键帧hover处理
  const handleKeyframeMouseEnter = (imagePath: string, event: React.MouseEvent) => {
    setHoverPreview({
      show: true,
      imageUrl: imagePath,
      x: event.clientX,
      y: event.clientY,
    });
  };

  const handleKeyframeMouseLeave = () => {
    setHoverPreview({
      show: false,
      imageUrl: '',
      x: 0,
      y: 0,
    });
  };

  const handleKeyframeMouseMove = (event: React.MouseEvent) => {
    setHoverPreview((prev) => ({
      ...prev,
      x: event.clientX,
      y: event.clientY,
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">视频管理</h2>
          <p className="text-muted-foreground text-sm mt-1">
            {projectName} - 管理项目下的所有视频
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleViewMediaData}
            className="cursor-pointer"
            disabled={loadingMediaData}
          >
            <Images className="w-4 h-4 mr-2" />
            查看素材数据
          </Button>
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

      {/* 素材数据查看对话框 */}
      <Dialog
        open={mediaDataDialogOpen}
        onOpenChange={(open) => {
          setMediaDataDialogOpen(open);
          if (!open) {
            setMediaData(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>项目素材数据</DialogTitle>
            <DialogDescription>
              查看项目所有视频的关键帧和ASR转录数据
            </DialogDescription>
          </DialogHeader>

          <div className="mt-4">
            {loadingMediaData ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
              </div>
            ) : mediaData ? (
              <div className="space-y-6">
                {/* 统计信息 */}
                <div className="grid grid-cols-3 gap-4 p-4 bg-slate-50 rounded-lg">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-orange-600">
                      {mediaData.stats.totalVideos}
                    </div>
                    <div className="text-sm text-muted-foreground">总视频数</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {mediaData.stats.videosWithKeyframes}
                    </div>
                    <div className="text-sm text-muted-foreground">已提取关键帧</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {mediaData.stats.videosWithAsr}
                    </div>
                    <div className="text-sm text-muted-foreground">已转录ASR</div>
                  </div>
                </div>

                {/* 视频列表 */}
                <div className="space-y-4">
                  {mediaData.videos.map((video: any) => (
                    <Card key={video.videoId}>
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base">
                            {video.displayTitle}
                          </CardTitle>
                          <div className="flex items-center gap-2">
                            {video.keyframes.hasData && (
                              <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                                <Images className="w-3 h-3" />
                                {video.keyframes.count} 帧
                              </span>
                            )}
                            {video.asr.hasData && (
                              <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                                <FileText className="w-3 h-3" />
                                ASR
                              </span>
                            )}
                          </div>
                        </div>
                        <CardDescription className="text-xs">
                          {video.episodeNumber} · {video.durationSeconds}秒
                        </CardDescription>
                      </CardHeader>

                      <CardContent className="space-y-4">
                        {/* 关键帧预览 */}
                        {video.keyframes.hasData && (
                          <div>
                            <h4 className="text-sm font-medium mb-2">关键帧预览</h4>
                            <div className="grid grid-cols-5 gap-2">
                              {video.keyframes.preview.map((kf: any, index: number) => {
                                // 修复图片路径：确保从public目录正确加载
                                const imagePath = kf.framePath.startsWith('/')
                                  ? kf.framePath  // 已经是相对路径，直接使用
                                  : `/${kf.framePath}`;  // 添加前导斜杠

                                return (
                                  <div
                                    key={kf.id}
                                    className="relative group cursor-pointer"
                                    onMouseEnter={(e) => handleKeyframeMouseEnter(imagePath, e)}
                                    onMouseLeave={handleKeyframeMouseLeave}
                                    onMouseMove={handleKeyframeMouseMove}
                                  >
                                    {kf.exists ? (
                                      <>
                                        <img
                                          src={imagePath}
                                          alt={`帧 ${kf.frameNumber}`}
                                          className="w-full h-20 object-cover rounded border transition-transform group-hover:scale-105"
                                          onError={(e) => {
                                            // 图片加载失败时隐藏图片并显示占位符
                                            const img = e.target as HTMLImageElement;
                                            img.style.display = 'none';
                                            // 查找并显示占位符（通过类名）
                                            const parent = img.parentElement;
                                            if (parent) {
                                              const placeholder = parent.querySelector('.img-error-placeholder');
                                              if (placeholder) {
                                                (placeholder as HTMLElement).classList.remove('hidden');
                                              }
                                            }
                                          }}
                                        />
                                        {/* 图片加载失败的占位符（默认隐藏） */}
                                        <div className="hidden absolute inset-0 bg-gray-100 rounded border flex items-center justify-center text-xs text-gray-400 img-error-placeholder">
                                          加载失败
                                        </div>
                                        {/* Hover时显示的提示 */}
                                        <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity rounded flex items-center justify-center pointer-events-none">
                                          <span className="text-white text-xs">悬停查看大图</span>
                                        </div>
                                      </>
                                    ) : (
                                      <div className="w-full h-20 bg-gray-100 rounded border flex items-center justify-center text-xs text-gray-400">
                                        缺失
                                      </div>
                                    )}
                                    <div className="text-xs text-muted-foreground mt-1 text-center">
                                      {(kf.timestampMs / 1000).toFixed(1)}s
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                            {video.keyframes.count > 20 && (
                              <p className="text-xs text-muted-foreground mt-2">
                                显示前 20 帧，共 {video.keyframes.count} 帧（鼠标悬停可查看大图）
                              </p>
                            )}
                          </div>
                        )}

                        {/* ASR转录预览 */}
                        {video.asr.hasData && (
                          <div>
                            <h4 className="text-sm font-medium mb-2">
                              ASR转录 ({video.asr.language || '自动检测'})
                            </h4>
                            <div className="p-3 bg-slate-50 rounded text-sm max-h-40 overflow-y-auto">
                              <p className="whitespace-pre-wrap">{video.asr.textPreview}</p>
                            </div>
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(video.asr.fullText);
                                alert("已复制到剪贴板");
                              }}
                              className="text-xs text-orange-600 hover:underline mt-2"
                            >
                              复制完整文本
                            </button>
                          </div>
                        )}

                        {/* 无数据提示 */}
                        {!video.keyframes.hasData && !video.asr.hasData && (
                          <div className="text-center py-6 text-muted-foreground text-sm">
                            暂无关键帧和ASR数据
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </DialogContent>
      </Dialog>

      {/* 关键帧hover预览浮窗 */}
      {hoverPreview.show && (
        <div
          className="fixed z-[9999] bg-white rounded-lg shadow-2xl border-2 border-orange-500 overflow-hidden"
          style={{
            left: `${hoverPreview.x + 15}px`,
            top: `${hoverPreview.y + 15}px`,
            maxWidth: '400px',
            maxHeight: '400px',
          }}
        >
          <img
            src={hoverPreview.imageUrl}
            alt="关键帧预览"
            className="max-w-full max-h-[400px] object-contain"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        </div>
      )}
    </div>
  );
}
