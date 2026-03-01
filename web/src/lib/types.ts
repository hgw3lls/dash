export type Opportunity = {
  id: string
  type: string
  title: string
  org: string | null
  location: string | null
  region_tag: string | null
  deadline: string | null
  deadline_bucket: string
  posted_date: string | null
  url: string | null
  source: string | null
  description: string | null
  priority: number
  status: 'new' | 'saved' | 'applied' | 'archived' | 'ignored'
  notes: string | null
  tags: string[]
  created_at: string
  updated_at: string
}

export type OpportunityListResponse = {
  items: Opportunity[]
  total: number
  page: number
  page_size: number
}

export type SavedView = {
  id: number
  name: string
  definition_json: string
}

export type IngestSummary = {
  folder: string
  pattern: string
  rows_read: number
  rows_upserted: number
  errors: number
  files_processed: number
}

export type OpportunityPatch = {
  status?: Opportunity['status']
  notes?: string
  priority?: number
  tags?: string[]
  region_tag?: string
}
