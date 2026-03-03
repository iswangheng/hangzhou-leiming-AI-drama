"use client";

/**
 * 杭州雷鸣 - 项目详情页
 *
 * 功能：
 * - 显示项目基本信息
 * - 三个功能标签：训练中心、智能剪辑、导出中心
 * - 项目管理（编辑、删除）
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Video, FileText, Download, Pencil, Trash2, Calendar, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { HangzhouLeimingLayout } from "@/components/hangzhou-leiming-layout";

interface HLProject {
  id: number;
  name: string;
  description: string | null;
  status: "created" | "training" | "ready" | "analyzing" | "error";
  skillFilePath: string | null;
  videoCount: number;
  markingCount: number;
  trainedAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();

  // Next.js 15 requires params to be awaited
  const [projectId, setProjectId] = useState<number | null>(null);

  useEffect(() => {
    params.then((resolvedParams) => {
      setProjectId(parseInt(resolvedParams.id));
    });
  }, [params]);
  const [project, setProject] = useState<HLProject | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

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
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
            <p className="mt-4 text-muted-foreground">加载中...</p>
          </div>
        </div>
      </HangzhouLeimingLayout>
    );
  }

  if (isLoading) {
    return (
      <HangzhouLeimingLayout projectId={projectId}>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
            <p className="mt-4 text-muted-foreground">加载中...</p>
          </div>
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
            <Button
              onClick={() => router.push("/hangzhou-leiming")}
              className="cursor-pointer"
            >
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
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
              {project.name}
            </h1>
            <p className="text-muted-foreground mt-2">
              {project.description || "暂无描述"}
            </p>
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
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                视频数量
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Video className="w-8 h-8 text-orange-600" />
                <div className="text-3xl font-bold">{project.videoCount}</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                标记数量
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <FileText className="w-8 h-8 text-red-600" />
                <div className="text-3xl font-bold">{project.markingCount}</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                创建时间
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Calendar className="w-8 h-8 text-blue-600" />
                <div className="text-sm">
                  {new Date(project.createdAt).toLocaleDateString("zh-CN")}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 功能标签页 */}
        <Tabs defaultValue="smart-editor" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-[800px]">
            <TabsTrigger value="videos" className="cursor-pointer">
              <Video className="w-4 h-4 mr-2" />
              视频管理
            </TabsTrigger>
            <TabsTrigger value="markings" className="cursor-pointer">
              <FileText className="w-4 h-4 mr-2" />
              标记管理
            </TabsTrigger>
            <TabsTrigger value="smart-editor" className="cursor-pointer">
              <Pencil className="w-4 h-4 mr-2" />
              智能剪辑
            </TabsTrigger>
            <TabsTrigger value="export" className="cursor-pointer">
              <Download className="w-4 h-4 mr-2" />
              导出中心
            </TabsTrigger>
          </TabsList>

          {/* 视频管理标签页 */}
          <TabsContent value="videos" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>视频管理</CardTitle>
                <p className="text-sm text-muted-foreground">
                  管理项目下的所有视频，上传新剧集
                </p>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">📹</div>
                  <h3 className="text-xl font-semibold mb-2">视频管理</h3>
                  <p className="text-muted-foreground mb-6">
                    上传和管理项目下的所有视频文件
                  </p>
                  <Link href={`/hangzhou-leiming/${projectId}/videos`}>
                    <Button className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600">
                      进入视频管理
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 标记管理标签页 */}
          <TabsContent value="markings" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>标记管理</CardTitle>
                <p className="text-sm text-muted-foreground">
                  查看和管理所有标记（高光点和钩子点）
                </p>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">📍</div>
                  <h3 className="text-xl font-semibold mb-2">标记管理</h3>
                  <p className="text-muted-foreground mb-6">
                    查看所有标记数据，支持筛选和删除
                  </p>
                  <Link href={`/hangzhou-leiming/${projectId}/markings`}>
                    <Button className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600">
                      进入标记管理
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 智能剪辑标签页 */}
          <TabsContent value="smart-editor" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>智能剪辑</CardTitle>
                <p className="text-sm text-muted-foreground">
                  基于全局训练技能，自动标注视频并生成剪辑组合
                </p>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">✨</div>
                  <h3 className="text-xl font-semibold mb-2">智能剪辑工作台</h3>
                  <p className="text-muted-foreground mb-6">
                    上传新视频，AI 将基于训练好的技能自动识别高光点和钩子点，生成最佳剪辑组合
                  </p>
                  <Link href={`/hangzhou-leiming/${projectId}/smart-editor`}>
                    <Button className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600">
                      进入智能剪辑
                    </Button>
                  </Link>
                  <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                    <div className="p-4 border rounded-lg">
                      <div className="text-2xl mb-2">📤</div>
                      <h4 className="font-semibold mb-1">上传视频</h4>
                      <p className="text-sm text-muted-foreground">支持批量上传新剧集视频</p>
                    </div>
                    <div className="p-4 border rounded-lg">
                      <div className="text-2xl mb-2">🎯</div>
                      <h4 className="font-semibold mb-1">AI 自动标注</h4>
                      <p className="text-sm text-muted-foreground">基于全局技能自动标记高光点和钩子点</p>
                    </div>
                    <div className="p-4 border rounded-lg">
                      <div className="text-2xl mb-2">🎬</div>
                      <h4 className="font-semibold mb-1">生成组合</h4>
                      <p className="text-sm text-muted-foreground">智能生成多个剪辑组合供选择</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 导出中心标签页 */}
          <TabsContent value="export" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>导出中心</CardTitle>
                <p className="text-sm text-muted-foreground">
                  一键导出剪辑组合，生成成品视频
                </p>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">📦</div>
                  <h3 className="text-xl font-semibold mb-2">导出中心</h3>
                  <p className="text-muted-foreground mb-6">
                    选择满意的剪辑组合，一键生成成品视频
                  </p>
                  <Link href={`/hangzhou-leiming/${projectId}/export`}>
                    <Button className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600">
                      进入导出中心
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* 删除确认对话框 */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="确认删除项目"
        description={`确定要删除项目「${project.name}」吗？此操作将删除项目下的所有数据，包括视频、标记、技能文件等，且无法恢复。`}
        confirmText="确认删除"
        cancelText="取消"
        onConfirm={handleDeleteProject}
        variant="destructive"
      />
    </HangzhouLeimingLayout>
  );
}
