import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const apiTarget = process.env.RIFTCOACH_WEB_API_TARGET ?? "http://127.0.0.1:8000";
if (!/^http:\/\/(?:127\.0\.0\.1|localhost):\d{2,5}$/.test(apiTarget)) {
  throw new Error("RIFTCOACH_WEB_API_TARGET must be an allowlisted local HTTP origin");
}

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: false,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    exclude: ["tests/e2e/**"],
    css: true,
    restoreMocks: true,
  },
});
