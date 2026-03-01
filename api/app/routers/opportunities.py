import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Opportunity, SavedView, Tag
from app.schemas.api import (
    OpportunityListResponse,
    OpportunityPatchRequest,
    OpportunityRead,
    SavedViewCreateRequest,
    SavedViewRead,
    SavedViewUpdateRequest,
)

ALLOWED_STATUS = {"new", "saved", "applied", "archived", "ignored"}

router = APIRouter(tags=["opportunities"])


def deadline_bucket(deadline: date | None) -> str:
    if deadline is None:
        return "none"
    today = date.today()
    if deadline < today:
        return "overdue"
    days = (deadline - today).days
    if days <= 7:
        return "7"
    if days <= 30:
        return "30"
    if days <= 90:
        return "90"
    return "later"


def _to_read(item: Opportunity) -> OpportunityRead:
    return OpportunityRead(
        id=item.id,
        type=item.type,
        title=item.title,
        org=item.org,
        location=item.location,
        region_tag=item.region_tag,
        deadline=item.deadline,
        deadline_bucket=deadline_bucket(item.deadline),
        posted_date=item.posted_date,
        url=item.url,
        source=item.source,
        description=item.description,
        priority=item.priority,
        status=item.status,
        notes=item.notes,
        tags=[t.name for t in item.tags],
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _csv_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _fts_available(db: Session) -> bool:
    row = db.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='opportunities_fts'")
    ).first()
    return row is not None


def _apply_search_filter(stmt, db: Session, q: str):
    if _fts_available(db):
        ids = db.execute(
            text("SELECT id FROM opportunities_fts WHERE opportunities_fts MATCH :query"),
            {"query": q},
        ).scalars().all()
        if not ids:
            return stmt.where(text("1=0"))
        return stmt.where(Opportunity.id.in_(ids))

    pattern = f"%{q}%"
    return stmt.where(
        or_(
            Opportunity.title.ilike(pattern),
            Opportunity.org.ilike(pattern),
            Opportunity.location.ilike(pattern),
            Opportunity.description.ilike(pattern),
        )
    )


def _apply_filters(
    stmt,
    db: Session,
    *,
    q,
    type_csv,
    status_csv,
    tags,
    deadline_from,
    deadline_to,
    due_bucket,
    region_csv,
):
    if q:
        stmt = _apply_search_filter(stmt, db, q)

    types = _csv_values(type_csv)
    if types:
        stmt = stmt.where(Opportunity.type.in_(types))

    statuses = _csv_values(status_csv)
    if statuses:
        stmt = stmt.where(Opportunity.status.in_(statuses))

    if tags:
        stmt = stmt.join(Opportunity.tags).where(Tag.name.in_(tags)).distinct()

    if deadline_from:
        stmt = stmt.where(Opportunity.deadline >= deadline_from)
    if deadline_to:
        stmt = stmt.where(Opportunity.deadline <= deadline_to)

    if due_bucket == "none":
        stmt = stmt.where(Opportunity.deadline.is_(None))
    elif due_bucket in {"overdue", "7", "30", "90"}:
        today = date.today()
        if due_bucket == "overdue":
            stmt = stmt.where(Opportunity.deadline < today)
        else:
            days = int(due_bucket)
            upper = date.fromordinal(today.toordinal() + days)
            stmt = stmt.where(and_(Opportunity.deadline >= today, Opportunity.deadline <= upper))

    region_tags = _csv_values(region_csv)
    if region_tags:
        stmt = stmt.where(Opportunity.region_tag.in_(region_tags))

    return stmt


@router.get("/opportunities", response_model=OpportunityListResponse)
def list_opportunities(
    q: str | None = None,
    type: str | None = Query(None),
    status: str | None = Query(None),
    tag: list[str] = Query(default=[]),
    deadline_from: date | None = None,
    deadline_to: date | None = None,
    due_bucket: str | None = Query(None, pattern="^(overdue|7|30|90|none)$"),
    region_tag: str | None = Query(None),
    sort: str = Query("deadline", pattern="^(deadline|priority|updated_at|posted_date)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    base = select(Opportunity)
    filtered = _apply_filters(
        base,
        db,
        q=q,
        type_csv=type,
        status_csv=status,
        tags=tag,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        due_bucket=due_bucket,
        region_csv=region_tag,
    )

    count_stmt = select(func.count()).select_from(filtered.subquery())
    sort_col = getattr(Opportunity, sort)
    primary_sort = sort_col.asc() if order == "asc" else sort_col.desc()
    if sort == "deadline":
        filtered = filtered.order_by(primary_sort, Opportunity.priority.desc(), Opportunity.updated_at.desc())
    else:
        filtered = filtered.order_by(primary_sort, Opportunity.updated_at.desc())

    total = db.scalar(count_stmt) or 0
    offset = (page - 1) * page_size
    rows = db.scalars(filtered.offset(offset).limit(page_size)).unique().all()

    return OpportunityListResponse(items=[_to_read(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityRead)
def get_opportunity(opportunity_id: str, db: Session = Depends(get_db)):
    item = db.get(Opportunity, opportunity_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opportunity_id}' was not found")
    return _to_read(item)


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityRead)
def patch_opportunity(opportunity_id: str, payload: OpportunityPatchRequest, db: Session = Depends(get_db)):
    item = db.get(Opportunity, opportunity_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opportunity_id}' was not found")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in ALLOWED_STATUS:
        allowed = ", ".join(sorted(ALLOWED_STATUS))
        raise HTTPException(status_code=422, detail=f"Invalid status '{data['status']}'. Allowed values: {allowed}")

    if "status" in data:
        item.status = data["status"]
    if "notes" in data:
        item.notes = data["notes"]
    if "priority" in data:
        item.priority = data["priority"]
    if "region_tag" in data:
        item.region_tag = data["region_tag"]
    if "tags" in data:
        names = sorted(set(data["tags"] or []))
        tag_models = []
        for name in names:
            existing = db.scalar(select(Tag).where(Tag.name == name))
            if not existing:
                existing = Tag(name=name)
                db.add(existing)
                db.flush()
            tag_models.append(existing)
        item.tags = tag_models

    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_read(item)


@router.get("/views", response_model=list[SavedViewRead])
def list_views(db: Session = Depends(get_db)):
    rows = db.scalars(select(SavedView).order_by(SavedView.name.asc())).all()
    return [SavedViewRead(id=r.id, name=r.name, definition_json=r.definition_json) for r in rows]


@router.post("/views", response_model=SavedViewRead)
def create_view(payload: SavedViewCreateRequest, db: Session = Depends(get_db)):
    item = SavedView(name=payload.name, definition_json=payload.definition_json)
    db.add(item)
    db.commit()
    db.refresh(item)
    return SavedViewRead(id=item.id, name=item.name, definition_json=item.definition_json)


@router.patch("/views/{view_id}", response_model=SavedViewRead)
def patch_view(view_id: int, payload: SavedViewUpdateRequest, db: Session = Depends(get_db)):
    item = db.get(SavedView, view_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Saved view '{view_id}' was not found")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        item.name = data["name"]
    if "definition_json" in data:
        item.definition_json = data["definition_json"]

    db.add(item)
    db.commit()
    db.refresh(item)
    return SavedViewRead(id=item.id, name=item.name, definition_json=item.definition_json)


@router.delete("/views/{view_id}")
def delete_view(view_id: int, db: Session = Depends(get_db)):
    item = db.get(SavedView, view_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Saved view '{view_id}' was not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


def _filtered_items_for_export(**kwargs):
    db: Session = kwargs.pop("db")
    stmt = select(Opportunity)
    stmt = _apply_filters(stmt, db, **kwargs)
    return db.scalars(stmt.order_by(Opportunity.updated_at.desc())).unique().all()


@router.get("/export/json")
def export_json(
    q: str | None = None,
    type: str | None = Query(None),
    status: str | None = Query(None),
    tag: list[str] = Query(default=[]),
    deadline_from: date | None = None,
    deadline_to: date | None = None,
    due_bucket: str | None = Query(None, pattern="^(overdue|7|30|90|none)$"),
    region_tag: str | None = Query(None),
    db: Session = Depends(get_db),
):
    items = _filtered_items_for_export(
        q=q,
        type_csv=type,
        status_csv=status,
        tags=tag,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        due_bucket=due_bucket,
        region_csv=region_tag,
        db=db,
    )
    serial = [_to_read(i).model_dump(mode="json") for i in items]
    return {"items": serial, "total": len(serial)}


@router.get("/export/csv")
def export_csv(
    q: str | None = None,
    type: str | None = Query(None),
    status: str | None = Query(None),
    tag: list[str] = Query(default=[]),
    deadline_from: date | None = None,
    deadline_to: date | None = None,
    due_bucket: str | None = Query(None, pattern="^(overdue|7|30|90|none)$"),
    region_tag: str | None = Query(None),
    db: Session = Depends(get_db),
):
    items = _filtered_items_for_export(
        q=q,
        type_csv=type,
        status_csv=status,
        tags=tag,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        due_bucket=due_bucket,
        region_csv=region_tag,
        db=db,
    )
    rows = [_to_read(i).model_dump(mode="json") for i in items]
    if not rows:
        rows = [{"id": "", "title": ""}]

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(iter([buffer.read()]), media_type="text/csv")
