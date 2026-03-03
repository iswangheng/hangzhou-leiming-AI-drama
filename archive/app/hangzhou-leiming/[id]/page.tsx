"use client";

/**
 * 杭州雷鸣 - 项目详情页（Tab切换版本）
 *
 * 功能：
 * - 显示项目基本信息
 * - 四个功能Tab：视频、标记、智能剪辑、导出
 * - 单页切换，无需路由跳转
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Trash2, Video, FileText, Wand2, Download, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { HangzhouLeimingLayout } from "@/components/hangzhou-leiming-layout";
import {
  VideosTabContent,
  MarkingsTabContent,
  SmartEditorTabContent,
  ExportTabContent,
} from "@/components/hangzhou-leiming-tabs";

interface HLProject {
  id: number;
  name: string;
  description: string | null;
  status: "created" | "training" | "ready" | "analyzing" | "error";
  videoCount: number;
  markingCount: number;
  createdAt: Date;
  updatedAt: Date;
}

export default function ProjectDetailPageWithTabs({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [project, setProject] = useState<HLProject | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("videos");

  // 加载 projectId
  useEffect(() => {
    params.then((resolvedParams) => {
      setProjectId(parseInt(resolvedParams.id));
    });
  }, [params]);

  // 加载项目详情
  const loadProject = async () => {
    if (!projectId) return;

    try {
      setIsLoading(true);
      const res = await fetch(`/api/hangzhou-leiming/projects/${projectId}`);
      const result = await res.json();

      if (result.success) {
        setProject(result.data);
      } else {
        alert(`加载失败：${result.message}`);
        router.push("/hangzhou-leiming");
      }
    } catch (error) {
      console.error("加载项目失败:", error);
      router.push("/hangzhou-leiming");
    } finally {
      setIsLoading(false);
    }
  };

  // 删除项目
  const handleDeleteProject = async () => {
    if (!projectId) return;

    try {
      const res = await fetch(`/api/hangzhou-leiming/projects/${projectId}`, {
        method: "DELETE",
      });

      const result = await res.json();

      if (result.success) {
        setDeleteDialogOpen(false);
        router.push("/hangzhou-leiming");
      } else {
        alert(`删除失败：${result.message}`);
      }
    } catch (error) {
      console.error("删除项目失败:", error);
      alert("删除项目失败，请稍后重试");
    }
  };

  useEffect(() => {
    loadProject();
  }, [projectId]);

  // 等待 projectId 解析
  if (projectId === null) {
    return (
      <HangzhouLeimingLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
        </div>
      </HangzhouLeimingLayout>
    );
  }

  if (isLoading) {
    return (
      <HangzhouLeimingLayout projectId={projectId}>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
        </div>
      </HangzhouLeimingLayout>
    );
  }

  if (!project) {
    return (
      <HangzhouLeimingLayout projectId={projectId}>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="text-6xl mb-4">❌</div>
            <h3 className="text-xl font-semibold mb-2">项目不存在</h3>
            <p className="text-muted-foreground mb-4">项目可能已被删除</p>
            <Button onClick={() => router.push("/hangzhou-leiming")} className="cursor-pointer">
              返回项目列表
            </Button>
          </div>
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
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push("/hangzhou-leiming")}
              className="cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              返回
            </Button>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
                {project.name}
              </h1>
              <p className="text-muted-foreground mt-2">
                {project.description || "暂无描述"}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="cursor-pointer hover:bg-red-50 hover:text-red-600 hover:border-red-300"
            onClick={() => setDeleteDialogOpen(true)}
          >
            <Trash2 className="w-4 h-4 mr-1" />
            删除项目
          </Button>
        </div>

        {/* 项目统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <Video className="w-10 h-10 text-orange-600" />
                <div>
                  <p className="text-sm text-muted-foreground">视频数量</p>
                  <p className="text-2xl font-bold">{project.videoCount}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <FileText className="w-10 h-10 text-red-600" />
                <div>
                  <p className="text-sm text-muted-foreground">标记数量</p>
                  <p className="text-2xl font-bold">{project.markingCount}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <FolderOpen className="w-10 h-10 text-blue-600" />
                <div>
                  <p className="text-sm text-muted-foreground">项目状态</p>
                  <p className="text-lg font-semibold">
                    {
                      {
                        created: "已创建",
                        training: "训练中",
                        ready: "就绪",
                        analyzing: "分析中",
                        error: "错误",
                      }[project.status]
                    }
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 功能Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-[600px]">
            <TabsTrigger value="videos" className="cursor-pointer">
              <Video className="w-4 h-4 mr-2" />
              视频管理
            </TabsTrigger>
            <TabsTrigger value="markings" className="cursor-pointer">
              <FileText className="w-4 h-4 mr-2" />
              标记管理
            </TabsTrigger>
            <TabsTrigger value="smart-editor" className="cursor-pointer">
              <Wand2 className="w-4 h-4 mr-2" />
              智能剪辑
            </TabsTrigger>
            <TabsTrigger value="export" className="cursor-pointer">
              <Download className="w-4 h-4 mr-2" />
              导出中心
            </TabsTrigger>
          </TabsList>

          <TabsContent value="videos" className="mt-6">
            <VideosTabContent
              projectId={projectId}
              projectName={project.name}
              onUpdate={loadProject}
            />
          </TabsContent>

          <TabsContent value="markings" className="mt-6">
            <MarkingsTabContent
              projectId={projectId}
              projectName={project.name}
              onUpdate={loadProject}
            />
          </TabsContent>

          <TabsContent value="smart-editor" className="mt-6">
            <SmartEditorTabContent
              projectId={projectId}
              projectName={project.name}
              onUpdate={loadProject}
            />
          </TabsContent>

          <TabsContent value="export" className="mt-6">
            <ExportTabContent
              projectId={projectId}
              projectName={project.name}
            />
          </TabsContent>
        </Tabs>
      </div>

      {/* 删除确认对话框 */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="确认删除项目"
        description={`确定要删除项目「${project.name}」吗？此操作将删除项目下的所有视频、标记和导出记录，且无法恢复。`}
        confirmText="确认删除"
        cancelText="取消"
        onConfirm={handleDeleteProject}
        variant="destructive"
      />
    </HangzhouLeimingLayout>
  );
}
