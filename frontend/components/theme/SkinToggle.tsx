"use client";

import { LayoutTemplateIcon } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SKIN_PREFERENCES, useSkin, type SkinPreference } from "@/lib/skin";

const LABELS: Record<SkinPreference, string> = {
  investar: "Investar",
  finviz: "Finviz",
};

export function SkinToggle() {
  const { skin, setSkin } = useSkin();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Skin: ${LABELS[skin]}`}
        className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <LayoutTemplateIcon className="size-4" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-36">
        <DropdownMenuRadioGroup value={skin} onValueChange={(v) => setSkin(v as SkinPreference)}>
          {SKIN_PREFERENCES.map((p) => (
            <DropdownMenuRadioItem key={p} value={p}>
              {LABELS[p]}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
