import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { AuthGate } from "./AuthGate"
import { AuthSessionError } from "./session"
import { renderWithLocale as render } from "../test/renderWithLocale"

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

    expect(screen.getByRole("heading", { name: /checking sign-in/i })).toBeInTheDocument()
    expect(screen.queryByText("live workbench")).not.toBeInTheDocument()
    resolve?.(session)
    expect(await screen.findByText("live workbench")).toBeInTheDocument()
  })

  it("shows an explicit unavailable state for provider configuration failure", async () => {
    const issue = vi.fn(async () => { throw new AuthSessionError("auth_unavailable", 503) })
    render(<AuthGate client={{ issue }}>
      {() => <p>live workbench</p>}
    </AuthGate>)

    const heading = await screen.findByRole("heading", { name: /sign-in is unavailable/i })
    await waitFor(() => expect(heading).toHaveFocus())
    expect(screen.queryByText("auth_unavailable")).not.toBeInTheDocument()
    expect(screen.queryByText("live workbench")).not.toBeInTheDocument()
  })

  it("projects an expired session as a recoverable boundary", () => {
    render(<AuthGate client={{ issue: vi.fn(async () => session) }} failureCode="auth_session_expired">
      {() => <p>live workbench</p>}
    </AuthGate>)

    expect(screen.getByRole("heading", { name: /your session has ended/i })).toBeInTheDocument()
    expect(screen.queryByText("auth_session_expired")).not.toBeInTheDocument()
  })

  it("keeps a signed-out session distinct and retries without exposing the wire code", async () => {
    const user = userEvent.setup()
    const issue = vi.fn()
      .mockRejectedValueOnce(new AuthSessionError("authentication_required", 401))
      .mockResolvedValueOnce(session)
    render(<AuthGate client={{ issue }}>
      {() => <p>live workbench</p>}
    </AuthGate>)

    expect(await screen.findByRole("heading", { name: /sign in to riftcoach/i })).toBeInTheDocument()
    expect(screen.queryByText("authentication_required")).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /check again/i }))

    expect(await screen.findByText("live workbench")).toBeInTheDocument()
    expect(issue).toHaveBeenCalledTimes(2)
  })

  it("aborts an in-flight session request when the account layer leaves", () => {
    let requestSignal: AbortSignal | undefined
    const issue = vi.fn((signal?: AbortSignal) => {
      requestSignal = signal
      return new Promise<typeof session>(() => undefined)
    })
    const view = render(<AuthGate client={{ issue }}>
      {() => <p>live workbench</p>}
    </AuthGate>)

    expect(requestSignal?.aborted).toBe(false)
    view.unmount()
    expect(requestSignal?.aborted).toBe(true)
  })
})
