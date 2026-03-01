from datetime import date
from pathlib import Path

from app.ingest import IngestOptions, generate_opportunity_id, ingest_folder, parse_date
from app.models import Opportunity


def test_parse_date_common_formats() -> None:
    assert parse_date("2026-01-31") == date(2026, 1, 31)
    assert parse_date("01/31/2026") == date(2026, 1, 31)
    assert parse_date("2026/01/31") == date(2026, 1, 31)
    assert parse_date("not-a-date") is None


def test_generate_id_prefers_url() -> None:
    a = generate_opportunity_id("cfp", "Title", "Org", date(2026, 1, 1), "https://example.org/test")
    b = generate_opportunity_id("job", "Other", "Else", None, "https://example.org/test")
    assert a == b


def test_upsert_preserves_status_and_notes(db_session, tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "mixed_tracker.csv"
    csv_copy = tmp_path / "mixed_tracker.csv"
    csv_copy.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    first = ingest_folder(db_session, IngestOptions(folder=str(tmp_path)))
    assert first.rows_upserted == 2

    existing = db_session.query(Opportunity).first()
    assert existing is not None
    existing.status = "applied"
    existing.notes = "user note"
    db_session.add(existing)
    db_session.commit()

    second = ingest_folder(db_session, IngestOptions(folder=str(tmp_path), overwrite_user_fields=False))
    assert second.rows_upserted == 2

    persisted = db_session.get(Opportunity, existing.id)
    assert persisted is not None
    assert persisted.status == "applied"
    assert persisted.notes == "user note"
