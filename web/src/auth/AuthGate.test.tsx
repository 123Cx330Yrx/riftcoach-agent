import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { AuthGate } from "./AuthGate"
import { AuthSessionError } from "./session"

const session = {
  schema_version: "1.0" as const,
  csrf_token: "csrf-token",
  expires_at: "2026-08-24T06:00:00Z",
}

describe("AuthGate", () => {
  it("keeps the workbench behind a checking state until the server session exists", async () => {
    let resolve: ((value: typeof session) => void) | undefined
    const issue = vi.fn(() => new Promise<typeof session>((next) => { resolve = next }))
    render(<AuthGate client={{ issue }}>
      {() => <p>live workbench</p>}
    </AuthGate>)

    expect(screen.getByRole("heading", { name: /checking your session/i })).toBeInTheDocument()
    expect(screen.queryByText("live workbench")).not.toBeInTheDocument()
    resolve?.(session)
    expect(await screen.findByText("live workbench")).toBeInTheDocument()
  })

  it("shows an explicit unavailable state for provider configuration failure", async () => {
    const issue = vi.fn(async () => { throw new AuthSessionError("auth_unavailable", 503) })
    render(<AuthGate client={{ issue }}>
      {() => <p>live workbench</p>}
    </AuthGate>)

    expect(await screen.findByRole("heading", { name: /sign-in is not ready/i })).toBeInTheDocument()
    expect(screen.getByText("auth_unavailable")).toBeInTheDocument()
    expect(screen.queryByText("live workbench")).not.toBeInTheDocument()
  })

  it("projects an expired session as a recoverable boundary", () => {
    render(<AuthGate client={{ issue: vi.fn(async () => session) }} failureCode="auth_session_expired">
      {() => <p>live workbench</p>}
    </AuthGate>)

    expect(screen.getByRole("heading", { name: /session needs attention/i })).toBeInTheDocument()
    expect(screen.getByText("auth_session_expired")).toBeInTheDocument()
  })
})
