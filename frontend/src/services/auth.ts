import { API_BASE_URL } from "./config";

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface LoginResponse {
  access_token?: string | null;
  token_type?: string | null;
  user?: User | null;
  requires_two_factor: boolean;
  otp_sent: boolean;
  challenge_token?: string | null;
  message?: string | null;
}

export interface LoginActivity {
  id: number;
  login_at: string;
  ip_address?: string | null;
  success: boolean;
  user_agent?: string | null;
}

export interface RegisterResponse {
  message: string;
  email: string;
  verification_required: boolean;
}

export interface TwoFactorLoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AuthSession {
  session_id: string;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  ip_address?: string | null;
  user_agent?: string | null;
  is_current: boolean;
}

export interface SessionActionResponse {
  message: string;
  session_id?: string;
  revoked_count?: number;
}

async function readResponse(response: Response): Promise<any> {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return {};
    }
  }

  const text = await response.text();
  return { detail: text };
}

function getErrorMessage(data: any, fallback: string): string {
  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item: any) =>
        typeof item === "string" ? item : item?.msg || "Invalid request.",
      )
      .join(", ");
  }

  if (typeof data?.message === "string") {
    return data.message;
  }

  return fallback;
}

async function postJson<T>(
  path: string,
  payload: Record<string, unknown>,
  fallback: string,
): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await readResponse(response);

    if (!response.ok) {
      throw new Error(
        getErrorMessage(data, `${fallback} Server returned ${response.status}.`),
      );
    }

    return data as T;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "Cannot connect to the ZUKA backend. Start FastAPI on http://127.0.0.1:8000.",
      );
    }

    throw error;
  }
}


async function getAuthenticatedJson<T>(
  path: string,
  fallback: string,
): Promise<T> {
  const token = localStorage.getItem("zuka_access_token");

  if (!token) {
    throw new Error("Your session has expired. Please sign in again.");
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await readResponse(response);

    if (!response.ok) {
      throw new Error(
        getErrorMessage(data, `${fallback} Server returned ${response.status}.`),
      );
    }

    return data as T;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "Cannot connect to the ZUKA backend. Start FastAPI on http://127.0.0.1:8000.",
      );
    }

    throw error;
  }
}

async function postAuthenticatedJson<T>(
  path: string,
  payload: Record<string, unknown>,
  fallback: string,
): Promise<T> {
  const token = localStorage.getItem("zuka_access_token");

  if (!token) {
    throw new Error("Your session has expired. Please sign in again.");
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await readResponse(response);

    if (!response.ok) {
      throw new Error(
        getErrorMessage(data, `${fallback} Server returned ${response.status}.`),
      );
    }

    return data as T;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "Cannot connect to the ZUKA backend. Start FastAPI on http://127.0.0.1:8000.",
      );
    }

    throw error;
  }
}

export async function register(payload: {
  username: string;
  email: string;
  password: string;
  role?: string;
}): Promise<RegisterResponse> {
  return postJson<RegisterResponse>(
    "/api/auth/register",
    payload,
    "Registration failed.",
  );
}

export async function verifyEmail(payload: {
  email: string;
  otp: string;
}): Promise<{ message: string }> {
  return postJson(
    "/api/auth/verify-email",
    payload,
    "Email verification failed.",
  );
}

export async function resendVerification(payload: {
  email: string;
}): Promise<{ message: string }> {
  return postJson(
    "/api/auth/resend-verification",
    payload,
    "Unable to resend verification code.",
  );
}

export async function login(payload: {
  username_or_email: string;
  password: string;
}): Promise<LoginResponse> {
  return postJson<LoginResponse>(
    "/api/auth/login",
    payload,
    "Authentication failed.",
  );
}

export async function verifyTwoFactorLogin(payload: {
  challenge_token: string;
  otp: string;
}): Promise<TwoFactorLoginResponse> {
  return postJson<TwoFactorLoginResponse>(
    "/api/auth/2fa/login",
    payload,
    "Two-step verification failed.",
  );
}

export async function getLoginActivity(
  limit = 50,
): Promise<LoginActivity[]> {
  return getAuthenticatedJson<LoginActivity[]>(
    `/api/auth/login-activity?limit=${encodeURIComponent(limit)}`,
    "Unable to load login activity.",
  );
}

export async function forgotPassword(payload: {
  email: string;
}): Promise<{ message: string }> {
  return postJson(
    "/api/auth/forgot-password",
    payload,
    "Unable to start password recovery.",
  );
}

export async function verifyResetOtp(payload: {
  email: string;
  otp: string;
}): Promise<{ message: string }> {
  return postJson(
    "/api/auth/verify-reset-otp",
    payload,
    "Invalid password reset code.",
  );
}

export async function resetPassword(payload: {
  email: string;
  otp: string;
  new_password: string;
}): Promise<{ message: string }> {
  return postJson(
    "/api/auth/reset-password",
    payload,
    "Unable to reset password.",
  );
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
  confirm_password: string;
}): Promise<{ message: string }> {
  return postAuthenticatedJson(
    "/api/auth/change-password",
    payload,
    "Unable to change password.",
  );
}

export async function getActiveSessions(): Promise<AuthSession[]> {
  return getAuthenticatedJson<AuthSession[]>(
    "/api/auth/sessions",
    "Unable to load active sessions.",
  );
}

export async function revokeSession(
  sessionId: string,
): Promise<SessionActionResponse> {
  return postAuthenticatedJson<SessionActionResponse>(
    `/api/auth/sessions/${encodeURIComponent(sessionId)}/revoke`,
    {},
    "Unable to sign out the selected session.",
  );
}

export async function revokeAllOtherSessions(): Promise<SessionActionResponse> {
  return postAuthenticatedJson<SessionActionResponse>(
    "/api/auth/sessions/revoke-all",
    {},
    "Unable to sign out the other sessions.",
  );
}
