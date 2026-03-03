"use client";

/**
 * 项目 Context
 * 用于管理全局当前选中的项目状态
 */

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

// 项目数据类型定义
export interface Project {
  id: number;
  name: string;
  description: string | null;
  status: "ready" | "processing" | "error";
  progress: number;
  currentStep: string | null;
  errorMessage: string | null;
  createdAt: number;
  updatedAt: number;
}

interface ProjectContextType {
  // 当前选中的项目
  currentProject: Project | null;

  // 项目列表
  projects: Project[];

  // 设置当前项目
  setCurrentProject: (project: Project | null) => void;

  // 刷新项目列表
  refreshProjects: () => Promise<void>;

  // 加载状态
  isLoading: boolean;

  // 错误信息
  error: string | null;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

interface ProjectProviderProps {
  children: ReactNode;
}

export function ProjectProvider({ children }: ProjectProviderProps) {
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 从 localStorage 加载上次选中的项目
  useEffect(() => {
    const savedProjectId = localStorage.getItem("currentProjectId");
    if (savedProjectId) {
      // 后续可以从 projects 列表中找到对应的项目
      console.log("已保存的项目 ID:", savedProjectId);
    }
  }, []);

  // 加载项目列表
  const refreshProjects = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch("/api/projects?limit=100");
      const result = await response.json();

      if (result.success) {
        setProjects(result.data);

        // 如果有当前项目，确保它在新列表中
        if (currentProject) {
          const stillExists = result.data.find((p: Project) => p.id === currentProject.id);
          if (!stillExists) {
            // 当前项目被删除了，清空选择
            setCurrentProject(null);
            localStorage.removeItem("currentProjectId");
          }
        } else if (result.data.length > 0) {
          // 如果没有当前项目，默认选择第一个
          const firstProject = result.data[0];
          setCurrentProject(firstProject);
          localStorage.setItem("currentProjectId", String(firstProject.id));
        }
      } else {
        setError(result.message || "加载项目列表失败");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载项目列表失败");
    } finally {
      setIsLoading(false);
    }
  };

  // 初始加载项目列表
  useEffect(() => {
    refreshProjects();
  }, []);

  // 更新当前项目时保存到 localStorage
  const handleSetCurrentProject = (project: Project | null) => {
    setCurrentProject(project);
    if (project) {
      localStorage.setItem("currentProjectId", String(project.id));
    } else {
      localStorage.removeItem("currentProjectId");
    }
  };

  const value: ProjectContextType = {
    currentProject,
    projects,
    setCurrentProject: handleSetCurrentProject,
    refreshProjects,
    isLoading,
    error,
  };

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

/**
 * 使用项目 Context 的 Hook
 *
 * @example
 * const { currentProject, projects, setCurrentProject } = useProject();
 */
export function useProject() {
  const context = useContext(ProjectContext);

  if (context === undefined) {
    throw new Error("useProject 必须在 ProjectProvider 内部使用");
  }

  return context;
}
