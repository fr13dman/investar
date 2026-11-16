import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { SkinProvider } from "@/components/theme/SkinProvider";
import { SkinToggle } from "@/components/theme/SkinToggle";
import { applySkin, readSkin, setSkinPreference, SKIN_STORAGE_KEY } from "@/lib/skin";
import { SKIN_INIT_SCRIPT } from "@/lib/skinScript";

describe("skin preference", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-skin");
  });

  it("defaults to investar and persists finviz", () => {
    expect(readSkin()).toBe("investar");
    setSkinPreference("finviz");
    expect(window.localStorage.getItem(SKIN_STORAGE_KEY)).toBe("finviz");
    expect(document.documentElement.dataset.skin).toBe("finviz");
    setSkinPreference("investar");
    expect(window.localStorage.getItem(SKIN_STORAGE_KEY)).toBeNull();
  });

  it("inline script applies stored skin before React", () => {
    window.localStorage.setItem(SKIN_STORAGE_KEY, "finviz");
    // eslint-disable-next-line no-eval
    eval(SKIN_INIT_SCRIPT);
    expect(document.documentElement.dataset.skin).toBe("finviz");
  });

  it("SkinToggle switches skins", () => {
    applySkin("investar");
    render(
      <SkinProvider>
        <SkinToggle />
      </SkinProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Skin: Investar" }));
    fireEvent.click(screen.getByRole("menuitemradio", { name: "Finviz" }));
    expect(document.documentElement.dataset.skin).toBe("finviz");
    expect(screen.getByRole("button", { name: "Skin: Finviz" })).toBeInTheDocument();
  });
});
