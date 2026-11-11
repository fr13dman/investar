import { expect, test } from "@playwright/test";

test("global presence: subsidiary map and revenue by region", async ({ page }) => {
  await page.goto("/company/AAPL");
  await page.getByRole("tab", { name: "Global presence" }).click();
  await expect(page.getByText(/Subsidiaries in 7 countries/)).toBeVisible(); // IE, JP, IN, GB, US, HK, BR
  // Real react-simple-maps rendering from the bundled world-atlas topology.
  const map = page.getByLabel("Subsidiary countries map");
  await expect(map.locator("path").first()).toBeVisible();
  expect(await map.locator("path").count()).toBeGreaterThan(100);
  await expect(map.locator('path[data-country="IE"]')).toHaveCount(1);
  const byCountry = page.getByRole("list", { name: "Subsidiaries by country" });
  await expect(byCountry.getByText("Ireland")).toBeVisible();
  await expect(byCountry.getByText("(not on map)")).toBeVisible(); // Hong Kong
  const revenue = page.getByRole("table", { name: "Revenue by region" });
  await expect(revenue.getByText("Other Countries")).toBeVisible();
  await expect(revenue.getByText("47.8%")).toBeVisible();
});

test("patents: totals, lists and assignee editing", async ({ page }) => {
  await page.goto("/company/NVDA");
  await page.getByRole("tab", { name: "Patents" }).click();
  await expect(page.getByTestId("applications-total")).toHaveText("2,700");
  await expect(page.getByRole("list", { name: "Granted patents" }).getByRole("listitem")).toHaveCount(50);
  await expect(page.getByRole("list", { name: "Pending applications" }).getByRole("listitem")).toHaveCount(25);
  await expect(page.getByRole("list", { name: "Patent assignee names" }).getByText("NVIDIA Corporation")).toBeVisible();

  await page.getByRole("textbox", { name: "Assignee name" }).fill("Mellanox Technologies");
  await page.getByLabel("Match type").selectOption("prefix");
  await page.getByRole("button", { name: "Add name" }).click();
  await expect(page.getByRole("list", { name: "Patent assignee names" }).getByText("Mellanox Technologies")).toBeVisible();
});

test("companies without filings show empty states", async ({ page }) => {
  await page.goto("/company/PEP");
  await page.getByRole("tab", { name: "Global presence" }).click();
  await expect(page.getByText(/No Exhibit 21 subsidiary list/)).toBeVisible();
  await expect(page.getByText(/Not reported/)).toBeVisible();
});
