import { mkdirSync } from "node:fs"
import { dirname, resolve } from "node:path"

import { test } from "@playwright/test"

const cases = [
  { name: "timeline-desktop", path: "/?scenario=published", width: 1440, height: 1000 },
  { name: "timeline-mobile", path: "/?scenario=published", width: 390, height: 844 },
  { name: "timeline-partial", path: "/?scenario=degraded", width: 1024, height: 900 },
] as const

for (const item of cases) {
  test(`captures ${item.name} for Timeline QA`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: item.width, height: item.height })
    await page.goto(item.path)
    await page.locator("#timeline").scrollIntoViewIfNeeded()
    if (item.name === "timeline-partial") {
      await page.getByRole("button", { name: /game 2.*ahri/i }).click()
    }
    const persistent = process.env.RIFTCOACH_CAPTURE_TIMELINE_DOCS === "1"
    const path = persistent
      ? resolve(process.cwd(), "..", "docs", "assets", "8e-timeline", `${item.name}.jpg`)
      : testInfo.outputPath(`${item.name}.png`)
    if (persistent) mkdirSync(dirname(path), { recursive: true })
    await page.locator("#timeline").screenshot({
      path,
      ...(persistent ? { type: "jpeg" as const, quality: 90 } : { type: "png" as const }),
    })
  })
}
