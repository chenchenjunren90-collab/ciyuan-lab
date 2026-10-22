import type { CourseId } from "./api";

export const WORKSPACE_PAGES = ["overview", "assessment", "classroom", "path", "tutor", "practice", "projects"] as const;
export type WorkspacePage = typeof WORKSPACE_PAGES[number];
export interface WorkspaceRoute { page: WorkspacePage; course: CourseId }

type NavigationBrowser = {
  location: Pick<Location, "href">;
  history: Pick<History, "state" | "replaceState" | "pushState">;
};

export function readWorkspaceRoute(href: string): WorkspaceRoute {
  const query = new URL(href).searchParams;
  const page = query.get("tab");
  const course = query.get("course");
  return {
    page: WORKSPACE_PAGES.includes(page as WorkspacePage) ? page as WorkspacePage : "overview",
    course: ["python", "c", "data_structures"].includes(course ?? "") ? course as CourseId : "python",
  };
}

function entryState(state: unknown, scrollY: number) {
  const existing = state && typeof state === "object" && !Array.isArray(state) ? state : {};
  return { ...existing, ciyuanWorkspace: { scrollY } };
}

export function workspaceScrollY(state: unknown): number {
  if (!state || typeof state !== "object" || !("ciyuanWorkspace" in state)) return 0;
  const entry = state.ciyuanWorkspace;
  if (!entry || typeof entry !== "object" || !("scrollY" in entry)) return 0;
  return typeof entry.scrollY === "number" && Number.isFinite(entry.scrollY) && entry.scrollY >= 0 ? entry.scrollY : 0;
}

/** Query URLs work with the existing deployment and keep navigation dependency-free. */
export function createWorkspaceNavigation(browser: NavigationBrowser) {
  function routeUrl(route: WorkspaceRoute) {
    const url = new URL(browser.location.href);
    url.searchParams.set("tab", route.page);
    url.searchParams.set("course", route.course);
    return url;
  }
  return {
    read: () => readWorkspaceRoute(browser.location.href),
    initialize(route: WorkspaceRoute) {
      browser.history.replaceState(entryState(browser.history.state, workspaceScrollY(browser.history.state)), "", routeUrl(route));
    },
    commit(route: WorkspaceRoute, scrollY: number): boolean {
      const current = readWorkspaceRoute(browser.location.href);
      // popstate updates Vue to the URL already selected by the browser. Never push it again.
      if (current.page === route.page && current.course === route.course) return false;
      browser.history.replaceState(entryState(browser.history.state, scrollY), "", browser.location.href);
      const url = routeUrl(route);
      url.hash = "";
      browser.history.pushState(entryState(null, 0), "", url);
      return true;
    },
  };
}
