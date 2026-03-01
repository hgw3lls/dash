import csv
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IngestRun, Opportunity, Tag

logger = logging.getLogger(__name__)

COLUMN_SYNONYMS: dict[str, list[str]] = {
    "title": ["title", "opportunity", "name", "position", "call"],
    "org": ["org", "organization", "company", "institution", "publisher"],
    "location": ["location", "city", "state", "region"],
    "deadline": ["deadline", "due", "due_date", "submission_deadline"],
    "url": ["url", "link", "website"],
    "source": ["source", "feed", "site"],
    "description": ["description", "details", "summary", "notes", "blurb"],
    "type": ["type", "category", "tracker"],
    "priority": ["priority", "score", "rank"],
    "tags": ["tags", "keywords", "topics"],
    "posted_date": ["posted", "date_posted", "published"],
}

COMMON_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d %H:%M:%S",
]


@dataclass
class IngestSummary:
    rows_read: int = 0
    rows_upserted: int = 0
    errors: int = 0
    files_processed: int = 0


@dataclass
class IngestOptions:
    folder: str
    pattern: str = "*.csv"
    overwrite_user_fields: bool = False
    type_default: str | None = None
    mapping_overrides: dict[str, dict[str, str]] | None = None


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _normalize_str(value: str | None) -> str:
    return (value or "").strip().lower()


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    for fmt in COMMON_DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        logger.warning("Invalid date value: %s", raw)
        return None


def generate_opportunity_id(
    type_value: str | None,
    title: str | None,
    org: str | None,
    deadline: date | None,
    url: str | None,
) -> str:
    if url and url.strip():
        basis = f"url::{url.strip().lower()}"
    else:
        basis = "::".join(
            [
                _normalize_str(type_value),
                _normalize_str(title),
                _normalize_str(org),
                deadline.isoformat() if deadline else "",
            ]
        )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:64]


def _find_value(
    row: dict[str, Any],
    canonical_field: str,
    file_overrides: dict[str, str] | None,
) -> str | None:
    normalized = {_normalize_key(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

    if file_overrides and canonical_field in file_overrides:
        override_key = _normalize_key(file_overrides[canonical_field])
        override_value = normalized.get(override_key)
        if isinstance(override_value, str) and override_value:
            return override_value

    for synonym in COLUMN_SYNONYMS.get(canonical_field, []):
        found = normalized.get(_normalize_key(synonym))
        if isinstance(found, str) and found:
            return found
    return None


def _infer_type(file_stem: str, explicit_type: str | None, type_default: str | None) -> str:
    if explicit_type:
        return explicit_type.strip().lower()
    stem = file_stem.lower()
    for candidate in ("cfp", "job", "art", "master"):
        if candidate in stem:
            return candidate
    return (type_default or "master").lower()


def _parse_tags(raw_tags: str | None, inferred_type: str, source: str | None) -> list[str]:
    if raw_tags:
        tokens = [t.strip().lower() for t in raw_tags.replace(";", ",").split(",")]
        clean = [t for t in tokens if t]
        if clean:
            return sorted(set(clean))
    inferred = [inferred_type]
    if source:
        s = source.lower()
        if any(tok in s for tok in ["local", "regional", "national", "international"]):
            inferred.append(s)
    return sorted(set(inferred))


def _to_priority(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def _get_or_create_tag(db: Session, name: str) -> Tag:
    existing = db.scalar(select(Tag).where(Tag.name == name))
    if existing:
        return existing
    tag = Tag(name=name)
    db.add(tag)
    db.flush()
    return tag


def _normalize_row(
    row: dict[str, Any],
    file_stem: str,
    options: IngestOptions,
) -> dict[str, Any]:
    file_overrides = (options.mapping_overrides or {}).get(file_stem)

    title = _find_value(row, "title", file_overrides) or "Untitled"
    org = _find_value(row, "org", file_overrides)
    location = _find_value(row, "location", file_overrides)
    deadline = parse_date(_find_value(row, "deadline", file_overrides))
    posted_date = parse_date(_find_value(row, "posted_date", file_overrides))
    url = _find_value(row, "url", file_overrides)
    source = _find_value(row, "source", file_overrides) or file_stem
    description = _find_value(row, "description", file_overrides)
    explicit_type = _find_value(row, "type", file_overrides)
    type_value = _infer_type(file_stem, explicit_type, options.type_default)
    priority = _to_priority(_find_value(row, "priority", file_overrides))
    raw_tags = _find_value(row, "tags", file_overrides)
    tags = _parse_tags(raw_tags, type_value, source)

    opp_id = generate_opportunity_id(type_value, title, org, deadline, url)

    return {
        "id": opp_id,
        "type": type_value,
        "title": title,
        "org": org,
        "location": location,
        "deadline": deadline,
        "posted_date": posted_date,
        "url": url,
        "source": source,
        "description": description,
        "priority": priority,
        "raw": json.dumps(row, ensure_ascii=False),
        "tags": tags,
    }


def upsert_opportunity(db: Session, normalized: dict[str, Any], overwrite_user_fields: bool) -> bool:
    tags = normalized.pop("tags", [])
    existing = db.get(Opportunity, normalized["id"])

    if existing:
        protected_fields = {"status", "notes"} if not overwrite_user_fields else set()
        for key, value in normalized.items():
            if key in protected_fields:
                continue
            setattr(existing, key, value)
        existing.updated_at = datetime.now()
        existing.tags = [_get_or_create_tag(db, t) for t in tags]
        db.add(existing)
        return False

    new_obj = Opportunity(**normalized)
    new_obj.tags = [_get_or_create_tag(db, t) for t in tags]
    db.add(new_obj)
    return True


def ingest_folder(db: Session, options: IngestOptions) -> IngestSummary:
    summary = IngestSummary()
    folder = Path(options.folder)

    if not folder.exists():
        logger.warning("Ingest folder does not exist: %s", folder)
        return summary

    files = sorted(folder.glob(options.pattern))
    summary.files_processed = len(files)

    for file in files:
        with file.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                summary.rows_read += 1
                try:
                    normalized = _normalize_row(row, file.stem, options)
                    upsert_opportunity(db, normalized, options.overwrite_user_fields)
                    summary.rows_upserted += 1
                except Exception:
                    summary.errors += 1
                    logger.exception("Failed to ingest row from %s", file)

    ingest_run = IngestRun(
        ran_at=datetime.now(),
        source_path=str(folder),
        rows_in=summary.rows_read,
        rows_upserted=summary.rows_upserted,
        errors=summary.errors,
    )
    db.add(ingest_run)
    db.commit()
    return summary
