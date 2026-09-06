import { describe, expect, it } from "vitest";

import {
  DEFAULT_UI_PREFERENCES,
  UI_PREFERENCES_KEY,
  applyUiPreferences,
  createLocalLearnerId,
  ensureLocalStudentId,
  loadLocalAccounts,
  loadUiPreferences,
  resolveTheme,
  saveUiPreferences,
  saveLocalAccounts,
  type KeyValueStorage,
} from "./uiPreferences";

function memoryStorage(initial: Record<string, string> = {}): KeyValueStorage {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

describe("UI preferences", () => {
  it("opens a new learner workspace in white mode", () => {
    expect(loadUiPreferences(memoryStorage()).theme).toBe("light");
    const root = { dataset: {}, style: {} } as unknown as HTMLElement;
    applyUiPreferences(root, loadUiPreferences(memoryStorage()), true);
    expect(root.dataset.theme).toBe("light");
    expect(root.style.colorScheme).toBe("light");
  });

  it("lets a white-mode link override the saved dark theme without losing other preferences", () => {
    const storage = memoryStorage();
    saveUiPreferences(storage, { ...DEFAULT_UI_PREFERENCES, theme: "dark", accent: "solar", reducedMotion: true });
    const linked = loadUiPreferences(storage, "light");
    expect(linked).toMatchObject({ theme: "light", accent: "solar", reducedMotion: true });
    saveUiPreferences(storage, linked);
    expect(loadUiPreferences(storage).theme).toBe("light");
  });

  it("preserves a chosen dark theme and ignores unsupported theme links", () => {
    const storage = memoryStorage();
    saveUiPreferences(storage, { ...DEFAULT_UI_PREFERENCES, theme: "dark" });
    expect(loadUiPreferences(storage).theme).toBe("dark");
    expect(loadUiPreferences(storage, "unknown").theme).toBe("dark");
    expect(loadUiPreferences(storage, "system").theme).toBe("system");
  });
  it("keeps defaults when stored preferences are invalid", () => {
    const storage = memoryStorage({ [UI_PREFERENCES_KEY]: "not-json" });
    expect(loadUiPreferences(storage)).toEqual(DEFAULT_UI_PREFERENCES);
    expect(storage.getItem(UI_PREFERENCES_KEY)).toBeNull();
  });

  it("persists supported appearance and accessibility settings", () => {
    const storage = memoryStorage();
    const preferences = {
      ...DEFAULT_UI_PREFERENCES,
      theme: "dark" as const,
      accent: "solar" as const,
      reducedMotion: true,
      highContrast: true,
    };
    saveUiPreferences(storage, preferences);
    expect(loadUiPreferences(storage)).toEqual(preferences);
  });

  it("falls back when an unsupported accent setting is stored", () => {
    const storage = memoryStorage({
      [UI_PREFERENCES_KEY]: JSON.stringify({
        ...DEFAULT_UI_PREFERENCES,
        accent: "violet",
        deviceMode: "desktop",
      }),
    });
    expect(loadUiPreferences(storage)).toEqual({
      ...DEFAULT_UI_PREFERENCES,
      deviceMode: "desktop",
    });
  });

  it("persists and applies the selected color style", () => {
    const storage = memoryStorage();
    const preferences = { ...DEFAULT_UI_PREFERENCES, accent: "pulse" as const };
    saveUiPreferences(storage, preferences);
    expect(loadUiPreferences(storage).accent).toBe("pulse");

    const root = { dataset: {}, style: {} } as unknown as HTMLElement;
    applyUiPreferences(root, preferences, false);
    expect(root.dataset.accent).toBe("pulse");
  });

  it("resolves the system theme and applies root data attributes", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    const root = { dataset: { accent: "pulse" }, style: {} } as unknown as HTMLElement;
    applyUiPreferences(root, { ...DEFAULT_UI_PREFERENCES, theme: "system" }, false);
    expect(root.dataset).toMatchObject({
      theme: "light",
      motion: "full",
      contrast: "standard",
    });
    expect(root.dataset.accent).toBe("ion");
  });

  it("creates one stable anonymous learner identity per browser", () => {
    const storage = memoryStorage();
    expect(ensureLocalStudentId(storage, () => "abcd-1234-xyz")).toBe("learner-abcd1234xyz");
    expect(ensureLocalStudentId(storage, () => "different")).toBe("learner-abcd1234xyz");
  });

  it("keeps the random tail when UUID APIs are unavailable", () => {
    expect(createLocalLearnerId("1777777777777-random-one"))
      .not.toBe(createLocalLearnerId("1777777777777-random-two"));
  });

  it("keeps multiple local learner accounts isolated by id", () => {
    const storage = memoryStorage();
    const firstId = createLocalLearnerId("first-123");
    const accounts = loadLocalAccounts(storage, firstId, "甲同学");
    accounts.push({ id: createLocalLearnerId("second-456"), displayName: "乙同学", createdAt: "2026-08-30T00:00:00.000Z" });
    saveLocalAccounts(storage, accounts);
    expect(loadLocalAccounts(storage, firstId, "备用称呼")).toMatchObject([
      { id: "learner-first123", displayName: "甲同学" },
      { id: "learner-second456", displayName: "乙同学" },
    ]);
  });
});
