const JSON_BODY_LIMIT = 2 * 1024 * 1024
const TEXT_BODY_LIMIT = 1024 * 1024

const ALLOWED_ERROR_CODES = new Set([
  "request_invalid",
  "service_unavailable",
  "player_profile_not_found",
  "task_not_found",
  "run_not_found",
  "run_not_ready",
  "run_not_available",
  "report_not_available",
  "run_integrity_failed",
  "evidence_not_available",
  "evidence_integrity_failed",
  "evidence_unavailable",
  "training_scope_not_found",
  "training_plan_not_found",
  "auth_unavailable",
  "authentication_required",
  "auth_session_invalid",
  "auth_session_expired",
  "auth_session_revoked",
  "csrf_invalid",
])

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

export class ApiClientError extends Error {
  readonly code: string
  readonly status: number
  readonly runId: string | undefined

  constructor(code: string, status: number, runId?: string) {
    super(code)
    this.name = "ApiClientError"
    this.code = code
    this.status = status
    this.runId = runId
  }
}

export interface ApiClientOptions {
  readonly fetcher?: Fetcher
}

function apiPath(endpoint: string): string {
  if (
    typeof endpoint !== "string" ||
    !endpoint.startsWith("/") ||
    endpoint.startsWith("//") ||
    endpoint.includes("://") ||
    endpoint.split("/").includes("..") ||
    /[\u0000-\u001f\u007f]/.test(endpoint)
  ) {
    throw new Error("API endpoint must be a safe relative path")
  }
  return `/api${endpoint}`
}

function contentLength(response: Response): number | undefined {
  const raw = response.headers.get("content-length")
  if (raw === null) return undefined
  const parsed = Number(raw)
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : undefined
}

async function boundedText(response: Response, limit: number): Promise<string> {
  const declared = contentLength(response)
  if (declared !== undefined && declared > limit) throw new Error("api_body_too_large")
  if (response.body === null) return ""

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  const chunks: string[] = []
  let received = 0
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      received += value.byteLength
      if (received > limit) {
        await reader.cancel().catch(() => undefined)
        throw new Error("api_body_too_large")
      }
      chunks.push(decoder.decode(value, { stream: true }))
    }
    chunks.push(decoder.decode())
    return chunks.join("")
  } finally {
    reader.releaseLock()
  }
}

function isJson(response: Response): boolean {
  const value = response.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase()
  return value === "application/json" || value?.endsWith("+json") === true
}

async function errorFrom(response: Response): Promise<ApiClientError> {
  if (!isJson(response)) return new ApiClientError("api_error_invalid", response.status)
  let value: unknown
  try {
    value = JSON.parse(await boundedText(response, 16 * 1024)) as unknown
  } catch {
    return new ApiClientError("api_error_invalid", response.status)
  }
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return new ApiClientError("api_error_invalid", response.status)
  }
  const row = value as Record<string, unknown>
  const keys = Object.keys(row)
  if (
    keys.some((key) => key !== "code" && key !== "run_id") ||
    typeof row.code !== "string" ||
    !ALLOWED_ERROR_CODES.has(row.code) ||
    (row.run_id !== undefined && typeof row.run_id !== "string")
  ) {
    return new ApiClientError("api_error_invalid", response.status)
  }
  return new ApiClientError(row.code, response.status, row.run_id as string | undefined)
}

export class ApiClient {
  private readonly fetcher: Fetcher

  constructor(options: ApiClientOptions = {}) {
    this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis)
  }

  async getJson<T>(
    endpoint: string,
    decode: (value: unknown) => T,
    signal?: AbortSignal,
  ): Promise<T> {
    const response = await this.fetcher(apiPath(endpoint), {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      ...(signal === undefined ? {} : { signal }),
    })
    if (!response.ok) throw await errorFrom(response)
    if (!isJson(response)) throw new Error("api_content_type_invalid")
    let value: unknown
    try {
      value = JSON.parse(await boundedText(response, JSON_BODY_LIMIT)) as unknown
    } catch (error) {
      if (error instanceof Error && error.message === "api_body_too_large") throw error
      throw new Error("api_json_invalid")
    }
    return decode(value)
  }

  async getText<T>(
    endpoint: string,
    decode: (value: unknown) => T,
    signal?: AbortSignal,
  ): Promise<T> {
    const response = await this.fetcher(apiPath(endpoint), {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "text/markdown" },
      ...(signal === undefined ? {} : { signal }),
    })
    if (!response.ok) throw await errorFrom(response)
    const mediaType = response.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase()
    if (mediaType !== "text/markdown") throw new Error("api_content_type_invalid")
    return decode(await boundedText(response, TEXT_BODY_LIMIT))
  }
}
