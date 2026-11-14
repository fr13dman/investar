import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ThemeProvider } from "@/components/theme/ThemeProvider";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { CHART_COLORS, useChartColors } from "@/lib/chartTheme";
import { readPreference, resolveTheme, setThemePreference, THEME_STORAGE_KEY } from "@/lib/theme";
import { THEME_INIT_SCRIPT } from "@/lib/themeScript";

let systemDark = true;
const mqListeners = new Set<() => void>();

function setSystemDark(dark: boolean) {
  systemDark = dark;
  mqListeners.forEach((l) => l());
}

beforeEach(() => {
  systemDark = true;
  mqListeners.clear();
  localStorage.clear();
  document.documentElement.className = "";
  document.documentElement.style.colorScheme = "";
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      get matches() {
        return query.includes("dark") && systemDark;
      },
      media: query,
      addEventListener: (_: string, l: () => void) => mqListeners.add(l),
      removeEventListener: (_: string, l: () => void) => mqListeners.delete(l),
    })),
  );
});

afterEach(() => {
  act(() => setThemePreference("system"));
  vi.unstubAllGlobals();
});

const isDark = () => document.documentElement.classList.contains("dark");

describe("theme preference", () => {
  it("defaults to system and ignores garbage in storage", () => {
    expect(readPreference()).toBe("system");
    localStorage.setItem(THEME_STORAGE_KEY, "purple");
    expect(readPreference()).toBe("system");
  });

  it("resolves system to the OS setting and explicit choices to themselves", () => {
    expect(resolveTheme("system", "dark")).toBe("dark");
    expect(resolveTheme("system", "light")).toBe("light");
    expect(resolveTheme("light", "dark")).toBe("light");
    expect(resolveTheme("dark", "light")).toBe("dark");
  });

  it("inline script applies the stored or system theme before React runs", () => {
    new Function(THEME_INIT_SCRIPT)();
    expect(isDark()).toBe(true);
    expect(document.documentElement.style.colorScheme).toBe("dark");
    localStorage.setItem(THEME_STORAGE_KEY, "light");
    new Function(THEME_INIT_SCRIPT)();
    expect(isDark()).toBe(false);
  });
});

describe("ThemeProvider", () => {
  it("follows the operating system while the preference is System", () => {
    render(<ThemeProvider>content</ThemeProvider>);
    expect(isDark()).toBe(true);
    act(() => setSystemDark(false));
    expect(isDark()).toBe(false);
    expect(document.documentElement.style.colorScheme).toBe("light");
  });

  it("an explicit choice overrides the OS and is persisted", () => {
    render(<ThemeProvider>content</ThemeProvider>);
    act(() => setThemePreference("light"));
    expect(isDark()).toBe(false);
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    act(() => setSystemDark(true));
    expect(isDark()).toBe(false);
    act(() => setThemePreference("system"));
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
    expect(isDark()).toBe(true);
  });
});

describe("ThemeToggle", () => {
  it("offers System, Light and Dark and switches the theme", async () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );
    const trigger = screen.getByRole("button", { name: "Theme: System" });
    fireEvent.click(trigger);
    const items = await screen.findAllByRole("menuitemradio");
    expect(items.map((i) => i.textContent?.trim())).toEqual(["System", "Light", "Dark"]);
    expect(items[0]).toHaveAttribute("aria-checked", "true");

    fireEvent.click(items[1]);
    expect(isDark()).toBe(false);
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(await screen.findByRole("button", { name: "Theme: Light" })).toBeInTheDocument();
  });
});

describe("useChartColors", () => {
  it("returns the palette for the resolved theme", () => {
    const { result } = renderHook(() => useChartColors());
    expect(result.current).toBe(CHART_COLORS.dark);
    act(() => setThemePreference("light"));
    expect(result.current).toBe(CHART_COLORS.light);
  });
});
