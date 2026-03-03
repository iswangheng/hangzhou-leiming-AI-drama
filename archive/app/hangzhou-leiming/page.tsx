"use client";

/**
 * 杭州雷鸣 - 首页（项目列表）
 *
 * 功能：
 * - 显示所有杭州雷鸣项目
 * - 创建新项目
 * - 删除项目
 * - 进入项目详情
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Pencil, Trash2, Video, Calendar, FileText, Brain } from "lucide-react";
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

export default function HangzhouLeimingPage() {
  const [projects, setProjects] = useState<HLProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<HLProject | null>(null);

  // 创建项目表单
  const [formData, setFormData] = useState({
    name: "",
    description: "",
  });

  // 加载项目列表
  const loadProjects = async () => {
    try {
      setIsLoading(true);
      const res = await fetch("/api/hangzhou-leiming/projects");
      const result = await res.json();

      if (result.success) {
        setProjects(result.data || []);
      } else {
        console.error("加载项目失败:", result.message);
      }
    } catch (error) {
      console.error("加载项目失败:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // 创建项目
  const handleCreateProject = async () => {
    try {
      const res = await fetch("/api/hangzhou-leiming/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const result = await res.json();

      if (result.success) {
        setCreateDialogOpen(false);
        setFormData({ name: "", description: "" });
        await loadProjects();
      } else {
        alert(`创建失败：${result.message}`);
      }
    } catch (error) {
      console.error("创建项目失败:", error);
      alert("创建项目失败，请稍后重试");
    }
  };

  // 删除项目
  const handleDeleteProject = async () => {
    if (!selectedProject) return;

    try {
      const res = await fetch(`/api/hangzhou-leiming/projects/${selectedProject.id}`, {
        method: "DELETE",
      });

      const result = await res.json();

      if (result.success) {
        setDeleteDialogOpen(false);
        setSelectedProject(null);
        await loadProjects();
      } else {
        alert(`删除失败：${result.message}`);
      }
    } catch (error) {
      console.error("删除项目失败:", error);
      alert("删除项目失败，请稍后重试");
    }
  };

  // 确认删除对话框
  const openDeleteDialog = (project: HLProject) => {
    setSelectedProject(project);
    setDeleteDialogOpen(true);
  };

  // 获取状态颜色
  const getStatusColor = (status: HLProject["status"]) => {
    switch (status) {
      case "created":
        return "bg-gray-100 text-gray-800";
      case "training":
        return "bg-blue-100 text-blue-800";
      case "ready":
        return "bg-green-100 text-green-800";
      case "analyzing":
        return "bg-yellow-100 text-yellow-800";
      case "error":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  // 获取状态文本
  const getStatusText = (status: HLProject["status"]) => {
    switch (status) {
      case "created":
        return "已创建";
      case "training":
        return "训练中";
      case "ready":
        return "就绪";
      case "analyzing":
        return "分析中";
      case "error":
        return "错误";
      default:
        return "未知";
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <HangzhouLeimingLayout>
      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {/* 顶部标题和操作按钮 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
              项目管理
            </h1>
            <p className="text-muted-foreground mt-2">
              管理所有短剧项目，训练 AI 剪辑技能
            </p>
          </div>
          <Button
            onClick={() => setCreateDialogOpen(true)}
            className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
          >
            <Plus className="w-4 h-4 mr-2" />
            创建项目
          </Button>
        </div>
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
              <p className="mt-4 text-muted-foreground">加载中...</p>
            </div>
          </div>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-96">
            <div className="text-6xl mb-4">📁</div>
            <h3 className="text-xl font-semibold mb-2">暂无项目</h3>
            <p className="text-muted-foreground mb-4">创建第一个项目开始使用杭州雷鸣</p>
            <Button
              onClick={() => setCreateDialogOpen(true)}
              className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
            >
              <Plus className="w-4 h-4 mr-2" />
              创建项目
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <Card
                key={project.id}
                className="hover:shadow-lg transition-shadow cursor-pointer group"
              >
                <Link href={`/hangzhou-leiming/${project.id}`}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-lg group-hover:text-orange-600 transition-colors">
                          {project.name}
                        </CardTitle>
                        <CardDescription className="mt-1">
                          {project.description || "暂无描述"}
                        </CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {/* 状态标签 */}
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">状态</span>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                            project.status
                          )}`}
                        >
                          {getStatusText(project.status)}
                        </span>
                      </div>

                      {/* 统计信息 */}
                      <div className="grid grid-cols-2 gap-3 pt-3 border-t">
                        <div className="flex items-center gap-2">
                          <Video className="w-4 h-4 text-muted-foreground" />
                          <span className="text-sm">{project.videoCount} 个视频</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-muted-foreground" />
                          <span className="text-sm">{project.markingCount} 个标记</span>
                        </div>
                      </div>

                      {/* 创建时间 */}
                      <div className="flex items-center gap-2 text-sm text-muted-foreground pt-3 border-t">
                        <Calendar className="w-4 h-4" />
                        <span>{new Date(project.createdAt).toLocaleDateString("zh-CN")}</span>
                      </div>
                    </div>
                  </CardContent>
                </Link>

                {/* 操作按钮 */}
                <div className="px-6 pb-6 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 cursor-pointer"
                    onClick={(e) => {
                      e.preventDefault();
                      window.location.href = `/hangzhou-leiming/${project.id}`;
                    }}
                  >
                    <Pencil className="w-4 h-4 mr-1" />
                    编辑
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="cursor-pointer hover:bg-red-50 hover:text-red-600 hover:border-red-300"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      openDeleteDialog(project);
                    }}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* 创建项目对话框 */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>创建新项目</DialogTitle>
            <DialogDescription>
              输入项目名称和描述，开始使用杭州雷鸣 AI 剪辑工具
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">项目名称 *</Label>
              <Input
                id="name"
                placeholder="例如：霸道总裁短剧剪辑"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="cursor-pointer"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">项目描述</Label>
              <Textarea
                id="description"
                placeholder="简要描述项目用途..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
                className="cursor-pointer"
              />
            </div>
          </div>
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
              disabled={!formData.name.trim()}
              className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
            >
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="确认删除项目"
        description={`确定要删除项目「${selectedProject?.name}」吗？此操作将删除项目下的所有数据，包括视频、标记、技能文件等，且无法恢复。`}
        confirmText="确认删除"
        cancelText="取消"
        onConfirm={handleDeleteProject}
        variant="destructive"
      />
    </HangzhouLeimingLayout>
  );
}
