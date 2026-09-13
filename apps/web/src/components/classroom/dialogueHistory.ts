import type { ClassroomDialogueTurn } from "../../services/api";

type HistoryTurn = ClassroomDialogueTurn & { kind?: string };
const terms = (value: string) => new Set(value.toLowerCase().match(/[a-z_][a-z_0-9]*|[\u4e00-\u9fff]{2}/g) ?? []);

/** Retrieve older relevant turns locally; never transmit the whole saved classroom log. */
export function selectDialogueHistory(history: HistoryTurn[], question: string): ClassroomDialogueTurn[] {
  const turns = history.slice(-200).filter(turn => turn.content.trim()
    && (!turn.kind || turn.kind === "student" || turn.kind === "reply"));
  const selected = new Set<number>();
  for (let i = Math.max(0, turns.length - 4); i < turns.length; i++) selected.add(i);
  const query = terms(question);
  const ranked = turns.slice(0, -4).map((turn, index) => ({ index,
    score: [...terms(turn.content)].filter(term => query.has(term)).length,
  })).filter(item => item.score > 0).sort((a, b) => b.score - a.score || b.index - a.index);
  for (const item of ranked) {
    if (selected.size >= 8) break;
    selected.add(item.index);
    // Keep the answer/question pair when possible, instead of recalling orphaned speech.
    const neighbor = turns[item.index]?.role === "student" ? item.index + 1 : item.index - 1;
    if (neighbor >= 0 && selected.size < 8) selected.add(neighbor);
  }
  for (let i = turns.length - 1; i >= 0 && selected.size < 8; i--) selected.add(i);
  return [...selected].sort((a, b) => a - b).map(index => ({
    role: turns[index]!.role, content: turns[index]!.content.slice(0, 1500),
  }));
}
