import { createHash } from "node:crypto"
import { expect, test } from "@playwright/test"


function observationFixture() {
  const report = "# Fixture observation\n\n<script>window.fixtureExecuted=true</script>"
  const archive = {
    schema_version: "showmaker-observation-v1", scope: "public_observed_archive", riot_id: "DK ShowMaker#KR1", region: "asia", source_run_id: "fixture_observation", observed_at: "2026-09-10T00:00:00Z", exported_at: "2026-09-11T00:00:00Z",
    report: { text: report, kind: "human_reviewed", sha256: createHash("sha256").update(report).digest("hex"), original_sha256: "a".repeat(64), automated_score: 95, original_manual_accepted: false },
    summary: { games: 2, wins: 1, losses: 1, positions: [{ position: "mid", games: 1, champions: ["FixtureMage"], cs_per_min: 8 }, { position: "support", games: 1, champions: ["FixtureSupport"], cs_per_min: null }], matches: [{ match_id: "fixture_mid", champion: "FixtureMage", position: "mid", win: true, cs_per_min: 8, damage_per_min: 500, deaths_before_15: 0 }, { match_id: "fixture_support", champion: "FixtureSupport", position: "support", win: false, cs_per_min: null, damage_per_min: null, deaths_before_15: 2 }] },
    evidence: { bundle_digest: "b".repeat(64), sources: [{ label: "Fixture source", detail: "Archived only", observed_at: "2026-09-10T00:00:00Z" }] },
    exercises: [{ id: "watch_mid", title: "中路观察示例", position: "mid", prompt: "观察录像中的参团时机。", match_ids: ["fixture_mid"], evidence_note: "仅观摩，不代表能力改善。" }],
  }
  return archive
}

test("observation import filters roles without account or training requests", async ({ page }) => {
  const requests: string[] = []
  page.on("request", request => { if (/^\/(api|memory|auth|tasks|runs|player-profiles)(\/|$)/.test(new URL(request.url()).pathname)) requests.push(request.url()) })
  const archive = observationFixture()
  const report = archive.report.text
  await page.goto("/?view=observation")
  await page.getByLabel("导入观摩资料", { exact: true }).setInputFiles({ name: "observation.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(archive)) })
  await expect(page.getByRole("heading", { name: "人工校订报告", exact: true })).toBeVisible()
  await expect(page.getByText("未重新自动评分", { exact: false })).toBeVisible()
  await expect(page.getByRole("table")).toContainText("FixtureSupport")
  await page.getByLabel("筛选位置").selectOption("mid")
  await expect(page.getByRole("table")).not.toContainText("FixtureSupport")
  await page.getByRole("checkbox", { name: "中路观察示例" }).check()
  await expect(page.getByRole("status")).toHaveText("本页已完成 1 / 1 项观察")
  expect(await page.evaluate(() => "fixtureExecuted" in window)).toBe(false)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  const broken = { ...archive, report: { ...archive.report, text: report + " altered" } }
  await page.getByLabel("导入观摩资料", { exact: true }).setInputFiles({ name: "broken.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(broken)) })
  await expect(page.getByRole("alert")).toBeVisible()
  await expect(page.getByRole("heading", { name: "人工校订报告", exact: true })).toHaveCount(0)
  expect(requests).toEqual([])
})

test("observation notes save through scoped APIs and survive page reload", async ({ page }) => {
  const archive = observationFixture()
  const profile = "11111111-1111-4111-8111-111111111111"
  const conversation = "22222222-2222-4222-8222-222222222222"
  const candidateId = "33333333-3333-4333-8333-333333333333"
  let notePayload: Record<string, unknown> | undefined
  let accepted = false
  let failFirstAcceptResponse = true
  let candidates = 0
  const writes: string[] = []
  const candidate = (status: string) => ({ schema_version: "1.0", candidate_id: candidateId, conversation_id: conversation, target_scope: "owner_player", candidate_kind: "review_memory", memory_key: "observation_note", operation: "append", requires_confirmation: true, status, gate_policy_version: "memory-gate-v2-user-observation", created_at: "2026-09-11T00:00:00Z", expires_at: "2026-10-11T00:00:00Z", decided_at: accepted ? "2026-09-11T00:01:00Z" : null, decision_reason_code: accepted ? "user_confirmed" : null })
  await page.route("**/api/**", async route => {
    const req = route.request(), path = new URL(req.url()).pathname
    if (!path.startsWith("/api/")) return route.continue()
    const send = (value: unknown) => route.fulfill({ contentType: "application/json", body: JSON.stringify(value) })
    if (path === "/api/auth/session") return send({ schema_version: "1.0", csrf_token: "test-note-csrf", expires_at: "2099-09-11T00:00:00Z" })
    if (path === "/api/player-profiles") return send({ schema_version: "1.0", limit: 50, profiles: [{ schema_version: "1.0", player_profile_id: profile, riot_id: archive.riot_id, routing_region: "asia", relationship_role: "observed", verification_status: "not_applicable", last_resolved_at: archive.observed_at }] })
    if (path === `/api/memory/players/${profile}/reviews`) return send({ schema_version: "1.0", records: accepted ? [{ schema_version: "1.0", record_id: candidateId, target_kind: "review_memory", relationship_id: profile, relationship_role: "observed", memory_key: "observation_note", version: 1, status: "active", payload: notePayload, supersedes_record_id: null, created_at: "2026-09-11T00:01:00Z", updated_at: "2026-09-11T00:01:00Z" }] : [] })
    expect(req.headers()["x-csrf-token"]).toBe("test-note-csrf")
    writes.push(path)
    if (path === "/api/conversations") {
      expect(req.postDataJSON()).toEqual({ player_profile_id: profile })
      return send({ schema_version: "1.0", disposition: "created", conversation_id: conversation, relationship_id: profile, relationship_role: "observed", status: "active", created_at: "2026-09-11T00:00:00Z", updated_at: "2026-09-11T00:00:00Z", last_message_at: null })
    }
    if (path === `/api/conversations/${conversation}/memory-candidates`) {
      candidates++
      const body = req.postDataJSON()
      expect(body.memory_key).toBe("observation_note")
      expect(body.source_run_id).toBeUndefined()
      notePayload = body.proposal_payload.value
      return send(candidate("pending"))
    }
    if (path === `/api/memory-candidates/${candidateId}/accept`) {
      expect(req.postData()).toBeNull()
      accepted = true
      if (failFirstAcceptResponse) { failFirstAcceptResponse = false; return route.abort("failed") }
      return send(candidate("accepted"))
    }
    throw Error(`Unexpected endpoint: ${path}`)
  })
  const importArchive = async () => {
    await page.getByLabel("导入观摩资料", { exact: true }).setInputFiles({ name: "observation.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(archive)) })
    await page.getByRole("button", { name: "连接观摩档案", exact: true }).click()
    await expect(page.getByLabel("这次观察到了什么？")).toBeVisible()
  }
  await page.goto("/?view=observation")
  await importArchive()
  await page.getByLabel("这次观察到了什么？").fill("下次先看离线前的兵线。")
  await page.getByRole("button", { name: "保存观摩笔记" }).click()
  await expect(page.getByRole("alert")).toContainText("保存结果尚未确认")
  await page.getByRole("button", { name: "重试本次保存" }).click()
  await expect(page.getByLabel("本份资料的已存笔记")).toContainText("下次先看离线前的兵线。")
  expect(candidates).toBe(1)
  await page.reload()
  await importArchive()
  await expect(page.getByLabel("本份资料的已存笔记")).toContainText("下次先看离线前的兵线。")
  expect(writes.filter(p => p.endsWith("/accept"))).toHaveLength(2)
  expect(writes.some(p => /training|reviews\/recent/.test(p))).toBe(false)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
