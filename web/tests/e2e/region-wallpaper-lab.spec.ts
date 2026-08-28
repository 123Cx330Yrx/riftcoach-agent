import { expect, test } from "@playwright/test"

test.describe("official wallpaper research preview", () => {
  test("keeps the region preview isolated from product I/O", async ({ page }) => {
    const requests: string[] = []
    page.on("request", (request) => requests.push(request.url()))
    await page.goto("/?surface=wallpaper-lab")
    await expect(page.getByTestId("wallpaper-lab")).toHaveAttribute("data-region", "demacia")
    await expect(page.getByRole("button", { name: /Demacia/i })).toHaveAttribute("aria-pressed", "true")
    await expect(page.getByRole("button", { name: /Enter RiftCoach/i })).toBeVisible()
    expect(requests.some((url) => /127\.0\.0\.1:4174\/api\/(auth|player|workbench|tasks)/i.test(url))).toBe(false)
  })

  test("supports keyboard activation and carries the selected region into account", async ({ page }) => {
    await page.goto("/?surface=wallpaper-lab")
    const enter = page.getByRole("button", { name: /Enter RiftCoach/i })
    await enter.focus()
    await enter.press("Enter")
    await expect(page.getByTestId("wallpaper-lab")).toHaveClass(/wallpaper-lab--activating/)
    await expect(page).toHaveURL(/stage=account&region=demacia/)
    await expect(page.getByTestId("account-access")).toHaveAttribute("data-wallpaper-region", "demacia")
  })
})
