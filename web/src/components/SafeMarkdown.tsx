import { createElement, type ReactNode } from "react"
import Markdown, { type Components, type ExtraProps } from "react-markdown"
import remarkGfm from "remark-gfm"
import type { Heading, Root, RootContent } from "mdast"

import "../styles/safe-markdown.css"

const allowedElements = [
  "h1", "h2", "h3", "h4", "h5", "h6", "p", "strong", "em", "del",
  "blockquote", "ul", "ol", "li", "hr", "pre", "code", "br", "sup",
  "table", "thead", "tbody", "tr", "th", "td", "a", "img", "input",
]

// Nest the report outline under its page section, including reports starting at ##.
function reportHeadings({ startLevel }: { startLevel: number }) {
  return (tree: Root) => {
    const headings: Heading[] = []
    function visit(nodes: readonly RootContent[]) {
      for (const node of nodes) {
        if (node.type === "heading") headings.push(node)
        if ("children" in node) visit(node.children)
      }
    }
    visit(tree.children)
    const firstLevel = Math.min(...headings.map((node) => node.depth))
    for (const node of headings) {
      node.depth = Math.min(6, startLevel + node.depth - firstLevel) as Heading["depth"]
    }
  }
}

interface SafeMarkdownProps {
  readonly markdown: string
  readonly headingLevel?: 3 | 4
  readonly tableLabel?: string
  readonly tableHint?: string
}

export function SafeMarkdown({ markdown, headingLevel = 3, tableLabel = "报告表格", tableHint = "左右滑动查看完整表格" }: SafeMarkdownProps) {
  // Keep link/image source as escaped text, including unsafe URLs. Never forward
  // URL attributes or raw node props to a DOM element; no HTML parser is enabled.
  function inertReference({ node, children }: ExtraProps & { children?: ReactNode }) {
    const start = node?.position?.start.offset
    const end = node?.position?.end.offset
    return <span className="safe-markdown__reference">{
      start !== undefined && end !== undefined ? markdown.slice(start, end) : children
    }</span>
  }
  const headings = Object.fromEntries([1, 2, 3, 4, 5, 6].map((level) => [
    `h${level}`,
    ({ children }: { children?: ReactNode }) => createElement(`h${level}`, {
      className: level === headingLevel ? "safe-markdown__title" : "safe-markdown__heading",
    }, children),
  ])) as Components

  return (
    <div className="safe-markdown" translate="no">
      <Markdown
        remarkPlugins={[remarkGfm, [reportHeadings, { startLevel: headingLevel }]]}
        allowedElements={allowedElements}
        unwrapDisallowed
        components={{
          ...headings,
          a: inertReference,
          img: inertReference,
          input: ({ checked }) => <span>{checked ? "[x] " : "[ ] "}</span>,
          table: ({ children }) => (
            <div className="safe-markdown__table">
              <p className="safe-markdown__table-hint">{tableHint}</p>
              <div className="safe-markdown__table-scroll" role="region" aria-label={tableLabel} tabIndex={0}>
                <table>{children}</table>
              </div>
            </div>
          ),
        }}
      >{markdown}</Markdown>
    </div>
  )
}
