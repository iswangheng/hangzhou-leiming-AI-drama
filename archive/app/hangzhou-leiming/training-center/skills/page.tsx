"use client";

/**
 * 杭州雷鸣 - 训练中心：技能管理页面
 *
 * 功能：
 * - 查看所有技能版本
 * - 查看技能文件内容
 * - 下载技能文件
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  FileText,
  Download,
  Eye,
  TrendingUp,
  Calendar,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { HangzhouLeimingLayout } from "@/components/hangzhou-leiming-layout";

interface GlobalSkill {
  id: number;
  version: string;
  skillFilePath: string;
  totalProjects: number;
  totalVideos: number;
  totalMarkings: number;
  trainingProjectIds: string;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  status: "training" | "ready" | "deprecated";
  createdAt: Date;
  updatedAt: Date;
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<GlobalSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSkill, setSelectedSkill] = useState<GlobalSkill | null>(null);
  const [skillContent, setSkillContent] = useState<string>("");
  const [viewDialogOpen, setViewDialogOpen] = useState(false);

  // 加载技能列表
  const loadSkills = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/hangzhou-leiming/training-center/skills");
      const result = await res.json();

      if (result.success) {
        // API 返回的是数组，直接使用
        setSkills(result.data || []);
      }
    } catch (error) {
      console.error("加载技能列表失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 查看技能文件内容
  const handleViewSkill = async (skill: GlobalSkill) => {
    try {
      // 读取技能文件内容
      const res = await fetch(
        `/api/hangzhou-leiming/training-center/skills/${skill.id}/content`
      );
      const result = await res.json();

      if (result.success) {
        setSkillContent(result.data.content);
        setSelectedSkill(skill);
        setViewDialogOpen(true);
      } else {
        alert(`加载失败：${result.message}`);
      }
    } catch (error) {
      console.error("查看技能文件失败:", error);
      alert("查看技能文件失败，请稍后重试");
    }
  };

  // 下载技能文件
  const handleDownloadSkill = async (skill: GlobalSkill) => {
    try {
      window.open(
        `/api/hangzhou-leiming/training-center/skills/${skill.id}/download`,
        "_blank"
      );
    } catch (error) {
      console.error("下载失败:", error);
      alert("下载失败，请稍后重试");
    }
  };

  useEffect(() => {
    loadSkills();
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
        ) : skills.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FileText className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">暂无技能文件</h3>
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
            {skills.map((skill) => (
              <Card key={skill.id} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="flex items-center gap-2">
                          <h3 className="text-xl font-bold">版本 {skill.version}</h3>
                          {skill.status === "ready" && (
                            <div className="flex items-center gap-1 text-green-600">
                              <CheckCircle className="w-4 h-4" />
                              <span className="text-sm font-medium">已就绪</span>
                            </div>
                          )}
                          {skill.status === "training" && (
                            <div className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                              训练中
                            </div>
                          )}
                          {skill.status === "deprecated" && (
                            <div className="px-2 py-1 bg-gray-100 text-gray-800 rounded-full text-xs font-medium">
                              已废弃
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-orange-100">
                            <FileText className="w-5 h-5 text-orange-600" />
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">训练项目</p>
                            <p className="text-lg font-semibold">{skill.totalProjects}</p>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-blue-100">
                            <TrendingUp className="w-5 h-5 text-blue-600" />
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">覆盖视频</p>
                            <p className="text-lg font-semibold">{skill.totalVideos}</p>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-green-100">
                            <CheckCircle className="w-5 h-5 text-green-600" />
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground">学习标记</p>
                            <p className="text-lg font-semibold">{skill.totalMarkings}</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="w-4 h-4" />
                        <span>
                          创建于 {new Date(skill.createdAt).toLocaleString("zh-CN")}
                        </span>
                        {skill.updatedAt !== skill.createdAt && (
                          <span>
                            · 更新于 {new Date(skill.updatedAt).toLocaleString("zh-CN")}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2 ml-4">
                      <Button
                        size="sm"
                        variant="outline"
                        className="cursor-pointer"
                        onClick={() => handleViewSkill(skill)}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        查看
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="cursor-pointer"
                        onClick={() => handleDownloadSkill(skill)}
                      >
                        <Download className="w-4 h-4 mr-1" />
                        下载
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* 查看技能文件对话框 */}
      <Dialog
        open={viewDialogOpen}
        onOpenChange={(open) => {
          setViewDialogOpen(open);
          if (!open) {
            setSelectedSkill(null);
            setSkillContent("");
          }
        }}
      >
        <DialogContent className="sm:max-w-[800px] max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>
              技能文件 - 版本 {selectedSkill?.version}
            </DialogTitle>
            <DialogDescription>
              训练项目: {selectedSkill?.totalProjects} · 覆盖视频:{" "}
              {selectedSkill?.totalVideos} · 学习标记: {selectedSkill?.totalMarkings}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto">
            <pre className="bg-slate-50 p-4 rounded-lg text-sm whitespace-pre-wrap">
              {skillContent || "加载中..."}
            </pre>
          </div>
        </DialogContent>
      </Dialog>
    </HangzhouLeimingLayout>
  );
}
