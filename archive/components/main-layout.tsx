"use client";

import { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { ProjectProvider } from "@/contexts/project-context";

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <ProjectProvider>
      <div className="min-h-screen bg-background">
        <Sidebar />
        <main className="ml-[260px] min-h-screen">
          {children}
        </main>
      </div>
    </ProjectProvider>
  );
}
