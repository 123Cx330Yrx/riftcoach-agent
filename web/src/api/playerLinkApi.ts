import { ApiClient } from "./client"
import { decodeCreatePlayerLink, decodePlayerLink, decodePlayerProfilePage } from "./decoders"
import type {
  CreatePlayerLinkResponseWire,
  PlayerLinkResponseWire,
  PlayerProfilePageWire,
  RoutingRegionWire,
} from "./wire"

const LINK_PATH_PATTERN = /^\/player-links\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i

export interface CreatePlayerLinkInput {
  readonly riotId: string
  readonly routingRegion: RoutingRegionWire
  readonly relationshipRole: "self" | "public_observed"
  readonly csrfToken: string
  readonly idempotencyKey: string
  readonly signal?: AbortSignal
}

export interface PlayerAccessApi {
  listProfiles(signal?: AbortSignal): Promise<PlayerProfilePageWire>
  createLink(input: CreatePlayerLinkInput): Promise<CreatePlayerLinkResponseWire>
  getLink(link: string, signal?: AbortSignal): Promise<PlayerLinkResponseWire>
}

export class PlayerLinkHttpApi implements PlayerAccessApi {
  constructor(private readonly client: ApiClient) {}

  listProfiles(signal?: AbortSignal) {
    return this.client.getJson("/player-profiles?limit=50", decodePlayerProfilePage, signal)
  }

  createLink(input: CreatePlayerLinkInput) {
    return this.client.postJson(
      "/player-links",
      {
        riot_id: input.riotId,
        routing_region: input.routingRegion,
        relationship_role: input.relationshipRole === "public_observed" ? "observed" : "self",
      },
      decodeCreatePlayerLink,
      { csrfToken: input.csrfToken, idempotencyKey: input.idempotencyKey },
      input.signal,
    )
  }

  async getLink(link: string, signal?: AbortSignal) {
    const match = LINK_PATH_PATTERN.exec(link)
    if (match === null) throw new Error("player link path is invalid")
    const linkTaskId = match[1]!
    return await this.client.getJson(link, (value) => decodePlayerLink(value, linkTaskId), signal)
  }
}
