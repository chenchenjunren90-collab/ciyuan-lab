import type { ClassroomBeat } from "../../services/api";

export interface BoardNotes {
  highlights: string[];
  pins: Record<string, { x: number; y: number }>;
}
export type BoardNotesByBeat = Record<string, BoardNotes>;
export interface BoardItem { id: string; kind: "explanation" | "point" | "code" | "trace" | "mistake"; text: string; label: string }
export const CODE_PREVIEW_LINES = 8;

export function boardItems(beat: ClassroomBeat): BoardItem[] {
  const items: BoardItem[] = [];
  const add = (kind: BoardItem["kind"], text: string, label: string) => {
    if (text.trim()) items.push({ id: `${kind}:${text}`, kind, text, label });
  };
  add("explanation", beat.board_explanation, "讲解");
  beat.board_points.filter(p => !p.startsWith("易错提醒：")).forEach((p, i) => add("point", p, `要点 ${i + 1}`));
  add("code", beat.board_code, "示例代码");
  beat.board_trace.forEach((p, i) => add("trace", p, `步骤 ${i + 1}`));
  beat.board_points.filter(p => p.startsWith("易错提醒：")).forEach(p => add("mistake", p.slice(5), "易错提醒"));
  return items;
}

/** Old drafts need no migration; malformed annotations must not discard learning progress. */
export function readBoardNotes(value: unknown): BoardNotesByBeat {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value).slice(0, 300).flatMap(([key, notes]) => {
    if (!notes || typeof notes !== "object" || Array.isArray(notes)) return [];
    const n = notes as Partial<BoardNotes>;
    const highlights = Array.isArray(n.highlights) ? n.highlights.filter((id): id is string => typeof id === "string").slice(0, 100) : [];
    const pins = Object.fromEntries(Object.entries(n.pins && typeof n.pins === "object" ? n.pins : {}).slice(0, 100).filter(([, p]) => (
      p && Number.isFinite(p.x) && Number.isFinite(p.y) && p.x >= 0 && p.x <= 100 && p.y >= 0 && p.y <= 100
    )));
    return [[key, { highlights, pins }]];
  }));
}
