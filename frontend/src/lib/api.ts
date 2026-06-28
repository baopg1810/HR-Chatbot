import type { User } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1');

export interface ApiUser {
  id: string;
  email: string;
  full_name: string;
  role: 'employee' | 'department_admin' | 'hr_admin';
  department_id?: string | null;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  user: ApiUser;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
}

export interface Citation {
  document_id: string;
  document_title: string;
  section?: string | null;
  excerpt: string;
  page?: number | null;
  score: number;
}

export interface ChatAction {
  type: 'hr_metric_lookup' | 'escalation_confirmation_required' | 'escalation_created' | 'none';
  label: string;
  data?: Record<string, unknown> | null;
}

export interface ChatResponse {
  message_id: string;
  session_id: string;
  answer: string;
  citations: Citation[];
  actions: ChatAction[];
  escalated_ticket_id?: string | null;
  refusal_reason?: string | null;
}

export interface DocumentRecord {
  id: string;
  title: string;
  status: string;
  visibility_roles: string[];
  department_ids: string[];
  created_at: string;
  chunk_count: number;
}

export interface TicketRecord {
  id: string;
  requester_id: string;
  status: 'open' | 'in_progress' | 'resolved' | 'rejected';
  priority: 'low' | 'normal' | 'high';
  reason: string;
  summary: string;
  assignee_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrendPin {
  id: string;
  topic_key: string;
  title: string;
  summary: string;
  source_query_count: number;
  citations: Citation[];
  created_at: string;
  expires_at?: string | null;
}

export type TrendCandidate = Omit<TrendPin, 'expires_at'>;

export function mapApiUser(apiUser: ApiUser, token: string): User {
  return {
    id: apiUser.id,
    email: apiUser.email,
    name: apiUser.full_name,
    role: apiUser.role === 'hr_admin' ? 'admin' : 'user',
    backendRole: apiUser.role,
    departmentId: apiUser.department_id || undefined,
    token,
  };
}

export function mapLoginUser(response: LoginResponse): User {
  return {
    ...mapApiUser(response.user, response.access_token),
    refreshToken: response.refresh_token,
  };
}

export async function loginRequest(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function refreshTokenRequest(refreshToken: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function logoutRequest(refreshToken: string): Promise<void> {
  await apiRequest('/auth/logout', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function chatRequest(token: string, message: string, sessionId?: string | null): Promise<ChatResponse> {
  return apiRequest<ChatResponse>('/chat', {
    method: 'POST',
    token,
    body: JSON.stringify({ message, session_id: sessionId || null }),
  });
}

export interface ChatStreamHandlers {
  onStart?: (data: { message_id: string; session_id: string }) => void;
  onToken?: (text: string) => void;
  onDone?: (response: ChatResponse) => void;
}

export async function streamChatRequest(
  token: string,
  message: string,
  sessionId: string | null | undefined,
  handlers: ChatStreamHandlers,
): Promise<ChatResponse> {
  const headers = new Headers();
  headers.set('Content-Type', 'application/json');
  headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, session_id: sessionId || null }),
  });
  if (!response.ok || !response.body) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResponse: ChatResponse | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';
    for (const part of parts) {
      const event = parseSseEvent(part);
      if (!event) continue;
      if (event.event === 'start') {
        handlers.onStart?.(event.data as { message_id: string; session_id: string });
      } else if (event.event === 'token') {
        const tokenData = event.data as { text?: string };
        handlers.onToken?.(tokenData.text || '');
      } else if (event.event === 'done') {
        finalResponse = event.data as ChatResponse;
        handlers.onDone?.(finalResponse);
      } else if (event.event === 'error') {
        const errorData = event.data as { detail?: string };
        throw new Error(errorData.detail || 'Streaming chat failed');
      }
    }
  }

  if (!finalResponse) {
    throw new Error('Máy chủ chưa trả về kết quả streaming hoàn chỉnh.');
  }
  return finalResponse;
}

function parseSseEvent(raw: string): { event: string; data: unknown } | null {
  const eventLine = raw.split('\n').find((line) => line.startsWith('event:'));
  const dataLines = raw
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart());
  if (!eventLine || dataLines.length === 0) {
    return null;
  }
  return {
    event: eventLine.slice(6).trim(),
    data: JSON.parse(dataLines.join('\n')),
  };
}

export async function listDocuments(token: string): Promise<DocumentRecord[]> {
  const data = await apiRequest<{ documents: DocumentRecord[] }>('/documents', { token });
  return data.documents;
}

export async function createTextDocument(
  token: string,
  payload: { title: string; content: string; visibility_roles: string[]; department_ids: string[] },
) {
  return apiRequest('/documents', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function uploadDocument(token: string, file: File, title?: string) {
  const form = new FormData();
  form.append('file', file);
  if (title?.trim()) {
    form.append('title', title.trim());
  }
  form.append('visibility_roles', 'employee');
  form.append('visibility_roles', 'department_admin');
  form.append('visibility_roles', 'hr_admin');
  return apiRequest('/documents/upload', {
    method: 'POST',
    token,
    body: form,
    json: false,
  });
}

export async function deleteDocument(token: string, documentId: string) {
  return apiRequest(`/documents/${documentId}`, {
    method: 'DELETE',
    token,
  });
}

export async function createEscalation(
  token: string,
  payload: { message: string; reason?: string; priority?: string; session_id?: string | null },
): Promise<TicketRecord> {
  return apiRequest<TicketRecord>('/escalations', {
    method: 'POST',
    token,
    body: JSON.stringify({
      message: payload.message,
      reason: payload.reason || 'user_requested',
      priority: payload.priority || 'normal',
      session_id: payload.session_id || null,
    }),
  });
}

export async function listAdminTickets(token: string): Promise<TicketRecord[]> {
  const data = await apiRequest<{ tickets: TicketRecord[] }>('/admin/tickets', { token });
  return data.tickets;
}

export async function listMyTickets(token: string): Promise<TicketRecord[]> {
  const data = await apiRequest<{ tickets: TicketRecord[] }>('/tickets', { token });
  return data.tickets;
}

export async function updateTicket(token: string, ticketId: string, payload: { status?: string; assignee_id?: string }) {
  return apiRequest<TicketRecord>(`/admin/tickets/${ticketId}`, {
    method: 'PATCH',
    token,
    body: JSON.stringify(payload),
  });
}

export async function listTrendPins(token: string): Promise<TrendPin[]> {
  const data = await apiRequest<{ pins: TrendPin[] }>('/trending/pins', { token });
  return data.pins;
}

export async function listTrendCandidates(token: string): Promise<TrendCandidate[]> {
  const data = await apiRequest<{ candidates: TrendCandidate[] }>('/admin/trending/candidates', { token });
  return data.candidates;
}

export async function runTrending(token: string, threshold = 5, windowMinutes = 60) {
  return apiRequest('/admin/trending/run', {
    method: 'POST',
    token,
    body: JSON.stringify({ threshold, window_minutes: windowMinutes }),
  });
}

export async function approveTrendCandidate(token: string, candidateId: string): Promise<TrendPin> {
  return apiRequest<TrendPin>(`/admin/trending/candidates/${candidateId}/pin`, {
    method: 'POST',
    token,
  });
}

export interface ChatSessionRecord {
  id: string;
  user_id: string;
  title: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface ChatMessageRecord {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string | null;
  citations: Citation[];
}

export async function listChatSessions(token: string): Promise<ChatSessionRecord[]> {
  return apiRequest<ChatSessionRecord[]>('/chat/sessions', { token });
}

export async function getChatSessionMessages(token: string, sessionId: string): Promise<ChatMessageRecord[]> {
  return apiRequest<ChatMessageRecord[]>(`/chat/sessions/${sessionId}/messages`, { token });
}

async function apiRequest<T>(
  path: string,
  options: RequestInit & { token?: string; json?: boolean } = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.json !== false) {
    headers.set('Content-Type', 'application/json');
  }
  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  const text = await response.text();
  const contentType = response.headers.get('content-type') || '';
  const data = text && contentType.includes('application/json') ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data?.detail || text || response.statusText;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg || item).join(', ') : String(detail));
  }
  if (text && !data) {
    throw new Error(`Máy chủ trả về phản hồi không phải JSON: ${text.slice(0, 120)}`);
  }
  return data as T;
}
