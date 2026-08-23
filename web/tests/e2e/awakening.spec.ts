import { expect, test } from "@playwright/test"

test.describe("Rift Awakening portal preview", () => {
  test("keeps the cinematic shell local and moves honestly into calibration", async ({ page }) => {
    const apiRequests: string[] = []
    page.on("request", (request) => {
      const pathname = new URL(request.url()).pathname
      if (["xhr", "fetch"].includes(request.resourceType()) && pathname.startsWith("/api/")) {
        apiRequests.push(request.url())
      }
    })

    await page.goto("/?surface=awakening")
    await expect(page.getByRole("heading", { name: /calibrate your analysis field/i })).toBeVisible()
    await expect(page.getByText(/preview only · no external lookup/i)).toBeVisible()
    await expect(page.getByTestId("awakening-scene")).toHaveAttribute("data-phase", "idle")

    await page.getByLabel("Riot ID").fill("ConceptPilot#ASIA")
    await page.getByRole("button", { name: /calibrate identity/i }).click()

    await expect(page.getByTestId("awakening-scene")).toHaveAttribute("data-phase", "calibrating")
    await expect(page.getByRole("button", { name: /calibrating route/i })).toBeDisabled()
    expect(apiRequests).toEqual([])

    await page.screenshot({ path: "test-results/awakening-desktop.png", fullPage: true })
  })

  test("keeps the form usable on a narrow viewport with reduced motion", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.emulateMedia({ reducedMotion: "reduce" })
    await page.goto("/?surface=awakening")

    const scene = page.getByTestId("awakening-scene")
    await expect(scene).toHaveAttribute("data-motion", "full")
    await expect(page.getByLabel("Riot ID")).toBeVisible()
    await expect(page.getByRole("button", { name: /calibrate identity/i })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.screenshot({ path: "test-results/awakening-mobile-reduced.png", fullPage: true })
  })

  test("hands an explicit ready preview into the fixture workbench", async ({ page }) => {
    await page.goto("/?surface=awakening&demo=ready")
    await expect(page.getByRole("button", { name: /enter broadcast workbench/i })).toBeVisible()

    await page.getByRole("button", { name: /enter broadcast workbench/i }).click()
    await expect(page).toHaveURL(/scenario=published/)
    await expect(page.getByRole("heading", { name: /rift command center/i })).toBeVisible()
    await expect(page.getByText(/fixture preview/i)).toBeVisible()
  })
})
