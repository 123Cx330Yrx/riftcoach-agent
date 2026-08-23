import { expect, test } from "@playwright/test"

test.describe("production shell auth gate", () => {
  test("does not load a live workbench when auth is unavailable", async ({ page }) => {
    await page.route("**/api/auth/session", (route) => route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ code: "auth_unavailable" }),
    }))

    await page.goto("/")
    await expect(page.getByRole("heading", { name: /sign-in is not ready/i })).toBeVisible()
    await expect(page.getByText("auth_unavailable", { exact: true })).toBeVisible()
    await expect(page.getByRole("heading", { name: /rift command center/i })).toHaveCount(0)
  })

  test("turns an expired session response into a recoverable boundary", async ({ page }) => {
    await page.route("**/api/player-profiles*", (route) => route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ code: "auth_session_expired" }),
    }))

    await page.goto("/")
    await expect(page.getByRole("heading", { name: /session needs attention/i })).toBeVisible()
    await expect(page.getByText("auth_session_expired", { exact: true })).toBeVisible()
  })
})
