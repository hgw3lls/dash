import { useEffect, useMemo, useState } from 'react'

import {
  createView,
  deleteView,
  getOpportunity,
  ingestFolder,
  listOpportunities,
  listViews,
  patchOpportunity,
} from './lib/api'
import type { IngestSummary, Opportunity, OpportunityPatch, SavedView } from './lib/types'

type SortKey = 'deadline' | 'priority' | 'updated_at' | 'posted_date'
type SortOrder = 'asc' | 'desc'

type Filters = {
  q: string
  types: string[]
  statuses: string[]
  due_bucket: '' | 'overdue' | '7' | '30' | '90' | 'none'
  region_tag: string
  tagsText: string
}

const PAGE_SIZE = 20
const allTypes = ['cfp', 'job', 'art', 'master']
const allStatuses: Opportunity['status'][] = ['new', 'saved', 'applied', 'archived', 'ignored']

function urgencyLabel(deadline: string | null): string {
  if (!deadline) return 'No deadline'
  const days = Math.floor((new Date(deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
  if (days < 0) return 'Overdue'
  if (days <= 7) return 'Due ≤ 7d'
  if (days <= 30) return 'Due ≤ 30d'
  if (days <= 90) return 'Due ≤ 90d'
  return 'Later'
}

function parseTagInput(value: string): string[] {
  return value
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean)
}

export default function App() {
  const [filters, setFilters] = useState<Filters>({
    q: '',
    types: [],
    statuses: [],
    due_bucket: '',
    region_tag: '',
    tagsText: '',
  })
  const [sort, setSort] = useState<SortKey>('deadline')
  const [order, setOrder] = useState<SortOrder>('asc')
  const [page, setPage] = useState(1)

  const [rows, setRows] = useState<Opportunity[]>([])
  const [total, setTotal] = useState(0)
  const [savedViews, setSavedViews] = useState<SavedView[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selected, setSelected] = useState<Opportunity | null>(null)
  const [drawerState, setDrawerState] = useState<OpportunityPatch>({})
  const [toast, setToast] = useState<string>('')

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))


  useEffect(() => {
    const raw = window.localStorage.getItem('dashboard:lastState')
    if (!raw) return
    try {
      const parsed = JSON.parse(raw) as { filters?: Filters; sort?: SortKey; order?: SortOrder }
      if (parsed.filters) setFilters(parsed.filters)
      if (parsed.sort) setSort(parsed.sort)
      if (parsed.order) setOrder(parsed.order)
    } catch {
      // ignore corrupted local storage
    }
  }, [])

  useEffect(() => {
    window.localStorage.setItem(
      'dashboard:lastState',
      JSON.stringify({ filters, sort, order })
    )
  }, [filters, sort, order])

  const params = useMemo(() => {
    const p = new URLSearchParams()
    if (filters.q) p.set('q', filters.q)
    if (filters.types.length) p.set('type', filters.types.join(','))
    if (filters.statuses.length) p.set('status', filters.statuses.join(','))
    if (filters.due_bucket) p.set('due_bucket', filters.due_bucket)
    if (filters.region_tag) p.set('region_tag', filters.region_tag)
    for (const tag of parseTagInput(filters.tagsText)) p.append('tag', tag)
    p.set('sort', sort)
    p.set('order', order)
    p.set('page', String(page))
    p.set('page_size', String(PAGE_SIZE))
    return p
  }, [filters, sort, order, page])

  async function refreshData() {
    const result = await listOpportunities(params)
    setRows(result.items)
    setTotal(result.total)
  }

  async function refreshViews() {
    const result = await listViews()
    setSavedViews(result)
  }

  useEffect(() => {
    refreshData().catch((error) => setToast(`Error loading opportunities: ${String(error)}`))
  }, [params])

  useEffect(() => {
    refreshViews().catch((error) => setToast(`Error loading saved views: ${String(error)}`))
  }, [])

  useEffect(() => {
    if (!selectedId) {
      setSelected(null)
      return
    }
    getOpportunity(selectedId)
      .then((item) => {
        setSelected(item)
        setDrawerState({
          status: item.status,
          notes: item.notes ?? '',
          priority: item.priority,
          tags: item.tags,
          region_tag: item.region_tag ?? '',
        })
      })
      .catch((error) => setToast(`Error loading opportunity: ${String(error)}`))
  }, [selectedId])

  function toggleArrayFilter(key: 'types' | 'statuses', value: string) {
    setPage(1)
    setFilters((current) => {
      const exists = current[key].includes(value)
      return {
        ...current,
        [key]: exists ? current[key].filter((item) => item !== value) : [...current[key], value],
      }
    })
  }

  function onSortClick(key: SortKey) {
    if (sort === key) {
      setOrder((current) => (current === 'asc' ? 'desc' : 'asc'))
    } else {
      setSort(key)
      setOrder('asc')
    }
  }

  async function onSaveView() {
    const name = window.prompt('Saved view name')
    if (!name) return
    const definition = {
      filters,
      sort,
      order,
      page_size: PAGE_SIZE,
    }
    await createView({ name, definition_json: JSON.stringify(definition) })
    await refreshViews()
    setToast(`Saved view '${name}' created`)
  }

  async function applyView(view: SavedView) {
    try {
      const parsed = JSON.parse(view.definition_json) as {
        filters?: Filters
        sort?: SortKey
        order?: SortOrder
      }
      if (parsed.filters) setFilters(parsed.filters)
      if (parsed.sort) setSort(parsed.sort)
      if (parsed.order) setOrder(parsed.order)
      setPage(1)
    } catch {
      setToast(`Invalid saved view JSON for '${view.name}'`)
    }
  }

  async function onDeleteView(id: number) {
    await deleteView(id)
    await refreshViews()
  }

  async function onIngest() {
    const folder = import.meta.env.VITE_INGEST_FOLDER ?? '../data'
    const summary: IngestSummary = await ingestFolder({ folder, pattern: '*.csv' })
    setToast(
      `Ingested ${summary.rows_upserted}/${summary.rows_read} rows from ${summary.files_processed} file(s), errors=${summary.errors}`
    )
    await refreshData()
  }

  async function onSaveDetails() {
    if (!selected) return
    const payload: OpportunityPatch = {
      status: drawerState.status,
      notes: drawerState.notes,
      priority: Number(drawerState.priority ?? 0),
      tags: drawerState.tags,
      region_tag: drawerState.region_tag,
    }
    await patchOpportunity(selected.id, payload)
    setToast('Opportunity updated')
    await refreshData()
    const refreshed = await getOpportunity(selected.id)
    setSelected(refreshed)
  }

  const activeChips = [
    filters.types.length ? `Type: ${filters.types.join(',')}` : '',
    filters.statuses.length ? `Status: ${filters.statuses.join(',')}` : '',
    filters.due_bucket ? `Due: ${filters.due_bucket}` : '',
    filters.region_tag ? `Region: ${filters.region_tag}` : '',
    filters.tagsText ? `Tags: ${filters.tagsText}` : '',
  ].filter(Boolean)

  return (
    <div className="h-screen bg-slate-100 text-slate-900">
      <div className="grid h-full grid-cols-12">
        <aside className="col-span-12 border-r bg-white p-4 md:col-span-3 lg:col-span-2">
          <h2 className="mb-2 text-lg font-semibold">Saved Views</h2>
          <button className="mb-3 w-full rounded border px-2 py-1 text-sm" onClick={onSaveView}>
            Save Current View
          </button>
          <div className="space-y-2">
            {savedViews.map((view) => (
              <div key={view.id} className="flex items-center gap-2">
                <button className="flex-1 rounded bg-slate-200 px-2 py-1 text-left text-sm" onClick={() => applyView(view)}>
                  {view.name}
                </button>
                <button className="rounded border px-2 py-1 text-xs" onClick={() => onDeleteView(view.id)}>
                  Delete
                </button>
              </div>
            ))}
          </div>

          <h3 className="mb-2 mt-6 text-sm font-semibold">Quick Filters</h3>
          <div className="space-y-2 text-sm">
            <button className="w-full rounded border px-2 py-1" onClick={() => { setFilters((f) => ({ ...f, due_bucket: '7' })); setPage(1) }}>
              Due &lt; 7 days
            </button>
            <button className="w-full rounded border px-2 py-1" onClick={() => { setFilters((f) => ({ ...f, region_tag: 'local' })); setPage(1) }}>
              Local only
            </button>
            <button className="w-full rounded border px-2 py-1" onClick={() => { setFilters((f) => ({ ...f, statuses: ['saved'] })); setPage(1) }}>
              Show Saved
            </button>
            <button
              className="w-full rounded border px-2 py-1"
              onClick={() => {
                setFilters({ q: '', types: [], statuses: [], due_bucket: '', region_tag: '', tagsText: '' })
                setSort('deadline')
                setOrder('asc')
                setPage(1)
              }}
            >
              Clear all
            </button>
          </div>
        </aside>

        <main className="col-span-12 flex h-full flex-col md:col-span-9 lg:col-span-7">
          <div className="border-b bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <input
                className="min-w-56 rounded border px-2 py-1"
                placeholder="Search"
                value={filters.q}
                onChange={(e) => {
                  setPage(1)
                  setFilters((f) => ({ ...f, q: e.target.value }))
                }}
              />
              <select
                className="rounded border px-2 py-1"
                value={filters.due_bucket}
                onChange={(e) => {
                  setPage(1)
                  setFilters((f) => ({ ...f, due_bucket: e.target.value as Filters['due_bucket'] }))
                }}
              >
                <option value="">Due bucket</option>
                <option value="overdue">overdue</option>
                <option value="7">7</option>
                <option value="30">30</option>
                <option value="90">90</option>
                <option value="none">none</option>
              </select>
              <input
                className="rounded border px-2 py-1"
                placeholder="Region tag"
                value={filters.region_tag}
                onChange={(e) => {
                  setPage(1)
                  setFilters((f) => ({ ...f, region_tag: e.target.value }))
                }}
              />
              <input
                className="rounded border px-2 py-1"
                placeholder="Tags (comma separated)"
                value={filters.tagsText}
                onChange={(e) => {
                  setPage(1)
                  setFilters((f) => ({ ...f, tagsText: e.target.value }))
                }}
              />
              <button className="rounded bg-blue-600 px-3 py-1 text-white" onClick={onIngest}>
                Ingest Folder
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              {allTypes.map((typeItem) => (
                <button
                  key={typeItem}
                  className={`rounded border px-2 py-1 ${filters.types.includes(typeItem) ? 'bg-slate-300' : 'bg-white'}`}
                  onClick={() => toggleArrayFilter('types', typeItem)}
                >
                  {typeItem}
                </button>
              ))}
              {allStatuses.map((statusItem) => (
                <button
                  key={statusItem}
                  className={`rounded border px-2 py-1 ${filters.statuses.includes(statusItem) ? 'bg-slate-300' : 'bg-white'}`}
                  onClick={() => toggleArrayFilter('statuses', statusItem)}
                >
                  {statusItem}
                </button>
              ))}
            </div>
            {activeChips.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1 text-xs">
                {activeChips.map((chip) => (
                  <span key={chip} className="rounded bg-slate-200 px-2 py-1">
                    {chip}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex-1 overflow-auto p-4">
            <table className="min-w-full border bg-white text-sm">
              <thead className="bg-slate-200">
                <tr>
                  <th className="cursor-pointer p-2 text-left" onClick={() => onSortClick('priority')}>
                    Priority
                  </th>
                  <th className="cursor-pointer p-2 text-left" onClick={() => onSortClick('deadline')}>
                    Deadline
                  </th>
                  <th className="p-2 text-left">Type</th>
                  <th className="p-2 text-left">Title</th>
                  <th className="p-2 text-left">Org</th>
                  <th className="p-2 text-left">Location</th>
                  <th className="p-2 text-left">Tags</th>
                  <th className="p-2 text-left">Status</th>
                  <th className="cursor-pointer p-2 text-left" onClick={() => onSortClick('updated_at')}>
                    Updated
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="cursor-pointer border-t hover:bg-slate-50" onClick={() => setSelectedId(row.id)}>
                    <td className="p-2">{row.priority}</td>
                    <td className="p-2">
                      <div>{row.deadline ?? '-'}</div>
                      <div className="text-xs text-slate-500">{urgencyLabel(row.deadline)}</div>
                    </td>
                    <td className="p-2">{row.type}</td>
                    <td className="p-2">{row.title}</td>
                    <td className="p-2">{row.org ?? '-'}</td>
                    <td className="p-2">{row.location ?? '-'}</td>
                    <td className="p-2">{row.tags.join(', ')}</td>
                    <td className="p-2">{row.status}</td>
                    <td className="p-2">{new Date(row.updated_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="mt-3 flex items-center justify-between text-sm">
              <span>
                Page {page} / {totalPages} • {total} total
              </span>
              <div className="space-x-2">
                <button className="rounded border px-2 py-1 disabled:opacity-50" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Prev
                </button>
                <button
                  className="rounded border px-2 py-1 disabled:opacity-50"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </main>

        <aside className="col-span-12 h-full border-l bg-white p-4 md:col-span-12 lg:col-span-3">
          <h2 className="mb-2 text-lg font-semibold">Opportunity Details</h2>
          {!selected && <p className="text-sm text-slate-500">Select a row to view details.</p>}
          {selected && (
            <div className="space-y-3 text-sm">
              <div>
                <h3 className="font-semibold">{selected.title}</h3>
                <p>{selected.org}</p>
                {selected.url && (
                  <a href={selected.url} target="_blank" className="text-blue-600 underline" rel="noreferrer">
                    Open link
                  </a>
                )}
              </div>

              <p>{selected.description}</p>

              <label className="block">
                <span className="mb-1 block">Status</span>
                <select
                  className="w-full rounded border px-2 py-1"
                  value={drawerState.status ?? 'new'}
                  onChange={(e) => setDrawerState((s) => ({ ...s, status: e.target.value as Opportunity['status'] }))}
                >
                  {allStatuses.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="mb-1 block">Priority</span>
                <input
                  className="w-full rounded border px-2 py-1"
                  type="number"
                  value={drawerState.priority ?? 0}
                  onChange={(e) => setDrawerState((s) => ({ ...s, priority: Number(e.target.value) }))}
                />
              </label>

              <label className="block">
                <span className="mb-1 block">Region tag</span>
                <input
                  className="w-full rounded border px-2 py-1"
                  value={drawerState.region_tag ?? ''}
                  onChange={(e) => setDrawerState((s) => ({ ...s, region_tag: e.target.value }))}
                />
              </label>

              <label className="block">
                <span className="mb-1 block">Tags (comma separated)</span>
                <input
                  className="w-full rounded border px-2 py-1"
                  value={(drawerState.tags ?? []).join(', ')}
                  onChange={(e) => setDrawerState((s) => ({ ...s, tags: parseTagInput(e.target.value) }))}
                />
              </label>

              <label className="block">
                <span className="mb-1 block">Notes</span>
                <textarea
                  className="h-32 w-full rounded border p-2"
                  value={drawerState.notes ?? ''}
                  onChange={(e) => setDrawerState((s) => ({ ...s, notes: e.target.value }))}
                />
              </label>

              <button className="rounded bg-blue-600 px-3 py-1 text-white" onClick={onSaveDetails}>
                Save Changes
              </button>
            </div>
          )}
        </aside>
      </div>

      {toast && (
        <div className="fixed bottom-4 right-4 rounded bg-slate-900 px-3 py-2 text-sm text-white">
          {toast}
          <button className="ml-2 underline" onClick={() => setToast('')}>
            dismiss
          </button>
        </div>
      )}
    </div>
  )
}
