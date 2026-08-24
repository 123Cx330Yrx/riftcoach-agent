const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export type ProductJourneyLocation =
  | { readonly stage: "portal"; readonly canonical: boolean }
  | { readonly stage: "account"; readonly canonical: true }
  | { readonly stage: "workbench"; readonly profileId: string; readonly canonical: true }

export type ProductJourneyTarget =
  | { readonly stage: "portal" }
  | { readonly stage: "account" }
  | { readonly stage: "workbench"; readonly profileId: string }

export function parseProductJourney(search: string): ProductJourneyLocation {
  const query = new URLSearchParams(search)
  const stage = query.get("stage")
  if (stage === null && query.size === 0) return { stage: "portal", canonical: true }
  if (stage === "account" && query.size === 1) return { stage: "account", canonical: true }
  if (stage === "workbench" && query.size === 2) {
    const profileId = query.get("player_profile_id")
    if (profileId !== null && UUID_PATTERN.test(profileId)) {
      return { stage: "workbench", profileId: profileId.toLowerCase(), canonical: true }
    }
  }
  return { stage: "portal", canonical: false }
}

export function productJourneyUrl(target: ProductJourneyTarget): string {
  if (target.stage === "portal") return "/"
  if (target.stage === "account") return "/?stage=account"
  if (!UUID_PATTERN.test(target.profileId)) throw new Error("profileId must be a UUID")
  const query = new URLSearchParams({
    stage: "workbench",
    player_profile_id: target.profileId.toLowerCase(),
  })
  return `/?${query.toString()}`
}
