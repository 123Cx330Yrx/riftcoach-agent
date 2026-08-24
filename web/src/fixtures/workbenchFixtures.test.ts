import { describe, expect, it } from "vitest";

import {
  assertPublicWorkbenchFixture,
  getSelectedProfile,
  getSelectedTraining,
  type ReviewWorkbenchFixture,
} from "../contracts/workbench";
import {
  publishedWorkbenchFixture,
  resolveWorkbenchScenario,
  workbenchScenarios,
} from "./workbenchFixtures";

describe("workbench fixture scenarios", () => {
  it("exposes the seven frozen client scenarios without mixing product state", () => {
    expect(Object.keys(workbenchScenarios).sort()).toEqual([
      "degraded",
      "empty",
      "error",
      "loading",
      "not_ready",
      "published",
      "rejected",
    ]);

    expect(workbenchScenarios.loading.client).toBe("loading");
    expect(workbenchScenarios.empty.client).toBe("empty");
    expect(workbenchScenarios.error.client).toBe("error");
    expect(workbenchScenarios.published.client).toBe("ready");
    expect(workbenchScenarios.degraded.client).toBe("ready");
    expect(workbenchScenarios.rejected.client).toBe("ready");
    expect(workbenchScenarios.not_ready.client).toBe("ready");

    if (
      workbenchScenarios.published.client !== "ready" ||
      workbenchScenarios.degraded.client !== "ready" ||
      workbenchScenarios.rejected.client !== "ready" ||
      workbenchScenarios.not_ready.client !== "ready"
    ) {
      throw new Error("ready fixtures unexpectedly changed shape");
    }

    expect(workbenchScenarios.published.data.productState.state).toBe(
      "published",
    );
    expect(workbenchScenarios.degraded.data.productState.state).toBe(
      "degraded",
    );
    expect(workbenchScenarios.rejected.data.productState.state).toBe(
      "rejected",
    );
    expect(workbenchScenarios.not_ready.data.productState.state).toBe(
      "not_ready",
    );
  });

  it("defaults to published but fails closed for an unknown scenario", () => {
    expect(resolveWorkbenchScenario()).toBe(workbenchScenarios.published);
    expect(resolveWorkbenchScenario("")).toBe(workbenchScenarios.published);
    expect(resolveWorkbenchScenario("degraded")).toBe(
      workbenchScenarios.degraded,
    );

    const unknown = resolveWorkbenchScenario("cinematic-but-not-real");
    expect(unknown).toEqual({
      fixture_mode: true,
      client: "error",
      code: "fixture_scenario_unknown",
    });
    expect(unknown).not.toBe(workbenchScenarios.published);
  });

  it("uses invented self and observed profiles with relationship-safe training", () => {
    expect(publishedWorkbenchFixture.fixture_mode).toBe(true);
    expect(publishedWorkbenchFixture.selectedProfileId).toBe(
      "profile-riverline-euw",
    );
    expect(publishedWorkbenchFixture.profiles).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          playerProfileId: "profile-riverline-euw",
          riotId: "Riverline#EUW",
          routingRegion: "europe",
          relationshipRole: "self",
          trainingView: "personal",
        }),
        expect.objectContaining({
          playerProfileId: "profile-northstar-kr",
          riotId: "Northstar#KR",
          routingRegion: "asia",
          relationshipRole: "public_observed",
          trainingView: "learning_observation",
        }),
      ]),
    );
    expect(JSON.stringify(publishedWorkbenchFixture).toLowerCase()).not.toContain(
      "showmaker",
    );

    const selectedProfile = getSelectedProfile(publishedWorkbenchFixture);
    const selectedTraining = getSelectedTraining(publishedWorkbenchFixture);
    expect(selectedProfile.relationshipRole).toBe("self");
    expect(selectedTraining.mode).toBe("personal");

    const observedFixture: ReviewWorkbenchFixture = {
      ...publishedWorkbenchFixture,
      selectedProfileId: "profile-northstar-kr",
    };
    expect(getSelectedProfile(observedFixture).relationshipRole).toBe(
      "public_observed",
    );
    expect(getSelectedTraining(observedFixture)).toMatchObject({
      mode: "learning_observation",
      readOnly: true,
    });
    expect(getSelectedTraining(observedFixture)).not.toHaveProperty(
      "completedSessions",
    );
  });

  it("keeps report and readiness semantics honest", () => {
    if (
      workbenchScenarios.degraded.client !== "ready" ||
      workbenchScenarios.rejected.client !== "ready" ||
      workbenchScenarios.not_ready.client !== "ready"
    ) {
      throw new Error("ready fixture unexpectedly changed shape");
    }

    expect(workbenchScenarios.degraded.data.report).toBeDefined();
    expect(workbenchScenarios.degraded.data.productState.reportAvailable).toBe(
      true,
    );
    const rejected = workbenchScenarios.rejected
      .data as ReviewWorkbenchFixture;
    const notReady = workbenchScenarios.not_ready
      .data as ReviewWorkbenchFixture;
    expect(rejected.report).toBeUndefined();
    expect(rejected.productState.reportAvailable).toBe(
      false,
    );
    expect(notReady.summary).toBeUndefined();
    expect(notReady.report).toBeUndefined();
    expect(notReady.trainingByProfile).toEqual({});
    expect(notReady.events.length).toBeGreaterThan(0);
  });
});

describe("public fixture safety boundary", () => {
  it("accepts every ready fixture and freezes the published fixture deeply", () => {
    for (const scenario of Object.values(workbenchScenarios)) {
      if (scenario.client === "ready") {
        expect(assertPublicWorkbenchFixture(scenario.data)).toBeUndefined();
      }
    }

    expect(Object.isFrozen(publishedWorkbenchFixture)).toBe(true);
    expect(Object.isFrozen(publishedWorkbenchFixture.profiles)).toBe(true);
    expect(Object.isFrozen(publishedWorkbenchFixture.profiles[0])).toBe(true);
    expect(Object.isFrozen(publishedWorkbenchFixture.evidence?.sources)).toBe(
      true,
    );
  });

  it.each([
    "owner_id",
    "PUUID",
    "prompt",
    "context_body",
    "raw_response",
    "worker_id",
    "lease_token",
    "refresh_id",
    "checkpoint_reference",
    "operation_identity",
    "file_path",
  ])("rejects a recursively injected %s field", (forbiddenKey) => {
    const fixture = structuredClone(publishedWorkbenchFixture) as Record<
      string,
      unknown
    >;
    fixture.summary = {
      ...(fixture.summary as Record<string, unknown>),
      nested: { [forbiddenKey]: "must-not-ship" },
    };

    expect(() => assertPublicWorkbenchFixture(fixture)).toThrow(
      /forbidden fixture field/i,
    );
  });

  it.each([
    "D:\\private\\runs\\report.json",
    "/home/riftcoach/private/report.json",
    "file:///tmp/private.json",
    "postgresql://coach:secret@localhost/riftcoach",
    ["RGAPI", "do-not-ship-this-secret"].join("-"),
  ])("rejects a forbidden nested value: %s", (forbiddenValue) => {
    const fixture = structuredClone(publishedWorkbenchFixture) as Record<
      string,
      unknown
    >;
    fixture.summary = {
      ...(fixture.summary as Record<string, unknown>),
      nested: { safeLabel: forbiddenValue },
    };

    expect(() => assertPublicWorkbenchFixture(fixture)).toThrow(
      /forbidden fixture value/i,
    );
  });

  it("rejects a malformed, cyclic, or non-fixture root", () => {
    expect(() => assertPublicWorkbenchFixture(null)).toThrow(
      /fixture must be an object/i,
    );
    expect(() =>
      assertPublicWorkbenchFixture({ fixture_mode: false }),
    ).toThrow(/fixture_mode must be true/i);

    const cyclic: Record<string, unknown> = { fixture_mode: true };
    cyclic.self = cyclic;
    expect(() => assertPublicWorkbenchFixture(cyclic)).toThrow(
      /fixture must be acyclic/i,
    );
  });
});
