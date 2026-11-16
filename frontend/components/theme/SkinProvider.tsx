"use client";

import { useLayoutEffect } from "react";

import { applySkin, useSkin } from "@/lib/skin";

export function SkinProvider({ children }: { children: React.ReactNode }) {
  const { skin } = useSkin();
  useLayoutEffect(() => {
    applySkin(skin);
  }, [skin]);
  return children;
}
