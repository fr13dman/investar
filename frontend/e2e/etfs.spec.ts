import { expect, test } from "@playwright/test";

test("ETF hub shows niche map and VistaShares families", async ({ page }) => {
  await page.goto("/etfs");
  await expect(page.getByRole("heading", { name: "Niche ETFs" })).toBeVisible();
  await expect(page.getByRole("img", { name: "ETF performance map" })).toBeVisible();
  await expect(page.getByRole("link", { name: "AIS" }).first()).toBeVisible();

  await page.getByRole("link", { name: "VistaShares" }).click();
  await expect(page.getByRole("heading", { name: "VistaShares ETFs" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Supercycle" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Target 15" })).toBeVisible();
});

test("ETF company page has holdings heatmap", async ({ page }) => {
  await page.goto("/company/AIS");
  await expect(page.getByRole("heading", { name: /VistaShares Artificial Intelligence/i })).toBeVisible();
  await page.getByRole("tab", { name: "Holdings" }).click();
  await expect(page.getByRole("heading", { name: "Holdings allocation" })).toBeVisible();
  await expect(page.getByRole("img", { name: "AIS holdings heatmap" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh" })).toBeVisible();
});

test("screener ETFs browse mode filters to ETFs", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "ETFs", exact: true }).click();
  await expect(page).toHaveURL(/browse=etfs/);
  await expect(page.getByText(/Showing curated niche ETFs/)).toBeVisible();
});
