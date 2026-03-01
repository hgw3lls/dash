import type {
  IngestSummary,
  Opportunity,
  OpportunityListResponse,
  OpportunityPatch,
  SavedView,
} from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init)
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Request failed: ${response.status}`)
  }
  return (await response.json()) as T
}

export function listOpportunities(query: URLSearchParams): Promise<OpportunityListResponse> {
  return apiFetch<OpportunityListResponse>(`/opportunities?${query.toString()}`)
}

export function getOpportunity(id: string): Promise<Opportunity> {
  return apiFetch<Opportunity>(`/opportunities/${id}`)
}

export function patchOpportunity(id: string, payload: OpportunityPatch): Promise<Opportunity> {
  return apiFetch<Opportunity>(`/opportunities/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function listViews(): Promise<SavedView[]> {
  return apiFetch<SavedView[]>('/views')
}

export function createView(payload: { name: string; definition_json: string }): Promise<SavedView> {
  return apiFetch<SavedView>('/views', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function deleteView(id: number): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/views/${id}`, { method: 'DELETE' })
}

export function ingestFolder(payload: {
  folder: string
  pattern?: string
  overwrite_user_fields?: boolean
  type_default?: string
}): Promise<IngestSummary> {
  return apiFetch<IngestSummary>('/ingest/folder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
