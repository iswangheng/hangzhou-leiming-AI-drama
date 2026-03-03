"use client";

import { useRouter, usePathname } from "next/navigation";
import { FolderOpen, Scissors, Mic, ListTodo, Settings, Zap } from "lucide-react";
import { ProjectSelector } from "./project-selector";

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  section?: string;
  path: string;
}

const navItems: NavItem[] = [
  { id: "projects", label: "项目管理", icon: <FolderOpen className="w-5 h-5" />, section: "work", path: "/projects" },
  { id: "highlight", label: "高光切片模式", icon: <Scissors className="w-5 h-5" />, section: "work", path: "/highlight" },
  { id: "recap", label: "深度解说模式", icon: <Mic className="w-5 h-5" />, section: "work", path: "/recap" },
  { id: "hangzhou-leiming", label: "杭州雷鸣", icon: <Zap className="w-5 h-5" />, section: "work", path: "/hangzhou-leiming" },
  { id: "tasks", label: "任务管理", icon: <ListTodo className="w-5 h-5" />, section: "system", path: "/tasks" },
];

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();

  // 从 pathname 提取当前活跃的导航项
  const getActiveItemId = () => {
    const path = pathname || "/";
    const item = navItems.find(item => path.startsWith(item.path));
    return item?.id || "projects";
  };

  const activeItem = getActiveItemId();

  const handleNavClick = (item: NavItem) => {
    router.push(item.path);
  };

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[260px] bg-white border-r border-border flex flex-col z-50">
      {/* Logo 区域 */}
      <div className="px-4 py-5 border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-gradient-to-br from-primary to-primary-700 rounded-lg flex items-center justify-center text-white text-lg font-bold">
            ▶
          </div>
          <span className="font-bold text-lg text-foreground">DramaCut AI</span>
        </div>
      </div>

      {/* 项目切换器 */}
      <ProjectSelector />

      {/* 导航菜单 */}
      <nav className="flex-1 px-2 py-3 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
          工作区
        </div>
        {navItems
          .filter((item) => item.section === "work")
          .map((item) => (
            <div
              key={item.id}
              onClick={() => handleNavClick(item)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all mb-0.5 ${
                activeItem === item.id
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <div className="flex-shrink-0">{item.icon}</div>
              <span className="text-sm font-medium">{item.label}</span>
            </div>
          ))}

        <div className="px-3 pb-2 pt-4 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
          系统
        </div>
        {navItems
          .filter((item) => item.section === "system")
          .map((item) => (
            <div
              key={item.id}
              onClick={() => handleNavClick(item)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all mb-0.5 ${
                activeItem === item.id
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <div className="flex-shrink-0">{item.icon}</div>
              <span className="text-sm font-medium">{item.label}</span>
            </div>
          ))}
      </nav>

      {/* 底部设置 */}
      <div className="p-3 border-t border-border/50">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all text-muted-foreground hover:bg-muted/50 hover:text-foreground">
          <Settings className="w-5 h-5" />
          <span className="text-sm font-medium">设置</span>
        </div>
      </div>
    </aside>
  );
}
