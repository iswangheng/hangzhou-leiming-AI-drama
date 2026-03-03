"use client";

/**
 * 项目选择器组件
 * 用于在导航栏快速切换项目
 */

import { useState } from "react";
import { Check, ChevronDown, Plus, Loader2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useProject } from "@/contexts/project-context";
import { cn } from "@/lib/utils";

export function ProjectSelector() {
  const { currentProject, projects, setCurrentProject, isLoading, refreshProjects } =
    useProject();

  const [isOpen, setIsOpen] = useState(false);

  // 处理项目切换
  const handleSelectProject = (projectId: number) => {
    const project = projects.find((p) => p.id === projectId);
    if (project) {
      setCurrentProject(project);
      setIsOpen(false);
    }
  };

  // 获取显示的项目名称
  const getProjectDisplayName = () => {
    if (currentProject) {
      return currentProject.name;
    }
    return isLoading ? "加载中..." : "请选择项目";
  };

  // 获取项目状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case "ready":
        return "text-green-600";
      case "processing":
        return "text-blue-600";
      case "error":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  // 获取项目状态标签
  const getStatusLabel = (status: string) => {
    switch (status) {
      case "ready":
        return "就绪";
      case "processing":
        return "处理中";
      case "error":
        return "错误";
      default:
        return "未知";
    }
  };

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger
        className={cn(
          "mx-3 mt-4 p-2.5",
          "bg-muted/50 border border-border rounded-xl",
          "cursor-pointer transition-all",
          "hover:bg-muted hover:border-border/80",
          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        )}
      >
        {/* 标签 */}
        <div className="flex items-center justify-between text-xs font-medium text-muted-foreground mb-1.5">
          <span>当前项目</span>
          {isLoading && <Loader2 className="w-3 h-3 animate-spin" />}
        </div>

        {/* 当前项目名称 */}
        <div className="flex items-center justify-between font-semibold text-foreground/80">
          <span className="text-sm truncate flex-1">{getProjectDisplayName()}</span>
          <ChevronDown className="w-4 h-4 ml-1 flex-shrink-0 transition-transform duration-200" />
        </div>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align="start"
        className="w-[236px] max-h-[480px] overflow-y-auto"
      >
        {/* 当前项目信息 */}
        {currentProject && (
          <>
            <div className="px-3 py-2 bg-muted/50">
              <div className="flex items-center gap-2">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground truncate">
                    {currentProject.name}
                  </div>
                  {currentProject.description && (
                    <div className="text-xs text-muted-foreground truncate mt-0.5">
                      {currentProject.description}
                    </div>
                  )}
                </div>
                <div
                  className={cn(
                    "text-xs font-medium",
                    getStatusColor(currentProject.status)
                  )}
                >
                  {getStatusLabel(currentProject.status)}
                </div>
              </div>
              {currentProject.currentStep && (
                <div className="text-xs text-muted-foreground mt-2">
                  {currentProject.currentStep}
                </div>
              )}
              {currentProject.progress > 0 && currentProject.progress < 100 && (
                <div className="mt-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                    <span>进度</span>
                    <span>{currentProject.progress}%</span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${currentProject.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
            <DropdownMenuSeparator />
          </>
        )}

        {/* 项目列表 */}
        <div className="px-2 py-1.5">
          <div className="text-xs font-medium text-muted-foreground px-2 mb-1">
            所有项目 ({projects.length})
          </div>
          {projects.length === 0 ? (
            <div className="px-2 py-4 text-center text-sm text-muted-foreground">
              {isLoading ? "加载中..." : "暂无项目"}
            </div>
          ) : (
            <div className="space-y-0.5">
              {projects.map((project) => (
                <DropdownMenuItem
                  key={project.id}
                  className="flex items-center gap-2 px-2 py-2 cursor-pointer rounded-md transition-colors hover:bg-accent"
                  onClick={() => handleSelectProject(project.id)}
                >
                  {/* 选中标记 */}
                  {currentProject?.id === project.id && (
                    <Check className="w-4 h-4 text-primary flex-shrink-0" />
                  )}
                  {currentProject?.id !== project.id && (
                    <div className="w-4 h-4 flex-shrink-0" />
                  )}

                  {/* 项目信息 */}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-foreground truncate">
                      {project.name}
                    </div>
                    {project.description && (
                      <div className="text-xs text-muted-foreground truncate">
                        {project.description}
                      </div>
                    )}
                  </div>

                  {/* 状态标签 */}
                  <div
                    className={cn(
                      "text-xs font-medium flex-shrink-0",
                      getStatusColor(project.status)
                    )}
                  >
                    {getStatusLabel(project.status)}
                  </div>
                </DropdownMenuItem>
              ))}
            </div>
          )}
        </div>

        <DropdownMenuSeparator />

        {/* 操作按钮 */}
        <div className="px-2 py-1.5 space-y-0.5">
          <DropdownMenuItem
            className="flex items-center gap-2 px-2 py-2 cursor-pointer rounded-md transition-colors hover:bg-accent"
            onClick={() => {
              // TODO: 打开创建项目弹窗
              console.log("创建新项目");
              setIsOpen(false);
            }}
          >
            <Plus className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">创建新项目</span>
          </DropdownMenuItem>

          <DropdownMenuItem
            className="flex items-center gap-2 px-2 py-2 cursor-pointer rounded-md transition-colors hover:bg-accent"
            onClick={() => {
              refreshProjects();
              setIsOpen(false);
            }}
          >
            <Loader2 className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">刷新列表</span>
          </DropdownMenuItem>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
