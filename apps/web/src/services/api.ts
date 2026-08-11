export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchApiHealth(fetcher: typeof fetch = fetch): Promise<HealthResponse> {
  const response = await fetcher(`${apiBaseUrl}/api/v1/health`, {
    headers: { Accept: "application/json" }
  });
  if (!response.ok) {
    throw new Error(`API health request failed with status ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}
