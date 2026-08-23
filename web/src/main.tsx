import "@fontsource-variable/manrope"
import "@fontsource-variable/oxanium"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import { App } from "./app/App"
import "./styles/tokens.css"
import "./styles/global.css"
import "./styles/workbench.css"

const root = document.getElementById("root")
if (root === null) {
  throw new Error("RiftCoach web root is missing")
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
