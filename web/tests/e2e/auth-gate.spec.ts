import { expect, test } from "@playwright/test"

test.describe("production shell auth gate", () => {
  test("does not load a live workbench when auth is unavailable", async ({ page }) => {
    await page.route("**/api/auth/session", (route) => route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ code: "auth_unavailable" }),
    }))

    await page.goto("/")
    await expect(page.getByRole("heading", { name: /read the rift/i })).toBeVisible()
    await page.getByRole("button", { name: /enter riftcoach/i }).click()
    await expect(page.getByRole("heading", { name: /sign-in is unavailable/i })).toBeVisible()
    await expect(page.getByText("auth_unavailable", { exact: true })).toHaveCount(0)
    await expect(page.getByRole("heading", { name: /match review/i })).toHaveCount(0)
  })

  test("turns an expired session response into a recoverable boundary", async ({ page }) => {
    await page.route("**/api/auth/session", (route) => route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ code: "auth_session_expired" }),
    }))

    await page.goto("/")
    await page.getByRole("button", { name: /enter riftcoach/i }).click()
    await expect(page.getByRole("heading", { name: /your session has ended/i })).toBeVisible()
    await expect(page.getByText("auth_session_expired", { exact: true })).toHaveCount(0)
  })

  test("returns Account profile expiry to the Auth boundary", async ({ page }) => {
    await page.route("**/api/player-profiles*", (route) => route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ code: "auth_session_expired" }),
    }))

    await page.goto("/")
    await page.getByRole("button", { name: /enter riftcoach/i }).click()
    await expect(page.getByRole("heading", { name: /your session has ended/i })).toBeVisible()
    await expect(page.getByTestId("account-access")).toHaveCount(0)
  })
})
