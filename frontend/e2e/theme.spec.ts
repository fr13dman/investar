import { expect, test } from "@playwright/test";

const html = (page: import("@playwright/test").Page) => page.locator("html");

test("follows the operating system theme by default", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await expect(html(page)).toHaveClass(/\bdark\b/);
  await expect(page.getByRole("button", { name: "Theme: System" })).toBeVisible();

  await page.emulateMedia({ colorScheme: "light" });
  await expect(html(page)).not.toHaveClass(/\bdark\b/);
  await page.reload();
  await expect(html(page)).not.toHaveClass(/\bdark\b/);
});

test("a manual choice overrides the system and survives a reload without hydration errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await page.getByRole("button", { name: "Theme: System" }).click();
  await page.getByRole("menuitemradio", { name: "Light" }).click();
  await expect(html(page)).not.toHaveClass(/\bdark\b/);
  await expect(html(page)).toHaveCSS("color-scheme", "light");

  await page.reload();
  await expect(html(page)).not.toHaveClass(/\bdark\b/);
  await expect(page.getByRole("button", { name: "Theme: Light" })).toBeVisible();

  await page.getByRole("button", { name: "Theme: Light" }).click();
  await page.getByRole("menuitemradio", { name: "Dark" }).click();
  await page.goto("/explore");
  await expect(html(page)).toHaveClass(/\bdark\b/);

  await page.getByRole("button", { name: "Theme: Dark" }).click();
  await page.getByRole("menuitemradio", { name: "System" }).click();
  await page.emulateMedia({ colorScheme: "light" });
  await expect(html(page)).not.toHaveClass(/\bdark\b/);
  expect(errors.filter((e) => /hydrat|script tag/i.test(e))).toEqual([]);
});
