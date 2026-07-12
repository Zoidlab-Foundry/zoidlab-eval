async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { ...init, credentials: "include", headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try { detail = (await r.json()).detail || detail; } catch {}
    const e = new Error(detail) as Error & { status?: number }; e.status = r.status; throw e;
  }
  return r.json();
}

export const api = {
  entitlements: () => req<any>("/api/auth/entitlements"),
  stats: () => req<any>("/api/stats"),
  meta: () => req<{ relay_available: boolean; billing_mode: string; featured_models: string[]; judge_model: string }>("/api/meta"),

  targets: () => req<{ targets: any[] }>("/api/targets").then((d) => d.targets),
  createTarget: (b: any) => req<any>("/api/targets", { method: "POST", body: JSON.stringify(b) }),
  deleteTarget: (id: string) => req<any>(`/api/targets/${id}`, { method: "DELETE" }),

  criteria: () => req<{ criteria: any[] }>("/api/criteria").then((d) => d.criteria),
  createCriterion: (b: any) => req<any>("/api/criteria", { method: "POST", body: JSON.stringify(b) }),
  deleteCriterion: (id: string) => req<any>(`/api/criteria/${id}`, { method: "DELETE" }),

  testsets: () => req<{ testsets: any[] }>("/api/testsets").then((d) => d.testsets),
  testset: (id: string) => req<any>(`/api/testsets/${id}`),
  createTestset: (b: any) => req<any>("/api/testsets", { method: "POST", body: JSON.stringify(b) }),
  deleteTestset: (id: string) => req<any>(`/api/testsets/${id}`, { method: "DELETE" }),

  startRun: (b: any) => req<any>("/api/runs", { method: "POST", body: JSON.stringify(b) }),
  runs: () => req<{ runs: any[] }>("/api/runs").then((d) => d.runs),
  run: (id: string, onlyFailed = false) => req<any>(`/api/runs/${id}${onlyFailed ? "?only_failed=true" : ""}`),

  exportJsonUrl: (rid: string) => `/api/runs/${rid}/export/json`,
  exportYamlUrl: (rid: string) => `/api/runs/${rid}/export/yaml`,
};

export const usd = (n: number) => "$" + (n ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 });
export const num = (n: number) => (n ?? 0).toLocaleString();
