import { expect, test } from "@playwright/test"

test.describe("Rift Awakening portal preview", () => {
  test("keeps the cinematic preview local and free of account controls", async ({ page }) => {
    const apiRequests: string[] = []
    page.on("request", (request) => {
      const pathname = new URL(request.url()).pathname
      if (["xhr", "fetch"].includes(request.resourceType()) && pathname.startsWith("/api/")) {
        apiRequests.push(request.url())
      }
    })

    await page.goto("/?surface=awakening")
    await expect(page.getByRole("heading", { name: /read the rift/i })).toBeVisible()
    await expect(page.getByText(/preview only · no external lookup/i)).toBeVisible()
    await expect(page.getByTestId("awakening-scene")).toHaveAttribute("data-phase", "idle")
    await expect(page.getByLabel("Riot ID")).toHaveCount(0)
    await expect(page.getByRole("button", { name: /view the demo/i })).toBeVisible()
    expect(apiRequests).toEqual([])

    await page.screenshot({ path: "test-results/awakening-desktop.png", fullPage: true })
  })

  test("keeps the core usable on a narrow viewport and freezes reduced motion", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.emulateMedia({ reducedMotion: "reduce" })
    await page.goto("/?surface=awakening")

    const scene = page.getByTestId("awakening-scene")
    await expect(scene).toHaveAttribute("data-motion", "full")
    const core = page.getByRole("button", { name: /view the demo/i })
    await expect(core).toBeVisible()
    await core.focus()
    await expect(core).toBeFocused()
    expect(await page.locator(".awakening-scene__core-orbit").first().evaluate(
      (element) => getComputedStyle(element).animationName,
    )).toBe("none")
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.screenshot({ path: "test-results/awakening-mobile-reduced.png", fullPage: true })
  })

  test("hands an explicit demo preview only into the fixture workbench", async ({ page }) => {
    await page.goto("/?surface=awakening&demo=ready")
    await expect(page.getByRole("button", { name: /view the demo/i })).toBeVisible()

    await page.getByRole("button", { name: /view the demo/i }).click()
    await expect(page).toHaveURL(/scenario=published/)
    await expect(page.getByRole("heading", { name: /match review/i })).toBeVisible()
    await expect(page.getByText("Demo review", { exact: true })).toBeVisible()
  })
})
