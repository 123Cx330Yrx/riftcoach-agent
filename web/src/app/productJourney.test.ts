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
  })
})
