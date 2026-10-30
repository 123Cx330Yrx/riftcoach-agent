import { expect, test, type Page } from "@playwright/test"

const TASK = "96000000-0000-4000-8000-000000000001"
const RUN = "review_live_workbench_1"
const SELF = "95000000-0000-4000-8000-000000000001"
test.use({ reducedMotion: "reduce" })
const ACCOUNTING = { scope: "cumulative_session", requests_reserved: 3, requests_observed: 3,
  known_tokens: 120, unknown_token_reservation: 80384, retries: 0, unresolved_intents: 0 }

async function pausedTask(page: Page, locale: "zh-CN" | "en", unresolved = false) {
  await page.context().addCookies([{ name: "riftcoach-test-scenario", value: "recovery", domain: "127.0.0.1", path: "/" }])
  await page.addInitScript(value => localStorage.setItem("riftcoach.ui-locale.v1", JSON.stringify({ schema_version: "1.0", locale: value })), locale)
  const posts: { path: string; body: string | null; key: string | undefined; csrf: string | undefined }[] = []
  let status = "recovery_required"
  await page.route(`**/api/tasks/${TASK}**`, async route => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (request.method() === "POST") {
      posts.push({ path, body: request.postData(), key: request.headers()["idempotency-key"], csrf: request.headers()["x-csrf-token"] })
      status = path.endsWith("/cancel") ? "cancelled" : "queued"
      await route.fulfill({ json: status === "cancelled"
        ? { schema_version: "1.0", task_id: TASK, disposition: "cancelled", status }
        : { task_id: TASK, run_id: RUN, status, replayed: false } })
    } else if (path.endsWith("/continuation")) {
      await route.fulfill({ json: { task_id: TASK, run_id: RUN, status, profile: "sol-dual-development-v1",
        checkpoint_sha256: "a".repeat(64), reason: "session_timeout_awaiting_manual_retry",
        session_accounting: { ...ACCOUNTING, unresolved_intents: unresolved ? 1 : 0 }, publication_allowed: false } })
    } else if (path.endsWith(TASK)) {
      const response = await route.fetch()
      await route.fulfill({ json: { ...await response.json(), status } })
    } else await route.continue()
  })
  await page.route(`**/api/runs/${RUN}/product-state`, async route => {
    const response = await route.fetch()
    await route.fulfill({ json: { ...await response.json(), state: status === "cancelled" ? "rejected" : "not_ready",
      task_status: status, reason_code: status === "cancelled" ? "task_cancelled" : status === "recovery_required" ? "recovery_required" : "task_pending" } })
  })
  await page.route(`**/api/runs/${RUN}/usage`, route => route.fulfill({ json: {
    schema_version: "1.0", run_id: RUN, task_status: status, usage: null, session_accounting: ACCOUNTING,
  } }))
  await page.goto(`/?stage=workbench&player_profile_id=${SELF}`)
  return posts
}

test("paused recovery is readable on mobile and sends only the explicitly chosen retry", async ({ page }, testInfo) => {
  const posts = await pausedTask(page, "zh-CN")
  const panel = page.getByRole("region", { name: "复盘已暂停" })
  await expect(panel).toBeVisible()
  for (const width of [1440, 320]) {
    await page.setViewportSize({ width, height: 900 })
    await expect(panel.getByRole("button", { name: "补测当前步骤一次" })).toBeVisible()
    await expect(page.getByRole("heading", { name: "战术简报等待任务恢复" })).toBeVisible()
    const widths = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth])
    expect(widths[0]).toBeLessThanOrEqual(widths[1]! + 1)
    await page.screenshot({ path: testInfo.outputPath(`recovery-${width}.png`), fullPage: true })
  }
  expect(posts).toHaveLength(0)
  await panel.getByRole("button", { name: "补测当前步骤一次" }).click()
  await expect(panel).toHaveCount(0)
  expect(posts).toHaveLength(1)
  expect(JSON.parse(posts[0]!.body!)).toEqual({ checkpoint_sha256: "a".repeat(64), manual_retry: true })
  expect(posts[0]!.key).toMatch(/^recovery-/)
  expect(posts[0]!.csrf).toMatch(/^csrf-/)
  await page.reload()
  await expect(page.getByRole("heading", { name: "复盘已暂停" })).toHaveCount(0)
  expect(posts).toHaveLength(1)
  await expect(page.locator(".safe-markdown")).toHaveCount(0)
})

test("unresolved request exposes cancellation and keeps unknown usage after cancelling", async ({ page }) => {
  const posts = await pausedTask(page, "en", true)
  const panel = page.getByRole("region", { name: "Review paused" })
  await expect(panel).toBeVisible()
  await expect(panel.getByRole("button", { name: "Retry this step once" })).toHaveCount(0)
  await panel.getByRole("button", { name: "Cancel this task" }).click()
  await expect(panel).toHaveCount(0)
  expect(posts).toHaveLength(1)
  expect(posts[0]!.body).toBeNull()
  await expect(page.getByText("80,384", { exact: true })).toBeVisible()
  await expect(page.locator(".safe-markdown")).toHaveCount(0)
})
