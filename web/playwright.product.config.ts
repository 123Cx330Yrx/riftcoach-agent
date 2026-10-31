import { defineConfig } from "@playwright/test"

const apiPort = process.env.RIFTCOACH_BROWSER_API_PORT
if (!apiPort || !/^\d{2,5}$/.test(apiPort)) throw new Error("Start through the disposable Python browser check")
export default defineConfig({
  testDir: "./tests/product-browser", fullyParallel: false, workers: 1, retries: 0,
  timeout: 90_000, expect: { timeout: 15_000 }, reporter: "list",
  outputDir: process.env.RIFTCOACH_BROWSER_OUTPUT ?? "test-results/product",
  use: { baseURL: "http://127.0.0.1:4183", browserName: "chromium", headless: true,
    screenshot: "only-on-failure", trace: "retain-on-failure", video: "off" },
  webServer: { command: "node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 4183",
    url: "http://127.0.0.1:4183", reuseExistingServer: false,
    env: { RIFTCOACH_WEB_API_TARGET: `http://127.0.0.1:${apiPort}` } },
})
