"use client";

import type { ReactNode } from "react";

interface StickyPrimaryActionProps {
  children: ReactNode;
}

export function StickyPrimaryAction({ children }: StickyPrimaryActionProps) {
  return (
    <div className="sticky bottom-0 z-40 -mx-3 border-t border-slate-200/80 bg-gradient-to-t from-slate-100 via-slate-100/95 to-transparent px-3 py-3 safe-bottom sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:px-0 sm:py-0">
      {children}
    </div>
  );
}
