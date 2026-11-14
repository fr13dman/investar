import { useSyncExternalStore } from "react";

import { DARK_QUERY, THEME_STORAGE_KEY } from "./themeScript";

export { THEME_STORAGE_KEY };
export type ThemePreference = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

export const THEME_PREFERENCES: ThemePreference[] = ["system", "light", "dark"];

function isPreference(v: unknown): v is ThemePreference {
  return typeof v === "string" && (THEME_PREFERENCES as string[]).includes(v);
}

export function readPreference(): ThemePreference {
  try {
    const v = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isPreference(v) ? v : "system";
  } catch {
    return "system";
  }
}

export function readSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return "light";
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

export function resolveTheme(preference: ThemePreference, system: ResolvedTheme): ResolvedTheme {
  return preference === "system" ? system : preference;
}

export function applyTheme(theme: ResolvedTheme, opts: { disableTransitions?: boolean } = {}): void {
  const root = document.documentElement;
  let restore: (() => void) | undefined;
  if (opts.disableTransitions) {
    const style = document.createElement("style");
    style.textContent = "*,*::before,*::after{transition:none!important}";
    document.head.appendChild(style);
    restore = () => {
      window.getComputedStyle(document.body);
      setTimeout(() => style.remove(), 1);
    };
  }
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
  restore?.();
}

const listeners = new Set<() => void>();

function subscribePreference(cb: () => void) {
  listeners.add(cb);
  const onStorage = (e: StorageEvent) => {
    if (e.key === THEME_STORAGE_KEY) cb();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", onStorage);
  };
}

function subscribeSystem(cb: () => void) {
  if (typeof window.matchMedia !== "function") return () => {};
  const mq = window.matchMedia(DARK_QUERY);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}

export function setThemePreference(preference: ThemePreference): void {
  try {
    if (preference === "system") window.localStorage.removeItem(THEME_STORAGE_KEY);
    else window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    /* storage disabled: the choice lasts for this page only */
  }
  listeners.forEach((l) => l());
}

/** Theme state shared by every component; server render assumes "system" + light until hydration. */
export function useTheme() {
  const preference = useSyncExternalStore(subscribePreference, readPreference, () => "system" as const);
  const system = useSyncExternalStore(subscribeSystem, readSystemTheme, () => "light" as const);
  return { preference, resolved: resolveTheme(preference, system), setPreference: setThemePreference };
}
