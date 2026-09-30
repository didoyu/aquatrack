const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";
const ls = localStorage;
export const auth = {
  save(d) { ls.setItem("aq_access", d.access); if (d.refresh) ls.setItem("aq_refresh", d.refresh); if (d.user) ls.setItem("aq_user", JSON.stringify(d.user)); },
  clear() { ["aq_access", "aq_refresh", "aq_user"].forEach((k) => ls.removeItem(k)); },
  user() { try { return JSON.parse(ls.getItem("aq_user")); } catch { return null; } },
  loggedIn() { return !!ls.getItem("aq_access"); },
};
async function refresh() {
  const r = ls.getItem("aq_refresh");
  if (!r) return false;
  const res = await fetch(`${BASE}/auth/refresh/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh: r }) });
  if (!res.ok) return false;
  auth.save(await res.json());
  return true;
}
export async function api(path, { method = "GET", body, retry = true } = {}) {
  const token = ls.getItem("aq_access");
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && token && retry && (await refresh())) return api(path, { method, body, retry: false });
  const data = await res.json().catch(() => null);
  if (res.status === 401 && token) { auth.clear(); location.href = "/login"; }
  if (!res.ok) throw new Error(data?.detail || Object.values(data || {}).flat().join(" ") || "Request failed");
  return data;
}
