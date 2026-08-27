import { useAuthStore } from "@/stores/authStore";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8100";

// Promesa compartida de refresh: si varias queries de TanStack disparan un
// 401 a la vez, solo se hace UNA llamada real a /auth/refresh (las demas
// esperan la misma promesa) en vez de rotar el refresh token N veces.
let refreshPromise: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  const { refreshToken, setSession, clear } = useAuthStore.getState();
  if (!refreshToken) {
    return false;
  }
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      clear();
      return false;
    }
    const data = (await response.json()) as { access_token: string; refresh_token: string };
    setSession(data.access_token, data.refresh_token);
    return true;
  } catch {
    clear();
    return false;
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Wrapper de fetch para /api/v1/*: adjunta Authorization: Bearer, y en un
// 401 intenta refrescar la sesion UNA vez (deduplicado) antes de reintentar
// la peticion original. Si el refresh tambien falla, la sesion queda
// limpia (RootLayout redirige a /login al detectar accessToken=null).
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const makeRequest = () => {
    const { accessToken } = useAuthStore.getState();
    return fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...init.headers,
      },
    });
  };

  let response = await makeRequest();

  if (response.status === 401) {
    refreshPromise ??= refreshSession().finally(() => {
      refreshPromise = null;
    });
    const refreshed = await refreshPromise;
    if (refreshed) {
      response = await makeRequest();
    }
  }

  if (!response.ok) {
    // FastAPI error bodies son {detail: "..."} -- se adjunta cuando esta
    // presente para que llamadas que necesitan el motivo exacto (p.ej. el
    // 409 de reactivacion de Cementerio, PARTE 6.3) no tengan que reparsear
    // la respuesta ellas mismas.
    const detail = await response
      .clone()
      .json()
      .then((body: unknown) =>
        typeof body === "object" && body !== null && "detail" in body
          ? String((body as { detail: unknown }).detail)
          : undefined
      )
      .catch(() => undefined);
    throw new ApiError(
      response.status,
      `${init.method ?? "GET"} ${path} -> ${response.status}`,
      detail
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
