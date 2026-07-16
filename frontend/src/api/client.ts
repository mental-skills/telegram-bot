import type { Bootstrap, Progress, Training, TransitionResult } from "./contracts";

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers }
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({ detail: "request_failed" }))) as {
      detail?: string;
    };
    throw new ApiError(response.status, body.detail ?? "request_failed");
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function authenticate(): Promise<void> {
  const initData = window.Telegram?.WebApp?.initData ?? "";
  if (initData) {
    await request("/api/v1/auth/telegram", {
      method: "POST",
      body: JSON.stringify({ init_data: initData })
    });
    return;
  }
  if (import.meta.env.DEV || import.meta.env.VITE_DEV_AUTH === "true") {
    await request("/api/v1/auth/dev", { method: "POST" });
    return;
  }
  throw new ApiError(401, "Откройте приложение из Telegram-бота");
}

export const getBootstrap = () => request<Bootstrap>("/api/v1/bootstrap");
export const getProgress = () => request<Progress>("/api/v1/progress");
export const getCurrentTraining = () => request<Training>("/api/v1/training/current");
export const startOrContinue = () =>
  request<Training>("/api/v1/training/start-or-continue", { method: "POST" });
export const restartTraining = () =>
  request<Training>("/api/v1/training/restart", { method: "POST" });
export const setAge = (age_group: string) =>
  request<{ telegram_user_id: number; age_group: string }>("/api/v1/me/age", {
    method: "PATCH",
    body: JSON.stringify({ age_group })
  });
export const transition = (training: Training, option_id: string) =>
  request<TransitionResult>(
    `/api/v1/training/sessions/${training.session_id}/transitions`,
    {
      method: "POST",
      body: JSON.stringify({ revision: training.revision, option_id })
    }
  );
