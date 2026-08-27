import { API_BASE_URL } from "@/api/client";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export class LoginError extends Error {}

// POST /auth/token exige application/x-www-form-urlencoded
// (OAuth2PasswordRequestForm de FastAPI, no JSON) -- username/password, no
// email/password. No pasa por apiFetch: todavia no hay accessToken.
export async function login(email: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch(`${API_BASE_URL}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    throw new LoginError("credenciales invalidas");
  }
  return (await response.json()) as TokenResponse;
}
