import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { LocaleSwitch } from "../components/LocaleSwitch"
import {
  ProductLocaleProvider,
  useI18n,
} from "./ProductLocaleProvider"
import type { LocaleStore, UiLocale } from "./locale"

function Probe() {
  const { locale, t, formatUtcTime } = useI18n()
  return <output>{locale}:{t("locale.current_language")}:{formatUtcTime("2026-08-24T00:05:06Z")}</output>
}

describe("ProductLocaleProvider", () => {
  it("resolves navigator locale, synchronizes document lang and persists explicit switches", async () => {
    const user = userEvent.setup()
    const store: LocaleStore = { read: vi.fn(() => undefined), write: vi.fn() }
    render(
      <ProductLocaleProvider store={store} navigatorLanguages={["zh-Hans-CN", "en-US"]}>
        <LocaleSwitch />
        <Probe />
      </ProductLocaleProvider>,
    )

    expect(screen.getByText("zh-CN:中文:00:05:06")).toBeInTheDocument()
    expect(document.documentElement.lang).toBe("zh-CN")

    await user.click(screen.getByRole("button", { name: "English" }))

    expect(screen.getByText("en:English:00:05:06")).toBeInTheDocument()
    expect(document.documentElement.lang).toBe("en")
    expect(store.write).toHaveBeenCalledTimes(1)
    expect(store.write).toHaveBeenCalledWith("en")
  })

  it("does not write locale storage during initial resolution", () => {
    const store: LocaleStore = { read: vi.fn<() => UiLocale | undefined>(() => "en"), write: vi.fn() }
    render(
      <ProductLocaleProvider store={store} navigatorLanguages={["zh-CN"]}>
        <Probe />
      </ProductLocaleProvider>,
    )

    expect(screen.getByText("en:English:00:05:06")).toBeInTheDocument()
    expect(store.write).not.toHaveBeenCalled()
  })

  it("supports keyboard switching and fails open when persistence is blocked", async () => {
    const user = userEvent.setup()
    const store: LocaleStore = {
      read: vi.fn<() => UiLocale | undefined>(() => "en"),
      write: vi.fn(() => { throw new DOMException("blocked", "SecurityError") }),
    }
    render(
      <ProductLocaleProvider store={store}>
        <LocaleSwitch />
        <Probe />
      </ProductLocaleProvider>,
    )

    const chinese = screen.getByRole("button", { name: "中文" })
    expect(chinese).toHaveAttribute("aria-pressed", "false")
    await user.tab()
    expect(chinese).toHaveFocus()
    await user.keyboard(" ")

    expect(chinese).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByText("zh-CN:中文:00:05:06")).toBeInTheDocument()
    expect(document.documentElement.lang).toBe("zh-CN")
  })
})
