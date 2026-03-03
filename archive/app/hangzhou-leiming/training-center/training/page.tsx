"use client";

/**
 * 杭州雷鸣 - 训练中心：执行训练页面
 *
 * 功能：
 * - 创建新项目（或选择现有项目）
 * - 上传多集视频
 * - 上传 Excel 标记文件
 * - 开始训练
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Plus,
  Upload,
  FileSpreadsheet,
  Video,
  Play,
  CheckCircle,
  Loader2,
  Download,
  Trash2,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { HangzhouLeimingLayout } from "@/components/hangzhou-leiming-layout";
import { TrainingLogs } from "@/components/training-logs";

interface Project {
  id: number;
  name: string;
  description: string | null;
  videoCount: number;
  markingCount: number;
  createdAt: Date;
}

export default function TrainingPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1); // 1:创建项目 2:上传视频 3:上传Excel 4:训练完成
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [allProjects, setAllProjects] = useState<Project[]>([]);

  // 步骤1：创建项目
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [projectFormData, setProjectFormData] = useState({
    name: "",
    description: "",
  });

  // 加载项目已有的视频
  const [existingVideos, setExistingVideos] = useState<any[]>([]);

  // 加载所有项目
  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const res = await fetch("/api/hangzhou-leiming/projects");
      const result = await res.json();
      if (result.success) {
        setAllProjects(result.data || []);
      }
    } catch (error) {
      console.error("加载项目列表失败:", error);
    }
  };

  // 步骤2：上传视频
  const [uploadedVideos, setUploadedVideos] = useState<any[]>([]);
  const [videoUploading, setVideoUploading] = useState(false);

  // 步骤3：上传Excel
  const [uploadedExcel, setUploadedExcel] = useState<File | null>(null);
  const [excelUploading, setExcelUploading] = useState(false);
  const [existingExcelFiles, setExistingExcelFiles] = useState<any[]>([]);
  const [loadingExcels, setLoadingExcels] = useState(false);

  // 步骤4：训练
  const [training, setTraining] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState(0);

  // 选择现有项目
  const handleSelectProject = async (project: Project) => {
    setCurrentProject(project);

    // 加载该项目的已有视频
    try {
      const res = await fetch(`/api/hangzhou-leiming/videos?projectId=${project.id}`);
      const result = await res.json();
      if (result.success) {
        setExistingVideos(result.data || []);
        setUploadedVideos(result.data || []);
      }
    } catch (error) {
      console.error("加载项目视频失败:", error);
    }

    // 加载该项目的已有Excel文件
    await loadExcelFiles(project.id);

    setStep(2); // 进入步骤2：上传视频
  };

  // 加载Excel文件列表
  const loadExcelFiles = async (projectId: number) => {
    try {
      setLoadingExcels(true);
      const res = await fetch(`/api/hangzhou-leiming/projects/${projectId}/excel-files`);
      const result = await res.json();
      if (result.success) {
        const files = result.data.files || [];
        setExistingExcelFiles(files);
        return files.length; // 返回文件数量
      }
      return 0;
    } catch (error) {
      console.error("加载Excel文件失败:", error);
      return 0;
    } finally {
      setLoadingExcels(false);
    }
  };

  // 删除Excel文件
  const handleDeleteExcel = async (filename: string) => {
    if (!currentProject) return;

    if (!confirm("确定要删除这个Excel文件吗？")) return;

    try {
      const res = await fetch(`/api/hangzhou-leiming/projects/${currentProject.id}/excel-files/${filename}`, {
        method: "DELETE",
      });

      const result = await res.json();

      if (result.success) {
        // 重新加载Excel文件列表
        await loadExcelFiles(currentProject.id);
      } else {
        alert(`删除失败：${result.message}`);
      }
    } catch (error) {
      console.error("删除Excel文件失败:", error);
      alert("删除Excel文件失败，请稍后重试");
    }
  };

  // 创建项目
  const handleCreateProject = async () => {
    try {
      const res = await fetch("/api/hangzhou-leiming/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(projectFormData),
      });

      const result = await res.json();

      if (result.success) {
        setCurrentProject(result.data);
        setCreateDialogOpen(false);
        // 重新加载项目列表
        await loadProjects();
        setStep(2); // 进入步骤2：上传视频
      } else {
        alert(`创建失败：${result.message}`);
      }
    } catch (error) {
      console.error("创建项目失败:", error);
      alert("创建项目失败，请稍后重试");
    }
  };

  // 上传视频
  const handleVideoUpload = async (files: FileList | null) => {
    if (!files || !currentProject) return;

    setVideoUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append("file", file);
        formData.append("projectId", currentProject.id.toString());

        const res = await fetch("/api/hangzhou-leiming/videos", {
          method: "POST",
          body: formData,
        });

        const result = await res.json();

        if (result.success) {
          // 存储服务器返回的完整视频数据，而不是 File 对象
          setUploadedVideos((prev) => [...prev, result.data]);
        } else {
          alert(`上传 ${file.name} 失败：${result.message}`);
        }
      }

      setVideoUploading(false);
    } catch (error) {
      console.error("上传视频失败:", error);
      alert("上传视频失败，请稍后重试");
      setVideoUploading(false);
    }
  };

  // 上传Excel
  const handleExcelUpload = async (file: File | null) => {
    if (!file || !currentProject) return;

    setExcelUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("projectId", currentProject.id.toString());

      const res = await fetch("/api/hangzhou-leiming/markings/import", {
        method: "POST",
        body: formData,
      });

      const result = await res.json();

      if (result.success) {
        setUploadedExcel(file);
        setExcelUploading(false);

        // 重新加载Excel文件列表并获取数量
        const fileCount = await loadExcelFiles(currentProject.id);

        // 如果上传成功，自动进入下一步
        if (fileCount > 0) {
          setStep(4);
        }
      } else {
        alert(`上传失败：${result.message}`);
        setExcelUploading(false);
      }
    } catch (error) {
      console.error("上传Excel失败:", error);
      alert("上传Excel失败，请稍后重试");
      setExcelUploading(false);
    }
  };

  // 开始训练
  const handleStartTraining = async () => {
    if (!currentProject) return;

    setTraining(true);
    setTrainingProgress(0);

    try {
      const res = await fetch("/api/hangzhou-leiming/training-center/training", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectIds: [currentProject.id],
        }),
      });

      const result = await res.json();

      if (result.success) {
        const trainingId = result.data.trainingId;

        // 保存trainingId供日志组件使用
        (window as any).currentTrainingId = trainingId;

        // 轮询获取训练进度
        const pollInterval = setInterval(async () => {
          try {
            const pollRes = await fetch("/api/hangzhou-leiming/training-center/history");
            const pollResult = await pollRes.json();

            if (pollResult.success) {
              const trainingRecord = pollResult.data.find((r: any) => r.id === trainingId);

              if (trainingRecord) {
                setTrainingProgress(trainingRecord.progress || 0);

                // 训练完成或失败
                if (trainingRecord.status === "completed") {
                  clearInterval(pollInterval);
                  setTraining(false);
                  setTrainingProgress(100);
                } else if (trainingRecord.status === "failed") {
                  clearInterval(pollInterval);
                  setTraining(false);
                  alert(`训练失败：${trainingRecord.errorMessage || "未知错误"}`);
                }
              }
            }
          } catch (error) {
            console.error("获取训练进度失败:", error);
          }
        }, 2000); // 每2秒轮询一次

        // 保存定时器ID，用于清理（可选）
        (window as any).trainingPollInterval = pollInterval;
      } else {
        alert(`训练失败：${result.message}`);
        setTraining(false);
      }
    } catch (error) {
      console.error("训练失败:", error);
      alert("训练失败，请稍后重试");
      setTraining(false);
    }
  };

  return (
    <HangzhouLeimingLayout>
      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-3xl mx-auto">
          {/* 步骤指示器 */}
          <div className="flex items-center justify-center mb-8">
            <div className="flex items-center">
              <StepNumber
                number={1}
                active={step === 1}
                completed={step > 1}
                onClick={() => setStep(1)}
              />
              <div className="w-16 h-1 bg-gray-200 mx-2" />
              <StepNumber
                number={2}
                active={step === 2}
                completed={step > 2}
                onClick={() => currentProject && setStep(2)}
              />
              <div className="w-16 h-1 bg-gray-200 mx-2" />
              <StepNumber
                number={3}
                active={step === 3}
                completed={step > 3}
                onClick={() => currentProject && setStep(3)}
              />
              <div className="w-16 h-1 bg-gray-200 mx-2" />
              <StepNumber
                number={4}
                active={step === 4}
                completed={step > 4}
                onClick={() => currentProject && setStep(4)}
              />
            </div>
          </div>

          {/* 步骤1：创建/选择项目 */}
          {step === 1 && (
            <Card>
              <CardHeader>
                <CardTitle>步骤 1：选择或创建项目</CardTitle>
                <CardDescription>
                  选择现有项目进行训练，或创建新的短剧项目
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* 现有项目列表 */}
                {allProjects.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="font-semibold text-sm">选择现有项目</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {allProjects.map((project) => (
                        <div
                          key={project.id}
                          className="border rounded-lg p-4 hover:bg-orange-50 hover:border-orange-300 cursor-pointer transition-colors"
                          onClick={() => handleSelectProject(project)}
                        >
                          <h4 className="font-medium">{project.name}</h4>
                          <p className="text-xs text-muted-foreground mt-1">
                            {project.videoCount || 0} 个视频 · {project.markingCount || 0} 个标记
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 分隔线 */}
                {allProjects.length > 0 && (
                  <div className="flex items-center gap-4">
                    <div className="flex-1 h-px bg-gray-200" />
                    <span className="text-sm text-muted-foreground">或创建新项目</span>
                    <div className="flex-1 h-px bg-gray-200" />
                  </div>
                )}

                {/* 创建新项目表单 */}
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">项目名称 *</Label>
                    <Input
                      id="name"
                      placeholder="例如：霸道总裁爱上我"
                      value={projectFormData.name}
                      onChange={(e) =>
                        setProjectFormData({ ...projectFormData, name: e.target.value })
                      }
                      className="cursor-pointer"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">项目描述</Label>
                    <Textarea
                      id="description"
                      placeholder="简要描述这部短剧..."
                      value={projectFormData.description}
                      onChange={(e) =>
                        setProjectFormData({
                          ...projectFormData,
                          description: e.target.value,
                        })
                      }
                      rows={3}
                      className="cursor-pointer"
                    />
                  </div>
                  <Button
                    onClick={() => setCreateDialogOpen(true)}
                    disabled={!projectFormData.name.trim()}
                    className="w-full cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    创建项目
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 步骤2：上传视频 */}
          {step === 2 && currentProject && (
            <Card>
              <CardHeader>
                <CardTitle>步骤 2：上传视频</CardTitle>
                <CardDescription>
                  上传这部短剧的多集视频（通常前10集）
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-center py-8">
                  <div className="text-6xl mb-4">📹</div>
                  <h3 className="text-xl font-semibold mb-2">上传视频文件</h3>
                  <p className="text-muted-foreground mb-6">
                    支持批量上传，通常上传前10集
                  </p>
                  <Button
                    onClick={() => document.getElementById('video-upload')?.click()}
                    className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
                    disabled={videoUploading}
                  >
                    {videoUploading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        上传中...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 mr-2" />
                        选择视频文件
                      </>
                    )}
                  </Button>
                  <input
                    id="video-upload"
                    type="file"
                    accept="video/*"
                    multiple
                    className="hidden"
                    onChange={(e) => handleVideoUpload(e.target.files)}
                  />
                </div>

                {/* 显示已有或新上传的视频 */}
                {uploadedVideos.length > 0 && (
                  <div className="border rounded-lg p-4">
                    <h4 className="font-semibold mb-3">已上传视频 ({uploadedVideos.length})</h4>
                    <div className="space-y-2">
                      {uploadedVideos.map((video, index) => (
                        <div key={index} className="flex items-center gap-3 p-2 bg-slate-50 rounded">
                          <Video className="w-5 h-5 text-blue-600" />
                          <div className="flex-1">
                            <div className="text-sm font-medium">{video.displayTitle || video.filename}</div>
                            <div className="text-xs text-muted-foreground">
                              {video.episodeNumber} · {(video.durationMs / 1000).toFixed(1)}秒
                            </div>
                          </div>
                          <CheckCircle className="w-5 h-5 text-green-600" />
                        </div>
                      ))}
                    </div>
                    <Button
                      onClick={() => setStep(3)}
                      className="w-full mt-4 cursor-pointer"
                    >
                      下一步：上传Excel标记文件
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* 步骤3：上传Excel */}
          {step === 3 && currentProject && (
            <Card>
              <CardHeader>
                <CardTitle>步骤 3：上传Excel标记文件</CardTitle>
                <CardDescription>
                  上传人工标记的Excel文件，包含高光点和钩子点的时间戳
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Excel格式说明 */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
                  <div className="flex items-center gap-2 text-blue-800">
                    <FileSpreadsheet className="w-5 h-5" />
                    <h4 className="font-semibold">Excel文件格式要求</h4>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="font-medium text-blue-900 mb-1">必需列：</p>
                      <ul className="space-y-1 text-blue-700">
                        <li>• <strong>集数</strong>：如"第1集"（必须与上传视频时设置的集数一致）</li>
                        <li>• <strong>时间点</strong>：格式为"00:35"或"01:20"</li>
                        <li>• <strong>标记类型</strong>：固定值"高光点"或"钩子点"</li>
                      </ul>
                    </div>
                    <div>
                      <p className="font-medium text-blue-900 mb-1">可选列：</p>
                      <ul className="space-y-1 text-blue-700">
                        <li>• <strong>描述</strong>：如"高能冲突"、"悬念结尾"</li>
                      </ul>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-blue-200">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.location.href = '/api/hangzhou-leiming/markings/example'}
                      className="cursor-pointer border-blue-300 text-blue-700 hover:bg-blue-100"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      下载示例Excel文件
                    </Button>
                  </div>
                </div>

                <div className="text-center py-8">
                  <div className="text-6xl mb-4">📊</div>
                  <h3 className="text-xl font-semibold mb-2">上传Excel标记文件</h3>
                  <p className="text-muted-foreground mb-6">
                    上传包含时间戳、类型、描述等信息的Excel文件
                  </p>
                  <Button
                    onClick={() => document.getElementById('excel-upload')?.click()}
                    className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
                    disabled={excelUploading}
                  >
                    {excelUploading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        上传中...
                      </>
                    ) : (
                      <>
                        <FileSpreadsheet className="w-4 h-4 mr-2" />
                        选择Excel文件
                      </>
                    )}
                  </Button>
                  <input
                    id="excel-upload"
                    type="file"
                    accept=".xlsx,.xls"
                    className="hidden"
                    onChange={(e) => handleExcelUpload(e.target.files?.[0] || null)}
                  />
                </div>

                {/* 已上传的Excel文件列表 */}
                {existingExcelFiles.length > 0 && (
                  <div className="border rounded-lg p-4">
                    <h4 className="font-semibold mb-3">已上传的Excel文件 ({existingExcelFiles.length})</h4>
                    <div className="space-y-2">
                      {existingExcelFiles.map((file) => (
                        <div key={file.filename} className="flex items-center gap-3 p-2 bg-slate-50 rounded">
                          <FileSpreadsheet className="w-5 h-5 text-green-600" />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate">{file.originalName || file.filename}</div>
                            <div className="text-xs text-muted-foreground">
                              {file.uploadTimeFormatted} · {file.fileSizeFormatted}
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.open(file.downloadUrl, '_blank')}
                            className="cursor-pointer"
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteExcel(file.filename)}
                            className="cursor-pointer hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                    <Button
                      onClick={() => setStep(4)}
                      className="w-full mt-4 cursor-pointer"
                    >
                      下一步：开始训练
                    </Button>
                  </div>
                )}

                {uploadedExcel && (
                  <div className="border rounded-lg p-4">
                    <div className="flex items-center gap-3">
                      <FileSpreadsheet className="w-8 h-8 text-green-600" />
                      <div className="flex-1">
                        <h4 className="font-semibold">{uploadedExcel.name}</h4>
                        <p className="text-sm text-muted-foreground">
                          {(uploadedExcel.size / 1024).toFixed(2)} KB
                        </p>
                      </div>
                      <CheckCircle className="w-6 h-6 text-green-600" />
                    </div>
                    <Button
                      onClick={() => setStep(4)}
                      className="w-full mt-4 cursor-pointer"
                    >
                      下一步：开始训练
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* 步骤4：训练 */}
          {step === 4 && currentProject && (
            <Card>
              <CardHeader>
                <CardTitle>步骤 4：开始训练</CardTitle>
                <CardDescription>
                  基于上传的视频和标记文件，训练全局剪辑技能
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="border rounded-lg p-4 space-y-4">
                  <div>
                    <h4 className="font-semibold mb-2">项目信息</h4>
                    <p className="text-sm text-muted-foreground">
                      {currentProject.name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {currentProject.description || "暂无描述"}
                    </p>
                  </div>

                  <div>
                    <h4 className="font-semibold mb-2">训练数据</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">视频数量：</span>
                        <span className="font-medium">{uploadedVideos.length} 个</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">标记文件：</span>
                        <span className="font-medium">
                          {existingExcelFiles.length > 0 ? `已上传 (${existingExcelFiles.length}个)` : "未上传"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* 显示已上传的Excel文件 */}
                  {existingExcelFiles.length > 0 && (
                    <div className="border rounded-lg p-3 bg-slate-50">
                      <h5 className="text-sm font-medium mb-2">已上传的标记文件：</h5>
                      <div className="space-y-1">
                        {existingExcelFiles.map((file) => (
                          <div key={file.filename} className="text-xs flex items-center gap-2">
                            <FileSpreadsheet className="w-3 h-3 text-green-600" />
                            <span className="truncate flex-1">{file.originalName || file.filename}</span>
                            <span className="text-muted-foreground">{file.fileSizeFormatted}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 开始训练按钮 */}
                  {!training && trainingProgress === 0 && (
                    <div className="space-y-2">
                      <Button
                        onClick={handleStartTraining}
                        disabled={uploadedVideos.length === 0 || existingExcelFiles.length === 0}
                        className="w-full cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Play className="w-4 h-4 mr-2" />
                        开始训练
                      </Button>
                      {uploadedVideos.length === 0 && (
                        <p className="text-xs text-orange-600 text-center">⚠️ 请先上传视频</p>
                      )}
                      {existingExcelFiles.length === 0 && (
                        <p className="text-xs text-orange-600 text-center">⚠️ 请先上传标记文件</p>
                      )}
                    </div>
                  )}

                  {training && (
                    <div className="space-y-4">
                      {/* 进度条 */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span>训练进度</span>
                          <span className="font-medium">{trainingProgress}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-orange-500 to-red-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${trainingProgress}%` }}
                          />
                        </div>
                      </div>

                      {/* 实时日志 */}
                      <TrainingLogs
                        trainingId={(window as any).currentTrainingId || null}
                        isTraining={training}
                      />

                      {/* 完成提示 */}
                      {trainingProgress === 100 && (
                        <div className="text-center py-4">
                          <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-2" />
                          <h3 className="text-lg font-semibold mb-2">训练完成！</h3>
                          <p className="text-muted-foreground mb-4">
                            全局技能文件已更新
                          </p>
                          <Link href="/hangzhou-leiming/training-center">
                            <Button className="cursor-pointer">
                              返回训练中心
                            </Button>
                          </Link>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* 创建项目确认对话框 */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>确认创建项目</DialogTitle>
            <DialogDescription>
              确定要创建项目「{projectFormData.name}」吗？
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateDialogOpen(false)}
              className="cursor-pointer"
            >
              取消
            </Button>
            <Button
              onClick={handleCreateProject}
              className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
            >
              确认创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </HangzhouLeimingLayout>
  );
}

// 步骤编号组件
function StepNumber({
  number,
  active,
  completed,
  onClick,
}: {
  number: number;
  active: boolean;
  completed: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
        completed
          ? "bg-green-600 text-white cursor-pointer hover:bg-green-700"
          : active
          ? "bg-orange-600 text-white"
          : "bg-gray-200 text-gray-600 cursor-pointer hover:bg-gray-300"
      }`}
      onClick={onClick}
    >
      {completed ? <CheckCircle className="w-5 h-5" /> : number}
    </div>
  );
}
