import { decodeTaskEvent } from "./decoders"
import type { TaskEventWire } from "./wire"

const SSE_EVENT_LIMIT = 64 * 1024
const TERMINAL_STATUSES = new Set(["succeeded", "failed", "cancelled"])

export type TaskEventStreamState =
  | "connecting"
  | "live"
  | "reconnecting"
  | "error"
  | "closed"

export interface EventSourceLike {
  onopen: ((event: Event) => void) | null
  onerror: ((event: Event) => void) | null
  addEventListener(type: string, listener: EventListenerOrEventListenerObject): void
  close(): void
}

export interface TaskEventStreamCallbacks {
  readonly onEvent: (event: TaskEventWire) => void
  readonly onState: (state: TaskEventStreamState) => void
  readonly onTerminal: (event: TaskEventWire) => void | Promise<void>
}

export interface TaskEventStreamHandle {
  close(): void
}

export interface CreateTaskEventStreamOptions extends TaskEventStreamCallbacks {
  readonly taskId: string
  readonly runId: string
  readonly afterCursor?: number
  readonly eventSourceFactory?: (url: string) => EventSourceLike
}

function nativeEventSource(url: string): EventSourceLike {
  return new EventSource(url)
}

function hasBoundedData(event: MessageEvent<string>): boolean {
  return typeof event.data === "string"
    && new TextEncoder().encode(event.data).byteLength <= SSE_EVENT_LIMIT
}

function isSafeStreamError(data: string): boolean {
  try {
    const value = JSON.parse(data) as unknown
    if (value === null || typeof value !== "object" || Array.isArray(value)) return false
    const row = value as Record<string, unknown>
    return Object.keys(row).length === 1 && row.code === "service_unavailable"
  } catch {
    return false
  }
}

export function createTaskEventStream(
  options: CreateTaskEventStreamOptions,
): TaskEventStreamHandle {
  let cursor = options.afterCursor ?? 0
  let closed = false
  const source = (options.eventSourceFactory ?? nativeEventSource)(
    `/api/tasks/${encodeURIComponent(options.taskId)}/events/stream`,
  )

  const publishState = (state: TaskEventStreamState): void => {
    if (!closed || state === "closed") options.onState(state)
  }

  const closeSource = (publishClosed: boolean): void => {
    if (closed) return
    closed = true
    source.close()
    if (publishClosed) publishState("closed")
  }

  const close = (): void => closeSource(true)

  const failClosed = (): void => {
    if (closed) return
    publishState("error")
    closeSource(false)
  }

  publishState("connecting")
  source.onopen = () => {
    if (!closed) publishState("live")
  }
  source.onerror = () => {
    if (!closed) publishState("reconnecting")
  }

  source.addEventListener("task.lifecycle", ((message: MessageEvent<string>) => {
    if (closed || !hasBoundedData(message)) {
      if (!closed) failClosed()
      return
    }
    try {
      const event = decodeTaskEvent(JSON.parse(message.data) as unknown, {
        taskId: options.taskId,
        runId: options.runId,
      })
      if (message.lastEventId !== "" && message.lastEventId !== String(event.event_cursor)) {
        failClosed()
        return
      }
      if (event.event_cursor <= cursor) return
      cursor = event.event_cursor
      options.onEvent(event)
      if (TERMINAL_STATUSES.has(event.status_after)) {
        close()
        void options.onTerminal(event)
      }
    } catch {
      failClosed()
    }
  }) as EventListener)

  source.addEventListener("stream.error", ((message: MessageEvent<string>) => {
    if (closed) return
    if (!hasBoundedData(message) || !isSafeStreamError(message.data)) {
      failClosed()
      return
    }
    failClosed()
  }) as EventListener)

  return { close }
}
