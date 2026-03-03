"use client";

/**
 * 杭州雷鸣 - 训练中心：训练历史页面
 *
 * 功能：
 * - 查看所有训练记录
 * - 查看训练详情
 * - 查看训练进度
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  History,
  Calendar,
  TrendingUp,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  Video,
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
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { HangzhouLeimingLayout } from "@/components/hangzhou-leiming-layout";

interface TrainingHistory {
  id: number;
  projectIds: number[];
  projectNames: string[];
  status: "pending" | "training" | "completed" | "failed";
  progress: number;
  skillVersion: string;
  currentStep: string;
  totalVideosProcessed: number;
  totalMarkingsLearned: number;
  errorMessage: string | null;
  startedAt: Date | null;
  completedAt: Date | null;
  createdAt: Date;
}

export default function TrainingHistoryPage() {
  const [history, setHistory] = useState<TrainingHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState<TrainingHistory | null>(
    null
  );
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // 加载训练历史
  const loadHistory = async () => {
    try {
      setLoading(true);
      const res = await fetch(
        "/api/hangzhou-leiming/training-center/history?limit=50"
      );

      // 检查HTTP状态
      if (!res.ok) {
        console.error(`API错误: ${res.status} ${res.statusText}`);
        setHistory([]);
        return;
      }

      // 解析JSON（带容错）
      let result;
      try {
        result = await res.json();
      } catch (jsonError) {
        console.error("JSON解析失败:", jsonError);
        setHistory([]);
        return;
      }

      if (result.success) {
        setHistory(result.data || []);
      }
    } catch (error) {
      console.error("加载训练历史失败:", error);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  // 查看训练详情
  const handleViewDetail = (record: TrainingHistory) => {
    setSelectedRecord(record);
    setDetailDialogOpen(true);
  };

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <HangzhouLeimingLayout>
      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
              <p className="mt-4 text-muted-foreground">加载中...</p>
            </div>
          </div>
        ) : history.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <History className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">暂无训练记录</h3>
              <p className="text-muted-foreground mb-6">
                开始第一次训练，生成全局剪辑技能
              </p>
              <Link href="/hangzhou-leiming/training-center/training">
                <Button className="cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600">
                  开始训练
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {history.map((record) => (
              <Card
                key={record.id}
                className="hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => handleViewDetail(record)}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
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
                          ) : record.status === "failed" ? (
                            <XCircle className="w-5 h-5 text-red-600" />
                          ) : (
                            <Clock className="w-5 h-5 text-gray-600" />
                          )}
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold">
                            {record.projectNames.join(", ")}
                          </h3>
                          <p className="text-sm text-muted-foreground">
                            版本 {record.skillVersion}
                          </p>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
                        <div className="flex items-center gap-2 text-sm">
                          <Video className="w-4 h-4 text-muted-foreground" />
                          <span className="text-muted-foreground">处理视频：</span>
                          <span className="font-medium">{record.totalVideosProcessed} 个</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                          <FileText className="w-4 h-4 text-muted-foreground" />
                          <span className="text-muted-foreground">学习标记：</span>
                          <span className="font-medium">{record.totalMarkingsLearned} 个</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                          <Calendar className="w-4 h-4 text-muted-foreground" />
                          <span className="text-muted-foreground">开始时间：</span>
                          <span className="font-medium">
                            {record.startedAt
                              ? new Date(record.startedAt).toLocaleString("zh-CN")
                              : "-"}
                          </span>
                        </div>
                      </div>

                      {record.status === "training" && (
                        <div className="mb-3">
                          <div className="flex items-center justify-between text-sm mb-1">
                            <span className="text-muted-foreground">{record.currentStep}</span>
                            <span className="font-medium">{record.progress}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-gradient-to-r from-orange-500 to-red-500 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${record.progress}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {record.status === "failed" && record.errorMessage && (
                        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                          <p className="text-sm text-red-800">
                            {record.errorMessage}
                          </p>
                        </div>
                      )}

                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="w-4 h-4" />
                        <span>
                          创建于 {new Date(record.createdAt).toLocaleString("zh-CN")}
                        </span>
                      </div>
                    </div>

                    <div
                      className={`ml-4 px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
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
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* 训练详情对话框 */}
      <Dialog
        open={detailDialogOpen}
        onOpenChange={(open) => {
          setDetailDialogOpen(open);
          if (!open) {
            setSelectedRecord(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>训练详情</DialogTitle>
            <DialogDescription>
              训练项目: {selectedRecord?.projectNames.join(", ")}
            </DialogDescription>
          </DialogHeader>
          {selectedRecord && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">状态</p>
                  <div
                    className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${
                      selectedRecord.status === "completed"
                        ? "bg-green-100 text-green-800"
                        : selectedRecord.status === "training"
                        ? "bg-blue-100 text-blue-800"
                        : selectedRecord.status === "failed"
                        ? "bg-red-100 text-red-800"
                        : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {selectedRecord.status === "completed"
                      ? "已完成"
                      : selectedRecord.status === "training"
                      ? "训练中"
                      : selectedRecord.status === "failed"
                      ? "失败"
                      : "等待中"}
                  </div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">技能版本</p>
                  <p className="font-medium">{selectedRecord.skillVersion}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">开始时间</p>
                  <p className="text-sm">
                    {selectedRecord.startedAt
                      ? new Date(selectedRecord.startedAt).toLocaleString("zh-CN")
                      : "-"}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">完成时间</p>
                  <p className="text-sm">
                    {selectedRecord.completedAt
                      ? new Date(selectedRecord.completedAt).toLocaleString("zh-CN")
                      : "-"}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-sm text-muted-foreground mb-2">训练结果</p>
                <div className="grid grid-cols-2 gap-4 p-4 bg-slate-50 rounded-lg">
                  <div>
                    <p className="text-2xl font-bold text-orange-600">
                      {selectedRecord.totalVideosProcessed}
                    </p>
                    <p className="text-sm text-muted-foreground">处理视频</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-blue-600">
                      {selectedRecord.totalMarkingsLearned}
                    </p>
                    <p className="text-sm text-muted-foreground">学习标记</p>
                  </div>
                </div>
              </div>

              {selectedRecord.status === "training" && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    训练进度：{selectedRecord.progress}%
                  </p>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-orange-500 to-red-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${selectedRecord.progress}%` }}
                    />
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {selectedRecord.currentStep}
                  </p>
                </div>
              )}

              {selectedRecord.errorMessage && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">错误信息</p>
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-800">
                      {selectedRecord.errorMessage}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </HangzhouLeimingLayout>
  );
}
