"use client";

/**
 * 杭州雷鸣 - 统一导航栏组件
 *
 * 用于所有杭州雷鸣页面，提供一致的导航体验
 */

import { useRouter, usePathname } from "next/navigation";
import {
  Brain,
  FolderOpen,
  Video,
  FileText,
  Wand2,
  Download,
} from "lucide-react";

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  description: string;
}

const navItems: NavItem[] = [
  {
    id: "training-center",
    label: "训练中心",
    icon: <Brain className="w-5 h-5" />,
    path: "/hangzhou-leiming/training-center",
    description: "训练全局剪辑技能",
  },
  {
    id: "projects",
    label: "项目管理",
    icon: <FolderOpen className="w-5 h-5" />,
    path: "/hangzhou-leiming",
    description: "管理所有短剧项目",
  },
];

interface ProjectNavItems {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  description: string;
}

const projectNavItems: ProjectNavItems[] = [
  {
    id: "videos",
    label: "视频管理",
    icon: <Video className="w-5 h-5" />,
    path: "/videos",
    description: "上传和管理视频",
  },
  {
    id: "markings",
    label: "标记管理",
    icon: <FileText className="w-5 h-5" />,
    path: "/markings",
    description: "查看和管理标记",
  },
  {
    id: "smart-editor",
    label: "智能剪辑",
    icon: <Wand2 className="w-5 h-5" />,
    path: "/smart-editor",
    description: "AI 自动标注和剪辑",
  },
  {
    id: "export",
    label: "导出中心",
    icon: <Download className="w-5 h-5" />,
    path: "/export",
    description: "导出成品视频",
  },
];

interface HangzhouLeimingNavbarProps {
  projectId?: number | null;
}

export function HangzhouLeimingNavbar({
  projectId,
}: HangzhouLeimingNavbarProps) {
  const router = useRouter();
  const pathname = usePathname();

  // 判断当前是否在训练中心
  const isInTrainingCenter = pathname.startsWith("/hangzhou-leiming/training-center");

  // 判断当前是否在项目详情页
  const isInProjectPage = projectId && pathname.startsWith(`/hangzhou-leiming/${projectId}`);

  // 项目详情页不显示导航菜单，只显示返回按钮
  if (isInProjectPage) {
    return (
      <nav className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <h1 className="text-xl font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
                杭州雷鸣
              </h1>
            </div>
          </div>
        </div>
      </nav>
    );
  }

  // 获取当前活跃的导航项
  const getActiveItemId = () => {
    if (isInTrainingCenter) {
      // 训练中心的子页面（按精确度排序，越精确的越靠前）
      if (pathname === "/hangzhou-leiming/training-center/skills") return "skills";
      if (pathname === "/hangzhou-leiming/training-center/history") return "history";
      if (pathname === "/hangzhou-leiming/training-center/training") return "training";
      if (pathname === "/hangzhou-leiming/training-center") return "training-center";

      // 兼容带查询参数的情况
      if (pathname.startsWith("/hangzhou-leiming/training-center/skills")) return "skills";
      if (pathname.startsWith("/hangzhou-leiming/training-center/history")) return "history";
      if (pathname.startsWith("/hangzhou-leiming/training-center/training")) return "training";

      return "training-center";
    }

    if (isInProjectPage) {
      // 项目详情页的子页面
      if (pathname.endsWith("/videos")) return "videos";
      if (pathname.endsWith("/markings")) return "markings";
      if (pathname.endsWith("/smart-editor")) return "smart-editor";
      if (pathname.endsWith("/export")) return "export";
      return "project-detail";
    }

    return "projects";
  };

  const activeItem = getActiveItemId();

  const handleNavClick = (item: NavItem | ProjectNavItems) => {
    if (projectId && "path" in item && !item.path.startsWith("/hangzhou-leiming/training-center")) {
      router.push(`/hangzhou-leiming/${projectId}${item.path}`);
    } else {
      router.push(item.path);
    }
  };

  return (
    <div className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* 左侧：Logo 和 返回按钮 */}
          <div className="flex items-center gap-4">
            <div
              className="flex items-center gap-2 cursor-pointer"
              onClick={() => router.push("/hangzhou-leiming")}
            >
              <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg flex items-center justify-center text-white">
                ⚡
              </div>
              <div>
                <h1 className="text-lg font-bold bg-gradient-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
                  杭州雷鸣
                </h1>
              </div>
            </div>

            {/* 返回按钮（在子页面显示） */}
            {(isInTrainingCenter || isInProjectPage) && (
              <>
                <div className="h-6 w-px bg-gray-300" />
                <div className="text-sm text-muted-foreground">
                  {isInTrainingCenter && "训练中心"}
                  {isInProjectPage && "项目详情"}
                </div>
              </>
            )}
          </div>

          {/* 右侧：导航菜单 */}
          <nav className="flex items-center gap-1">
            {isInTrainingCenter ? (
              // 训练中心导航
              <>
                <NavItem
                  item={{
                    id: "training-home",
                    label: "首页",
                    icon: <Brain className="w-4 h-4" />,
                    path: "/hangzhou-leiming/training-center",
                    description: "",
                  }}
                  active={activeItem === "training-center"}
                  onClick={() => router.push("/hangzhou-leiming/training-center")}
                />
                <NavItem
                  item={{
                    id: "training",
                    label: "开始训练",
                    icon: <Wand2 className="w-4 h-4" />,
                    path: "/hangzhou-leiming/training-center/training",
                    description: "",
                  }}
                  active={activeItem === "training"}
                  onClick={() => router.push("/hangzhou-leiming/training-center/training")}
                />
                <NavItem
                  item={{
                    id: "skills",
                    label: "技能管理",
                    icon: <FileText className="w-4 h-4" />,
                    path: "/hangzhou-leiming/training-center/skills",
                    description: "",
                  }}
                  active={activeItem === "skills"}
                  onClick={() => router.push("/hangzhou-leiming/training-center/skills")}
                />
                <NavItem
                  item={{
                    id: "history",
                    label: "训练历史",
                    icon: <Video className="w-4 h-4" />,
                    path: "/hangzhou-leiming/training-center/history",
                    description: "",
                  }}
                  active={activeItem === "history"}
                  onClick={() => router.push("/hangzhou-leiming/training-center/history")}
                />
              </>
            ) : isInProjectPage ? (
              // 项目详情页导航
              projectNavItems.map((item) => (
                <NavItem
                  key={item.id}
                  item={item}
                  active={activeItem === item.id}
                  onClick={() => handleNavClick(item)}
                />
              ))
            ) : (
              // 项目列表页导航
              <NavItem
                item={{
                  id: "training-center",
                  label: "训练中心",
                  icon: <Brain className="w-4 h-4" />,
                  path: "/hangzhou-leiming/training-center",
                  description: "",
                }}
                active={false}
                onClick={() => router.push("/hangzhou-leiming/training-center")}
              />
            )}
          </nav>
        </div>
      </div>
    </div>
  );
}

// 导航项组件
function NavItem({
  item,
  active,
  onClick,
}: {
  item: any;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-all text-sm font-medium ${
        active
          ? "bg-orange-100 text-orange-700"
          : "text-gray-600 hover:bg-gray-100"
      }`}
    >
      {item.icon}
      <span>{item.label}</span>
    </div>
  );
}
