"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import type { Video } from "@/lib/db/schema";

interface EditVideoDialogProps {
  video: Video | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function EditVideoDialog({
  video,
  open,
  onOpenChange,
  onSuccess,
}: EditVideoDialogProps) {
  const [episodeNumber, setEpisodeNumber] = useState<string>("");
  const [displayTitle, setDisplayTitle] = useState<string>("");
  const [sortOrder, setSortOrder] = useState<string>("0");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 当视频数据变化时，更新表单
  useEffect(() => {
    if (video) {
      setEpisodeNumber(video.episodeNumber?.toString() || "");
      setDisplayTitle(video.displayTitle || "");
      setSortOrder(video.sortOrder?.toString() || "0");
    }
  }, [video]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!video) {
      setError("视频数据不存在");
      return;
    }

    try {
      setSaving(true);

      const response = await fetch(`/api/videos/${video.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          episodeNumber: episodeNumber ? parseInt(episodeNumber, 10) : null,
          displayTitle: displayTitle || null,
          sortOrder: parseInt(sortOrder, 10) || 0,
        }),
      });

      const data = await response.json();

      if (data.success) {
        onSuccess();
        onOpenChange(false);
      } else {
        setError(data.message || "更新失败");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>编辑视频信息</DialogTitle>
          <DialogDescription>
            修改视频的集数、显示标题和排序顺序
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            {/* 原始文件名（只读） */}
            <div className="grid gap-2">
              <Label htmlFor="filename" className="text-muted-foreground">
                原始文件名
              </Label>
              <Input
                id="filename"
                value={video?.filename || ""}
                disabled
                className="bg-muted"
              />
            </div>

            {/* 集数 */}
            <div className="grid gap-2">
              <Label htmlFor="episodeNumber">
                集数 <span className="text-muted-foreground">(留空表示无集数)</span>
              </Label>
              <Input
                id="episodeNumber"
                type="number"
                min="1"
                max="200"
                placeholder="例如：1"
                value={episodeNumber}
                onChange={(e) => setEpisodeNumber(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                系统会自动从文件名识别集数，如需修改请手动输入
              </p>
            </div>

            {/* 显示标题 */}
            <div className="grid gap-2">
              <Label htmlFor="displayTitle">
                显示标题 <span className="text-muted-foreground">(可选)</span>
              </Label>
              <Input
                id="displayTitle"
                placeholder="例如：第1集：骨血灯"
                value={displayTitle}
                onChange={(e) => setDisplayTitle(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                留空则使用集数自动生成（如：第1集）
              </p>
            </div>

            {/* 排序顺序 */}
            <div className="grid gap-2">
              <Label htmlFor="sortOrder">
                排序顺序 <span className="text-muted-foreground">(数字越小越靠前)</span>
              </Label>
              <Input
                id="sortOrder"
                type="number"
                min="0"
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                用于调整视频在列表中的显示顺序
              </p>
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">
                {error}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={saving}
            >
              取消
            </Button>
            <Button type="submit" disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              保存
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
