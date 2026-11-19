import type { SubmissionResult } from "./api";

// Older classroom drafts contain the result without the source it was run against.
export type ReviewedSubmission = SubmissionResult & { submittedSource?: string };

export function currentVerification(result: ReviewedSubmission | null, draft: string) {
  return result?.submittedSource === draft ? result.verification : null;
}
