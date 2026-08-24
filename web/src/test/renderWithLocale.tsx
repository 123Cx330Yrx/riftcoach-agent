import { render, type RenderOptions } from "@testing-library/react"
import type { ReactElement, ReactNode } from "react"

import { ProductLocaleProvider } from "../i18n/ProductLocaleProvider"
import type { LocaleStore, UiLocale } from "../i18n/locale"

export function renderWithLocale(
  ui: ReactElement,
  locale: UiLocale = "en",
  options?: Omit<RenderOptions, "wrapper">,
) {
  const store: LocaleStore = { read: () => locale, write: () => undefined }
  function Wrapper({ children }: { readonly children: ReactNode }) {
    return <ProductLocaleProvider store={store}>{children}</ProductLocaleProvider>
  }
  return render(ui, { ...options, wrapper: Wrapper })
}
