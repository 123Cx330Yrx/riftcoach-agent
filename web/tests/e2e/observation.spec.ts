import { createHash } from "node:crypto"
import { expect, test } from "@playwright/test"

test("observation import filters roles without account or training requests", async ({ page }) => {
  const requests: string[] = []
  page.on("request", request => { if (/^\/(api|memory|auth|tasks|runs|player-profiles)(\/|$)/.test(new URL(request.url()).pathname)) requests.push(request.url()) })
  const report = "# Fixture observation\n\n<script>window.fixtureExecuted=true</script>"
  const archive = {
    schema_version: "showmaker-observation-v1", scope: "public_observed_archive", riot_id: "DK ShowMaker#KR1", region: "asia", source_run_id: "fixture_observation", observed_at: "2026-09-10T00:00:00Z", exported_at: "2026-09-11T00:00:00Z",
    report: { text: report, kind: "human_reviewed", sha256: createHash("sha256").update(report).digest("hex"), original_sha256: "a".repeat(64), automated_score: 95, original_manual_accepted: false },
    summary: { games: 2, wins: 1, losses: 1, positions: [{ position: "mid", games: 1, champions: ["FixtureMage"], cs_per_min: 8 }, { position: "support", games: 1, champions: ["FixtureSupport"], cs_per_min: null }], matches: [{ match_id: "fixture_mid", champion: "FixtureMage", position: "mid", win: true, cs_per_min: 8, damage_per_min: 500, deaths_before_15: 0 }, { match_id: "fixture_support", champion: "FixtureSupport", position: "support", win: false, cs_per_min: null, damage_per_min: null, deaths_before_15: 2 }] },
    evidence: { bundle_digest: "b".repeat(64), sources: [{ label: "Fixture source", detail: "Archived only", observed_at: "2026-09-10T00:00:00Z" }] },
    exercises: [{ id: "watch_mid", title: "中路观察示例", position: "mid", prompt: "观察录像中的参团时机。", match_ids: ["fixture_mid"], evidence_note: "仅观摩，不代表能力改善。" }],
  }
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
