"use client";

import { useEffect, useState } from "react";
import { Trash2, FileText, Clock, Loader2, Tag, Download, FileSpreadsheet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/confirm-dialog";

interface HLMarking {
  id: number;
  projectId: number;
  videoId: number;
  videoName: string;
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

interface MarkingsTabContentProps {
  projectId: number;
  projectName: string;
  onUpdate?: () => void;
}

interface ExcelFile {
  filename: string;
  uploadTime: number;
  uploadTimeFormatted: string;
  fileSize: number;
  fileSizeFormatted: string;
  downloadUrl: string;
}

export function MarkingsTabContent({ projectId, projectName, onUpdate }: MarkingsTabContentProps) {
  const [markings, setMarkings] = useState<HLMarking[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedMarking, setSelectedMarking] = useState<HLMarking | null>(null);
  const [excelFiles, setExcelFiles] = useState<ExcelFile[]>([]);
  const [loadingExcels, setLoadingExcels] = useState(false);
  const [deleteExcelDialogOpen, setDeleteExcelDialogOpen] = useState(false);
  const [selectedExcelFile, setSelectedExcelFile] = useState<ExcelFile | null>(null);

  useEffect(() => {
    loadMarkings();
    loadExcelFiles();
  }, [projectId]);

  const loadMarkings = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/hangzhou-leiming/markings?projectId=${projectId}`);
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

  const loadExcelFiles = async () => {
    try {
      setLoadingExcels(true);
      const res = await fetch(`/api/hangzhou-leiming/projects/${projectId}/excel-files`);
      const result = await res.json();
      if (result.success) {
        setExcelFiles(result.data.files || []);
      }
    } catch (error) {
      console.error("加载Excel文件失败:", error);
    } finally {
      setLoadingExcels(false);
    }
  };

  const handleDeleteExcelFile = async () => {
    if (!selectedExcelFile) return;

    try {
      const res = await fetch(selectedExcelFile.deleteUrl, {
        method: "DELETE",
      });

      const result = await res.json();

      if (result.success) {
        setDeleteExcelDialogOpen(false);
        setSelectedExcelFile(null);
        await loadExcelFiles(); // 重新加载文件列表
      } else {
        alert(`删除失败：${result.message}`);
      }
    } catch (error) {
      console.error("删除Excel文件失败:", error);
      alert("删除Excel文件失败，请稍后重试");
    }
  };

  const handleDelete = async () => {
    if (!selectedMarking) return;
    try {
      const res = await fetch(`/api/hangzhou-leiming/markings/${selectedMarking.id}`, { method: "DELETE" });
      if (res.ok) {
        setDeleteDialogOpen(false);
        loadMarkings();
        onUpdate?.();
      }
    } catch (error) {
      alert("删除失败");
    }
  };

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">标记管理</h2>
          <p className="text-muted-foreground text-sm mt-1">{projectName} - 人工标记数据（用于AI训练）</p>
        </div>
      </div>

      {/* 已上传的Excel文件 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-green-600" />
            已上传的Excel文件
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loadingExcels ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-orange-600" />
            </div>
          ) : excelFiles.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              暂无已上传的Excel文件
            </div>
          ) : (
            <div className="space-y-2">
              {excelFiles.map((file) => (
                <div
                  key={file.filename}
                  className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <FileSpreadsheet className="w-5 h-5 text-green-600" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{file.originalName || file.filename}</div>
                      <div className="text-xs text-muted-foreground">
                        {file.uploadTimeFormatted} · {file.fileSizeFormatted}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(file.downloadUrl, '_blank')}
                      className="cursor-pointer"
                    >
                      <Download className="w-4 h-4 mr-1" />
                      下载
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setSelectedExcelFile(file);
                        setDeleteExcelDialogOpen(true);
                      }}
                      className="cursor-pointer hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-orange-600" /></div>
      ) : markings.length === 0 ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">暂无标记数据</CardContent></Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {markings.map((marking) => (
            <Card key={marking.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Tag className="w-4 h-4" />
                      {marking.subType || marking.description || "未命名"}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground mt-1">{marking.videoName}</p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => { setSelectedMarking(marking); setDeleteDialogOpen(true); }}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="w-4 h-4 text-muted-foreground" />
                  <span className="text-muted-foreground">时间点：</span>
                  <span>{marking.timestamp}（{formatTime(marking.seconds)}）</span>
                </div>
                {marking.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">{marking.description}</p>
                )}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`px-2 py-1 rounded-full text-xs ${marking.type === "高光点" ? "bg-orange-100 text-orange-800" : "bg-blue-100 text-blue-800"}`}>
                    {marking.type}
                  </span>
                  {marking.score && <span className="text-xs text-muted-foreground">得分: {marking.score}</span>}
                  {marking.aiEnhanced && (
                    <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
                      AI增强
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <ConfirmDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen} title="确认删除标记" description={`确定要删除此标记吗？`} confirmText="确认删除" onConfirm={handleDelete} variant="destructive" />

      {/* 删除Excel文件确认对话框 */}
      <ConfirmDialog
        open={deleteExcelDialogOpen}
        onOpenChange={setDeleteExcelDialogOpen}
        title="确认删除Excel文件"
        description={`确定要删除文件「${selectedExcelFile?.originalName || selectedExcelFile?.filename}」吗？此操作无法撤销。`}
        confirmText="确认删除"
        onConfirm={handleDeleteExcelFile}
        variant="destructive"
      />
    </div>
  );
}
