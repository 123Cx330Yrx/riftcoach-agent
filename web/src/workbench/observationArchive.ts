export interface ObservationArchive {
  schema_version: "showmaker-observation-v1"
  scope: "public_observed_archive"
  riot_id: string
  region: string
  source_run_id: string
  observed_at: string
  exported_at: string
  report: { text: string; kind: "human_reviewed"; sha256: string; original_sha256: string; automated_score: number; original_manual_accepted: false }
  summary: {
    games: number; wins: number; losses: number
    positions: { position: string; games: number; champions: string[]; cs_per_min: number | null }[]
    matches: { match_id: string; champion: string; position: string; win: boolean; cs_per_min: number | null; damage_per_min: number | null; deaths_before_15: number | null }[]
  }
  evidence: { bundle_digest: string; sources: { label: string; detail: string; observed_at: string }[] }
  exercises: { id: string; title: string; position: string; prompt: string; match_ids: string[]; evidence_note: string }[]
}

export const ARCHIVE_MAX_BYTES = 250_000
function reject(): never { throw new Error("observation_archive_invalid") }
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return reject()
  return value as Record<string, unknown>
}
function text(value: unknown, max = 300): string {
  if (typeof value !== "string" || !value.trim() || value.length > max) return reject()
  return value
}
function number(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return reject()
  return value
}
function count(value: unknown): number {
  const result = number(value)
  return Number.isInteger(result) && result <= 20 ? result : reject()
}
function rows(value: unknown, max = 20): unknown[] {
  if (!Array.isArray(value) || !value.length || value.length > max) return reject()
  return value
}
function digest(value: unknown): string {
  const result = text(value, 64)
  return /^[a-f0-9]{64}$/.test(result) ? result : reject()
}
function date(value: unknown): string {
  const result = text(value, 50)
  return /(?:Z|[+-]\d\d:\d\d)$/.test(result) && Number.isFinite(Date.parse(result)) ? result : reject()
}

export async function parseObservationArchive(raw: string): Promise<ObservationArchive> {
  if (new TextEncoder().encode(raw).length > ARCHIVE_MAX_BYTES) return reject()
  const v = object(JSON.parse(raw))
  if (v.schema_version !== "showmaker-observation-v1" || v.scope !== "public_observed_archive") return reject()
  if (v.riot_id !== "DK ShowMaker#KR1" || v.region !== "asia") return reject()
  text(v.source_run_id, 96); date(v.observed_at); date(v.exported_at)
  const report = object(v.report)
  if (report.kind !== "human_reviewed" || report.original_manual_accepted !== false) return reject()
  const reportText = text(report.text, 50_000)
  digest(report.original_sha256)
  if (number(report.automated_score) > 100) return reject()
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(reportText))), b => b.toString(16).padStart(2, "0")).join("")
  if (hash !== digest(report.sha256)) return reject()
  const summary = object(v.summary)
  const matches = rows(summary.matches)
  if (count(summary.games) !== matches.length || count(summary.wins) + count(summary.losses) !== summary.games) return reject()
  const ids = new Set<string>()
  let wins = 0
  for (const value of matches) {
    const m = object(value)
    const id = text(m.match_id, 100)
    if (ids.has(id) || typeof m.win !== "boolean") return reject()
    ids.add(id); wins += m.win ? 1 : 0
    text(m.champion, 100); text(m.position, 30)
    for (const key of ["cs_per_min", "damage_per_min", "deaths_before_15"]) if (m[key] !== null) number(m[key])
  }
  if (wins !== summary.wins) return reject()
  let total = 0
  const positions = new Set<string>()
  for (const value of rows(summary.positions, 6)) {
    const p = object(value), position = text(p.position, 30)
    if (positions.has(position)) return reject()
    positions.add(position); total += count(p.games)
    if (matches.filter(m => object(m).position === position).length !== p.games) return reject()
    for (const champion of rows(p.champions)) text(champion, 100)
    if (p.cs_per_min !== null) number(p.cs_per_min)
  }
  if (total !== summary.games) return reject()
  const evidence = object(v.evidence); digest(evidence.bundle_digest)
  for (const value of rows(evidence.sources, 10)) {
    const s = object(value); text(s.label, 100); text(s.detail, 1500); date(s.observed_at)
  }
  const exerciseIds = new Set<string>()
  for (const value of rows(v.exercises, 8)) {
    const e = object(value), id = text(e.id, 60)
    if (exerciseIds.has(id) || !positions.has(text(e.position, 30))) return reject()
    exerciseIds.add(id); text(e.title, 120); text(e.prompt, 2000); text(e.evidence_note, 1500)
    for (const match of rows(e.match_ids)) {
      const matchId = text(match, 100)
      if (!matches.some(m => object(m).match_id === matchId && object(m).position === e.position)) return reject()
    }
  }
  // Only these explicitly selected fields are rendered; imported text is data.
  return v as unknown as ObservationArchive
}
