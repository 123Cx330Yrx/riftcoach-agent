import { describe, expect, it, vi } from "vitest"

import {
  createTaskEventStream,
  type EventSourceLike,
  type TaskEventStreamState,
} from "./taskEventStream"

const TASK_ID = "96000000-0000-4000-8000-000000000001"
const RUN_ID = "review_live_workbench_1"
const DIGEST = "a".repeat(64)

function payload(cursor: number, status = "running") {
  return JSON.stringify({
    event_schema_version: "1.0",
    event_cursor: cursor,
    event_identity: DIGEST,
    task_id: TASK_ID,
    run_id: RUN_ID,
    task_sequence: cursor,
    event_kind: status === "succeeded" ? "succeeded" : "heartbeat",
    status_after: status,
    lease_generation: 1,
    reason: status === "succeeded" ? "quality_gate_passed" : null,
    occurred_at: "2026-08-23T11:00:00Z",
  })
}

class FakeEventSource implements EventSourceLike {
  readonly listeners = new Map<string, (event: MessageEvent<string>) => void>()
  onopen: ((event: Event) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  close = vi.fn()

  addEventListener(type: string, listener: EventListenerOrEventListenerObject): void {
    this.listeners.set(type, listener as (event: MessageEvent<string>) => void)
  }

  emit(type: string, data: string, lastEventId = ""): void {
    this.listeners.get(type)?.({ data, lastEventId } as MessageEvent<string>)
  }
}

describe("one native EventSource lifecycle", () => {
  it("accepts cursor jumps, ignores replay duplicates and closes on terminal", () => {
    const source = new FakeEventSource()
    const events: number[] = []
    const states: TaskEventStreamState[] = []
    createTaskEventStream({
      taskId: TASK_ID,
      runId: RUN_ID,
      afterCursor: 2,
      eventSourceFactory: () => source,
      onEvent: (event) => events.push(event.event_cursor),
      onState: (state) => states.push(state),
      onTerminal: vi.fn(),
    })

    source.onopen?.(new Event("open"))
    source.emit("task.lifecycle", payload(2), "2")
    source.emit("task.lifecycle", payload(5), "5")
    source.emit("task.lifecycle", payload(6, "succeeded"), "6")

    expect(events).toEqual([5, 6])
    expect(states).toContain("live")
    expect(source.close).toHaveBeenCalledTimes(1)
  })

  it("keeps transport reconnecting separate from Product State", () => {
    const source = new FakeEventSource()
    const states: TaskEventStreamState[] = []
    createTaskEventStream({
      taskId: TASK_ID,
      runId: RUN_ID,
      eventSourceFactory: () => source,
      onEvent: vi.fn(),
      onState: (state) => states.push(state),
      onTerminal: vi.fn(),
    })

    source.onerror?.(new Event("error"))

    expect(states.at(-1)).toBe("reconnecting")
    expect(source.close).not.toHaveBeenCalled()
  })

  it("fails closed for identity drift, event id mismatch and stream.error", () => {
    for (const emit of [
      (source: FakeEventSource) => source.emit("task.lifecycle", payload(3).replace(RUN_ID, "review_other"), "3"),
      (source: FakeEventSource) => source.emit("task.lifecycle", payload(3), "4"),
      (source: FakeEventSource) => source.emit("stream.error", '{"code":"service_unavailable"}'),
    ]) {
      const source = new FakeEventSource()
      const states: TaskEventStreamState[] = []
      createTaskEventStream({
        taskId: TASK_ID,
        runId: RUN_ID,
        eventSourceFactory: () => source,
        onEvent: vi.fn(),
        onState: (state) => states.push(state),
        onTerminal: vi.fn(),
      })

      emit(source)

      expect(states.at(-1)).toBe("error")
      expect(source.close).toHaveBeenCalledTimes(1)
    }
  })

  it("closes explicitly on profile switch or unmount", () => {
    const source = new FakeEventSource()
    const handle = createTaskEventStream({
      taskId: TASK_ID,
      runId: RUN_ID,
      eventSourceFactory: () => source,
      onEvent: vi.fn(),
      onState: vi.fn(),
      onTerminal: vi.fn(),
    })

    handle.close()
    handle.close()

    expect(source.close).toHaveBeenCalledTimes(1)
  })
})
