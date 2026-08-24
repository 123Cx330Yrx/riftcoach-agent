import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import { UI_LOCALE_STORAGE_KEY } from "../i18n/locale";

afterEach(() => {
  cleanup();
  try {
    window.localStorage.removeItem(UI_LOCALE_STORAGE_KEY);
  } catch {
    // Tests that deliberately replace the storage getter must still clean up safely.
  }
  document.documentElement.lang = "en";
  window.history.replaceState(null, "", "/");
});
