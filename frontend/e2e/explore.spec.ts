import { expect, test } from "@playwright/test";

const stocksTable = (page: import("@playwright/test").Page) => page.getByRole("table", { name: "Stocks" });

test("screener: browse by niche and sub-niche", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("group", { name: "Browse by" }).getByRole("button", { name: "Niches" }).click();
  await expect(page).toHaveURL(/browse=niches/);
  await page.getByRole("button", { name: "Niche AI" }).click();
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(7);

  await page.getByRole("button", { name: "Sub-niche Neoclouds" }).click();
  await expect(page).toHaveURL(/niche=ai&sub=neoclouds/);
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(1);
  await expect(stocksTable(page).getByRole("link", { name: "CRWV" })).toBeVisible();
  await expect(page.getByText("Top movers in Neoclouds")).toBeVisible();

  await page.getByRole("button", { name: "Niche Energy Transition" }).click();
  await expect(page).toHaveURL(/niche=energy-transition/);
  await page.getByLabel("Asset type").selectOption("etf");
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(1);
  await expect(stocksTable(page).getByText("ETF", { exact: true })).toBeVisible();

  await page.getByLabel("Asset type").selectOption("all");
  await expect(page).not.toHaveURL(/type=etf/);
  await page.getByLabel("Index").selectOption("other");
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(2);
});

test("explore: filter by niche and gains", async ({ page }) => {
  await page.goto("/explore");
  await expect(page.getByRole("heading", { name: "Explore niches" })).toBeVisible();
  await page.getByLabel("Niche", { exact: true }).selectOption("energy-transition");
  await expect(page).toHaveURL(/niche=energy-transition/);
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(2);
  await page.getByLabel("Sub-niche").selectOption("small-modular-reactors");
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(1);
  await expect(stocksTable(page).getByRole("link", { name: "OKLO" })).toBeVisible();

  await page.getByRole("button", { name: "Reset filters" }).click();
  await page.getByLabel("Change window").selectOption("chg_1d");
  // Checkbox state lives in the URL, so click and wait for the navigation instead of check().
  await page.getByLabel("Gainers only").click();
  await expect(page).toHaveURL(/gainers=1/);
  await expect(page.getByLabel("Gainers only")).toBeChecked();
  await expect
    .poll(async () => {
      const headers = await stocksTable(page).locator("thead th").allInnerTexts();
      const idx = headers.findIndex((h) => h.trim() === "1D");
      const cells = await stocksTable(page).locator(`tbody tr td:nth-child(${idx + 1})`).allInnerTexts();
      return cells.length > 0 && cells.every((c) => !c.trim().startsWith("-"));
    })
    .toBe(true);
});

test("explore: search the market, add a symbol with niches, then stop tracking it", async ({ page }) => {
  await page.goto("/explore");
  await page.getByLabel("Search the market").fill("nebius");
  const results = page.getByRole("list", { name: "Market search results" });
  await expect(results.locator('[data-symbol="YDX.DE"]').getByText("Not US-listed")).toBeVisible();
  const nbis = results.locator('[data-symbol="NBIS"]');
  await nbis.getByRole("button", { name: "Add NBIS" }).click();
  await nbis.getByLabel("Neoclouds").check();
  await nbis.getByRole("button", { name: "Add to screener" }).click();
  await expect(nbis.getByText("Added.")).toBeVisible({ timeout: 15_000 });

  await page.getByLabel("Niche", { exact: true }).selectOption("ai");
  await page.getByLabel("Sub-niche").selectOption("neoclouds");
  await expect(stocksTable(page).getByRole("link", { name: "NBIS" })).toBeVisible();
  await expect(stocksTable(page).locator('tr[data-ticker="NBIS"]').getByText("Added")).toBeVisible();

  await nbis.getByRole("link", { name: "Open NBIS" }).click();
  await expect(page.getByRole("heading", { name: "Nebius Group N.V." })).toBeVisible();
  await expect(page.getByRole("list", { name: "Company niches" }).getByText("AI › Neoclouds")).toBeVisible();
  await page.getByRole("button", { name: "Stop tracking" }).click();
  await page.getByRole("button", { name: "Confirm: stop tracking NBIS" }).click();
  await expect(page).toHaveURL(/\/explore$/);
  await page.goto("/company/NBIS");
  await expect(page.getByRole("heading", { name: "Unknown ticker NBIS" })).toBeVisible();
});

test("ETF pages skip filings-based research", async ({ page }) => {
  await page.goto("/company/URA");
  await expect(page.getByRole("heading", { name: "Global X Uranium ETF" })).toBeVisible();
  await expect(page.getByRole("tab")).toHaveText(["Overview", "News"]);
  await expect(page.getByRole("list", { name: "Company niches" }).getByText("Energy Transition")).toBeVisible();
});
