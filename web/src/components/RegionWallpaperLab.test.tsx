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
    expect(screen.getAllByRole("button").filter((button) => (button as HTMLButtonElement).disabled)).toHaveLength(12)
    expect(screen.getByRole("button", { name: /enter riftcoach/i })).toBeVisible()
  })

  it("uses natural Chinese product copy when the locale is zh-CN", () => {
    render(<ProductLocaleProvider navigatorLanguages={["zh-CN"]}><RegionWallpaperLab /></ProductLocaleProvider>)
    expect(screen.getByRole("heading", { name: /选择一处地区.*开启 RiftCoach/i })).toBeInTheDocument()
    expect(screen.getByText("先选一处符文大陆，再进入 RiftCoach。这里的画面只负责氛围，复盘仍由真实数据驱动。")).toBeInTheDocument()
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
})
