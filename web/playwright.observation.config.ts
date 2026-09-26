import { defineConfig } from "@playwright/test"

// This archive surface must work without the fixture API or an account server.
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "observation.spec.ts",
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  workers: 1,
  use: { baseURL: "http://127.0.0.1:5186", browserName: "chromium", headless: true, screenshot: "only-on-failure" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5186 --strictPort", url: "http://127.0.0.1:5186", reuseExistingServer: !process.env.CI, timeout: 60000 },
})
