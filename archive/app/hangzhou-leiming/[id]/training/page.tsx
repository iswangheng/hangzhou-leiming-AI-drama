"use client";

/**
 * 杭州雷鸣 - 训练中心页面
 *
 * 功能：
 * - 上传历史视频
 * - 导入Excel标记数据
 * - AI学习生成技能文件
 * - 查看和编辑技能文件
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Upload,
  FileSpreadsheet,
  Brain,
  FileText,
  Video,
  Trash2,
  CheckCircle,
  XCircle,
  Loader2,
  Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfirmDialog } from "@/components/confirm-dialog";

interface HLVideo {
  id: number;
  filename: string;
  episodeNumber: string;
  displayTitle: string;
  fileSize: number;
  durationMs: number;
  status: string;
  createdAt: Date;
}

interface HLMarking {
  id: number;
  videoId: number;
  timestamp: string;
  type: string;
  description: string;
}

interface HLSkill {
  id: number;
  name: string;
  content: string;
  generatedFrom: string;
  totalMarkings: number;
  createdAt: Date;
}

export default function TrainingCenterPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [projectName, setProjectName] = useState<string>("");

  // 数据状态
  const [videos, setVideos] = useState<HLVideo[]>([]);
  const [markings, setMarkings] = useState<HLMarking[]>([]);
  const [skills, setSkills] = useState<HLSkill[]>([]);

  // 上传状态
  const [uploadingVideo, setUploadingVideo] = useState(false);
  const [uploadingExcel, setUploadingExcel] = useState(false);
  const [learning, setLearning] = useState(false);

  // 对话框状态
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<HLVideo | null>(null);

  // 加载projectId
  useEffect(() => {
    params.then((resolvedParams) => {
      setProjectId(parseInt(resolvedParams.id));
    });
  }, [params]);

  // 加载数据
  useEffect(() => {
    if (projectId) {
      loadVideos();
      loadMarkings();
      loadSkills();
    }
  }, [projectId]);

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

  const loadMarkings = async () => {
    if (!projectId) return;

    try {
      const res = await fetch(
        `/api/hangzhou-leiming/markings?projectId=${projectId}`
      );
      const result = await res.json();
      if (result.success) {
        setMarkings(result.data || []);
      }
    } catch (error) {
      console.error("加载标记失败:", error);
    }
  };

  const loadSkills = async () => {
    if (!projectId) return;

    try {
      const res = await fetch(
        `/api/hangzhou-leiming/skills?projectId=${projectId}`
      );
      const result = await res.json();
      if (result.success) {
        setSkills(result.data || []);
      }
    } catch (error) {
      console.error("加载技能失败:", error);
    }
  };

  // 上传视频
  const handleUploadVideo = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (!e.target.files || e.target.files.length === 0 || !projectId) return;

    try {
      setUploadingVideo(true);
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append("file", file);
      formData.append("projectId", String(projectId));
      formData.append("episodeNumber", `第${videos.length + 1}集`);
      formData.append("displayTitle", file.name);

      const res = await fetch("/api/hangzhou-leiming/videos", {
        method: "POST",
        body: formData,
      });

      const result = await res.json();

      if (result.success) {
        alert("视频上传成功！");
        await loadVideos();
      } else {
        alert(`上传失败：${result.message}`);
      }
    } catch (error) {
      console.error("上传视频失败:", error);
      alert("上传视频失败");
    } finally {
      setUploadingVideo(false);
      e.target.value = "";
    }
  };

  // 导入Excel
  const handleImportExcel = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (!e.target.files || e.target.files.length === 0 || !projectId) return;

    try {
      setUploadingExcel(true);
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append("file", file);
      formData.append("projectId", String(projectId));

      const res = await fetch("/api/hangzhou-leiming/markings/import", {
        method: "POST",
        body: formData,
      });

      const result = await res.json();

      if (result.success) {
        alert(result.message);
        await loadMarkings();
      } else {
        alert(`导入失败：${result.message}`);
      }
    } catch (error) {
      console.error("导入Excel失败:", error);
      alert("导入Excel失败");
    } finally {
      setUploadingExcel(false);
      e.target.value = "";
    }
  };

  // 开始AI学习
  const handleStartLearning = async () => {
    if (!projectId) return;

    if (videos.length === 0) {
      alert("请先上传视频");
      return;
    }

    if (markings.length === 0) {
      alert("请先导入Excel标记数据");
      return;
    }

    try {
      setLearning(true);
      const res = await fetch(
        `/api/hangzhou-leiming/projects/${projectId}/learn`,
        {
          method: "POST",
        }
      );

      const result = await res.json();

      if (result.success) {
        alert("AI学习已启动，请稍候...");
        await loadSkills();
      } else {
        alert(`启动失败：${result.message}`);
      }
    } catch (error) {
      console.error("启动AI学习失败:", error);
      alert("启动AI学习失败");
    } finally {
      setLearning(false);
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
      alert("删除视频失败");
    }
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  };

  // 等待projectId
  if (projectId === null) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <div className="border-b bg-white/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.back()}
              className="cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回
            </Button>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
                训练中心
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                上传历史数据，让 AI 学习剪辑手法
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <Tabs defaultValue="upload" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 lg:w-[600px]">
            <TabsTrigger value="upload" className="cursor-pointer">
              <Upload className="w-4 h-4 mr-2" />
              数据上传
            </TabsTrigger>
            <TabsTrigger value="learning" className="cursor-pointer">
              <Brain className="w-4 h-4 mr-2" />
              AI学习
            </TabsTrigger>
            <TabsTrigger value="skills" className="cursor-pointer">
              <FileText className="w-4 h-4 mr-2" />
              技能文件
            </TabsTrigger>
          </TabsList>

          {/* 数据上传标签页 */}
          <TabsContent value="upload" className="space-y-6">
            {/* 视频上传 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Video className="w-5 h-5" />
                  上传历史视频
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">
                      支持 MP4, MOV, AVI, MKV 格式，最大 500MB
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    disabled={uploadingVideo}
                    onClick={() => document.getElementById('video-upload-training')?.click()}
                    className="cursor-pointer"
                  >
                    {uploadingVideo ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        上传中...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 mr-2" />
                        选择视频
                      </>
                    )}
                  </Button>
                  <Input
                    id="video-upload-training"
                    type="file"
                    accept="video/*"
                    className="hidden"
                    onChange={handleUploadVideo}
                    disabled={uploadingVideo}
                  />
                </div>

                {/* 视频列表 */}
                {videos.length > 0 && (
                  <div className="space-y-2">
                    {videos.map((video) => (
                      <div
                        key={video.id}
                        className="flex items-center justify-between p-3 bg-muted rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <CheckCircle className="w-5 h-5 text-green-600" />
                          <div>
                            <p className="font-medium">{video.filename}</p>
                            <p className="text-xs text-muted-foreground">
                              {video.episodeNumber} · {formatFileSize(video.fileSize)}
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="cursor-pointer hover:text-red-600"
                          onClick={() => {
                            setSelectedVideo(video);
                            setDeleteDialogOpen(true);
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Excel导入 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5" />
                  导入Excel标记数据
                </CardTitle>
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
                        <li>• <strong>集数</strong>：如"第1集"</li>
                        <li>• <strong>时间点</strong>：格式为"00:35"或"01:20"</li>
                        <li>• <strong>标记类型</strong>："高光点"或"钩子点"</li>
                      </ul>
                    </div>
                    <div>
                      <p className="font-medium text-blue-900 mb-1">可选列：</p>
                      <ul className="space-y-1 text-blue-700">
                        <li>• <strong>描述</strong>：如"高能冲突"</li>
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

                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">
                      已导入 {markings.length} 条标记数据
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    disabled={uploadingExcel}
                    onClick={() => document.getElementById('excel-upload-training')?.click()}
                    className="cursor-pointer"
                  >
                    {uploadingExcel ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        导入中...
                      </>
                    ) : (
                      <>
                        <FileSpreadsheet className="w-4 h-4 mr-2" />
                        选择Excel
                      </>
                    )}
                  </Button>
                  <Input
                    id="excel-upload-training"
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    className="hidden"
                    onChange={handleImportExcel}
                    disabled={uploadingExcel}
                  />
                </div>

                {/* 标记数据预览 */}
                {markings.length > 0 && (
                  <div className="max-h-60 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-background">
                        <tr className="border-b">
                          <th className="p-2 text-left">集数</th>
                          <th className="p-2 text-left">时间点</th>
                          <th className="p-2 text-left">类型</th>
                          <th className="p-2 text-left">描述</th>
                        </tr>
                      </thead>
                      <tbody>
                        {markings.slice(0, 20).map((marking) => (
                          <tr key={marking.id} className="border-b">
                            <td className="p-2">{marking.videoId}</td>
                            <td className="p-2">{marking.timestamp}</td>
                            <td className="p-2">
                              <span
                                className={`px-2 py-1 rounded-full text-xs ${
                                  marking.type === "高光点"
                                    ? "bg-blue-100 text-blue-800"
                                    : "bg-orange-100 text-orange-800"
                                }`}
                              >
                                {marking.type}
                              </span>
                            </td>
                            <td className="p-2">{marking.description || "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {markings.length > 20 && (
                      <p className="text-center text-muted-foreground py-2">
                        ...还有 {markings.length - 20} 条数据
                      </p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* AI学习标签页 */}
          <TabsContent value="learning" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>AI 学习配置</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center p-6 bg-muted rounded-lg">
                    <div className="text-4xl font-bold text-orange-600">
                      {videos.length}
                    </div>
                    <div className="text-sm text-muted-foreground mt-2">
                      已上传视频
                    </div>
                  </div>
                  <div className="text-center p-6 bg-muted rounded-lg">
                    <div className="text-4xl font-bold text-blue-600">
                      {markings.length}
                    </div>
                    <div className="text-sm text-muted-foreground mt-2">
                      标记数据
                    </div>
                  </div>
                  <div className="text-center p-6 bg-muted rounded-lg">
                    <div className="text-4xl font-bold text-green-600">
                      {skills.length}
                    </div>
                    <div className="text-sm text-muted-foreground mt-2">
                      已生成技能
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle
                      className={`w-5 h-5 mt-0.5 ${
                        videos.length > 0 ? "text-green-600" : "text-gray-400"
                      }`}
                    />
                    <div>
                      <p className="font-medium">上传历史视频</p>
                      <p className="text-sm text-muted-foreground">
                        {videos.length > 0
                          ? `已上传 ${videos.length} 个视频`
                          : "请先上传视频"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <CheckCircle
                      className={`w-5 h-5 mt-0.5 ${
                        markings.length > 0 ? "text-green-600" : "text-gray-400"
                      }`}
                    />
                    <div>
                      <p className="font-medium">导入Excel标记数据</p>
                      <p className="text-sm text-muted-foreground">
                        {markings.length > 0
                          ? `已导入 ${markings.length} 条标记`
                          : "请先导入标记数据"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Brain className="w-5 h-5 mt-0.5 text-blue-600" />
                    <div>
                      <p className="font-medium">AI 分析学习</p>
                      <p className="text-sm text-muted-foreground">
                        自动识别模式，生成技能文件
                      </p>
                    </div>
                  </div>
                </div>

                <Button
                  onClick={handleStartLearning}
                  disabled={learning || videos.length === 0 || markings.length === 0}
                  className="w-full cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
                >
                  {learning ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      学习中...
                    </>
                  ) : (
                    <>
                      <Brain className="w-4 h-4 mr-2" />
                      开始 AI 学习
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 技能文件标签页 */}
          <TabsContent value="skills" className="space-y-6">
            {skills.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <FileText className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold mb-2">暂无技能文件</h3>
                  <p className="text-muted-foreground mb-6">
                    完成 AI 学习后，技能文件将在这里显示
                  </p>
                </CardContent>
              </Card>
            ) : (
              skills.map((skill) => (
                <Card key={skill.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>{skill.name}</CardTitle>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <FileText className="w-4 h-4" />
                        {skill.totalMarkings} 条标记
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="prose prose-sm max-w-none">
                      <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg">
                        {skill.content}
                      </pre>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>
        </Tabs>
      </div>

      {/* 删除确认对话框 */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="确认删除视频"
        description={`确定要删除视频「${selectedVideo?.filename}」吗？此操作无法撤销。`}
        confirmText="确认删除"
        cancelText="取消"
        onConfirm={handleDeleteVideo}
        variant="destructive"
      />
    </div>
  );
}
