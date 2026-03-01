import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ingest import IngestOptions, ingest_folder
from app.schemas.api import IngestFolderRequest, IngestSummaryResponse

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/folder", response_model=IngestSummaryResponse)
def ingest_from_folder(payload: IngestFolderRequest, db: Session = Depends(get_db)):
    options = IngestOptions(
        folder=payload.folder,
        pattern=payload.pattern,
        overwrite_user_fields=payload.overwrite_user_fields,
        type_default=payload.type_default,
    )
    summary = ingest_folder(db, options)
    return IngestSummaryResponse(
        folder=options.folder,
        pattern=options.pattern,
        rows_read=summary.rows_read,
        rows_upserted=summary.rows_upserted,
        errors=summary.errors,
        files_processed=summary.files_processed,
    )


@router.post("/upload", response_model=IngestSummaryResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    overwrite_user_fields: bool = False,
    type_default: str | None = None,
    db: Session = Depends(get_db),
):
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / (file.filename or "upload.csv")
        file_path.write_bytes(await file.read())

        options = IngestOptions(
            folder=tmpdir,
            pattern=file_path.name,
            overwrite_user_fields=overwrite_user_fields,
            type_default=type_default,
        )
        summary = ingest_folder(db, options)
        return IngestSummaryResponse(
            folder=options.folder,
            pattern=options.pattern,
            rows_read=summary.rows_read,
            rows_upserted=summary.rows_upserted,
            errors=summary.errors,
            files_processed=summary.files_processed,
        )
