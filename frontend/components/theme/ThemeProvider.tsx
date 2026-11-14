"use client";

import { useLayoutEffect, useRef } from "react";

import { applyTheme, useTheme } from "@/lib/theme";

/** Keeps the `dark` class on <html> in sync with the stored preference and the OS setting. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { resolved } = useTheme();
  const first = useRef(true);
  // Layout effect: also re-applies after React Strict Mode's dev remount resets <html> attributes.
  useLayoutEffect(() => {
    applyTheme(resolved, { disableTransitions: !first.current });
    first.current = false;
  }, [resolved]);
  return children;
}
