// Capture UI screenshots from a running Investar instance.
//   node scripts/capture-screenshots.mjs <outDir> [baseUrl] [set]
// set = "live" (real data: screener, research tabs) or "demo" (seeded data: news, patents, watchlists)
import { chromium } from "@playwright/test";

const [out = "screenshots", base = "http://localhost:3010", set = "live"] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

async function tab(ticker, name, readyText, file, { fullPage = true } = {}) {
  await page.goto(`${base}/company/${ticker}`);
  await page.getByRole("tab", { name }).click();
  await page.getByText(readyText).first().waitFor({ timeout: 90_000 });
  await page.waitForTimeout(1500);
  if (!fullPage) await page.getByRole("tab", { name }).evaluate((el) => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 16));
  await page.screenshot({ path: `${out}/${file}`, fullPage });
}

if (set === "live") {
  await page.goto(`${base}/?sector=Technology&industry=Semiconductors&sort=chg_ytd`);
  await page.getByRole("table", { name: "Stocks" }).getByRole("link").first().waitFor();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${out}/01-screener-semiconductors-ytd.png` });

  await page.goto(`${base}/?sort=chg_1d&order=asc&mode=abs`);
  await page.getByRole("table", { name: "Stocks" }).getByRole("link").first().waitFor();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${out}/02-screener-biggest-1d-losers-dollar.png` });

  await page.goto(`${base}/company/NVDA`);
  await page.getByTestId("price-chart").locator("canvas").first().waitFor();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/03-company-overview-chart-vs-spy.png`, fullPage: true });

  await tab("NVDA", "CEO performance", "Return vs SPY", "04-ceo-scorecard.png");
  await tab("AAPL", "Global presence", /Subsidiaries in [1-9]\d* countries/, "05-global-presence-map.png");
} else if (set === "niches") {
  // Seeded data with OFFLINE_PROVIDERS=true: niche browsing, Explore, and both color themes.
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto(`${base}/?browse=niches&niche=ai`);
  await page.getByRole("table", { name: "Stocks" }).getByRole("link").first().waitFor();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${out}/09-screener-niches-ai-dark.png` });

  await page.emulateMedia({ colorScheme: "light" });
  await page.goto(`${base}/explore?niche=energy-transition`);
  await page.getByRole("table", { name: "Stocks" }).getByRole("link").first().waitFor();
  await page.getByLabel("Search the market").fill("nebius");
  await page.getByRole("button", { name: "Add NBIS" }).click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${out}/10-explore-light.png`, fullPage: true });

  await page.goto(`${base}/company/NVDA`);
  await page.getByTestId("price-chart").locator("canvas").first().waitFor();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/11-company-light.png`, fullPage: true });
  await tab("NVDA", "Patents", "Granted patents per year", "12-patents-light.png", { fullPage: false });
} else {
  await tab("AAPL", "News", "Average sentiment", "06-news-sentiment-demo.png");
  await page.setViewportSize({ width: 1440, height: 1200 });
  await tab("NVDA", "Patents", "Granted patents per year", "07-patents-demo.png", { fullPage: false });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${base}/watchlists`);
  await page.getByLabel("New watchlist name").fill("Chips");
  await page.getByRole("button", { name: "Create" }).click();
  const card = page.getByLabel("Watchlist Chips");
  for (const t of ["NVDA", "AMD"]) {
    await card.getByLabel("Add ticker").fill(t);
    await card.getByRole("button", { name: "Add" }).click();
    await card.getByRole("link", { name: t }).waitFor();
  }
  await page.screenshot({ path: `${out}/08-watchlists-demo.png` });
}
await browser.close();
