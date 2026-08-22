/**
 * Typed API client.
 *
 * Centralises fetch handling so every component surfaces backend errors the
 * same way instead of each one silently swallowing a failed request.
 */

export interface ApiError extends Error {
  status?: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });

  const text = await response.text();
  const data = text ? safeParse(text) : null;

  if (!response.ok) {
    const error: ApiError = new Error(
      (data && (data.detail || data.message)) || `Request failed (${response.status})`
    );
    error.status = response.status;
    throw error;
  }

  return data as T;
}

function safeParse(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return { message: text };
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

/* ---------------------------------------------------------------- */
/*  Shared types                                                     */
/* ---------------------------------------------------------------- */

export interface ContextUsed {
  glossary_terms: string[];
  rules_applied: string[];
  similar_questions: string[];
  documents_used: { source: string; title: string }[];
}

export interface AnalysisResponse {
  answer: string;
  confidence: number;
  sql_query: string | null;
  needs_review: boolean;
  market_context: string | null;
  episode_id: number | null;
  context_used: ContextUsed | null;
}

export interface SystemStatus {
  analyst_ready: boolean;
  database_connected: boolean;
  features: {
    newsroom: boolean;
    code_sandbox: boolean;
    sandbox_isolation: string;
    air_gap: boolean;
    proactive_monitoring: boolean;
  };
  briefing: { hour: number; timezone: string };
}

export interface GlossaryTerm {
  id: number;
  term: string;
  definition: string;
  source: string;
  updated_at: string | null;
}

export interface ProceduralRule {
  id: number;
  rule: string;
  active: boolean;
  times_applied: number;
  source_episode_id: number | null;
  created_at: string | null;
}

export interface Episode {
  id: number;
  question: string;
  sql_query: string | null;
  answer: string | null;
  confidence: number | null;
  rating: number | null;
  correction: string | null;
  timestamp: string | null;
}

export interface AuditEntry {
  id: number;
  timestamp: string | null;
  action: string;
  actor: string;
  detail: Record<string, unknown>;
  success: boolean;
}
