import { webcrypto } from "node:crypto"
import { afterEach, describe, expect, it, vi } from "vitest"
import { parseObservationArchive } from "./observationArchive"

export async function observationFixture() {
  const body = "# Fixture report\n\n<script>alert('fixture')</script>"
  const digest = Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256", new TextEncoder().encode(body))), b => b.toString(16).padStart(2, "0")).join("")
  return { schema_version: "showmaker-observation-v1", scope: "public_observed_archive", riot_id: "DK ShowMaker#KR1", region: "asia", source_run_id: "fixture_observation", observed_at: "2026-09-10T00:00:00Z", exported_at: "2026-09-11T00:00:00Z",
    report: { text: body, kind: "human_reviewed", sha256: digest, original_sha256: "a".repeat(64), automated_score: 95, original_manual_accepted: false },
    summary: { games: 2, wins: 1, losses: 1, positions: [{ position: "mid", games: 1, champions: ["FixtureMage"], cs_per_min: 8 }, { position: "support", games: 1, champions: ["FixtureSupport"], cs_per_min: null }], matches: [{ match_id: "fixture_mid", champion: "FixtureMage", position: "mid", win: true, cs_per_min: 8, damage_per_min: 500, deaths_before_15: 0 }, { match_id: "fixture_support", champion: "FixtureSupport", position: "support", win: false, cs_per_min: null, damage_per_min: null, deaths_before_15: 2 }] },
    evidence: { bundle_digest: "b".repeat(64), sources: [{ label: "Fixture source", detail: "Archived only", observed_at: "2026-09-10T00:00:00Z" }] },
    exercises: [{ id: "watch_mid", title: "中路观察示例", position: "mid", prompt: "观察录像中的参团时机。", match_ids: ["fixture_mid"], evidence_note: "仅观摩，不代表能力改善。" }] }
}
afterEach(() => vi.unstubAllGlobals())
describe("local observation archive", () => {
  it("keeps null metrics and accepts a body with markup as inert text", async () => {
    vi.stubGlobal("crypto", webcrypto)
    const result = await parseObservationArchive(JSON.stringify(await observationFixture()))
    expect(result.summary.matches[1]?.cs_per_min).toBeNull()
    expect(result.report.text).toContain("<script>")
  })
  it.each(["body", "personal", "counts", "exercise", "exercise-role", "positions"])("rejects altered %s", async change => {
    vi.stubGlobal("crypto", webcrypto)
    const value = await observationFixture()
    if (change === "body") value.report.text += " changed"
    if (change === "personal") value.scope = "self"
    if (change === "counts") value.summary.wins = 2
    if (change === "exercise") value.exercises[0]!.match_ids = ["missing"]
    if (change === "exercise-role") value.exercises[0]!.match_ids = ["fixture_support"]
    if (change === "positions") value.summary.positions[0]!.games = 2
    await expect(parseObservationArchive(JSON.stringify(value))).rejects.toThrow()
  })
})
