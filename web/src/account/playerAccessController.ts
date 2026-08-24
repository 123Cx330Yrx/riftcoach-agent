import { ApiClientError } from "../api/client"
import type { PlayerAccessApi } from "../api/playerLinkApi"
import type {
  PlayerLinkFailureWire,
  PlayerProfileWire,
  RoutingRegionWire,
} from "../api/wire"

export type PlayerAccessLinkState =
  | { readonly status: "idle" }
  | { readonly status: "submitting" }
  | { readonly status: "waiting" }
  | { readonly status: "pending"; readonly link: string }
  | { readonly status: "succeeded"; readonly riotId: string }
  | { readonly status: "failed"; readonly code: PlayerLinkFailureWire["code"]; readonly retryable: boolean }
  | { readonly status: "error"; readonly code: string }

export type PlayerAccessSnapshot =
  | { readonly status: "loading" }
  | { readonly status: "error"; readonly code: string }
  | {
      readonly status: "ready"
      readonly profiles: readonly PlayerProfileWire[]
      readonly selectedProfileId: string | undefined
      readonly link: PlayerAccessLinkState
    }

type ReadyPlayerAccessSnapshot = Extract<PlayerAccessSnapshot, { readonly status: "ready" }>

export interface AddPlayerInput {
  readonly riotId: string
  readonly routingRegion: RoutingRegionWire
  readonly relationshipRole: "self" | "public_observed"
}

type Listener = () => void

const DEFAULT_POLL_DELAYS = [500, 1_000, 2_000, 2_000, 2_000, 2_000, 2_000, 2_000, 2_000, 2_000, 2_000, 2_000, 2_000, 2_000, 2_000] as const

function defaultIdempotencyKey(): string {
  if (typeof globalThis.crypto?.randomUUID !== "function") throw new Error("secure idempotency source unavailable")
  return `player-link-${globalThis.crypto.randomUUID()}`
}

function aborted(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}

function safeErrorCode(error: unknown): string {
  return error instanceof ApiClientError ? error.code : "service_unavailable"
}

function wait(ms: number, signal: AbortSignal): Promise<void> {
  if (signal.aborted) return Promise.reject(new DOMException("Aborted", "AbortError"))
  if (ms <= 0) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const finish = () => {
      signal.removeEventListener("abort", onAbort)
      resolve()
    }
    const onAbort = () => {
      globalThis.clearTimeout(timer)
      signal.removeEventListener("abort", onAbort)
      reject(new DOMException("Aborted", "AbortError"))
    }
    const timer = globalThis.setTimeout(finish, ms)
    signal.addEventListener("abort", onAbort, { once: true })
  })
}

export class PlayerAccessController {
  private readonly api: PlayerAccessApi
  private readonly csrfToken: string
  private readonly idempotencyKeyFactory: () => string
  private readonly pollDelaysMs: readonly number[]
  private readonly listeners = new Set<Listener>()
  private state: PlayerAccessSnapshot = { status: "loading" }
  private generation = 0
  private controller: AbortController | undefined

  constructor(options: {
    readonly api: PlayerAccessApi
    readonly csrfToken: string
    readonly idempotencyKeyFactory?: () => string
    readonly pollDelaysMs?: readonly number[]
  }) {
    this.api = options.api
    this.csrfToken = options.csrfToken
    this.idempotencyKeyFactory = options.idempotencyKeyFactory ?? defaultIdempotencyKey
    this.pollDelaysMs = options.pollDelaysMs ?? DEFAULT_POLL_DELAYS
  }

  get snapshot(): PlayerAccessSnapshot {
    return this.state
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private publish(next: PlayerAccessSnapshot): void {
    this.state = next
    for (const listener of this.listeners) listener()
  }

  private begin(): { generation: number; signal: AbortSignal } {
    this.controller?.abort()
    const controller = new AbortController()
    this.controller = controller
    return { generation: ++this.generation, signal: controller.signal }
  }

  private active(generation: number): boolean {
    return generation === this.generation && this.controller?.signal.aborted === false
  }

  async start(): Promise<void> {
    const { generation, signal } = this.begin()
    this.publish({ status: "loading" })
    try {
      const page = await this.api.listProfiles(signal)
      if (!this.active(generation)) return
      this.publish({
        status: "ready",
        profiles: page.profiles,
        selectedProfileId: page.profiles[0]?.player_profile_id,
        link: { status: "idle" },
      })
    } catch (error) {
      if (!aborted(error) && this.active(generation)) {
        this.publish({ status: "error", code: safeErrorCode(error) })
      }
    }
  }

  selectProfile(profileId: string): void {
    if (this.state.status !== "ready" || !this.state.profiles.some((profile) => profile.player_profile_id === profileId)) {
      throw new Error("profile selection must be owner-scoped")
    }
    this.publish({ ...this.state, selectedProfileId: profileId })
  }

  private async pollLink(
    link: string,
    previous: ReadyPlayerAccessSnapshot,
    generation: number,
    signal: AbortSignal,
  ): Promise<void> {
    for (let index = 0; index < this.pollDelaysMs.length; index += 1) {
      const projection = await this.api.getLink(link, signal)
      if (!this.active(generation)) return
      if (projection.status === "succeeded") {
        const page = await this.api.listProfiles(signal)
        if (!this.active(generation)) return
        const profileId = projection.relationship_id
        if (profileId === null || !page.profiles.some((profile) => profile.player_profile_id === profileId)) {
          this.publish({ ...previous, link: { status: "error", code: "player_profile_not_found" } })
          return
        }
        this.publish({
          status: "ready",
          profiles: page.profiles,
          selectedProfileId: profileId,
          link: { status: "succeeded", riotId: projection.confirmed_riot_id! },
        })
        return
      }
      if (projection.status === "failed") {
        this.publish({
          ...previous,
          link: {
            status: "failed",
            code: projection.failure!.code,
            retryable: projection.failure!.retryable,
          },
        })
        return
      }
      if (index === this.pollDelaysMs.length - 1) {
        this.publish({ ...previous, link: { status: "pending", link } })
        return
      }
      await wait(this.pollDelaysMs[index]!, signal)
    }
    this.publish({ ...previous, link: { status: "pending", link } })
  }

  async addPlayer(input: AddPlayerInput): Promise<void> {
    if (this.state.status !== "ready") throw new Error("player access is not ready")
    if (["submitting", "waiting", "pending"].includes(this.state.link.status)) {
      throw new Error("player link is already active")
    }
    const previous = this.state
    const { generation, signal } = this.begin()
    this.publish({ ...previous, link: { status: "submitting" } })
    try {
      const created = await this.api.createLink({
        ...input,
        csrfToken: this.csrfToken,
        idempotencyKey: this.idempotencyKeyFactory(),
        signal,
      })
      if (!this.active(generation)) return
      this.publish({ ...previous, link: { status: "waiting" } })
      await this.pollLink(created.link, previous, generation, signal)
    } catch (error) {
      if (!aborted(error) && this.active(generation)) {
        this.publish({ ...previous, link: { status: "error", code: safeErrorCode(error) } })
      }
    }
  }

  async resumePending(): Promise<void> {
    const current = this.state
    if (current.status !== "ready") throw new Error("player link is not pending")
    const pendingLink = current.link
    if (pendingLink.status !== "pending") throw new Error("player link is not pending")
    const previous = current
    const link = pendingLink.link
    const { generation, signal } = this.begin()
    this.publish({ ...previous, link: { status: "waiting" } })
    try {
      await this.pollLink(link, previous, generation, signal)
    } catch (error) {
      if (!aborted(error) && this.active(generation)) {
        this.publish({ ...previous, link: { status: "error", code: safeErrorCode(error) } })
      }
    }
  }

  dispose(): void {
    this.generation += 1
    this.controller?.abort()
    this.controller = undefined
    this.listeners.clear()
  }
}
