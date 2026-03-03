// ============================================
// 项目管理 API 客户端
// 封装所有项目管理相关的 API 调用
// ============================================

import type { Project, Video } from '@/lib/db/schema';

// ============================================
// 类型定义
// ============================================

export interface ProjectWithStats extends Project {
  videoCount: number;
  totalDuration: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  meta?: Record<string, unknown>;
}

// ============================================
// API 客户端
// ============================================

export const projectsApi = {
  /**
   * 获取项目列表
   */
  async list(limit = 50, offset = 0): Promise<ApiResponse<Project[]>> {
    const response = await fetch(`/api/projects?limit=${limit}&offset=${offset}`);
    return response.json();
  },

  /**
   * 创建新项目
   */
  async create(data: { name: string; description?: string }): Promise<ApiResponse<Project>> {
    const response = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },

  /**
   * 获取项目详情（包含统计）
   */
  async getById(id: number): Promise<ApiResponse<ProjectWithStats>> {
    const response = await fetch(`/api/projects/${id}`);
    return response.json();
  },

  /**
   * 更新项目
   */
  async update(id: number, data: Partial<Project>): Promise<ApiResponse<Project>> {
    const response = await fetch(`/api/projects/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },

  /**
   * 更新项目进度
   */
  async updateProgress(
    id: number,
    progress: number,
    currentStep?: string
  ): Promise<ApiResponse<Project>> {
    const response = await fetch(`/api/projects/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ progress, currentStep }),
    });
    return response.json();
  },

  /**
   * 删除项目
   */
  async delete(id: number): Promise<ApiResponse<{ id: number }>> {
    const response = await fetch(`/api/projects/${id}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  /**
   * 搜索项目
   */
  async search(keyword: string, limit = 50): Promise<ApiResponse<Project[]>> {
    const response = await fetch(`/api/projects/search?q=${encodeURIComponent(keyword)}&limit=${limit}`);
    return response.json();
  },

  /**
   * 获取项目的视频列表
   */
  async getVideos(projectId: number): Promise<ApiResponse<Video[]>> {
    const response = await fetch(`/api/projects/${projectId}/videos`);
    return response.json();
  },

  /**
   * 上传视频到项目
   */
  async uploadVideo(
    projectId: number,
    data: {
      filename: string;
      filePath: string;
      fileSize: number;
      durationMs: number;
      width: number;
      height: number;
      fps: number;
    }
  ): Promise<ApiResponse<Video>> {
    const response = await fetch(`/api/projects/${projectId}/videos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return response.json();
  },
};

export const videosApi = {
  /**
   * 删除视频
   */
  async delete(id: number): Promise<ApiResponse<{ id: number }>> {
    const response = await fetch(`/api/videos/${id}`, {
      method: 'DELETE',
    });
    return response.json();
  },
};

// ============================================
// 导出
// ============================================

export default projectsApi;
