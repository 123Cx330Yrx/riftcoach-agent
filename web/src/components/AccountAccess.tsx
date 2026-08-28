import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type FormEvent,
} from "react"

import type { PlayerAccessApi } from "../api/playerLinkApi"
import type { PlayerLinkFailureWire, RoutingRegionWire } from "../api/wire"
import { PlayerAccessController } from "../account/playerAccessController"
import { isAuthSessionFailure } from "../auth/session"
import { useI18n } from "../i18n/ProductLocaleProvider"
import type { MessageKey } from "../i18n/locale"
import type { WallpaperRegion } from "../wallpapers/regionWallpaperCatalog"
import { LocaleSwitch } from "./LocaleSwitch"

const regions: readonly RoutingRegionWire[] = ["americas", "europe", "asia", "sea"]

const regionKeys: Readonly<Record<RoutingRegionWire, MessageKey>> = {
  americas: "region.americas",
  europe: "region.europe",
  asia: "region.asia",
  sea: "region.sea",
}

const regionLongKeys: Readonly<Record<RoutingRegionWire, MessageKey>> = {
  americas: "region.americas_long",
  europe: "region.europe_long",
  asia: "region.asia_long",
  sea: "region.sea_long",
}

const failureKeys: Readonly<Record<PlayerLinkFailureWire["code"], MessageKey>> = {
  riot_rate_limited: "account.failure.rate_limited",
  upstream_timeout: "account.failure.upstream_timeout",
  upstream_unavailable: "account.failure.upstream_unavailable",
  player_not_found: "account.failure.player_not_found",
  riot_authentication_failed: "account.failure.riot_authentication",
  account_response_invalid: "account.failure.response_invalid",
  relationship_role_conflict: "account.failure.relationship_conflict",
}

export function AccountAccess({
  api,
  csrfToken,
  onBack,
  onContinue,
  focusReady = true,
  idempotencyKeyFactory,
  pollDelaysMs,
  onAuthFailure,
  wallpaperRegion,
}: {
  readonly api: PlayerAccessApi
  readonly csrfToken: string
  readonly onBack: () => void
  readonly onContinue: (profileId: string) => void
  readonly focusReady?: boolean
  readonly idempotencyKeyFactory?: () => string
  readonly pollDelaysMs?: readonly number[]
  readonly onAuthFailure?: (code: string) => void
  readonly wallpaperRegion?: WallpaperRegion
}) {
  const { t } = useI18n()
  const [controller] = useState(() => new PlayerAccessController({
    api,
    csrfToken,
    ...(idempotencyKeyFactory === undefined ? {} : { idempotencyKeyFactory }),
    ...(pollDelaysMs === undefined ? {} : { pollDelaysMs }),
  }))
  const subscribe = useCallback((listener: () => void) => controller.subscribe(listener), [controller])
  const getSnapshot = useCallback(() => controller.snapshot, [controller])
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
  const [showEditor, setShowEditor] = useState(false)
  const [riotId, setRiotId] = useState("")
  const [routingRegion, setRoutingRegion] = useState<RoutingRegionWire>("asia")
  const [relationshipRole, setRelationshipRole] = useState<"self" | "public_observed">("self")
  const titleRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    void controller.start()
    return () => controller.dispose()
  }, [controller])

  useEffect(() => {
    if (focusReady) titleRef.current?.focus()
  }, [focusReady])

  useEffect(() => {
    const code = snapshot.status === "error"
      ? snapshot.code
      : snapshot.status === "ready" && snapshot.link.status === "error"
        ? snapshot.link.code
        : undefined
    if (code !== undefined && isAuthSessionFailure(code)) onAuthFailure?.(code)
  }, [onAuthFailure, snapshot])

  const editorVisible = showEditor || (snapshot.status === "ready" && snapshot.profiles.length === 0)
  const busy = snapshot.status === "ready" && (snapshot.link.status === "submitting" || snapshot.link.status === "waiting")
  const pending = snapshot.status === "ready" && snapshot.link.status === "pending"

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void controller.addPlayer({ riotId: riotId.trim(), routingRegion, relationshipRole })
  }

  return (
    <main className="account-access" data-testid="account-access" data-wallpaper-region={wallpaperRegion ?? "default"}>
      <div className="account-access__atmosphere" aria-hidden="true" />
      <header className="account-access__header">
        <button type="button" className="account-access__back" onClick={onBack}>{t("account.back")}</button>
        <LocaleSwitch />
      </header>
      <section className="account-access__intro" aria-labelledby="account-access-title">
        <p className="eyebrow">{t("account.kicker")}</p>
        <h1 id="account-access-title" ref={titleRef} tabIndex={-1}>{t("account.title")}</h1>
        <p>{t("account.lede")}</p>
      </section>
      <section className="account-access__panel" aria-live="polite">
        {snapshot.status === "loading" ? (
          <div className="account-access__state" role="status">
            <span className="account-access__pulse" aria-hidden="true" />
            <p>{t("account.loading")}</p>
          </div>
        ) : snapshot.status === "error" ? (
          <div className="account-access__state" role="alert">
            <h2>{t("account.unavailable_title")}</h2>
            <p>{t("account.unavailable_body")}</p>
            <button type="button" onClick={() => { void controller.start() }}>{t("account.retry")}</button>
          </div>
        ) : (
          <>
            {snapshot.profiles.length > 0 ? (
              <fieldset className="account-access__profiles">
                <legend>{t("account.saved_players")}</legend>
                {snapshot.profiles.map((profile) => (
                  <label className="account-access__profile" key={profile.player_profile_id}>
                    <input
                      type="radio"
                      name="playerProfile"
                      value={profile.player_profile_id}
                      checked={snapshot.selectedProfileId === profile.player_profile_id}
                      onChange={() => controller.selectProfile(profile.player_profile_id)}
                      disabled={busy || pending}
                    />
                    <span className="account-access__profile-mark" aria-hidden="true" />
                    <span>
                      <strong translate="no">{profile.riot_id}</strong>
                      <small>
                        <span className="account-access__region">{t(regionKeys[profile.routing_region])}</span>
                        <span aria-hidden="true"> · </span>
                        <span>{t(profile.relationship_role === "self" ? "account.role_self" : "account.role_observed")}</span>
                      </small>
                    </span>
                  </label>
                ))}
              </fieldset>
            ) : null}

            {editorVisible ? (
              <form className="account-access__form" onSubmit={submit} aria-labelledby="add-player-title">
                <div className="account-access__form-heading">
                  <h2 id="add-player-title">{t("account.add_title")}</h2>
                  {snapshot.profiles.length > 0 ? (
                    <button type="button" disabled={busy || pending} onClick={() => setShowEditor(false)}>{t("account.cancel_add")}</button>
                  ) : null}
                </div>
                <label>
                  <span>Riot ID</span>
                  <input
                    name="riotId"
                    value={riotId}
                    onChange={(event) => setRiotId(event.target.value)}
                    placeholder="Name#Tag"
                    autoComplete="off"
                    minLength={3}
                    maxLength={97}
                    pattern="[^#]+#[^#]+"
                    required
                    disabled={busy || pending}
                  />
                </label>
                <div className="account-access__form-grid">
                  <label>
                    <span>{t("account.region")}</span>
                    <select value={routingRegion} onChange={(event) => setRoutingRegion(event.target.value as RoutingRegionWire)} disabled={busy || pending}>
                      {regions.map((region) => <option key={region} value={region}>{t(regionLongKeys[region])}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>{t("account.relationship")}</span>
                    <select value={relationshipRole} onChange={(event) => setRelationshipRole(event.target.value as "self" | "public_observed")} disabled={busy || pending}>
                      <option value="self">{t("account.role_self_full")}</option>
                      <option value="public_observed">{t("account.role_observed_full")}</option>
                    </select>
                  </label>
                </div>
                <button className="account-access__submit" type="submit" disabled={busy || pending}>
                  {busy ? t("account.adding") : t("account.add_action")}
                </button>
                <p className="account-access__identity-note">{t("auth.identity_boundary")}</p>
                {snapshot.link.status === "pending" ? (
                  <div className="account-access__pending" role="status">
                    <p>{t("account.pending")}</p>
                    <button type="button" onClick={() => { void controller.resumePending() }}>{t("account.check_status")}</button>
                  </div>
                ) : null}
                {snapshot.link.status === "succeeded" ? <p role="status">{t("account.added", { riotId: snapshot.link.riotId })}</p> : null}
                {snapshot.link.status === "failed" ? <p role="alert">{t(failureKeys[snapshot.link.code])}</p> : null}
                {snapshot.link.status === "error" ? <p role="alert">{t("account.link_error")}</p> : null}
              </form>
            ) : (
              <button className="account-access__add" type="button" onClick={() => setShowEditor(true)}>
                {t("account.add_another")}
              </button>
            )}

            <button
              className="account-access__continue"
              type="button"
              disabled={snapshot.selectedProfileId === undefined || busy}
              onClick={() => { if (snapshot.selectedProfileId !== undefined) onContinue(snapshot.selectedProfileId) }}
            >
              {t("account.continue")}
            </button>
          </>
        )}
      </section>
    </main>
  )
}
