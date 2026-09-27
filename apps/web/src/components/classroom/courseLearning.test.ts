import { describe, expect, it } from "vitest";
import type { KnowledgePoint, KnowledgePointDetail, LearnerProfile } from "../../services/api";
import { lessonScenes, orderKnowledge, readLessonPosition, recommendPoint } from "./courseLearning";
const point = (id: string, prerequisites: string[] = []): KnowledgePoint => ({ id, prerequisites, title: id, difficulty: "beginner", concepts: [], source_refs: [] });
describe("course-independent classroom planning", () => {
  const points = [point("C-PTR-01", ["C-BASE-03"]), point("C-BASE-03")];
  it("prioritizes prerequisites instead of filenames or browsing completion", () => {
    expect(orderKnowledge(points).map(item => item.id)).toEqual(["C-BASE-03", "C-PTR-01"]);
    expect(recommendPoint(points, null)).toBe("C-BASE-03");
    const profile: LearnerProfile = { student_id: "test", course_id: "c", mastery: [{ knowledge_point_id: "C-BASE-03", score: .9, evidence_count: 0, updated_at: null }] };
    expect(recommendPoint(points, profile)).toBe("C-BASE-03");
    profile.mastery[0]!.evidence_count = 1;
    expect(recommendPoint(points, profile)).toBe("C-PTR-01");
  });
  it("detects cycles", () => expect(() => orderKnowledge([point("A", ["B"]), point("B", ["A"])])).toThrow());
  it("shows the real course explanation and mistakes when a scene script is absent", () => {
    const detail = { ...points[0], lesson: { summary: "指针保存地址", key_points: ["解引用修改对象"], common_mistakes: ["悬空指针不可访问"] } } as KnowledgePointDetail;
    expect(lessonScenes(detail).map(item => item.content)).toEqual(["指针保存地址", "解引用修改对象", "悬空指针不可访问"]);
  });
  it("ignores invalid or unavailable storage", () => {
    expect(readLessonPosition({ getItem: () => 'null' }, "key")).toBe("");
    expect(readLessonPosition({ getItem: () => { throw new Error(); } }, "key")).toBe("");
    expect(readLessonPosition({ getItem: () => 'DS-GRAPH-02' }, "key")).toBe("DS-GRAPH-02");
  });
});
