import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

const API_PORT = 8100;
const WEB_PORT = 3100;
const backendDir = path.resolve(__dirname, "../backend");
const dbFile = path.resolve(__dirname, "e2e/.data/e2e.db");
const backendEnv = `DATABASE_URL=sqlite:///${dbFile} ENABLE_SCHEDULER=false FINNHUB_API_KEY= PATENTSVIEW_API_KEY= OFFLINE_PROVIDERS=true`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Seeded, offline database: no live API calls during end-to-end tests.
      command: `rm -f ${dbFile}* && mkdir -p ${path.dirname(dbFile)} && cd ${backendDir} && ${backendEnv} uv run investar seed-demo && ${backendEnv} uv run uvicorn app.main:app --port ${API_PORT}`,
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `INVESTAR_API_ORIGIN=http://127.0.0.1:${API_PORT} pnpm exec next dev --port ${WEB_PORT}`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
