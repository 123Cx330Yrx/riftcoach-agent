import { expect, test } from "@playwright/test"
import { writeFileSync } from "node:fs"
import { join } from "node:path"

test("observed review uses real HTTP/SQL, preserves its prefix and exposes only published content", async ({ page }, info) => {
  const action = process.env.RIFTCOACH_BROWSER_ACTION!
  const requests: { method: string; path: string }[] = []
  const remote: string[] = []
  // This guard blocks external assets too; local API traffic is never mocked.
  await page.route("**/*", route => {
    const host = new URL(route.request().url()).hostname
    if (!["127.0.0.1", "localhost"].includes(host)) { remote.push(host); return route.abort() }
    return route.continue()
  })
  page.on("request", req => requests.push({ method: req.method(), path: new URL(req.url()).pathname }))
  await page.addInitScript(() => localStorage.setItem("riftcoach.ui-locale.v1", JSON.stringify({ schema_version: "1.0", locale: "zh-CN" })))
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto(`/?stage=workbench&player_profile_id=${process.env.RIFTCOACH_BROWSER_PROFILE}`)
  const start = page.getByRole("button", { name: "发起复盘", exact: true })
  await expect(start).toBeVisible()
  expect(requests.some(r => r.path.endsWith("/reviews/recent") && r.method === "POST")).toBe(false)
  const created = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/reviews/recent"), { timeout: 15_000 })
  await start.click()
  const createdResponse = await created
  expect(createdResponse.status()).toBe(202)
  const task = await createdResponse.json()
  await expect(page.getByRole("region", { name: "复盘已暂停" })).toBeVisible({ timeout: 45_000 })
  const before = await (await page.request.get(`/api/tasks/${task.task_id}/continuation`)).json()
  expect(before.session_accounting.requests_reserved).toBe(3)
  expect(before.session_accounting.known_tokens).toBe(action === "retry" ? 40 : 60)
  expect(await page.locator(".safe-markdown").count()).toBe(0)
  await page.reload()
  await expect(page.getByRole("region", { name: "复盘已暂停" })).toBeVisible()
  expect(requests.filter(r => r.method === "POST" && r.path.endsWith("/resume"))).toHaveLength(0)
  await page.screenshot({ path: info.outputPath("paused-desktop.png"), fullPage: true })
  const button = action === "cancel" ? "取消此任务" : action === "retry" ? "补测当前步骤一次" : "检查并继续"
  await page.getByRole("button", { name: button, exact: true }).click()
  if (action === "cancel") {
    await expect(page.getByRole("heading", { name: "复盘已取消" })).toBeVisible()
    await expect(page.locator(".safe-markdown")).toHaveCount(0)
  } else {
    await expect(page.locator(".safe-markdown")).toBeVisible({ timeout: 45_000 })
    const evidence = await page.request.get(`/api/runs/${task.run_id}/evidence`)
    expect(evidence.status()).toBe(200)
    expect((await page.request.get(`/api/runs/${task.run_id}/report`)).status()).toBe(200)
    expect(requests.some(r => r.path.endsWith("/evidence"))).toBe(true)
  }
  await expect(page.getByRole("region", { name: "任务用量" })).toBeVisible()
  const usage = await (await page.request.get(`/api/runs/${task.run_id}/usage`)).json()
  expect(usage.session_accounting.requests_reserved).toBe(action === "retry" ? 5 : action === "cancel" ? 3 : 4)
  expect(usage.session_accounting.known_tokens).toBe(action === "cancel" ? 60 : 80)
  expect(usage.session_accounting.retries).toBe(action === "retry" ? 1 : 0)
  expect(usage.session_accounting.unknown_token_reservation).toBe(before.session_accounting.unknown_token_reservation)
  for (const width of [1440, 320]) {
    await page.setViewportSize({ width, height: 1000 })
    await page.screenshot({ path: info.outputPath(`terminal-${width}.png`), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true)
    if (action !== "cancel") {
      await page.locator(".safe-markdown").scrollIntoViewIfNeeded()
      await page.screenshot({ path: info.outputPath(`report-viewport-${width}.png`) })
      await page.getByRole("button", { name: "证据 打开证据", exact: true }).click()
      await expect(page.getByRole("dialog", { name: "复盘证据", exact: true })).toBeVisible()
      await page.screenshot({ path: info.outputPath(`evidence-viewport-${width}.png`) })
      await page.keyboard.press("Escape")
    }
  }
  expect(requests.filter(r => r.method === "POST" && r.path.endsWith("/reviews/recent"))).toHaveLength(1)
  expect(requests.some(r => r.path.includes("training-plan") || r.path.includes("training-progress"))).toBe(false)
  expect(remote).toEqual([])
  writeFileSync(join(process.env.RIFTCOACH_BROWSER_OUTPUT!, "browser-proof.json"), JSON.stringify({ action, task,
    accounting: usage.session_accounting, requests, externalRequests: remote }, null, 2) + "\n")
})
