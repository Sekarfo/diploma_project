const BASE_URL = "http://127.0.0.1:8000";

function getToken(): string | null {
  try {
    const raw = localStorage.getItem("selects-auth");
    if (!raw) return null;
    return (JSON.parse(raw) as { state?: { token?: string } })?.state?.token ?? null;
  } catch {
    return null;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}
