import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

type PackageManifest = {
  private?: boolean;
  type?: string;
  engines?: Record<string, string>;
  scripts?: Record<string, string>;
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
};

const manifestPath = resolve(process.cwd(), "package.json");
const manifest = JSON.parse(
  readFileSync(manifestPath, "utf8"),
) as PackageManifest;

const allowedRuntimeDependencies = [
  "@fontsource-variable/manrope",
  "@fontsource-variable/oxanium",
  "@radix-ui/react-dialog",
  "motion",
  "react",
  "react-dom",
] as const;

const forbiddenDependencyPattern =
  /(?:tailwind|shadcn|aceternity|react-bits|magicui|uiverse|gsap|anime(?:js)?|(?:^|\/)ogl$|(?:^|\/)three$|echarts)/i;

describe("web package dependency boundary", () => {
  it("keeps a private, Node 24-compatible package with no install hooks", () => {
    expect(manifest.private).toBe(true);
    expect(manifest.type).toBe("module");
    expect(manifest.engines?.node).toBe(">=24.0.0");

    expect(manifest.scripts).not.toHaveProperty("preinstall");
    expect(manifest.scripts).not.toHaveProperty("install");
    expect(manifest.scripts).not.toHaveProperty("postinstall");
  });

  it("allows only the accepted runtime dependency set", () => {
    const runtimeDependencies = Object.keys(manifest.dependencies ?? {}).sort();

    expect(runtimeDependencies).toEqual([...allowedRuntimeDependencies].sort());
  });

  it("pins every dependency and excludes rejected visual stacks", () => {
    const dependencies = {
      ...(manifest.dependencies ?? {}),
      ...(manifest.devDependencies ?? {}),
    };

    for (const [name, version] of Object.entries(dependencies)) {
      expect(name).not.toMatch(forbiddenDependencyPattern);
      expect(version, `${name} must use an exact version`).toMatch(
        /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/,
      );
    }
  });
});
