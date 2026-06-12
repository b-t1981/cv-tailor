"use client";

import { useEffect } from "react";
import { resetWorkspaceSession } from "@/lib/api";
import { runWorkspaceResetOnLoad } from "@/lib/workspace-reset";

runWorkspaceResetOnLoad();

export function WorkspaceReset() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    if (nav && nav.type === "back_forward") return;
    void resetWorkspaceSession().catch(() => {
      /* backend may be offline on first paint */
    });
  }, []);

  return null;
}
