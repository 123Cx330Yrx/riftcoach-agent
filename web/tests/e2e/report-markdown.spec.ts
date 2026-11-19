import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page } from "@playwright/test"
import { createHash, randomUUID } from "node:crypto"
import { readFileSync } from "node:fs"

// Original sealed report, copied without prose edits. This is frontend fixture
// evidence only; the local API does not run SQL, generation or review requests.
const report = readFileSync(new URL("../fixtures/verified-report-20261103.md", import.meta.url), "utf8")
const reportUrl = "**/api/runs/review_live_workbench_1/report"
const workbenchUrl = "/?stage=workbench&player_profile_id=95000000-0000-4000-8000-000000000001"

async function openReport(page: Page, markdown: string) {
  const testId = `report-markdown-${randomUUID()}`
  const remote: string[] = [], writes: string[] = [], errors: string[] = []
  page.on("request", (request) => {
    if (!["127.0.0.1", "localhost"].includes(new URL(request.url()).hostname)) remote.push(request.url())
    if (!["GET", "HEAD"].includes(request.method())) writes.push(`${request.method()} ${request.url()}`)
  })
  page.on("pageerror", (error) => errors.push(error.message))
  await page.context().addCookies([
    { name: "riftcoach-test-scenario", value: "published", domain: "127.0.0.1", path: "/" },
    { name: "riftcoach-test-id", value: testId, domain: "127.0.0.1", path: "/" },
  ])
  await page.addInitScript(() => localStorage.setItem("riftcoach.ui-locale.v1", JSON.stringify({ schema_version: "1.0", locale: "zh-CN" })))
  await page.route(reportUrl, (route) => route.fulfill({ contentType: "text/markdown; charset=utf-8", body: markdown }))
  const response = page.waitForResponse((response) => response.url().endsWith("/report"))
  await page.goto(workbenchUrl)
  expect(await (await response).text()).toBe(markdown)
  await expect(page.locator(".safe-markdown")).toBeVisible()
  return { testId, remote, writes, errors }
}

for (const width of [1440, 320]) {
  test(`full original report is readable and inert at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 })
    const observed = await openReport(page, report)
    const body = page.locator(".safe-markdown")
    await expect(body).toHaveAttribute("translate", "no")
    await expect(body.getByRole("heading")).toHaveCount(8)
    await expect(body.getByRole("heading", { level: 4 })).toHaveText("RiftCoach 教练式复盘报告")
    await expect(body.getByRole("heading", { level: 5 })).toHaveCount(7)
    await expect(body.getByRole("listitem")).toHaveCount(15)
    await expect(body.getByRole("table")).toHaveCount(1)
    await expect(body.getByRole("row")).toHaveCount(4)
    expect(await body.getByRole("cell").allTextContents()).toEqual([
      "补刀/分钟", "8.14", "5.38", "输局低 2.75",
      "伤害/分钟", "1280.92", "535.77", "输局低 745.15",
      "视野分", "23", "52.67", "输局高 29.67",
    ])
    for (const line of report.split(/\r?\n/).filter((line) => line && !line.startsWith("|"))) {
      await expect(body).toContainText(line.replace(/^#{1,6} |^(?:- |\d+\. )/g, "").replace(/\*\*/g, ""))
    }
    await expect(body.locator("a,img,script,iframe,input,[href],[src]")).toHaveCount(0)
    const widths = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }))
    expect(widths.scroll).toBeLessThanOrEqual(widths.client)
    const table = body.getByRole("region", { name: "报告表格" })
    const tableWidths = await table.evaluate((node) => ({ client: node.clientWidth, scroll: node.scrollWidth }))
    await table.focus()
    await expect(table).toBeFocused()
    if (width === 320) {
      await expect(body.getByText("左右滑动查看完整表格")).toBeVisible()
      expect(tableWidths.scroll).toBeGreaterThan(tableWidths.client)
      await page.keyboard.press("ArrowRight")
      await expect.poll(() => table.evaluate((node) => node.scrollLeft)).toBeGreaterThan(0)
      await page.keyboard.press("ArrowLeft")
      await expect.poll(() => table.evaluate((node) => node.scrollLeft)).toBe(0)
    }
    expect((await new AxeBuilder({ page }).include(".safe-markdown").analyze()).violations).toEqual([])
    await body.screenshot({ path: testInfo.outputPath(`report-full-${width}.png`) })
    await table.screenshot({ path: testInfo.outputPath(`report-table-${width}.png`) })
    for (const [name, selector] of [["top", "h4"], ["table", ".safe-markdown__table-scroll"], ["end", "h5:last-of-type"]]) {
      await body.locator(selector).evaluate((node) => {
        node.scrollIntoView({ block: "start", behavior: "instant" })
        window.scrollBy({ top: -160, behavior: "instant" })
      })
      // The last section can be clamped by the document's maximum scroll.
      await expect.poll(() => body.locator(selector).evaluate((node) => {
        const top = node.getBoundingClientRect().top
        return top >= 159 && top < window.innerHeight - 100
      })).toBe(true)
      await page.screenshot({ path: testInfo.outputPath(`viewport-${name}-${width}.png`) })
    }
    const ledger = await (await page.request.get(`http://127.0.0.1:4174/__requests?test_id=${observed.testId}`)).json()
    // Existing client bootstraps a synthetic auth session. No task/recovery,
    // model, source, memory or training mutation is permitted by this fixture.
    expect(ledger.requests.filter((entry: string) => !entry.startsWith("GET "))).toEqual(["POST /auth/session"])
    expect(observed.remote).toEqual([])
    expect(observed.writes).toEqual(["POST http://127.0.0.1:4173/api/auth/session"])
    expect(observed.errors).toEqual([])
    await testInfo.attach("readonly-report-evidence", {
      body: JSON.stringify({ width, report_sha256: createHash("sha256").update(report).digest("hex"), heading_count: 8, list_items: 15, table_rows: 4, widths, tableWidths, ...observed, ledger }, null, 2),
      contentType: "application/json",
    })
  })
}

test("unsafe report syntax creates no active DOM or remote requests", async ({ page }) => {
  const markdown = '# Unsafe fixture\n\n<script>window.reportExecuted=true</script>\n\n<img src="https://evil.invalid/pixel" onerror="window.reportExecuted=true">\n\n[run](javascript:alert%281%29)\n\n[![nested](https://evil.invalid/pixel)](https://evil.invalid)\n\n<iframe src="https://evil.invalid"></iframe>\n\nhttps://evil.invalid\n\n- [x] text only'
  const observed = await openReport(page, markdown)
  const body = page.locator(".safe-markdown")
  await expect(body.getByRole("heading", { name: "Unsafe fixture", level: 4 })).toBeVisible()
  await expect(body.locator("a,img,script,iframe,input,svg,form,object,embed,style,link,[href],[src],[onerror]")).toHaveCount(0)
  await expect(body).toContainText('[![nested](https://evil.invalid/pixel)](https://evil.invalid)')
  expect(await page.evaluate(() => "reportExecuted" in window)).toBe(false)
  expect(observed.remote).toEqual([])
  expect(observed.writes).toEqual(["POST http://127.0.0.1:4173/api/auth/session"])
  expect(observed.errors).toEqual([])
})
