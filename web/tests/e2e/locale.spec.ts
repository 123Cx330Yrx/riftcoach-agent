import AxeBuilder from "@axe-core/playwright"
import { randomUUID } from "node:crypto"
import { expect, test, type Locator, type Page } from "@playwright/test"

const STORAGE_KEY = "riftcoach.ui-locale.v1"
const SELF = "95000000-0000-4000-8000-000000000001"

function uniqueTestId(prefix: string) {
  return `${prefix}-${randomUUID()}`
}

async function useScenario(page: Page, scenario: string, testId: string) {
  await page.context().addCookies([
    { name: "riftcoach-test-scenario", value: scenario, domain: "127.0.0.1", path: "/" },
    { name: "riftcoach-test-id", value: testId, domain: "127.0.0.1", path: "/" },
  ])
}

async function requestLedger(page: Page, testId: string) {
  const response = await page.request.get(`http://127.0.0.1:4174/__requests?test_id=${testId}`)
  expect(response.ok()).toBe(true)
  return await response.json() as { requests: string[]; open_streams: number; closed_streams: number }
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
}

async function expectInsideViewport(locator: Locator, page: Page) {
  const box = await locator.boundingBox()
  const viewport = page.viewportSize()
  expect(box).not.toBeNull()
  expect(viewport).not.toBeNull()
  expect(box!.x).toBeGreaterThanOrEqual(-1)
  expect(box!.y).toBeGreaterThanOrEqual(-1)
  expect(box!.x + box!.width).toBeLessThanOrEqual(viewport!.width + 1)
}

test.describe("bilingual product surface", () => {
  test("persists an exact locale envelope and preserves generated content bytes", async ({ page }) => {
    await page.goto("/?scenario=published")
    const report = /Protect your farm baseline, then make every early river move/i
    const trainingTitle = "Objective-first movement"
    const trainingObjective = "Name the wave state before every early river move."

    await expect(page.getByText(report)).toBeVisible()
    await expect(page.getByText(trainingTitle, { exact: true })).toBeVisible()
    await expect(page.getByText(trainingObjective, { exact: true })).toBeVisible()

    const chinese = page.getByRole("button", { name: "中文" })
    await chinese.click()

    await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN")
    await expect(chinese).toHaveAttribute("aria-pressed", "true")
    expect(await page.evaluate((key) => window.localStorage.getItem(key), STORAGE_KEY)).toBe(
      '{"schema_version":"1.0","locale":"zh-CN"}',
    )
    await expect(page.getByText(report)).toBeVisible()
    await expect(page.getByText(trainingTitle, { exact: true })).toBeVisible()
    await expect(page.getByText(trainingObjective, { exact: true })).toBeVisible()

    await page.reload()
    await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN")
    await expect(page.getByRole("heading", { level: 1, name: "对局复盘" })).toBeVisible()
    await expect(page.getByText(report)).toBeVisible()
  })

  test("supports keyboard switching without moving focus away from the chosen control", async ({ page }) => {
    await page.goto("/?scenario=published")
    const chinese = page.getByRole("button", { name: "中文" })

    await chinese.focus()
    await page.keyboard.press("Space")

    await expect(chinese).toBeFocused()
    await expect(chinese).toHaveAttribute("aria-pressed", "true")
    await expect(page.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "false")
  })

  test("keeps Portal and Workbench Chinese layouts inside desktop, 390 and 320 pixel viewports", async ({ page }, testInfo) => {
    for (const viewport of [
      { width: 1440, height: 1000 },
      { width: 390, height: 844 },
      { width: 320, height: 740 },
    ]) {
      await page.setViewportSize(viewport)
      await page.goto("/?surface=awakening")
      const portalChinese = page.getByRole("button", { name: "中文" })
      await portalChinese.click()
      await expect(portalChinese).toHaveAttribute("aria-pressed", "true")
      await page.mouse.move(0, 0)
      await expect(page.getByRole("heading", { name: "看懂这一局，打好下一局。" })).toBeVisible()
      await expectNoHorizontalOverflow(page)
      await expectInsideViewport(page.locator(".locale-switch"), page)
      const portalFit = await page.locator(".awakening-scene__header, .awakening-scene__hero, .awakening-scene__enter-hint").evaluateAll(
        (elements) => elements.every((element) => element.scrollWidth <= element.clientWidth + 1),
      )
      expect(portalFit).toBe(true)
      await page.screenshot({
        path: testInfo.outputPath(`portal-zh-${viewport.width}.png`),
        fullPage: true,
      })

      await page.goto("/?scenario=published")
      await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN")
      await expect(page.getByRole("button", { name: "中文" })).toHaveAttribute("aria-pressed", "true")
      await page.mouse.move(0, 0)
      await expect(page.getByRole("heading", { level: 1, name: "对局复盘" })).toBeVisible()
      await expectNoHorizontalOverflow(page)
      await expectInsideViewport(page.locator(".command-rail .locale-switch"), page)
      await page.screenshot({
        path: testInfo.outputPath(`workbench-zh-${viewport.width}.png`),
        fullPage: true,
      })

      await page.getByRole("button", { name: "打开证据" }).click()
      const drawer = page.getByRole("dialog", { name: "复盘证据" })
      await expect(drawer).toBeVisible()
      await expectInsideViewport(drawer, page)
      await expectNoHorizontalOverflow(page)
      const results = await new AxeBuilder({ page }).analyze()
      expect(results.violations.filter((violation) =>
        violation.impact === "critical" || violation.impact === "serious",
      )).toEqual([])
      await page.screenshot({
        path: testInfo.outputPath(`evidence-zh-${viewport.width}.png`),
        fullPage: true,
      })
      await page.keyboard.press("Escape")
    }
  })

  test("translates auth recovery without exposing internal codes", async ({ page }) => {
    await page.route("**/api/auth/session", (route) => route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ code: "auth_unavailable" }),
    }))

    await page.goto("/")
    await page.getByRole("button", { name: "中文" }).click()
    await page.getByRole("button", { name: /进入 RiftCoach/i }).click()
    await expect(page.getByRole("heading", { name: "暂时无法登录" })).toBeVisible()
    await expect(page.getByText("现在还无法打开已保存的玩家。")).toBeVisible()
    await expect(page.getByText("auth_unavailable", { exact: true })).toHaveCount(0)
  })

  test("does not refetch APIs or reconnect an open SSE channel on locale switch", async ({ page }) => {
    const testId = uniqueTestId("locale-open-stream")
    await useScenario(page, "locale-open-stream", testId)
    await page.goto(`/?stage=workbench&player_profile_id=${SELF}`)
    await expect(page.getByText("In progress", { exact: true })).toBeVisible()
    await expect(page.getByText("Early death control", { exact: true })).toBeVisible()
    await expect.poll(async () => (await requestLedger(page, testId)).open_streams).toBe(1)
    const before = await requestLedger(page, testId)

    await page.getByRole("button", { name: "中文" }).click()
    await expect(page.locator(".product-state__label")).toHaveText("分析中")
    await expect(page.getByText("Early death control", { exact: true })).toBeVisible()
    const after = await requestLedger(page, testId)

    expect(after.requests).toEqual(before.requests)
    expect(after.open_streams).toBe(before.open_streams)
    expect(after.closed_streams).toBe(before.closed_streams)
  })

  test("keeps the Portal preview local while switching language", async ({ page }) => {
    const apiRequests: string[] = []
    const remoteRequests: string[] = []
    page.on("request", (request) => {
      const url = new URL(request.url())
      if (["xhr", "fetch"].includes(request.resourceType()) && url.pathname.startsWith("/api/")) {
        apiRequests.push(request.url())
      }
      if (!new Set(["127.0.0.1", "localhost"]).has(url.hostname)) remoteRequests.push(request.url())
    })

    await page.goto("/?surface=awakening")
    await page.getByRole("button", { name: "中文" }).click()
    await expect(page.getByText(/仅供预览 · 不查询外部数据，也不登录/)).toBeVisible()
    expect(apiRequests).toEqual([])
    expect(remoteRequests).toEqual([])
  })
})
