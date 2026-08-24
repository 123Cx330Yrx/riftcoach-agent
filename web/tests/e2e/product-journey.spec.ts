import { randomUUID } from "node:crypto"
import { expect, test, type Page } from "@playwright/test"

const SELF = "95000000-0000-4000-8000-000000000001"
const ADDED = "95000000-0000-4000-8000-000000000003"

interface RequestLedger {
  readonly requests: string[]
  readonly open_streams: number
  readonly closed_streams: number
  readonly player_link_polls: number
  readonly player_link_succeeded: boolean
  readonly player_link_submissions: readonly {
    readonly riot_id: string
    readonly routing_region: string
    readonly relationship_role: string
    readonly csrf_valid: boolean
    readonly idempotency_key: string
  }[]
}

function uniqueTestId(prefix: string) {
  return `${prefix}-${randomUUID()}`
}

async function useScenario(page: Page, scenario: string, testId: string) {
  await page.context().addCookies([
    { name: "riftcoach-test-scenario", value: scenario, domain: "127.0.0.1", path: "/" },
    { name: "riftcoach-test-id", value: testId, domain: "127.0.0.1", path: "/" },
  ])
}

async function requestLedger(page: Page, testId: string): Promise<RequestLedger> {
  const response = await page.request.get(`http://127.0.0.1:4174/__requests?test_id=${testId}`)
  expect(response.ok()).toBe(true)
  return await response.json() as RequestLedger
}

async function expectPortalOnly(page: Page) {
  await expect(page.getByTestId("awakening-scene")).toHaveCount(1)
  await expect(page.getByTestId("account-access")).toHaveCount(0)
  await expect(page.getByRole("heading", { level: 1, name: /match review/i })).toHaveCount(0)
}

async function expectAccountOnly(page: Page) {
  await expect(page.getByTestId("awakening-scene")).toHaveCount(0)
  await expect(page.getByTestId("account-access")).toHaveCount(1)
  await expect(page.getByRole("heading", { level: 1, name: /match review/i })).toHaveCount(0)
}

async function expectWorkbenchOnly(page: Page) {
  await expect(page.getByTestId("awakening-scene")).toHaveCount(0)
  await expect(page.getByTestId("account-access")).toHaveCount(0)
  await expect(page.getByRole("heading", { level: 1, name: /match review/i })).toHaveCount(1)
}

test.describe("Portal to Account to Workbench journey", () => {
  test("performs zero API work before core activation and enters the live path without a fixture", async ({ page }) => {
    const testId = uniqueTestId("default-journey")
    await useScenario(page, "published", testId)
    const remoteRequests: string[] = []
    page.on("request", (request) => {
      const hostname = new URL(request.url()).hostname
      if (hostname !== "127.0.0.1" && hostname !== "localhost") remoteRequests.push(request.url())
    })

    await page.goto("/")
    await expect(page.getByRole("heading", { name: /read the rift/i })).toBeVisible()
    await expectPortalOnly(page)
    expect((await requestLedger(page, testId)).requests).toEqual([])

    const core = page.getByRole("button", { name: /enter riftcoach/i })
    await core.focus()
    await expect(core).toBeFocused()
    await page.keyboard.press("Enter")

    await expect(page).toHaveURL(/\?stage=account$/)
    await expect(page.getByRole("heading", { name: /who are we reviewing/i })).toBeVisible()
    await expect(page.getByRole("heading", { name: /who are we reviewing/i })).toBeFocused()
    await expectAccountOnly(page)
    const accountLedger = await requestLedger(page, testId)
    expect(accountLedger.requests.some((path) => path === "POST /auth/session")).toBe(true)
    expect(accountLedger.requests.some((path) => path === "GET /player-profiles?limit=50")).toBe(true)
    expect(accountLedger.requests.every((path) =>
      path === "POST /auth/session" || path === "GET /player-profiles?limit=50",
    )).toBe(true)

    await page.getByRole("button", { name: /open this review/i }).click()
    await expect(page).toHaveURL(new RegExp(`stage=workbench&player_profile_id=${SELF}$`))
    await expect(page.getByText("Live review", { exact: true })).toBeVisible()
    await expect(page.getByRole("heading", { level: 1, name: /match review/i })).toBeFocused()
    await expect(page.getByText("Published", { exact: true })).toBeVisible()
    await expect(page.getByText("Demo review", { exact: true })).toHaveCount(0)
    await expectWorkbenchOnly(page)

    const workbenchLedger = await requestLedger(page, testId)
    expect(workbenchLedger.requests.some((path) => path.includes(`/player-profiles/${SELF}/reviews/recent/latest`))).toBe(true)
    expect(workbenchLedger.requests.some((path) => path.includes("/product-state"))).toBe(true)
    expect(page.url()).not.toContain("scenario=")
    expect(remoteRequests).toEqual([])
  })

  test("creates an observed player through queued, running and succeeded before refreshing profiles", async ({ page }) => {
    const testId = uniqueTestId("player-link")
    await useScenario(page, "link", testId)
    await page.goto("/")
    await page.getByRole("button", { name: /enter riftcoach/i }).click()
    await expect(page.getByRole("heading", { name: /who are we reviewing/i })).toBeVisible()

    await page.getByRole("button", { name: /add another player/i }).click()
    await page.getByLabel("Riot ID").fill("FreshPilot#NA1")
    await page.getByLabel("Region").selectOption("americas")
    await page.getByLabel(/is this your account/i).selectOption("public_observed")
    await page.getByRole("button", { name: /^add player$/i }).click()

    await expect(page.getByText("FreshPilot#NA1 is ready.", { exact: true })).toBeVisible({ timeout: 6_000 })
    await expect(page.getByRole("radio", { name: /FreshPilot#NA1/i })).toBeChecked()
    const ledger = await requestLedger(page, testId)
    expect(ledger.player_link_polls).toBe(3)
    expect(ledger.player_link_succeeded).toBe(true)
    expect(ledger.requests.filter((path) => path === "GET /player-profiles?limit=50").length).toBeGreaterThanOrEqual(2)
    expect(ledger.requests.filter((path) => path.includes("/player-links/"))).toHaveLength(3)
    expect(ledger.player_link_submissions).toHaveLength(1)
    expect(ledger.player_link_submissions[0]).toMatchObject({
      riot_id: "FreshPilot#NA1",
      routing_region: "americas",
      relationship_role: "observed",
      csrf_valid: true,
    })
    expect(ledger.player_link_submissions[0]!.idempotency_key).toMatch(/^player-link-[0-9a-f-]{36}$/i)

    await page.getByRole("button", { name: /open this review/i }).click()
    await expect(page).toHaveURL(new RegExp(`stage=workbench&player_profile_id=${ADDED}$`))
    await expect(page.getByRole("heading", { name: "FreshPilot#NA1" })).toBeVisible()
    await expect(page.getByText("Live review", { exact: true })).toBeVisible()
    await expect(page.getByText("Demo review", { exact: true })).toHaveCount(0)
    const finalLedger = await requestLedger(page, testId)
    expect(finalLedger.requests.some((path) => path.includes(`/player-profiles/${ADDED}/reviews/recent/latest`))).toBe(true)
    expect(finalLedger.requests.some((path) => path.includes("training-plan"))).toBe(false)
    expect(finalLedger.requests.some((path) => path.includes("training-progress"))).toBe(false)
  })

  test("keeps exactly one product layer across reload, back and forward navigation", async ({ page }) => {
    const testId = uniqueTestId("history")
    await useScenario(page, "history-open-stream", testId)
    await page.goto("/")
    await expectPortalOnly(page)

    const core = page.getByRole("button", { name: /enter riftcoach/i })
    await core.focus()
    await page.keyboard.press("Space")
    await expect(page).toHaveURL(/\?stage=account$/)
    await expectAccountOnly(page)

    await page.getByRole("button", { name: /open this review/i }).click()
    await expect(page.getByText("In progress", { exact: true })).toBeVisible()
    await expect.poll(async () => (await requestLedger(page, testId)).open_streams).toBe(1)
    await expectWorkbenchOnly(page)

    await page.reload()
    await expect(page.getByText("In progress", { exact: true })).toBeVisible()
    await expectWorkbenchOnly(page)

    await page.goBack()
    await expect(page).toHaveURL(/\?stage=account$/)
    await expectAccountOnly(page)

    await page.goBack()
    await expect(page).toHaveURL(/127\.0\.0\.1:4173\/$/)
    await expectPortalOnly(page)

    await page.goForward()
    await expectAccountOnly(page)
    await page.goForward()
    await expect(page.getByText("In progress", { exact: true })).toBeVisible()
    await expectWorkbenchOnly(page)
    await expect.poll(async () => (await requestLedger(page, testId)).closed_streams).toBeGreaterThan(0)
  })

  test("rejects an owner-unlisted workbench profile instead of selecting the first profile", async ({ page }) => {
    const testId = uniqueTestId("unlisted-profile")
    await useScenario(page, "published", testId)
    const unlisted = "95000000-0000-4000-8000-000000000099"

    await page.goto(`/?stage=workbench&player_profile_id=${unlisted}`)
    await expect(page.getByText(/this player profile is unavailable/i)).toBeVisible()
    await expect(page.getByRole("heading", { name: "Riverline#EUW" })).toHaveCount(0)
    const ledger = await requestLedger(page, testId)
    expect(ledger.requests.some((path) => path.includes("/reviews/recent/latest"))).toBe(false)
    expect(ledger.requests.some((path) => path.includes("/events/stream"))).toBe(false)
  })
})
