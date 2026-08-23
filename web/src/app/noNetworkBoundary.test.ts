import { readFileSync, readdirSync, statSync } from "node:fs"
import { extname, join, relative, resolve } from "node:path"

import { describe, expect, it } from "vitest"

const root = resolve(process.cwd())
const productionExtensions = new Set([".ts", ".tsx", ".css", ".html"])
const forbiddenNetworkTokens = [
  /\bfetch\s*\(/,
  /\bglobalThis\.fetch\b/,
  /\bEventSource\s*\(/,
  /\bXMLHttpRequest\b/,
  /\bWebSocket\s*\(/,
  /https?:\/\//i,
] as const

function productionFiles(directory: string): string[] {
  const files: string[] = []
  for (const name of readdirSync(directory)) {
    const path = join(directory, name)
    if (statSync(path).isDirectory()) {
      if (["node_modules", "dist", "test-results", "tests", "test"].includes(name)) {
        continue
      }
      files.push(...productionFiles(path))
      continue
    }
    if (productionExtensions.has(extname(path)) && !path.endsWith(".test.ts") && !path.endsWith(".test.tsx")) {
      files.push(path)
    }
  }
  return files
}

describe("8E browser network boundary", () => {
  it("keeps network access inside the approved same-origin client seams", () => {
    const scanned = [resolve(root, "index.html"), ...productionFiles(resolve(root, "src"))]
    const violations: string[] = []

    for (const path of scanned) {
      const content = readFileSync(path, "utf8")
      const projectPath = relative(root, path).replaceAll("\\", "/")
      for (const pattern of forbiddenNetworkTokens) {
        if (pattern.test(content)) {
          if (projectPath === "src/api/client.ts" && pattern.source === "\\bglobalThis\\.fetch\\b") {
            continue
          }
          if (projectPath === "src/api/taskEventStream.ts" && pattern.source === "\\bEventSource\\s*\\(") {
            continue
          }
          violations.push(`${relative(root, path)} matched ${pattern.source}`)
        }
      }
    }

    expect(violations).toEqual([])
  })
})
