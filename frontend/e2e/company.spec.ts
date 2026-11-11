import { expect, test } from "@playwright/test";

test("open a company from the screener and explore research tabs", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("table", { name: "Stocks" }).getByRole("link", { name: "AAPL" }).click();
  await expect(page).toHaveURL(/\/company\/AAPL$/);
  await expect(page.getByRole("heading", { name: "Apple Inc." })).toBeVisible();
  await expect(page.getByTestId("live-price")).toContainText("$");
  await expect(page.getByText("Delayed (Yahoo)", { exact: false })).toBeVisible();

  // Candlestick chart renders a canvas; switching ranges refetches.
  await expect(page.getByTestId("price-chart").locator("canvas").first()).toBeVisible();
  await page.getByRole("group", { name: "Chart range" }).getByRole("button", { name: "5Y" }).click();
  await expect(page.getByRole("group", { name: "Chart range" }).getByRole("button", { name: "5Y" })).toHaveAttribute("aria-pressed", "true");

  // CEO scorecard
  await page.getByRole("tab", { name: "CEO performance" }).click();
  await expect(page.getByText("Jordan Avery").first()).toBeVisible();
  await expect(page.getByText("Return vs SPY")).toBeVisible();
  await expect(page.getByRole("table", { name: "Pay versus performance" })).toBeVisible();
  await page.getByLabel("Tenure start").fill("2025-06-02");
  await page.getByRole("button", { name: "Save override" }).click();
  await expect(page.getByText(/CEO since Jun 2, 2025 \(set manually\)/)).toBeVisible();

  // News with sentiment
  await page.getByRole("tab", { name: "News" }).click();
  const news = page.getByRole("list", { name: "News" });
  await expect(news.getByRole("listitem")).toHaveCount(5);
  await page.getByRole("group", { name: "Sentiment filter" }).getByRole("button", { name: /^positive/ }).click();
  const positives = await news.getByRole("listitem").count();
  expect(positives).toBeGreaterThan(0);
  expect(positives).toBeLessThan(5);
});

test("sector breadcrumb links back to a filtered screener", async ({ page }) => {
  await page.goto("/company/NVDA");
  await page.getByRole("link", { name: "Semiconductors" }).click();
  await expect(page).toHaveURL(/sector=Technology&industry=Semiconductors/);
  await expect(page.getByRole("table", { name: "Stocks" }).locator("tbody tr")).toHaveCount(2);
});

test("unknown ticker shows a helpful page", async ({ page }) => {
  await page.goto("/company/ZZZZ");
  await expect(page.getByRole("heading", { name: "Unknown ticker ZZZZ" })).toBeVisible();
});
