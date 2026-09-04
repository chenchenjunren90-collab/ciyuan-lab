export type ThemeMode = "light" | "dark" | "system";
export type DeviceMode = "auto" | "mobile" | "desktop";

export interface UiPreferences {
  theme: ThemeMode;
  deviceMode: DeviceMode;
  reducedMotion: boolean;
  highContrast: boolean;
  welcomeOnLaunch: boolean;
}

export interface KeyValueStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export interface LocalLearnerAccount {
  id: string;
  displayName: string;
  createdAt: string;
}

export const UI_PREFERENCES_KEY = "ciyuan-ui-preferences-v1";
export const WELCOME_COMPLETE_KEY = "ciyuan-welcome-complete-v1";
export const DISPLAY_NAME_KEY = "ciyuan-display-name";
export const STUDENT_ID_KEY = "ciyuan-student-id";
export const LOCAL_ACCOUNTS_KEY = "ciyuan-local-accounts-v1";

export const DEFAULT_UI_PREFERENCES: UiPreferences = {
  theme: "system",
  deviceMode: "auto",
  reducedMotion: false,
  highContrast: false,
  welcomeOnLaunch: false,
};

const THEMES: ThemeMode[] = ["light", "dark", "system"];
const DEVICE_MODES: DeviceMode[] = ["auto", "mobile", "desktop"];

export function loadUiPreferences(storage: KeyValueStorage): UiPreferences {
  try {
    const raw = storage.getItem(UI_PREFERENCES_KEY);
    if (!raw) return { ...DEFAULT_UI_PREFERENCES };
    const candidate = JSON.parse(raw) as Partial<UiPreferences>;
    return {
      theme: THEMES.includes(candidate.theme as ThemeMode)
        ? candidate.theme as ThemeMode
        : DEFAULT_UI_PREFERENCES.theme,
      deviceMode: DEVICE_MODES.includes(candidate.deviceMode as DeviceMode)
        ? candidate.deviceMode as DeviceMode
        : DEFAULT_UI_PREFERENCES.deviceMode,
      reducedMotion: candidate.reducedMotion === true,
      highContrast: candidate.highContrast === true,
      welcomeOnLaunch: candidate.welcomeOnLaunch === true,
    };
  } catch {
    storage.removeItem(UI_PREFERENCES_KEY);
    return { ...DEFAULT_UI_PREFERENCES };
  }
}

export function saveUiPreferences(storage: KeyValueStorage, preferences: UiPreferences): void {
  storage.setItem(UI_PREFERENCES_KEY, JSON.stringify(preferences));
}

export function resolveTheme(theme: ThemeMode, prefersDark: boolean): "light" | "dark" {
  return theme === "system" ? (prefersDark ? "dark" : "light") : theme;
}

export function applyUiPreferences(
  root: HTMLElement,
  preferences: UiPreferences,
  prefersDark: boolean,
): void {
  root.dataset.theme = resolveTheme(preferences.theme, prefersDark);
  delete root.dataset.accent;
  root.dataset.device = preferences.deviceMode;
  root.dataset.motion = preferences.reducedMotion ? "reduced" : "full";
  root.dataset.contrast = preferences.highContrast ? "high" : "standard";
  root.style.colorScheme = root.dataset.theme;
}

export function ensureLocalStudentId(
  storage: KeyValueStorage,
  createId: () => string,
): string {
  const existing = storage.getItem(STUDENT_ID_KEY)?.trim();
  if (existing) return existing;
  const generated = createLocalLearnerId(createId());
  storage.setItem(STUDENT_ID_KEY, generated);
  return generated;
}

export function createLocalLearnerId(seed: string): string {
  const normalized = seed.replace(/[^a-zA-Z0-9]/g, "");
  // Keep the tail so the random component survives timestamp-based fallbacks
  // used by browsers where crypto.randomUUID is unavailable (for example HTTP).
  return `learner-${normalized.slice(-24)}`;
}

export function loadLocalAccounts(
  storage: KeyValueStorage,
  currentId: string,
  fallbackName: string,
): LocalLearnerAccount[] {
  try {
    const parsed = JSON.parse(storage.getItem(LOCAL_ACCOUNTS_KEY) ?? "[]") as unknown;
    const accounts = Array.isArray(parsed)
      ? parsed.filter((item): item is LocalLearnerAccount => (
          typeof item === "object" && item !== null
          && typeof (item as LocalLearnerAccount).id === "string"
          && typeof (item as LocalLearnerAccount).displayName === "string"
          && typeof (item as LocalLearnerAccount).createdAt === "string"
        ))
      : [];
    if (accounts.some((item) => item.id === currentId)) return accounts;
    return [...accounts, { id: currentId, displayName: fallbackName, createdAt: new Date().toISOString() }];
  } catch {
    storage.removeItem(LOCAL_ACCOUNTS_KEY);
    return [{ id: currentId, displayName: fallbackName, createdAt: new Date().toISOString() }];
  }
}

export function saveLocalAccounts(
  storage: KeyValueStorage,
  accounts: LocalLearnerAccount[],
): void {
  storage.setItem(LOCAL_ACCOUNTS_KEY, JSON.stringify(accounts));
}
