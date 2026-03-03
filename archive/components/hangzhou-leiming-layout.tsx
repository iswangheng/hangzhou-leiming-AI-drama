"use client";

/**
 * 杭州雷鸣 - 统一布局组件
 *
 * 为所有杭州雷鸣页面提供统一的外观和导航
 */

import { ReactNode } from "react";
import { HangzhouLeimingNavbar } from "@/components/hangzhou-leiming-navbar";

interface HangzhouLeimingLayoutProps {
  children: ReactNode;
  projectId?: number | null;
}

export function HangzhouLeimingLayout({
  children,
  projectId,
}: HangzhouLeimingLayoutProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* 统一导航栏 */}
      <HangzhouLeimingNavbar projectId={projectId} />

      {/* 页面内容 */}
      {children}
    </div>
  );
}
