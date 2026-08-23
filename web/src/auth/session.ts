import { decodeAuthSession } from "../api/decoders"
import type { AuthSessionWire } from "../api/wire"

const AUTH_ERROR_CODES = new Set([
  "auth_unavailable",
  "authentication_required",
  "auth_session_invalid",
  "auth_session_expired",
  "auth_session_revoked",
  "csrf_invalid",
])

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

export class AuthSessionError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, status: number) {
    super(code)
    this.name = "AuthSessionError"
    this.code = code
    this.status = status
  }
}

export interface AuthSessionClient {
  issue(signal?: AbortSignal): Promise<AuthSessionWire>
}

async function boundedErrorCode(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase()
  if (contentType !== "application/json") return "auth_unavailable"
  const body = await response.text()
  if (body.length > 16 * 1024) return "auth_unavailable"
  try {
    const value: unknown = JSON.parse(body)
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      const code = (value as { code?: unknown }).code
      if (typeof code === "string" && AUTH_ERROR_CODES.has(code)) return code
    }
  } catch {
    // Keep the auth boundary body-free and fail closed.
  }
  return "auth_unavailable"
}

export class BrowserAuthSessionClient implements AuthSessionClient {
  private readonly fetcher: Fetcher

  constructor(fetcher: Fetcher = globalThis.fetch.bind(globalThis)) {
    this.fetcher = fetcher
  }

  async issue(signal?: AbortSignal): Promise<AuthSessionWire> {
    const response = await this.fetcher("/api/auth/session", {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      ...(signal === undefined ? {} : { signal }),
    })
    if (!response.ok) throw new AuthSessionError(await boundedErrorCode(response), response.status)
    const contentType = response.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase()
    if (contentType !== "application/json") throw new AuthSessionError("auth_unavailable", response.status)
    let value: unknown
    try {
      value = JSON.parse(await response.text()) as unknown
    } catch {
      throw new AuthSessionError("auth_unavailable", response.status)
    }
    try {
      return decodeAuthSession(value)
    } catch {
      throw new AuthSessionError("auth_unavailable", response.status)
    }
  }
}

export function isAuthSessionFailure(code: string): boolean {
  return AUTH_ERROR_CODES.has(code)
}
