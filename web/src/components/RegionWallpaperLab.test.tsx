import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { ProductLocaleProvider } from "../i18n/ProductLocaleProvider"
import { RegionWallpaperLab } from "./RegionWallpaperLab"

function renderLab() {
  return render(<ProductLocaleProvider navigatorLanguages={["en"]}><RegionWallpaperLab /></ProductLocaleProvider>)
}

describe("RegionWallpaperLab", () => {
  it("renders the local wallpaper candidate and semantic region control", () => {
    renderLab()
    expect(screen.getByTestId("wallpaper-lab")).toHaveAttribute("data-region", "demacia")
    expect(screen.getByRole("button", { name: /demacia/i })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getAllByRole("button")).toHaveLength(16)
    expect(screen.getAllByRole("button").filter((button) => (button as HTMLButtonElement).disabled)).toHaveLength(11)
    expect(screen.getByRole("button", { name: /enter riftcoach/i })).toBeVisible()
  })

  it("switches the local preview when an audited candidate region is selected", () => {
    renderLab()
    fireEvent.click(screen.getByRole("button", { name: /bandle city/i }))
    expect(screen.getByTestId("wallpaper-lab")).toHaveAttribute("data-region", "bandle-city")
    expect(screen.getByRole("button", { name: /bandle city/i })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByTestId("wallpaper-lab").querySelector("video source")).toHaveAttribute("src", "/assets/wallpapers/candidates/bandle-city.webm")
    expect(screen.getByText("Official wallpaper candidate · local preview")).toBeInTheDocument()
  })

  it("uses natural Chinese product copy when the locale is zh-CN", () => {
    render(<ProductLocaleProvider navigatorLanguages={["zh-CN"]}><RegionWallpaperLab /></ProductLocaleProvider>)
    expect(screen.getByRole("heading", { name: /先选一处.*落脚点/i })).toBeInTheDocument()
    expect(screen.getByText("选定地区后，RiftCoach 会带着对应的场景进入账号页。画面负责氛围，复盘仍由真实数据驱动。")).toBeInTheDocument()
  })

  it("keeps a poster fallback when video fails", async () => {
    const { container } = renderLab()
    const video = container.querySelector("video")
    if (video === null) throw new Error("video should be mounted for motion-eligible test")
    fireEvent.error(video)
    await waitFor(() => expect(screen.getByTestId("wallpaper-lab")).toHaveAttribute("data-video", "poster"))
    expect(screen.getByText(/motion file could not play/i)).toBeInTheDocument()
  })

  it("provides a bounded activation transition without navigating or adding another control", async () => {
    vi.useFakeTimers()
    renderLab()
    fireEvent.click(screen.getByRole("button", { name: /enter riftcoach/i }))
    expect(screen.getByTestId("wallpaper-lab")).toHaveClass("wallpaper-lab--activating")
    await act(async () => { vi.advanceTimersByTime(760) })
    expect(screen.getByTestId("wallpaper-lab")).not.toHaveClass("wallpaper-lab--activating")
    vi.useRealTimers()
  })

  it("passes the selected region to the account transition", async () => {
    vi.useFakeTimers()
    const onEnter = vi.fn()
    render(<ProductLocaleProvider navigatorLanguages={["en"]}><RegionWallpaperLab onEnter={onEnter} /></ProductLocaleProvider>)
    fireEvent.click(screen.getByRole("button", { name: /bandle city/i }))
    fireEvent.click(screen.getByRole("button", { name: /enter riftcoach/i }))
    await act(async () => { vi.advanceTimersByTime(760) })
    expect(onEnter).toHaveBeenCalledWith("bandle-city")
    vi.useRealTimers()
  })
})
