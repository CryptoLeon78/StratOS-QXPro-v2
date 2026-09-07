import { API_BASE_URL } from "@/api/client";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export class LoginError extends Error {}

export interface RecoveryStatus {
  configured: boolean;
  minimum_password_length: number;
}

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

export async function getRecoveryStatus(): Promise<RecoveryStatus> {
  const response = await fetch(`${API_BASE_URL}/auth/recovery/status`);
  if (!response.ok) throw new Error("recovery-status");
  return (await response.json()) as RecoveryStatus;
}

export async function requestPasswordRecovery(email: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/auth/recovery/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) throw new Error("recovery-request");
}

export async function confirmPasswordRecovery(
  email: string,
  code: string,
  newPassword: string
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/auth/recovery/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code, new_password: newPassword }),
  });
  if (!response.ok) throw new Error("recovery-confirm");
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
  accessToken: string
): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/password`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!response.ok) throw new Error("password-change");
  return (await response.json()) as TokenResponse;
}
