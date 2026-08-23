import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { SafeMarkdown } from "./SafeMarkdown"

describe("restricted verified report text", () => {
  it("renders escaped plain text without HTML, links or images", () => {
    const { container } = render(
      <SafeMarkdown markdown={'## Verified\n\n- Hold the wave\n\n<a href="https://evil.invalid">raw</a>\n\n[external](https://evil.invalid)\n\n![pixel](https://evil.invalid/pixel.png)'} />,
    )

    expect(screen.getByText(/## Verified/)).toBeInTheDocument()
    expect(container).toHaveTextContent("Hold the wave")
    expect(container.querySelector("a")).toBeNull()
    expect(container.querySelector("img")).toBeNull()
    expect(container.querySelector("script")).toBeNull()
    expect(screen.queryByRole("link", { name: "raw" })).not.toBeInTheDocument()
  })
})
