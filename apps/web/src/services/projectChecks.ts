import type { SubmissionResult } from "./api";
import { verificationUnavailable } from "./workspaceState";

export interface ProjectCheck { passed: number; total: number; at: string }

export function projectCheck(result: SubmissionResult): ProjectCheck | null {
  const v = result.verification;
  if (!v || verificationUnavailable(result) || v.total_tests < 1) return null;
  return { passed: v.passed_tests, total: v.total_tests, at: new Date().toISOString() };
}

export function readProjectChecks(raw: string | null, ids: string[]): Record<string, ProjectCheck> {
  try {
    const data = JSON.parse(raw || "{}");
    return Object.fromEntries(ids.flatMap(id => {
      const item = data?.[id];
      if (!item || !Number.isInteger(item.passed) || !Number.isInteger(item.total)
        || item.total < 1 || item.passed < 0 || item.passed > item.total
        || typeof item.at !== "string" || !Number.isFinite(Date.parse(item.at))) return [];
      return [[id, { passed: item.passed, total: item.total, at: item.at }]];
    }));
  } catch { return {}; }
}
