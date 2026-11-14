"use client";

import { MonitorIcon, MoonIcon, SunIcon } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { THEME_PREFERENCES, useTheme, type ThemePreference } from "@/lib/theme";

const OPTIONS: Record<ThemePreference, { label: string; Icon: typeof SunIcon }> = {
  system: { label: "System", Icon: MonitorIcon },
  light: { label: "Light", Icon: SunIcon },
  dark: { label: "Dark", Icon: MoonIcon },
};

export function ThemeToggle() {
  const { preference, resolved, setPreference } = useTheme();
  const Current = preference === "system" ? MonitorIcon : resolved === "dark" ? MoonIcon : SunIcon;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Theme: ${OPTIONS[preference].label}`}
        className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <Current className="size-4" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-36">
        <DropdownMenuRadioGroup value={preference} onValueChange={(v) => setPreference(v as ThemePreference)}>
          {THEME_PREFERENCES.map((p) => {
            const { label, Icon } = OPTIONS[p];
            return (
              <DropdownMenuRadioItem key={p} value={p}>
                <Icon /> {label}
              </DropdownMenuRadioItem>
            );
          })}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
