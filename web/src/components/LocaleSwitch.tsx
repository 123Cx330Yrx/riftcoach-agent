import { useI18n } from "../i18n/ProductLocaleProvider"
import type { UiLocale } from "../i18n/locale"

const options: readonly { readonly locale: UiLocale; readonly label: "locale.chinese" | "locale.english" }[] = [
  { locale: "zh-CN", label: "locale.chinese" },
  { locale: "en", label: "locale.english" },
]

export function LocaleSwitch() {
  const { locale, setLocale, t } = useI18n()
  return (
    <div className="locale-switch" role="group" aria-label={t("locale.label")}>
      {options.map((option) => (
        <button
          key={option.locale}
          type="button"
          aria-pressed={locale === option.locale}
          onClick={() => setLocale(option.locale)}
        >
          {t(option.label)}
        </button>
      ))}
    </div>
  )
}
