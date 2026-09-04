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
      reducedMotion: true,
      highContrast: true,
    };
    saveUiPreferences(storage, preferences);
    expect(loadUiPreferences(storage)).toEqual(preferences);
  });

  it("ignores the retired accent setting from older browsers", () => {
    const storage = memoryStorage({
      [UI_PREFERENCES_KEY]: JSON.stringify({
        ...DEFAULT_UI_PREFERENCES,
        accent: "blue",
        deviceMode: "desktop",
      }),
    });
    expect(loadUiPreferences(storage)).toEqual({
      ...DEFAULT_UI_PREFERENCES,
      deviceMode: "desktop",
    });
  });

  it("resolves the system theme and applies root data attributes", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    const root = { dataset: { accent: "blue" }, style: {} } as unknown as HTMLElement;
    applyUiPreferences(root, DEFAULT_UI_PREFERENCES, false);
    expect(root.dataset).toMatchObject({
      theme: "light",
      motion: "full",
      contrast: "standard",
    });
    expect(root.dataset.accent).toBeUndefined();
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
