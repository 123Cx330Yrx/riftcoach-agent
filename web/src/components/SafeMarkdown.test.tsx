import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { SafeMarkdown } from "./SafeMarkdown"
import verifiedReport from "../../tests/fixtures/verified-report-20261103.md?raw"

describe("restricted report Markdown", () => {
  it("renders structure but keeps HTML, links and images inert", () => {
    const { container } = render(
      <SafeMarkdown markdown={'## Verified\n\n- Hold the wave\n\n<a href="https://evil.invalid">raw</a>\n\n[external](https://evil.invalid)\n\n![pixel](https://evil.invalid/pixel.png)'} />,
    )

    expect(screen.getByRole("heading", { name: "Verified", level: 3 })).toBeInTheDocument()
    expect(screen.getByRole("listitem")).toHaveTextContent("Hold the wave")
    expect(container).toHaveTextContent("Hold the wave")
    expect(container.querySelector("a")).toBeNull()
    expect(container.querySelector("img")).toBeNull()
    expect(container.querySelector("script")).toBeNull()
    expect(screen.queryByRole("link", { name: "raw" })).not.toBeInTheDocument()
    expect(container).toHaveTextContent('<a href="https://evil.invalid">raw</a>')
    expect(container).toHaveTextContent("[external](https://evil.invalid)")
    expect(container).toHaveTextContent("![pixel](https://evil.invalid/pixel.png)")
  })

  it.each([
    '<script>alert(1)</script>\n\n<iframe src="https://evil.invalid"></iframe>',
    '<img src=x onerror="alert(1)">\n\n<svg onload="alert(1)"></svg>',
    '[run](javascript:alert%281%29) ![pixel](data:image/svg+xml;base64,PHN2Zz4=)',
    '[![nested](https://evil.invalid/pixel)](https://evil.invalid)\n\nhttps://evil.invalid',
    '&lt;script&gt;alert(1)&lt;/script&gt;\n\n<form><input autofocus></form>',
  ])("never produces active content from %s", (markdown) => {
    const { container } = render(<SafeMarkdown markdown={markdown} />)
    expect(container.querySelector("a,img,script,iframe,svg,form,input,style,link,object,embed,video,audio")).toBeNull()
    expect(container.querySelector("[href],[src],[srcset],[onerror],[onload],[autofocus]")).toBeNull()
    expect(container.firstElementChild).toHaveAttribute("translate", "no")
  })

  it("preserves every paragraph, number, list entry, table cell and citation in the full verified report", () => {
    const markdown = verifiedReport
    const { container } = render(<SafeMarkdown markdown={markdown} headingLevel={4} />)
    expect(screen.getAllByRole("heading")).toHaveLength(8)
    expect(screen.getByRole("heading", { level: 4 })).toHaveTextContent("RiftCoach 教练式复盘报告")
    expect(screen.getAllByRole("heading", { level: 5 })).toHaveLength(7)
    expect(screen.getAllByRole("listitem")).toHaveLength(15)
    expect(screen.getAllByRole("row")).toHaveLength(4)
    expect(screen.getAllByRole("columnheader")).toHaveLength(4)
    expect(screen.getAllByRole("cell").map((cell) => cell.textContent)).toEqual([
      "补刀/分钟", "8.14", "5.38", "输局低 2.75",
      "伤害/分钟", "1280.92", "535.77", "输局低 745.15",
      "视野分", "23", "52.67", "输局高 29.67",
    ])
    const visible = container.textContent!.replace(/\s+/g, " ")
    // This fixed source fixture has one paragraph/item per line; test all of it.
    for (const line of markdown.split(/\r?\n/).filter((line) => line && !line.startsWith("|"))) {
      const words = line.replace(/^#{1,6} |^(?:- |\d+\. )/g, "").replace(/\*\*/g, "").replace(/\s+/g, " ")
      expect(visible).toContain(words)
    }
  })

  it("handles nested lists, escaped syntax, code and task text without hiding content", () => {
    const { container } = render(<SafeMarkdown headingLevel={4} markdown={'## Section\n\n3. Keep **2.75** [K1]\n   - *Nested* ~~old~~\n\n- [x] done\n\n\\*literal\\*\n\n```html\n<img src="remote">\n```'} />)
    expect(screen.getByRole("heading", { name: "Section", level: 4 })).toBeInTheDocument()
    expect(container.querySelector("ol")).toHaveAttribute("start", "3")
    expect(container.querySelector("strong")).toHaveTextContent("2.75")
    expect(container.querySelector("em")).toHaveTextContent("Nested")
    expect(container.querySelector("del")).toHaveTextContent("old")
    expect(container).toHaveTextContent("[x] done")
    expect(container).toHaveTextContent("*literal*")
    expect(container.querySelector("pre code")).toHaveTextContent('<img src="remote">')
    expect(container.querySelector("img,input")).toBeNull()
  })
})
