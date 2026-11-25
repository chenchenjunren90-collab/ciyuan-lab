import { describe, expect, it, vi } from "vitest";

import { api, ApiError, fetchApiHealth } from "./api";

describe("student-facing exercise feedback", () => {
  it("reads a result from an older API without showing its exercise key", async () => {
    const exercise = "C-BASE-01-Q1";
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({
      feedback: exercise + " 已通过确定性判定。请回顾关键边界，并继续下一项活动。",
      verification: null, mastery_updated: []
    })));
    try {
      const result = await api.submit("test-learner", "c", exercise, { response: "A" });
      expect(result.feedback).toBe("回答正确。");
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("explains a missing course item without exposing its stored path", async () => {
    const fetcher = async () => Response.json({detail: "course record not found: c/C-BASE-01"}, {status: 404});
    await expect(fetchApiHealth(fetcher)).rejects.toMatchObject({
      status: 404, message: "这项学习内容暂时无法打开，请刷新课程目录后重试。"
    });
  });
});

describe("fetchApiHealth", () => {
  it("returns the parsed health response", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(
        JSON.stringify({ status: "ok", service: "词元研究所", version: "0.1.0" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );
    const fetcher = fetchMock as unknown as typeof fetch;

    await expect(fetchApiHealth(fetcher)).resolves.toEqual({
      status: "ok",
      service: "词元研究所",
      version: "0.1.0"
    });
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/health");
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      headers: { Accept: "application/json" }
    });
    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBeInstanceOf(AbortSignal);
  });

  it("keeps a stable ApiError for a non-JSON server failure", async () => {
    const fetcher = vi.fn(async () => new Response("service unavailable", { status: 503 })) as unknown as typeof fetch;

    const promise = fetchApiHealth(fetcher);

    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toMatchObject({ status: 503, message: "请求失败（503）" });
  });

  it("aborts a stalled request and maps it to a friendly timeout error", async () => {
    const fetcher = vi.fn((_input: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener(
          "abort",
          () => reject(new DOMException("Aborted", "AbortError")),
          { once: true }
        );
      })) as unknown as typeof fetch;

    const promise = fetchApiHealth(fetcher, 5);

    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toMatchObject({
      status: 408,
      message: "请求超时，请检查服务状态后重试"
    });
  });
});
