import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page } from "@playwright/test"
import { randomUUID } from "node:crypto"

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

async function expectNoOverflow(page: Page) {
  const widths = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }))
  expect(widths.scroll).toBeLessThanOrEqual(widths.client + 1)
}

test.describe("live owner-scoped workbench", () => {
  test("moves from active SSE to authoritative published content with no remote I/O", async ({ page }) => {
    const testId = uniqueTestId("active-published")
    await useScenario(page, "active", testId)
    const remote: string[] = []
    page.on("request", (request) => {
      const hostname = new URL(request.url()).hostname
      if (hostname !== "127.0.0.1" && hostname !== "localhost") remote.push(request.url())
    })

    await page.goto("/")
    await expect(page.getByText("Live server projection", { exact: true })).toBeVisible()
    await expect(page.getByText("Not ready", { exact: true })).toBeVisible()
    await expect(page.getByText("Published", { exact: true })).toBeVisible({ timeout: 5_000 })
    await expect(page.getByRole("heading", { name: "Recent performance snapshot" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Match phase review" })).toBeVisible()
    await expect(page.getByRole("button", { name: /baron nashor secured at 27:44/i })).toBeVisible()
    await expect(page.getByText(/## Verified brief/)).toBeVisible()
    await expect(page.getByText("Early death control", { exact: true })).toBeVisible()

    const ledger = await requestLedger(page, testId)
    expect(ledger.requests.some((path) => path.includes("/events/stream"))).toBe(true)
    expect(ledger.open_streams).toBe(0)
    expect(remote).toEqual([])
  })

  test("keeps degraded, rejected and empty states honest and escapes report markup", async ({ page }) => {
    await useScenario(page, "degraded", uniqueTestId("degraded"))
    await page.goto("/")
    await expect(page.getByText("Degraded", { exact: true })).toBeVisible()
    await expect(page.getByText(/1 of 2 timelines unavailable/i)).toBeVisible()
    await expect(page.getByText(/## Limited brief/)).toBeVisible()
    expect(await page.locator(".safe-markdown a, .safe-markdown img, .safe-markdown script").count()).toBe(0)

    await useScenario(page, "rejected", uniqueTestId("rejected"))
    await page.reload()
    await expect(page.getByText("Rejected", { exact: true })).toBeVisible()
    await expect(page.getByRole("heading", { name: /review withheld/i })).toBeVisible()
    await expect(page.locator(".safe-markdown")).toHaveCount(0)

    await useScenario(page, "empty", uniqueTestId("empty"))
    await page.reload()
    await expect(page.getByRole("heading", { name: /no player profiles yet/i })).toBeVisible()
  })

  test("clears self content, closes its stream and never requests personal Training for observed", async ({ page }) => {
    const testId = uniqueTestId("switch-observed")
    await useScenario(page, "switch", testId)
    await page.goto("/")
    await expect(page.getByText("Not ready", { exact: true })).toBeVisible()

    await page.getByRole("combobox", { name: /player profile/i }).selectOption("95000000-0000-4000-8000-000000000002")
    await expect(page.getByRole("heading", { name: "Northstar#KR" })).toBeVisible()
    await expect(page.getByRole("heading", { name: /learning observation/i })).toBeVisible()
    await expect(page.getByRole("heading", { name: /recent performance snapshot/i })).toHaveCount(0)

    await expect.poll(async () => (await requestLedger(page, testId)).closed_streams).toBeGreaterThan(0)
    const ledger = await requestLedger(page, testId)
    expect(ledger.requests.filter((path) => path.includes("training-plan"))).toHaveLength(1)
    expect(ledger.requests.filter((path) => path.includes("training-progress"))).toHaveLength(1)
  })

  test("uses only a server-listed URL profile and skips observed Training", async ({ page }) => {
    const testId = uniqueTestId("url-observed")
    await useScenario(page, "switch", testId)

    await page.goto("/?player_profile_id=95000000-0000-4000-8000-000000000002")

    await expect(page.getByRole("heading", { name: "Northstar#KR" })).toBeVisible()
    await expect(page.getByRole("heading", { name: /learning observation/i })).toBeVisible()
    const ledger = await requestLedger(page, testId)
    expect(ledger.requests.filter((path) => path.includes("training-plan"))).toHaveLength(0)
    expect(ledger.requests.filter((path) => path.includes("training-progress"))).toHaveLength(0)
  })

  test("preserves four responsive viewports, keyboard focus, reduced motion and a11y", async ({ page }) => {
    await useScenario(page, "published", uniqueTestId("responsive"))
    for (const viewport of [
      { width: 1440, height: 1000 },
      { width: 1024, height: 900 },
      { width: 390, height: 844 },
      { width: 320, height: 740 },
    ]) {
      await page.setViewportSize(viewport)
      await page.goto("/")
      await expect(page.getByText("Published", { exact: true })).toBeVisible()
      await expectNoOverflow(page)
    }

    const trigger = page.getByRole("button", { name: /open evidence/i })
    await trigger.focus()
    await page.keyboard.press("Enter")
    await expect(page.getByRole("dialog", { name: /evidence ledger/i })).toBeVisible()
    await page.keyboard.press("Escape")
    await expect(trigger).toBeFocused()

    await page.emulateMedia({ reducedMotion: "reduce" })
    await page.reload()
    const animations = await page.evaluate(() => ({
      atmosphere: getComputedStyle(document.querySelector<HTMLElement>(".rift-atmosphere")!).animationName,
      orbit: getComputedStyle(document.querySelector<HTMLElement>(".coach-core__orbit")!).animationName,
    }))
    expect(animations).toEqual({ atmosphere: "none", orbit: "none" })

    const results = await new AxeBuilder({ page }).analyze()
    expect(results.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious")).toEqual([])
  })
})
