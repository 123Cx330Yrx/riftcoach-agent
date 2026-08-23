import type { SVGProps } from "react"

export type GlyphName =
  | "command"
  | "review"
  | "evidence"
  | "training"
  | "arrow"
  | "close"
  | "check"
  | "limit"
  | "withheld"
  | "pending"

interface GlyphProps extends SVGProps<SVGSVGElement> {
  readonly name: GlyphName
}

export function Glyph({ name, ...props }: GlyphProps) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    ...props,
  }

  switch (name) {
    case "command":
      return (
        <svg {...common}>
          <path d="M12 2.8 20 7.4v9.2L12 21.2 4 16.6V7.4Z" />
          <path d="m8.2 14.8 3.8-7.6 3.8 7.6-3.8 2.1Z" />
        </svg>
      )
    case "review":
      return (
        <svg {...common}>
          <path d="M4 17.8 9 12l3 2.7L20 6" />
          <path d="M17 6h3v3" />
          <path d="M4 5v14h16" />
        </svg>
      )
    case "evidence":
      return (
        <svg {...common}>
          <path d="M12 3 20 7v5c0 4.8-3.3 7.6-8 9-4.7-1.4-8-4.2-8-9V7Z" />
          <path d="m8.4 12.3 2.2 2.2 5-5" />
        </svg>
      )
    case "training":
      return (
        <svg {...common}>
          <path d="M4 19V9m5 10V5m6 14v-7m5 7V3" />
          <path d="m3 8 6-4 6 7 6-9" />
        </svg>
      )
    case "arrow":
      return (
        <svg {...common}>
          <path d="M5 12h13" />
          <path d="m14 7 5 5-5 5" />
        </svg>
      )
    case "close":
      return (
        <svg {...common}>
          <path d="m6 6 12 12M18 6 6 18" />
        </svg>
      )
    case "check":
      return (
        <svg {...common}>
          <path d="m5 12.5 4.2 4L19 7" />
        </svg>
      )
    case "limit":
      return (
        <svg {...common}>
          <path d="M12 3 21 19H3Z" />
          <path d="M12 9v4.2M12 16.4v.1" />
        </svg>
      )
    case "withheld":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="8.5" />
          <path d="m6 18 12-12" />
        </svg>
      )
    case "pending":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="8.5" />
          <path d="M12 7v5l3.2 2" />
        </svg>
      )
  }
}
