"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Upload, X, Film, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { uploadVideos } from "@/lib/upload/video";
import { parseEpisodeNumber, generateDisplayTitle } from "@/lib/utils/episode-parser";

interface UploadVideoDialogProps {
  projectId?: number;
  onUploadComplete?: () => void;
}

interface UploadResult {
  file: File;
  success: boolean;
  data?: unknown;
  message?: string;
}

export function UploadVideoDialog({ projectId, onUploadComplete }: UploadVideoDialogProps) {
  const [open, setOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([]);
  const [creatingRecords, setCreatingRecords] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setUploadedFiles(acceptedFiles);
      setUploadResults([]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "video/*": [".mp4", ".mov", ".avi", ".mkv", ".webm"],
    },
    multiple: true,
  });

  const handleUpload = async () => {
    if (uploadedFiles.length === 0) return;

    if (!projectId) {
      alert("缺少项目 ID");
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadResults([]);

    try {
      // 步骤 1: 上传文件
      const results = await uploadVideos(
        uploadedFiles,
        (current, total) => {
          const progress = Math.round((current / total) * 50); // 上传占 50%
          setUploadProgress(progress);
        }
      );

      setUploadResults(results);

      // 步骤 2: 为成功上传的文件创建数据库记录
      const successResults = results.filter((r) => r.success);

      if (successResults.length > 0) {
        setCreatingRecords(true);

        for (let i = 0; i < successResults.length; i++) {
          const result = successResults[i];
          if (result.data) {
            try {
              // 自动解析集数
              const episodeNumber = parseEpisodeNumber(result.data.filename);
              const displayTitle = episodeNumber
                ? generateDisplayTitle(episodeNumber, result.data.filename)
                : null;

              // 计算排序顺序：如果有集数则使用集数，否则使用文件名
              let sortOrder = 0;
              if (episodeNumber) {
                sortOrder = episodeNumber;
              } else {
                // 没有集数时，使用当前时间戳作为排序顺序
                sortOrder = Date.now();
              }

              const response = await fetch(`/api/projects/${projectId}/videos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  filename: result.data.filename,
                  filePath: result.data.filePath,
                  fileSize: result.data.fileSize,
                  durationMs: result.data.durationMs,
                  width: result.data.width,
                  height: result.data.height,
                  fps: result.data.fps,
                  // 自动解析的集数信息
                  episodeNumber: episodeNumber,
                  displayTitle: displayTitle,
                  sortOrder: sortOrder,
                }),
              });
              const data = await response.json();

              if (!data.success) {
                throw new Error(data.message || '创建视频记录失败');
              }

              // 更新进度（创建记录占 50%）
              const progress = 50 + Math.round(((i + 1) / successResults.length) * 50);
              setUploadProgress(progress);
            } catch (error) {
              console.error(`创建视频记录失败: ${result.file.name}`, error);
              // 更新结果为失败
              result.success = false;
              result.message = error instanceof Error ? error.message : "创建记录失败";
            }
          }
        }

        setCreatingRecords(false);
      }

      // 延迟关闭对话框，让用户看到结果
      setTimeout(() => {
        setOpen(false);
        setUploadedFiles([]);
        setUploadProgress(0);
        setUploadResults([]);
        setUploading(false);
        onUploadComplete?.();
      }, 1500);
    } catch (error) {
      console.error("上传失败:", error);
      alert(error instanceof Error ? error.message : "上传失败");
      setUploading(false);
      setCreatingRecords(false);
    }
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles(uploadedFiles.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2" disabled={uploading}>
          <Upload className="w-4 h-4" />
          上传视频
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>上传视频</DialogTitle>
          <DialogDescription>
            支持 MP4、MOV、AVI、MKV、WebM 格式，单文件最大 2GB
          </DialogDescription>
        </DialogHeader>

        {/* 可滚动的内容区域 */}
        <div className="space-y-4 py-4 flex-1 overflow-y-auto pr-2">
          {/* 拖拽上传区域 */}
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
              transition-base
              ${
                isDragActive
                  ? "border-primary bg-primary/10"
                  : "border-border hover:border-primary/50 hover:bg-muted/50"
              }
              ${uploading ? "opacity-50 pointer-events-none" : ""}
            `}
          >
            <input {...getInputProps()} />
            <Film className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            {isDragActive ? (
              <p className="text-sm text-foreground">松开以上传文件...</p>
            ) : (
              <div>
                <p className="text-sm text-foreground mb-2">
                  拖拽视频文件到这里，或点击选择文件
                </p>
                <p className="text-xs text-muted-foreground">
                  支持 MP4、MOV、AVI、MKV、WebM 格式
                </p>
              </div>
            )}
          </div>

          {/* 已选择的文件列表 */}
          {uploadedFiles.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">
                已选择 {uploadedFiles.length} 个文件
              </p>
              {uploadedFiles.map((file, index) => {
                const result = uploadResults[index];
                // 自动解析集数用于显示
                const episodeNumber = parseEpisodeNumber(file.name);
                const displayTitle = episodeNumber
                  ? generateDisplayTitle(episodeNumber, file.name)
                  : file.name;

                return (
                  <div
                    key={index}
                    className="flex items-center gap-3 p-3 bg-muted rounded-lg"
                  >
                    <Film className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">
                        {displayTitle}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{formatFileSize(file.size)}</span>
                        {episodeNumber && (
                          <>
                            <span>·</span>
                            <span className="text-primary font-medium">第{episodeNumber}集</span>
                          </>
                        )}
                      </div>
                      {/* 显示原始文件名 */}
                      {displayTitle !== file.name && (
                        <p className="text-xs text-muted-foreground truncate">
                          原文件名：{file.name}
                        </p>
                      )}
                    </div>
                    {result && (
                      <div className="flex-shrink-0">
                        {result.success ? (
                          <CheckCircle className="w-5 h-5 text-green-600" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-600" />
                        )}
                      </div>
                    )}
                    {!uploading && !result && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveFile(index)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* 上传进度 */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {creatingRecords ? "创建数据库记录..." : "上传中..."}
                </span>
                <span className="font-medium text-foreground">{uploadProgress}%</span>
              </div>
              <Progress value={uploadProgress} className="h-2" />
              {creatingRecords && (
                <p className="text-xs text-muted-foreground">
                  正在创建视频记录，请稍候...
                </p>
              )}
            </div>
          )}

          {/* 上传结果 */}
          {uploadResults.length > 0 && !uploading && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">上传结果</p>
              <div className="p-3 bg-muted rounded-lg text-sm">
                {uploadResults.filter((r) => r.success).length} 成功,
                {uploadResults.filter((r) => !r.success).length} 失败
              </div>
            </div>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="flex justify-end gap-3">
          <Button
            variant="outline"
            onClick={() => {
              setOpen(false);
              setUploadedFiles([]);
              setUploadProgress(0);
              setUploadResults([]);
            }}
            disabled={uploading}
          >
            取消
          </Button>
          <Button
            onClick={handleUpload}
            disabled={uploadedFiles.length === 0 || uploading}
          >
            {uploading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                {creatingRecords ? "保存中..." : "上传中..."}
              </span>
            ) : (
              "开始上传"
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
