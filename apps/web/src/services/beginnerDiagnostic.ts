import type { DiagnosticQuiz } from "./api";

/** An explicit self-report of unknown knowledge, never a fabricated correct answer. */
export function beginnerDiagnosticAnswers(
  quiz: DiagnosticQuiz | null,
  answers: Record<string, string>,
): Record<string, string> | null {
  if (!quiz || quiz.phase !== "initial" || !quiz.items.length) return null;
  const next: Record<string, string> = {};
  for (const item of quiz.items) {
    const answer = answers[item.exercise_id] || "UNKNOWN";
    if (!item.options.some(option => option.id === answer)) return null;
    next[item.exercise_id] = answer;
  }
  return next;
}
