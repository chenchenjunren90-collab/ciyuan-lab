import { describe, expect, it, vi } from "vitest";

import { fetchApiHealth } from "./api";

describe("fetchApiHealth", () => {
  it("returns the parsed health response", async () => {
    const fetcher = vi.fn(async () =>
      new Response(
        JSON.stringify({ status: "ok", service: "词元研究所", version: "0.1.0" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    ) as unknown as typeof fetch;

    await expect(fetchApiHealth(fetcher)).resolves.toEqual({
      status: "ok",
      service: "词元研究所",
      version: "0.1.0"
    });
    expect(fetcher).toHaveBeenCalledWith("/api/v1/health", {
      headers: { Accept: "application/json" }
    });
  });
});
