// Client-side token storage. Bearer-in-localStorage is the right fit here: the
// frontend (vercel.app) and API (onrender.com) are different sites, so httpOnly
// cookies would be third-party and blocked by browsers.
const TOKEN_KEY = "flow_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window !== "undefined") window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window !== "undefined") window.localStorage.removeItem(TOKEN_KEY);
}
