import { describe, expect, it, vi } from "vitest"

import {
  BrowserLocaleStore,
  enCatalog,
  UI_LOCALE_STORAGE_KEY,
  resolveUiLocale,
  translate,
  zhCnCatalog,
  type LocaleStorage,
} from "./locale"

function storage(initial?: string) {
  return {
    getItem: vi.fn<(key: string) => string | null>(() => initial ?? null),
    setItem: vi.fn<(key: string, value: string) => void>(),
  } satisfies LocaleStorage
}

describe("UI locale contract", () => {
  it("keeps catalog keys and placeholder sets exactly aligned", () => {
    expect(Object.keys(zhCnCatalog).sort()).toEqual(Object.keys(enCatalog).sort())
    const placeholders = (value: string) => [...value.matchAll(/\{\{([a-zA-Z0-9_]+)\}\}/g)]
      .map((match) => match[1])
      .sort()
    for (const key of Object.keys(enCatalog) as Array<keyof typeof enCatalog>) {
      expect(placeholders(zhCnCatalog[key]), key).toEqual(placeholders(enCatalog[key]))
    }
  })

  it("uses strict versioned storage before navigator languages", () => {
    const store = new BrowserLocaleStore(storage('{"schema_version":"1.0","locale":"zh-CN"}'))

    expect(resolveUiLocale(store, ["en-US"])).toBe("zh-CN")
  })

  it.each([
    "not-json",
    "{}",
    '{"schema_version":"2.0","locale":"zh-CN"}',
    '{"schema_version":"1.0","locale":"fr"}',
    '{"schema_version":"1.0","locale":"en","extra":true}',
  ])("rejects corrupt or non-exact persisted values: %s", (value) => {
    const store = new BrowserLocaleStore(storage(value))

    expect(resolveUiLocale(store, ["zh-Hans-CN"])).toBe("zh-CN")
  })

  it("falls back from navigator language to English and tolerates storage exceptions", () => {
    const throwingStore = {
      read: () => { throw new DOMException("blocked") },
      write: () => { throw new DOMException("blocked") },
    }

    expect(resolveUiLocale(throwingStore, ["fr-FR", "de-DE"])).toBe("en")
  })

  it("survives a browser localStorage getter that throws before getItem", () => {
    const getter = vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError")
    })
    try {
      expect(resolveUiLocale(new BrowserLocaleStore(), ["zh-CN"])).toBe("zh-CN")
    } finally {
      getter.mockRestore()
    }
  })

  it("writes only the exact non-sensitive locale envelope", () => {
    const target = storage()
    const store = new BrowserLocaleStore(target)

    store.write("zh-CN")

    expect(target.setItem).toHaveBeenCalledWith(
      UI_LOCALE_STORAGE_KEY,
      '{"schema_version":"1.0","locale":"zh-CN"}',
    )
  })

  it("translates placeholders and falls back to English or the auditable key", () => {
    expect(translate("zh-CN", "timeline.partial_notice", { unavailable: 2, total: 5 })).toBe(
      "共 5 场，其中 2 场暂无事件记录；其余对局可正常查看。",
    )
    expect(translate("zh-CN", "locale.current_language", undefined, {
      en: enCatalog,
      "zh-CN": {},
    })).toBe("English")
    expect(translate("zh-CN", "future.missing.key")).toBe("future.missing.key")
  })
})
