import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

async function expectNoHorizontalOverflow(page: import("@playwright/test").Page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
}

test.describe("Rift Command Center", () => {
  test("renders the published desktop hierarchy without overflow or serious accessibility violations", async ({ page }) => {
    const remoteRequests: string[] = []
    page.on("request", (request) => {
      const url = new URL(request.url())
      if (!new Set(["127.0.0.1", "localhost"]).has(url.hostname)) {
        remoteRequests.push(request.url())
      }
    })
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto("/?scenario=published")

    await expect(page.getByRole("heading", { level: 1, name: "Rift Command Center" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "Riverline#EUW" })).toBeVisible()
    await expect(page.getByText("Published", { exact: true })).toBeVisible()
    await expect(page.getByText(/Fixture preview/i)).toBeVisible()
    await expect(page.getByText(/Aggregate segments · not a match history/i)).toBeVisible()
    await expect(page.getByRole("heading", { name: /match phase review/i })).toBeVisible()
    await expect(page.getByRole("list", { name: /chronological events/i })).toBeVisible()
    await page.getByRole("button", { name: /game 2.*ahri/i }).focus()
    await page.keyboard.press("Enter")
    await expect(page.getByRole("button", { name: /05:12 hextech alternator/i })).toBeVisible()
    await expectNoHorizontalOverflow(page)

    const results = await new AxeBuilder({ page }).analyze()
    const blocking = results.violations.filter((violation) =>
      violation.impact === "critical" || violation.impact === "serious",
    )
    expect(blocking).toEqual([])
    expect(remoteRequests).toEqual([])
  })

  test("opens the Evidence Drawer by keyboard, closes with Escape and returns focus", async ({ page }) => {
    await page.goto("/?scenario=published")
    const trigger = page.getByRole("button", { name: /open evidence/i })

    await trigger.focus()
    await page.keyboard.press("Enter")
    await expect(page.getByRole("dialog", { name: /evidence ledger/i })).toBeVisible()
    await expect(page.getByText("Riot Match API")).toBeVisible()
    await expect(page.getByText("OP.GG meta snapshot")).toBeVisible()
    await expect(page.getByRole("heading", { name: /safe run path/i })).toBeVisible()
    await page.keyboard.press("Escape")
    await expect(page.getByRole("dialog", { name: /evidence ledger/i })).toBeHidden()
    await expect(trigger).toBeFocused()
  })

  test("keeps product states structurally honest", async ({ page }) => {
    await page.goto("/?scenario=degraded")
    await expect(page.getByText("Degraded", { exact: true })).toBeVisible()
    await expect(page.getByRole("heading", { name: /tactical brief/i })).toBeVisible()
    await expect(page.getByText("evidence_expired", { exact: true })).toBeVisible()

    await page.goto("/?scenario=rejected")
    await expect(page.getByText("Rejected", { exact: true })).toBeVisible()
    await expect(page.getByRole("heading", { name: /review withheld/i })).toBeVisible()
    await expect(page.getByRole("heading", { name: /tactical brief/i })).toHaveCount(0)

    await page.goto("/?scenario=not_ready")
    await expect(page.getByText("Not ready", { exact: true })).toBeVisible()
    await expect(page.getByText("task_pending", { exact: true })).toBeVisible()
    await expect(page.locator("body")).not.toContainText(/\d+%/)
  })

  test("does not rebind one player's review when switching to an observed profile", async ({ page }) => {
    await page.goto("/?scenario=published")
    await page.getByRole("combobox", { name: /player profile/i }).selectOption("profile-northstar-kr")

    await expect(page.getByRole("heading", { name: "Northstar#KR" })).toBeVisible()
    await expect(page.getByRole("heading", { name: /learning observation/i })).toBeVisible()
    await expect(page.getByText(/no loaded review in the current fixture/i)).toBeVisible()
    await expect(page.getByRole("heading", { name: /recent form/i })).toHaveCount(0)
    await expect(page.getByRole("heading", { name: /match phase review/i })).toHaveCount(0)
    await expect(page.getByRole("heading", { name: /your training plan/i })).toHaveCount(0)
  })

  test("reflows the tablet and mobile layouts without clipping", async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 900 })
    await page.goto("/?scenario=published")
    await expectNoHorizontalOverflow(page)
    const tabletGrid = await page.locator(".command-layout").evaluate((element) => getComputedStyle(element).gridTemplateColumns)
    expect(tabletGrid.split(" ")).toHaveLength(1)

    await page.setViewportSize({ width: 390, height: 844 })
    await expectNoHorizontalOverflow(page)
    const navBox = await page.getByRole("navigation", { name: /command sections/i }).boundingBox()
    expect(navBox?.width).toBeGreaterThanOrEqual(389)
    await page.getByRole("button", { name: /open evidence/i }).click()
    const dialogBox = await page.getByRole("dialog", { name: /evidence ledger/i }).boundingBox()
    expect(dialogBox?.width).toBeLessThanOrEqual(390.1)
    await page.keyboard.press("Escape")

    await page.setViewportSize({ width: 320, height: 740 })
    await expectNoHorizontalOverflow(page)
  })

  test.use({ reducedMotion: "reduce" })
  test("preserves the visual identity while disabling continuous and transform motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" })
    await page.goto("/?scenario=published")
    const behavior = await page.evaluate(() => {
      const atmosphere = document.querySelector<HTMLElement>(".rift-atmosphere")
      const orbit = document.querySelector<HTMLElement>(".coach-core__orbit")
      const workspace = document.querySelector<HTMLElement>(".review-workspace")
      return {
        atmosphereAnimation: atmosphere === null ? "missing" : getComputedStyle(atmosphere).animationName,
        orbitAnimation: orbit === null ? "missing" : getComputedStyle(orbit).animationName,
        workspaceTransform: workspace === null ? "missing" : getComputedStyle(workspace).transform,
        atmosphereVisible: atmosphere !== null && Number.parseFloat(getComputedStyle(atmosphere).opacity) > 0,
      }
    })
    expect(behavior.atmosphereAnimation).toBe("none")
    expect(behavior.orbitAnimation).toBe("none")
    expect(behavior.workspaceTransform).toBe("none")
    expect(behavior.atmosphereVisible).toBe(true)
  })
})
