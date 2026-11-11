import { expect, test } from "@playwright/test";

const stocksTable = (page: import("@playwright/test").Page) => page.getByRole("table", { name: "Stocks" });

async function columnValues(page: import("@playwright/test").Page, header: string): Promise<number[]> {
  const headers = await stocksTable(page).locator("thead th").allInnerTexts();
  const idx = headers.findIndex((h) => h.trim() === header);
  const texts = await stocksTable(page).locator(`tbody tr td:nth-child(${idx + 1})`).allInnerTexts();
  return texts.map((t) => Number(t.replace(/[^0-9.-]/g, "")));
}

test("filter by sector and industry, then sort by swings", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Stock screener" })).toBeVisible();
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(12);

  await page.getByRole("button", { name: "Sector Technology" }).click();
  await expect(page).toHaveURL(/sector=Technology/);
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(6);

  await page.getByRole("button", { name: "Industry Semiconductors" }).click();
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(2);
  await expect(stocksTable(page).getByRole("link", { name: "NVDA" })).toBeVisible();
  await expect(page.getByText("Top movers in Semiconductors")).toBeVisible();

  await page.getByRole("button", { name: "All Technology" }).click();
  await stocksTable(page).getByRole("button", { name: "YTD" }).click();
  await expect(page).toHaveURL(/sort=chg_ytd/);
  await expect.poll(async () => {
    const v = await columnValues(page, "YTD");
    return v.length === 6 && v.every((x, i) => i === 0 || v[i - 1] >= x);
  }).toBe(true);

  await stocksTable(page).getByRole("button", { name: "YTD" }).click();
  await expect(page).toHaveURL(/order=asc/);
  await expect.poll(async () => {
    const v = await columnValues(page, "YTD");
    return v.every((x, i) => i === 0 || v[i - 1] <= x);
  }).toBe(true);

  const firstYtd = async () => {
    const headers = await stocksTable(page).locator("thead th").allInnerTexts();
    const idx = headers.findIndex((h) => h.trim() === "YTD");
    return stocksTable(page).locator(`tbody tr:first-child td:nth-child(${idx + 1})`).innerText();
  };
  await expect.poll(firstYtd).toMatch(/%$/);
  await page.getByRole("button", { name: "$" }).click();
  await expect(page).toHaveURL(/mode=abs/);
  await expect.poll(firstYtd).toMatch(/^[+-]?\$/);
});

test("index filter and search", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Index").selectOption("ndx100");
  await expect(stocksTable(page).getByRole("link", { name: "ASML" })).toBeVisible();
  await expect(stocksTable(page).getByRole("link", { name: "JPM" })).toHaveCount(0);

  await page.getByLabel("Index").selectOption("all");
  await page.getByLabel("Search ticker or company").fill("goldman");
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(1);
  await expect(stocksTable(page).getByRole("link", { name: "GS" })).toBeVisible();
});

test("watchlists: create, add from the screener, filter", async ({ page }) => {
  await page.goto("/watchlists");
  await page.getByLabel("New watchlist name").fill("Chips");
  await page.getByRole("button", { name: "Create" }).click();
  const card = page.getByLabel("Watchlist Chips");
  await expect(card).toBeVisible();
  await card.getByLabel("Add ticker").fill("AMD");
  await card.getByRole("button", { name: "Add" }).click();
  await expect(card.getByRole("link", { name: "AMD" })).toBeVisible();

  await page.goto("/");
  await page.getByRole("button", { name: "Watchlists for NVDA" }).click();
  await page.getByRole("menuitemcheckbox", { name: /Chips/ }).click();
  await expect(page.getByRole("menuitemcheckbox", { name: /Chips/ })).toHaveAttribute("aria-checked", "true");

  await page.getByLabel("Watchlist", { exact: true }).selectOption({ label: "Chips" });
  await expect(stocksTable(page).locator("tbody tr")).toHaveCount(2);
});
