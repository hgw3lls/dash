from datetime import date, datetime

from pydantic import BaseModel, Field


class IngestFolderRequest(BaseModel):
    folder: str
    pattern: str = "*.csv"
    overwrite_user_fields: bool = False
    type_default: str | None = None


class IngestSummaryResponse(BaseModel):
    folder: str
    pattern: str
    rows_read: int
    rows_upserted: int
    errors: int
    files_processed: int


class OpportunityRead(BaseModel):
    id: str
    type: str
    title: str
    org: str | None = None
    location: str | None = None
    region_tag: str | None = None
    deadline: date | None = None
    deadline_bucket: str
    posted_date: date | None = None
    url: str | None = None
    source: str | None = None
    description: str | None = None
    priority: int
    status: str
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class OpportunityListResponse(BaseModel):
    items: list[OpportunityRead]
    total: int
    page: int
    page_size: int


class OpportunityPatchRequest(BaseModel):
    status: str | None = None
    notes: str | None = None
    priority: int | None = None
    tags: list[str] | None = None
    region_tag: str | None = None


class SavedViewCreateRequest(BaseModel):
    name: str
    definition_json: str


class SavedViewUpdateRequest(BaseModel):
    name: str | None = None
    definition_json: str | None = None


class SavedViewRead(BaseModel):
    id: int
    name: str
    definition_json: str
