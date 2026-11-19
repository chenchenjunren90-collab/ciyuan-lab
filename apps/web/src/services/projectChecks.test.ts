import { describe, expect, it } from "vitest";
import { projectCheck, readProjectChecks } from "./projectChecks";
import { currentVerification, type ReviewedSubmission } from "./submittedCode";

const submission: ReviewedSubmission = {
  feedback: "", mastery_updated: [], citations: [],
  next_activity: { activity_id: "next", activity_type: "concept", reason: "" },
  verification: { accepted: false, passed_tests: 1, total_tests: 3, diagnostics: ["公开样例未通过"] },
};

describe("practice evidence", () => {
  it("only uses diagnostics from the exact submitted text, including after restoring an older draft", () => {
    expect(currentVerification(submission, "x")).toBeNull();
    const result = { ...submission, submittedSource: "x" };
    expect(currentVerification(result, "y")).toBeNull();
    expect(currentVerification(result, "x")).toBe(submission.verification);
  });
  it("retains partial results and excludes unavailable or unrelated checks", () => {
    const check = projectCheck(submission);
    expect(check).toMatchObject({ passed: 1, total: 3 });
    expect(projectCheck({ ...submission, verification: null })).toBeNull();
    expect(projectCheck({ ...submission, verification: {
      accepted: false, passed_tests: 0, total_tests: 3, diagnostics: ["验证服务暂不可用"],
    } })).toBeNull();
    expect(readProjectChecks(JSON.stringify({ a: check, b: check, c: { ...check, passed: 4 } }), ["a", "c"])).toEqual({ a: check });
    expect(readProjectChecks("broken", ["a"])).toEqual({});
  });
});
