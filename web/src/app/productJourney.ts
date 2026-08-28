const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const JOURNEY_REGIONS = ["demacia", "bandle-city"] as const
export type ProductJourneyRegion = typeof JOURNEY_REGIONS[number]

function parseRegion(value: string | null): ProductJourneyRegion | undefined {
  return value !== null && (JOURNEY_REGIONS as readonly string[]).includes(value)
    ? value as ProductJourneyRegion
    : undefined
}

export type ProductJourneyLocation =
  | { readonly stage: "portal"; readonly canonical: boolean; readonly region?: ProductJourneyRegion }
  | { readonly stage: "account"; readonly canonical: true; readonly region?: ProductJourneyRegion }
  | { readonly stage: "workbench"; readonly profileId: string; readonly canonical: true; readonly region?: ProductJourneyRegion }

export type ProductJourneyTarget =
  | { readonly stage: "portal"; readonly region?: ProductJourneyRegion }
  | { readonly stage: "account"; readonly region?: ProductJourneyRegion }
  | { readonly stage: "workbench"; readonly profileId: string; readonly region?: ProductJourneyRegion }

export function parseProductJourney(search: string): ProductJourneyLocation {
  const query = new URLSearchParams(search)
  const stage = query.get("stage")
  const region = parseRegion(query.get("region"))
  const hasValidRegion = query.has("region") && region !== undefined
  if (stage === null && (query.size === 0 || (query.size === 1 && hasValidRegion))) {
    return region === undefined ? { stage: "portal", canonical: true } : { stage: "portal", canonical: true, region }
  }
  if (stage === "account" && (query.size === 1 || (query.size === 2 && hasValidRegion))) {
    return region === undefined ? { stage: "account", canonical: true } : { stage: "account", canonical: true, region }
  }
  if (stage === "workbench" && (query.size === 2 || (query.size === 3 && hasValidRegion))) {
    const profileId = query.get("player_profile_id")
    if (profileId !== null && UUID_PATTERN.test(profileId)) {
      return region === undefined
        ? { stage: "workbench", profileId: profileId.toLowerCase(), canonical: true }
        : { stage: "workbench", profileId: profileId.toLowerCase(), canonical: true, region }
    }
  }
  return { stage: "portal", canonical: false }
}

export function productJourneyUrl(target: ProductJourneyTarget): string {
  if (target.stage === "portal") {
    if (target.region === undefined) return "/"
    return `/?region=${encodeURIComponent(target.region)}`
  }
  if (target.stage === "account") {
    const query = new URLSearchParams({ stage: "account" })
    if (target.region !== undefined) query.set("region", target.region)
    return `/?${query.toString()}`
  }
  if (!UUID_PATTERN.test(target.profileId)) throw new Error("profileId must be a UUID")
  const query = new URLSearchParams({
    stage: "workbench",
    player_profile_id: target.profileId.toLowerCase(),
  })
  if (target.region !== undefined) query.set("region", target.region)
  return `/?${query.toString()}`
}
