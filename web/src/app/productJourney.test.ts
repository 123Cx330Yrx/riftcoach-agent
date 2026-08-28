import { describe, expect, it } from "vitest"

import { parseProductJourney, productJourneyUrl } from "./productJourney"

const PROFILE_ID = "95000000-0000-4000-8000-000000000002"

describe("product journey URL contract", () => {
  it("starts at the cinematic portal and accepts only explicit legal stages", () => {
    expect(parseProductJourney("")).toEqual({ stage: "portal", canonical: true })
    expect(parseProductJourney("?stage=account")).toEqual({ stage: "account", canonical: true })
    expect(parseProductJourney(`?stage=workbench&player_profile_id=${PROFILE_ID}`)).toEqual({
      stage: "workbench",
      profileId: PROFILE_ID,
      canonical: true,
    })
    expect(parseProductJourney("?region=demacia")).toEqual({ stage: "portal", canonical: true, region: "demacia" })
    expect(parseProductJourney("?stage=account&region=bandle-city")).toEqual({ stage: "account", canonical: true, region: "bandle-city" })
  })

  it("fails closed to the portal for unknown stages or unbound workbench links", () => {
    expect(parseProductJourney("?stage=admin")).toEqual({ stage: "portal", canonical: false })
    expect(parseProductJourney("?stage=workbench")).toEqual({ stage: "portal", canonical: false })
    expect(parseProductJourney("?stage=workbench&player_profile_id=not-a-uuid")).toEqual({
      stage: "portal",
      canonical: false,
    })
  })

  it("builds canonical same-page URLs without carrying preview or fixture controls", () => {
    expect(productJourneyUrl({ stage: "portal" })).toBe("/")
    expect(productJourneyUrl({ stage: "account" })).toBe("/?stage=account")
    expect(productJourneyUrl({ stage: "workbench", profileId: PROFILE_ID })).toBe(
      `/?stage=workbench&player_profile_id=${PROFILE_ID}`,
    )
    expect(productJourneyUrl({ stage: "account", region: "demacia" })).toBe("/?stage=account&region=demacia")
    expect(productJourneyUrl({ stage: "portal", region: "bandle-city" })).toBe("/?region=bandle-city")
    expect(productJourneyUrl({ stage: "workbench", profileId: PROFILE_ID, region: "demacia" })).toBe(
      `/?stage=workbench&player_profile_id=${PROFILE_ID}&region=demacia`,
    )
  })
})
