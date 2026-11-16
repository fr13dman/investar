import { useSyncExternalStore } from "react";

import { SKIN_STORAGE_KEY } from "./skinScript";

export { SKIN_STORAGE_KEY };
export type SkinPreference = "investar" | "finviz";

export const SKIN_PREFERENCES: SkinPreference[] = ["investar", "finviz"];

function isSkin(v: unknown): v is SkinPreference {
  return typeof v === "string" && (SKIN_PREFERENCES as string[]).includes(v);
}

export function readSkin(): SkinPreference {
  try {
    const v = window.localStorage.getItem(SKIN_STORAGE_KEY);
    return isSkin(v) ? v : "investar";
  } catch {
    return "investar";
  }
}

export function applySkin(skin: SkinPreference): void {
  document.documentElement.dataset.skin = skin;
}

const listeners = new Set<() => void>();

function subscribe(cb: () => void) {
  listeners.add(cb);
  const onStorage = (e: StorageEvent) => {
    if (e.key === SKIN_STORAGE_KEY) cb();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", onStorage);
  };
}

export function setSkinPreference(skin: SkinPreference): void {
  try {
    if (skin === "investar") window.localStorage.removeItem(SKIN_STORAGE_KEY);
    else window.localStorage.setItem(SKIN_STORAGE_KEY, skin);
  } catch {
    /* storage disabled */
  }
  applySkin(skin);
  listeners.forEach((l) => l());
}

export function useSkin() {
  const skin = useSyncExternalStore(subscribe, readSkin, () => "investar" as const);
  return { skin, setSkin: setSkinPreference };
}
