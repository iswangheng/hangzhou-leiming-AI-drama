// ============================================
// 编辑项目对话框组件
// ============================================

"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Edit } from "lucide-react";

interface EditProjectDialogProps {
  projectId: number;
  projectName: string;
  projectDescription?: string | null;
  onUpdate?: () => void;
}

export function EditProjectDialog({
  projectId,
  projectName,
  projectDescription,
  onUpdate,
}: EditProjectDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(projectName);
  const [description, setDescription] = useState(projectDescription || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 打开对话框时重置表单
  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (newOpen) {
      setName(projectName);
      setDescription(projectDescription || "");
      setError(null);
    }
  };

  // 保存编辑
  const handleSave = async () => {
    // 验证
    if (!name.trim()) {
      setError("项目名称不能为空");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const response = await fetch(`/api/projects/${projectId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
        }),
      });

      const result = await response.json();

      if (result.success) {
        // 关闭对话框
        setOpen(false);
        // 通知父组件刷新
        onUpdate?.();
      } else {
        setError(result.message || "更新失败");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Edit className="w-4 h-4 mr-2" />
          编辑
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>编辑项目</DialogTitle>
          <DialogDescription>修改项目名称和描述信息</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* 项目名称 */}
          <div className="space-y-2">
            <Label htmlFor="name">
              项目名称 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="输入项目名称"
              disabled={saving}
            />
          </div>

          {/* 项目描述 */}
          <div className="space-y-2">
            <Label htmlFor="description">项目描述</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="输入项目描述（可选）"
              rows={3}
              disabled={saving}
            />
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={saving}
          >
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                保存中...
              </span>
            ) : (
              "保存"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
