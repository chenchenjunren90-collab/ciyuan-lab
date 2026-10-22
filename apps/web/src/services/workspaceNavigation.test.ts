import { describe, expect, it } from "vitest";
import { createWorkspaceNavigation, readWorkspaceRoute, workspaceScrollY, WORKSPACE_PAGES } from "./workspaceNavigation";

function fakeBrowser(href = "https://learning.example/?theme=dark") {
  const entries: { href: string; state: unknown }[] = [{ href, state: { existing: "preserved" } }];
  let index = 0;
  const location = { href };
  const history = {
    get state() { return entries[index]!.state; },
    replaceState(state: unknown, _unused: string, url?: string | URL | null) {
      entries[index] = { state, href: url ? String(url) : location.href };
      location.href = entries[index]!.href;
    },
    pushState(state: unknown, _unused: string, url?: string | URL | null) {
      entries.splice(index + 1);
      entries.push({ state, href: url ? String(url) : location.href });
      index += 1;
      location.href = entries[index]!.href;
    },
  };
  return {
    location, history, entries,
    go(offset: number) { index += offset; location.href = entries[index]!.href; },
  };
}

describe("workspace page URLs and browser history", () => {
  it.each(WORKSPACE_PAGES)("can open %s directly or after a refresh", (page) => {
    expect(readWorkspaceRoute(`https://learning.example/?tab=${page}&course=c`)).toEqual({ page, course: "c" });
  });
  it("defaults invalid pages and courses without accepting arbitrary destinations", () => {
    expect(readWorkspaceRoute("https://learning.example/?tab=unknown&course=other")).toEqual({ page: "overview", course: "python" });
  });
  it("canonicalizes the initial URL without creating a phantom Back entry", () => {
    const browser = fakeBrowser();
    const navigation = createWorkspaceNavigation(browser);
    navigation.initialize(navigation.read());
    expect(browser.entries).toHaveLength(1);
    expect(browser.location.href).toContain("tab=overview");
    expect(browser.history.state).toMatchObject({ existing: "preserved" });
  });
  it("records page and course changes, but not repeated clicks on the current page", () => {
    const browser = fakeBrowser();
    const navigation = createWorkspaceNavigation(browser);
    navigation.initialize(navigation.read());
    expect(navigation.commit({ page: "assessment", course: "python" }, 420)).toBe(true);
    expect(navigation.commit({ page: "assessment", course: "python" }, 0)).toBe(false);
    expect(navigation.commit({ page: "assessment", course: "c" }, 180)).toBe(true);
    expect(browser.entries).toHaveLength(3);
    expect(workspaceScrollY(browser.entries[0]!.state)).toBe(420);
    expect(workspaceScrollY(browser.entries[1]!.state)).toBe(180);
  });
  it("restores Back and Forward without pushing the restored route again", () => {
    const browser = fakeBrowser();
    const navigation = createWorkspaceNavigation(browser);
    navigation.initialize(navigation.read());
    navigation.commit({ page: "assessment", course: "python" }, 200);
    navigation.commit({ page: "practice", course: "python" }, 350);
    browser.go(-1);
    expect(navigation.read()).toEqual({ page: "assessment", course: "python" });
    expect(workspaceScrollY(browser.history.state)).toBe(350);
    expect(navigation.commit(navigation.read(), 0)).toBe(false);
    browser.go(1);
    expect(navigation.read().page).toBe("practice");
    expect(browser.entries).toHaveLength(3);
  });
  it("preserves the current palette and unrelated query settings on navigation", () => {
    const browser = fakeBrowser("https://learning.example/?theme=dawn&preview=workspace#old-section");
    const navigation = createWorkspaceNavigation(browser);
    navigation.commit({ page: "projects", course: "data_structures" }, 0);
    const url = new URL(browser.location.href);
    expect(url.searchParams.get("theme")).toBe("dawn");
    expect(url.searchParams.get("preview")).toBe("workspace");
    expect(url.hash).toBe("");
  });
  it("drops the abandoned forward branch after a new navigation", () => {
    const browser = fakeBrowser();
    const navigation = createWorkspaceNavigation(browser);
    navigation.commit({ page: "assessment", course: "python" }, 0);
    navigation.commit({ page: "practice", course: "python" }, 0);
    browser.go(-1);
    navigation.commit({ page: "tutor", course: "python" }, 0);
    expect(browser.entries).toHaveLength(3);
    expect(readWorkspaceRoute(browser.entries[2]!.href).page).toBe("tutor");
  });
  it.each([null, {}, { ciyuanWorkspace: null }, { ciyuanWorkspace: { scrollY: -1 } }, { ciyuanWorkspace: { scrollY: Number.NaN } }])("ignores invalid scroll metadata %j", (state) => {
    expect(workspaceScrollY(state)).toBe(0);
  });
});
