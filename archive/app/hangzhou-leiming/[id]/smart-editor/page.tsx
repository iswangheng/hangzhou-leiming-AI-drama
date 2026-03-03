"use client";

/**
 * 杭州雷鸣 - 智能剪辑页面
 *
 * 功能：
 * - 上传新视频
 * - AI自动标记高光点和钩子点
 * - 生成剪辑组合
 * - 按广告转化效果排序
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Upload,
  Video,
  Sparkles,
  Play,
  Clock,
  TrendingUp,
  Loader2,
  Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { HangzhouLeimingLayout } from "@/components/hangzhou-leiming-layout";

interface HLVideo {
  id: number;
  filename: string;
  filePath: string;
  durationMs: number;
}

interface HLSkill {
  id: number;
  name: string;
  content: string;
}

interface ClipCombination {
  id: string;
  name: string;
  clips: Array<{
    videoId: number;
    videoName: string;
    startMs: number;
    endMs: number;
    type: string;
  }>;
  totalDurationMs: number;
  overallScore: number;
  reasoning: string;
}

export default function SmartEditorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const [projectId, setProjectId] = useState<number | null>(null);

  // 数据状态
  const [newVideos, setNewVideos] = useState<HLVideo[]>([]);
  const [skills, setSkills] = useState<HLSkill[]>([]);
  const [combinations, setCombinations] = useState<ClipCombination[]>([]);

  // 配置
  const [selectedSkillId, setSelectedSkillId] = useState<number | null>(null);
  const [minDuration, setMinDuration] = useState([120]);
  const [maxDuration, setMaxDuration] = useState([300]);

  // 处理状态
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [exporting, setExporting] = useState(false);

  // 加载projectId
  useEffect(() => {
    params.then((resolvedParams) => {
      setProjectId(parseInt(resolvedParams.id));
    });
  }, [params]);

  // 加载数据
  useEffect(() => {
    if (projectId) {
      loadSkills();
      loadNewVideos();
    }
  }, [projectId]);

  const loadSkills = async () => {
    try {
      // 加载全局技能（由训练中心管理）
      const res = await fetch("/api/hangzhou-leiming/training-center/skills");
      const result = await res.json();
      if (result.success && result.data) {
        // 将全局技能转换为组件需要的格式
        setSkills([{
          id: result.data.id,
          name: `全局技能 v${result.data.version}`,
          content: result.data.skillFilePath,
        }]);
        setSelectedSkillId(result.data.id);
      }
    } catch (error) {
      console.error("加载技能失败:", error);
    }
  };

  const loadNewVideos = async () => {
    if (!projectId) return;

    try {
      const res = await fetch(
        `/api/hangzhou-leiming/videos/new?projectId=${projectId}`
      );
      const result = await res.json();
      if (result.success) {
        setNewVideos(result.data || []);
      }
    } catch (error) {
      console.error("加载视频失败:", error);
    }
  };

  // 上传新视频
  const handleUploadVideo = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (!e.target.files || e.target.files.length === 0 || !projectId) return;

    try {
      setUploading(true);
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append("file", file);
      formData.append("projectId", String(projectId));
      formData.append("episodeNumber", "新视频");
      formData.append("displayTitle", file.name);

      const res = await fetch("/api/hangzhou-leiming/videos", {
        method: "POST",
        body: formData,
      });

      const result = await res.json();

      if (result.success) {
        alert("视频上传成功！");
        await loadNewVideos();
      } else {
        alert(`上传失败：${result.message}`);
      }
    } catch (error) {
      console.error("上传视频失败:", error);
      alert("上传视频失败");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  // 生成剪辑组合
  const handleGenerateCombinations = async () => {
    if (!projectId || !selectedSkillId) {
      alert("请先选择技能文件");
      return;
    }

    if (newVideos.length === 0) {
      alert("请先上传视频");
      return;
    }

    try {
      setAnalyzing(true);
      const res = await fetch(
        `/api/hangzhou-leiming/projects/${projectId}/analyze`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            skillId: selectedSkillId,
            minDurationMs: minDuration[0] * 1000,
            maxDurationMs: maxDuration[0] * 1000,
          }),
        }
      );

      const result = await res.json();

      if (result.success) {
        setCombinations(result.data || []);
      } else {
        alert(`分析失败：${result.message}`);
      }
    } catch (error) {
      console.error("生成组合失败:", error);
      alert("生成组合失败");
    } finally {
      setAnalyzing(false);
    }
  };

  // 格式化时长
  const formatDuration = (ms: number) => {
    const totalSeconds = Math.floor(ms / 1000);
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // 导出视频
  const handleExport = async (combinationId: string) => {
    if (!projectId) return;

    try {
      setExporting(true);

      const res = await fetch("/api/hangzhou-leiming/exports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          combinationId: parseInt(combinationId),
          projectId,
        }),
      });

      const result = await res.json();

      if (result.success) {
        alert("导出任务已创建！正在后台处理，请前往导出中心查看进度。");
        // 跳转到导出中心查看进度
        router.push(`/hangzhou-leiming/${projectId}/export`);
      } else {
        alert(`导出失败：${result.message}`);
      }
    } catch (error) {
      console.error("导出失败:", error);
      alert("导出失败，请稍后重试");
    } finally {
      setExporting(false);
    }
  };

  // 等待projectId
  if (projectId === null) {
    return (
      <HangzhouLeimingLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
        </div>
      </HangzhouLeimingLayout>
    );
  }

  return (
    <HangzhouLeimingLayout projectId={projectId}>
      {/* Main Content */}
      <div className="container mx-auto px-4 py-8 space-y-6">
        {/* 页面标题 */}
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
            智能剪辑
          </h1>
          <p className="text-muted-foreground mt-2">
            AI 自动标记，智能推荐剪辑组合
          </p>
        </div>
        {/* 步骤1：上传视频 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Video className="w-5 h-5" />
              步骤1：上传新视频
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">
                  上传需要分析的短剧视频
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  已上传 {newVideos.length} 个视频
                </p>
              </div>
              <Button
                variant="outline"
                disabled={uploading}
                onClick={() => document.getElementById('video-upload-smart')?.click()}
                className="cursor-pointer"
              >
                {uploading ? (
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
                id="video-upload-smart"
                type="file"
                accept="video/*"
                className="hidden"
                onChange={handleUploadVideo}
                disabled={uploading}
              />
            </div>

            {/* 视频列表 */}
            {newVideos.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {newVideos.map((video) => (
                  <div
                    key={video.id}
                    className="flex items-center gap-3 p-3 bg-muted rounded-lg"
                  >
                    <Video className="w-10 h-10 text-orange-600" />
                    <div className="flex-1">
                      <p className="font-medium">{video.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDuration(video.durationMs)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 步骤2：配置分析 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5" />
              步骤2：配置分析参数
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* 技能选择 */}
            <div className="space-y-2">
              <Label>选择技能文件</Label>
              {skills.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  暂无技能文件，请先在训练中心完成学习
                </p>
              ) : (
                <select
                  className="w-full px-3 py-2 border rounded-md cursor-pointer"
                  value={selectedSkillId || ""}
                  onChange={(e) => setSelectedSkillId(parseInt(e.target.value))}
                >
                  {skills.map((skill) => (
                    <option key={skill.id} value={skill.id}>
                      {skill.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* 时长设定 */}
            <div className="space-y-4">
              <Label>剪辑时长范围（秒）</Label>
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">最短时长</span>
                    <span className="text-sm font-medium">{minDuration[0]} 秒</span>
                  </div>
                  <Slider
                    value={minDuration}
                    onValueChange={setMinDuration}
                    min={30}
                    max={300}
                    step={10}
                    className="cursor-pointer"
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">最长时长</span>
                    <span className="text-sm font-medium">{maxDuration[0]} 秒</span>
                  </div>
                  <Slider
                    value={maxDuration}
                    onValueChange={setMaxDuration}
                    min={60}
                    max={600}
                    step={10}
                    className="cursor-pointer"
                  />
                </div>
              </div>
            </div>

            {/* 生成按钮 */}
            <Button
              onClick={handleGenerateCombinations}
              disabled={
                analyzing ||
                newVideos.length === 0 ||
                !selectedSkillId
              }
              className="w-full cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
            >
              {analyzing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  AI 分析中...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  生成剪辑组合
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* 步骤3：查看推荐 */}
        {combinations.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                步骤3：推荐剪辑组合
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                AI 已生成 {combinations.length} 个剪辑组合，按广告转化效果排序
              </p>

              <div className="space-y-4">
                {combinations.map((combo, index) => (
                  <div
                    key={combo.id}
                    className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-r from-orange-500 to-red-500 text-white font-bold">
                            {index + 1}
                          </div>
                          <h3 className="font-semibold text-lg">{combo.name}</h3>
                          <div className="flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                            <TrendingUp className="w-3 h-3" />
                            {combo.overallScore.toFixed(0)} 分
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground mb-3">
                          {combo.reasoning}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Clock className="w-4 h-4" />
                        {formatDuration(combo.totalDurationMs)}
                      </div>
                    </div>

                    {/* 片段列表 */}
                    <div className="space-y-2 mb-3">
                      {combo.clips.map((clip, clipIndex) => (
                        <div
                          key={clipIndex}
                          className="flex items-center gap-3 p-2 bg-muted rounded text-sm"
                        >
                          <div
                            className={`px-2 py-1 rounded-full text-xs ${
                              clip.type === "高光点"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-orange-100 text-orange-800"
                            }`}
                          >
                            {clip.type}
                          </div>
                          <span className="flex-1">{clip.videoName}</span>
                          <span className="text-muted-foreground">
                            {formatDuration(clip.startMs)} - {formatDuration(clip.endMs)}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1 cursor-pointer"
                        onClick={() => alert("预览功能开发中...")}
                      >
                        <Play className="w-4 h-4 mr-2" />
                        预览
                      </Button>
                      <Button
                        size="sm"
                        className="flex-1 cursor-pointer bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
                        onClick={() => handleExport(combo.id)}
                        disabled={exporting}
                      >
                        {exporting ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            导出中...
                          </>
                        ) : (
                          <>
                            <Download className="w-4 h-4 mr-2" />
                            导出视频
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </HangzhouLeimingLayout>
  );
}
