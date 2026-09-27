from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.runs import RunCreate, RunOut, run_to_response
from app.services.ingestion_service import (
    IngestionConflictError,
    get_run_by_external_id,
    ingest_run,
)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/runs",
    response_model=RunOut,
    status_code=status.HTTP_201_CREATED,
)
def create_run(payload: RunCreate, db: Session = Depends(get_db)) -> RunOut:
    try:
        run = ingest_run(db, payload)
    except IngestionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message,
        ) from exc
    return run_to_response(run)


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)) -> RunOut:
    run = get_run_by_external_id(db, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with run_id '{run_id}' not found",
        )
    return run_to_response(run)
