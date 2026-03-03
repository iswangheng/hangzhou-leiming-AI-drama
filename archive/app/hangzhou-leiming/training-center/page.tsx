"use client";

/**
 * 杭州雷鸣 - 训练中心（独立模块）
 *
 * 功能：
 * - 查看全局技能文件状态
 * - 选择多个历史项目进行训练
 * - 查看训练历史记录
 * - 管理技能文件
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Brain,
  TrendingUp,
  History,
  Settings,
  Plus,
  Calendar,
  FileText,
  CheckCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { HangzhouLeimingLayout } from "@/components/hangzhou-leiming-layout";

interface GlobalSkill {
  id: number;
  version: string;
  totalProjects: number;
  totalVideos: number;
  totalMarkings: number;
  createdAt: Date;
  updatedAt: Date;
}

interface TrainingHistory {
  id: number;
  projectIds: number[];
  projectNames: string[];
  status: "pending" | "training" | "completed" | "failed";
  progress: number;
  skillVersion: string;
  createdAt: Date;
  completedAt: Date | null;
}

export default function TrainingCenterPage() {
  const [globalSkill, setGlobalSkill] = useState<GlobalSkill | null>(null);
  const [trainingHistory, setTrainingHistory] = useState<TrainingHistory[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // 加载数据
  const loadData = async () => {
    try {
      setIsLoading(true);

      // 并行加载全局技能和训练历史
      const [skillRes, historyRes] = await Promise.all([
        fetch("/api/hangzhou-leiming/training-center/skills"),
        fetch("/api/hangzhou-leiming/training-center/history"),
      ]);

      const [skillResult, historyResult] = await Promise.all([
        skillRes.json(),
        historyRes.json(),
      ]);

      if (skillResult.success) {
        setGlobalSkill(skillResult.data);
      }

      if (historyResult.success) {
        setTrainingHistory(historyResult.data || []);
      }
    } catch (error) {
      console.error("加载数据失败:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <HangzhouLeimingLayout>
      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
              <p className="mt-4 text-muted-foreground">加载中...</p>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* 快捷操作卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link href="/hangzhou-leiming/training-center/training">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-full bg-orange-100">
                        <Brain className="w-6 h-6 text-orange-600" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">开始训练</CardTitle>
                        <CardDescription className="text-sm">
                          选择项目进行训练
                        </CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                </Link>
              </Card>

              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link href="/hangzhou-leiming/training-center/skills">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-full bg-blue-100">
                        <Settings className="w-6 h-6 text-blue-600" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">技能管理</CardTitle>
                        <CardDescription className="text-sm">
                          查看和编辑技能文件
                        </CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                </Link>
              </Card>

              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <Link href="/hangzhou-leiming/training-center/history">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-full bg-green-100">
                        <History className="w-6 h-6 text-green-600" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">训练历史</CardTitle>
                        <CardDescription className="text-sm">
                          查看历史训练记录
                        </CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                </Link>
              </Card>
            </div>

            {/* 当前技能状态 */}
            {globalSkill && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>当前技能状态</CardTitle>
                      <CardDescription>
                        版本 {globalSkill.version} · 最后更新:{" "}
                        {new Date(globalSkill.updatedAt).toLocaleString("zh-CN")}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-green-600" />
                      <span className="text-sm font-medium text-green-600">
                        已就绪
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-lg bg-orange-100">
                        <FileText className="w-6 h-6 text-orange-600" />
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">训练项目</p>
                        <p className="text-2xl font-bold">{globalSkill.totalProjects}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-lg bg-blue-100">
                        <TrendingUp className="w-6 h-6 text-blue-600" />
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">覆盖视频</p>
                        <p className="text-2xl font-bold">{globalSkill.totalVideos}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-lg bg-green-100">
                        <CheckCircle className="w-6 h-6 text-green-600" />
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">学习标记</p>
                        <p className="text-2xl font-bold">{globalSkill.totalMarkings}</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 最近训练记录 */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>最近训练记录</CardTitle>
                  <Link href="/hangzhou-leiming/training-center/history">
                    <Button variant="outline" size="sm" className="cursor-pointer">
                      查看全部
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                {trainingHistory.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="text-6xl mb-4">📊</div>
                    <h3 className="text-xl font-semibold mb-2">暂无训练记录</h3>
                    <p className="text-muted-foreground mb-6">
                      开始第一次训练，生成全局剪辑技能
                    </p>
                    <Link href="/hangzhou-leiming/training-center/training">
                      <Button className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600">
                        <Plus className="w-4 h-4 mr-2" />
                        开始训练
                      </Button>
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {trainingHistory.slice(0, 5).map((record) => (
                      <div
                        key={record.id}
                        className="flex items-center justify-between p-4 border rounded-lg hover:bg-slate-50 transition-colors"
                      >
                        <div className="flex items-center gap-4">
                          <div
                            className={`p-2 rounded-full ${
                              record.status === "completed"
                                ? "bg-green-100"
                                : record.status === "training"
                                ? "bg-blue-100"
                                : record.status === "failed"
                                ? "bg-red-100"
                                : "bg-gray-100"
                            }`}
                          >
                            {record.status === "completed" ? (
                              <CheckCircle className="w-5 h-5 text-green-600" />
                            ) : record.status === "training" ? (
                              <TrendingUp className="w-5 h-5 text-blue-600 animate-pulse" />
                            ) : (
                              <Calendar className="w-5 h-5 text-gray-600" />
                            )}
                          </div>
                          <div>
                            <p className="font-medium">
                              {record.projectNames.join(", ")}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              版本 {record.skillVersion} ·{" "}
                              {new Date(record.createdAt).toLocaleString("zh-CN")}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          {record.status === "training" && (
                            <div className="text-sm text-muted-foreground">
                              {record.progress}%
                            </div>
                          )}
                          <div
                            className={`px-3 py-1 rounded-full text-xs font-medium ${
                              record.status === "completed"
                                ? "bg-green-100 text-green-800"
                                : record.status === "training"
                                ? "bg-blue-100 text-blue-800"
                                : record.status === "failed"
                                ? "bg-red-100 text-red-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {record.status === "completed"
                              ? "已完成"
                              : record.status === "training"
                              ? "训练中"
                              : record.status === "failed"
                              ? "失败"
                              : "等待中"}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </HangzhouLeimingLayout>
  );
}
