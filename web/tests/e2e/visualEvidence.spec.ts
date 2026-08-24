import { mkdirSync } from "node:fs"
import { resolve } from "node:path"

import { test } from "@playwright/test"

function evidencePath(testInfo: import("@playwright/test").TestInfo, name: string): string {
  if (process.env.RIFTCOACH_CAPTURE_DOCS !== "1") {
    return testInfo.outputPath(`${name}.png`)
  }
  const root = resolve(process.cwd(), "..", "docs", "assets", "8e-batch-d")
  mkdirSync(root, { recursive: true })
  return resolve(root, `${name}.jpg`)
}

async function capture(
  page: import("@playwright/test").Page,
  testInfo: import("@playwright/test").TestInfo,
  name: string,
) {
  const persistent = process.env.RIFTCOACH_CAPTURE_DOCS === "1"
  if (persistent) {
    await page.screenshot({ path: evidencePath(testInfo, name), fullPage: true, type: "jpeg", quality: 88 })
    return
  }
  await page.screenshot({ path: evidencePath(testInfo, name), fullPage: true, type: "png" })
}

const visualCases = [
  { name: "desktop-published", path: "/?scenario=published", width: 1440, height: 1000 },
  { name: "desktop-degraded", path: "/?scenario=degraded", width: 1440, height: 1000 },
  { name: "tablet-published", path: "/?scenario=published", width: 1024, height: 900 },
  { name: "mobile-published", path: "/?scenario=published", width: 390, height: 844 },
] as const

for (const visualCase of visualCases) {
  test(`captures ${visualCase.name} for manual QA`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: visualCase.width, height: visualCase.height })
    await page.goto(visualCase.path)
    await capture(page, testInfo, visualCase.name)
  })
}

test("captures desktop evidence drawer for manual QA", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto("/?scenario=published")
  await page.getByRole("button", { name: /open evidence/i }).click()
  await capture(page, testInfo, "desktop-evidence-drawer")
  await page.getByRole("dialog", { name: /review evidence/i }).evaluate((element) => {
    element.scrollTop = element.scrollHeight
  })
  await capture(page, testInfo, "desktop-evidence-drawer-bottom")
})

test.use({ reducedMotion: "reduce" })
test("captures reduced-motion desktop for manual QA", async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto("/?scenario=published")
  await capture(page, testInfo, "desktop-reduced-motion")
})
