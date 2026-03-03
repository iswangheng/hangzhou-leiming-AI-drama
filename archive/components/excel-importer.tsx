"use client";

/**
 * 杭州雷鸣 - Excel 导入组件
 *
 * 功能：
 * - 支持拖拽上传 Excel 文件
 * - 文件格式验证
 * - 上传进度显示
 * - 导入结果展示
 * - 示例模板下载
 */

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
import {
  FileSpreadsheet,
  Upload,
  X,
  CheckCircle,
  XCircle,
  Loader2,
  Download,
  AlertCircle,
} from "lucide-react";

interface ExcelImporterProps {
  projectId?: number;
  onImportComplete?: () => void;
}

interface ImportResult {
  success: boolean;
  message: string;
  data?: {
    successCount: number;
    errorCount: number;
    total: number;
  };
}

interface ValidationError {
  row: number;
  error: string;
}

export function ExcelImporter({ projectId, onImportComplete }: ExcelImporterProps) {
  const [open, setOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setSelectedFile(file);
      setImportResult(null);
      setValidationErrors([]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "text/csv": [".csv"],
    },
    maxFiles: 1,
  });

  const handleImport = async () => {
    if (!selectedFile || !projectId) return;

    setUploading(true);
    setUploadProgress(0);
    setImportResult(null);
    setValidationErrors([]);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("projectId", String(projectId));

      // 模拟上传进度
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const res = await fetch("/api/hangzhou-leiming/markings/import", {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      const result: ImportResult = await res.json();
      setImportResult(result);

      if (result.success) {
        // 延迟关闭对话框，让用户看到结果
        setTimeout(() => {
          setOpen(false);
          setSelectedFile(null);
          setUploadProgress(0);
          setImportResult(null);
          setValidationErrors([]);
          onImportComplete?.();
        }, 1500);
      }
    } catch (error) {
      console.error("导入Excel失败:", error);
      setImportResult({
        success: false,
        message: error instanceof Error ? error.message : "导入Excel失败",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const res = await fetch("/api/hangzhou-leiming/markings/example");
      if (!res.ok) throw new Error("下载失败");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "杭州雷鸣-标记数据示例.xlsx";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("下载示例文件失败:", error);
      alert("下载示例文件失败");
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2" disabled={uploading}>
          <FileSpreadsheet className="w-4 h-4" />
          导入标记数据
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>导入 Excel 标记数据</DialogTitle>
          <DialogDescription>
            支持 .xlsx、.xls、.csv 格式，文件大小不超过 10MB
          </DialogDescription>
        </DialogHeader>

        {/* 可滚动的内容区域 */}
        <div className="space-y-4 py-4 flex-1 overflow-y-auto pr-2">
          {/* 文件格式说明 */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2 text-blue-800">
              <FileSpreadsheet className="w-5 h-5" />
              <h4 className="font-semibold">Excel 文件格式要求</h4>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <p className="font-medium text-blue-900 mb-1">必需列：</p>
                <ul className="space-y-1 text-blue-700">
                  <li>• 集数：如"第1集"</li>
                  <li>• 时间点：格式为"00:35"或"01:20"</li>
                  <li>• 标记类型："高光点"或"钩子点"</li>
                </ul>
              </div>
              <div>
                <p className="font-medium text-blue-900 mb-1">可选列：</p>
                <ul className="space-y-1 text-blue-700">
                  <li>• 描述：如"高能冲突"</li>
                </ul>
              </div>
            </div>

            <div className="pt-2 border-t border-blue-200">
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadTemplate}
                className="cursor-pointer border-blue-300 text-blue-700 hover:bg-blue-100"
              >
                <Download className="w-4 h-4 mr-2" />
                下载示例 Excel 文件
              </Button>
            </div>
          </div>

          {/* 拖拽上传区域 */}
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
              transition-colors
              ${
                isDragActive
                  ? "border-primary bg-primary/10"
                  : "border-border hover:border-primary/50 hover:bg-muted/50"
              }
              ${uploading ? "opacity-50 pointer-events-none" : ""}
            `}
          >
            <input {...getInputProps()} />
            <FileSpreadsheet className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            {isDragActive ? (
              <p className="text-sm text-foreground">松开以上传文件...</p>
            ) : (
              <div>
                <p className="text-sm text-foreground mb-2">
                  拖拽 Excel 文件到这里，或点击选择文件
                </p>
                <p className="text-xs text-muted-foreground">
                  支持 .xlsx、.xls、.csv 格式
                </p>
              </div>
            )}
          </div>

          {/* 已选择的文件 */}
          {selectedFile && (
            <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
              <FileSpreadsheet className="w-5 h-5 text-muted-foreground flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
              {!uploading && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSelectedFile(null);
                    setImportResult(null);
                    setValidationErrors([]);
                  }}
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
          )}

          {/* 上传进度 */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">导入中...</span>
                <span className="font-medium text-foreground">{uploadProgress}%</span>
              </div>
              <Progress value={uploadProgress} className="h-2" />
            </div>
          )}

          {/* 导入结果 */}
          {importResult && !uploading && (
            <div
              className={`p-4 rounded-lg ${
                importResult.success
                  ? "bg-green-50 border border-green-200"
                  : "bg-red-50 border border-red-200"
              }`}
            >
              <div className="flex items-start gap-3">
                {importResult.success ? (
                  <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p
                    className={`text-sm font-medium ${
                      importResult.success ? "text-green-900" : "text-red-900"
                    }`}
                  >
                    {importResult.message}
                  </p>
                  {importResult.data && (
                    <div className="mt-2 text-sm text-green-800">
                      <p>
                        总计 {importResult.data.total} 条，成功{" "}
                        {importResult.data.successCount} 条，失败{" "}
                        {importResult.data.errorCount} 条
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 验证错误列表 */}
          {validationErrors.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-red-600">
                <AlertCircle className="w-4 h-4" />
                <p>发现 {validationErrors.length} 个错误</p>
              </div>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {validationErrors.map((error, index) => (
                  <div
                    key={index}
                    className="text-xs text-red-600 bg-red-50 p-2 rounded"
                  >
                    第 {error.row} 行：{error.error}
                  </div>
                ))}
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
              setSelectedFile(null);
              setUploadProgress(0);
              setImportResult(null);
              setValidationErrors([]);
            }}
            disabled={uploading}
          >
            取消
          </Button>
          <Button
            onClick={handleImport}
            disabled={!selectedFile || uploading}
          >
            {uploading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                导入中...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Upload className="w-4 h-4" />
                开始导入
              </span>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
