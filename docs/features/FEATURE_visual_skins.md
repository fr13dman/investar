# Feature: Visual skins (Investar / Finviz)

Color mode (System / Light / Dark) and **visual skin** are independent. Skins change typography, density and
heat-map chrome; light/dark still apply inside each skin. Default skin is **Investar**; **Finviz** is opt-in.

## What was built

| Area | Files |
| --- | --- |
| Pre-paint script | `frontend/lib/skinScript.ts` (`data-skin` on `<html>`) |
| State | `frontend/lib/skin.ts` (`useSkin`, `setSkinPreference`, `applySkin`) |
| Provider | `frontend/components/theme/SkinProvider.tsx` |
| Header control | `frontend/components/theme/SkinToggle.tsx` (next to `ThemeToggle`) |
| Tokens | `frontend/app/globals.css` — `[data-skin=finviz]` overrides |

## How it works

1. Inline head script sets `document.documentElement.dataset.skin` to `investar` or `finviz` before paint.
2. `useSkin()` stores preference in `localStorage` key `investar-skin` (absent = investar).
3. Finviz skin uses a Tahoma/Arial stack, tighter table padding, smaller radius, and classic green/red heat
   CSS variables (`--heat-up`, `--heat-down`, …) consumed by ETF treemaps.

```ts
// frontend/lib/skin.ts
export type SkinPreference = "investar" | "finviz";
export function applySkin(skin: SkinPreference): void {
  document.documentElement.dataset.skin = skin;
}
```

```css
:root { --app-font-sans: var(--font-geist-sans), ui-sans-serif, system-ui, sans-serif; }
@theme inline { --font-sans: var(--app-font-sans); }
html[data-skin="finviz"] {
  --app-font-sans: Tahoma, Arial, "Helvetica Neue", Helvetica, sans-serif;
  --radius: 0.15rem;
  --heat-up: #008000;
  --heat-down: #c80000;
}
```

## Design notes

- Skins are an extension point for future looks without forking routes.
- Finviz v1 is a **token + density** skin plus map-first ETF pages — not a full redesign of every research panel.
- Light/dark remains orthogonal; Finviz defines both light and dark heat colors.

## Technologies considered

| Approach | Decision |
| --- | --- |
| Replace Investar UI with Finviz only | Rejected — keep default Investar, add skin system |
| next-themes for skins | Rejected — same custom pattern as light/dark (React 19 / FOUC control) |
| Per-route skin default on `/etfs` | Rejected — global preference is clearer |

## Tests

- Unit: `frontend/__tests__/skin.test.tsx`
- E2E: Finviz skin opt-in in `frontend/e2e/theme.spec.ts`
