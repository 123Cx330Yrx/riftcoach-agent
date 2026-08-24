import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"

import {
  BrowserLocaleStore,
  resolveUiLocale,
  translate,
  type LocaleStore,
  type MessageKey,
  type UiLocale,
} from "./locale"

interface I18nValue {
  readonly locale: UiLocale
  readonly setLocale: (locale: UiLocale) => void
  readonly t: (key: MessageKey, params?: Readonly<Record<string, string | number>>) => string
  readonly formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string
  readonly formatUtcTime: (value: string | Date) => string
}

const ProductLocaleContext = createContext<I18nValue | undefined>(undefined)

function browserLanguages(): readonly string[] {
  if (typeof navigator === "undefined") return []
  return navigator.languages
}

export function ProductLocaleProvider({
  children,
  store,
  navigatorLanguages,
}: {
  readonly children: ReactNode
  readonly store?: LocaleStore
  readonly navigatorLanguages?: readonly string[]
}) {
  const [localeStore] = useState<LocaleStore>(() => store ?? new BrowserLocaleStore())
  const [locale, setLocaleState] = useState<UiLocale>(() => (
    resolveUiLocale(localeStore, navigatorLanguages ?? browserLanguages())
  ))

  useEffect(() => {
    if (typeof document !== "undefined") document.documentElement.lang = locale
  }, [locale])

  const setLocale = useCallback((next: UiLocale) => {
    try {
      localeStore.write(next)
    } catch {
      // Injected stores follow the same fail-open contract as BrowserLocaleStore.
    }
    setLocaleState(next)
  }, [localeStore])
  const t = useCallback<I18nValue["t"]>(
    (key, params) => translate(locale, key, params),
    [locale],
  )
  const numberFormatters = useMemo(() => new Map<string, Intl.NumberFormat>(), [locale])
  const formatNumber = useCallback<I18nValue["formatNumber"]>((number, options = {}) => {
    const key = JSON.stringify(options)
    let formatter = numberFormatters.get(key)
    if (formatter === undefined) {
      formatter = new Intl.NumberFormat(locale, options)
      numberFormatters.set(key, formatter)
    }
    return formatter.format(number)
  }, [locale, numberFormatters])
  const timeFormatter = useMemo(() => new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
    timeZone: "UTC",
  }), [locale])
  const value = useMemo<I18nValue>(() => ({
    locale,
    setLocale,
    t,
    formatNumber,
    formatUtcTime: (date) => timeFormatter.format(typeof date === "string" ? new Date(date) : date),
  }), [formatNumber, locale, setLocale, t, timeFormatter])

  return <ProductLocaleContext.Provider value={value}>{children}</ProductLocaleContext.Provider>
}

export function useI18n(): I18nValue {
  const value = useContext(ProductLocaleContext)
  if (value === undefined) throw new Error("ProductLocaleProvider is required")
  return value
}
