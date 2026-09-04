import { describe, expect, it, vi } from "vitest";

import { ApiError, fetchApiHealth } from "./api";

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
