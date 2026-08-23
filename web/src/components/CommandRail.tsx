import { Glyph } from "./VisualGlyphs"

const links = [
  { href: "#overview", label: "Review", icon: "review" as const },
  { href: "#coach-brief", label: "Coach", icon: "command" as const },
  { href: "#training", label: "Training", icon: "training" as const },
  { href: "#evidence", label: "Evidence", icon: "evidence" as const },
]

export function CommandRail({ mode }: { readonly mode: "fixture" | "live" }) {
  return (
    <nav className="command-rail" aria-label="Command sections">
      <a className="brand-mark" href="#review-workspace" aria-label="RiftCoach command center">
        <span className="brand-mark__sigil">
          <Glyph name="command" />
        </span>
        <span className="brand-mark__word">RIFT<br />COACH</span>
      </a>

      <div className="command-rail__links">
        {links.map((link, index) => (
          <a
            className={`command-link${index === 0 ? " command-link--active" : ""}`}
            href={link.href}
            key={link.href}
          >
            <Glyph name={link.icon} />
            <span>{link.label}</span>
          </a>
        ))}
      </div>

      <div className="command-rail__mode" aria-label="Runtime environment">
        <span className="mode-pulse" />
        <span>{mode === "live" ? "LIVE" : "FIXTURE"}</span>
        <small>{mode === "live" ? "OWNER SCOPED" : "NO LIVE I/O"}</small>
      </div>
    </nav>
  )
}
