from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.diff import DiffReport
from app.schemas.runs import RunCreate, RunResponse, run_to_response
from app.schemas.stability import StabilityReport
from app.services.diff_service import (
    DiffNotFoundError,
    DiffValidationError,
    compare_runs,
)
from app.services.ingestion_service import (
    IngestionConflictError,
    get_run_by_external_id,
    ingest_run,
)
from app.services.stability_service import (
    StabilityNotFoundError,
    get_test_case_stability,
)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/runs",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_run(payload: RunCreate, db: Session = Depends(get_db)) -> RunResponse:
    try:
        run = ingest_run(db, payload)
    except IngestionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message,
        ) from exc
    return run_to_response(run)


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)) -> RunResponse:
    run = get_run_by_external_id(db, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with run_id '{run_id}' not found",
        )
    return run_to_response(run)


@router.get("/diff", response_model=DiffReport)
def get_diff(
    base_run_id: str = Query(..., min_length=1),
    head_run_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> DiffReport:
    try:
        return compare_runs(db, base_run_id=base_run_id, head_run_id=head_run_id)
    except DiffValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    except DiffNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.get("/tests/{test_case_id}/stability", response_model=StabilityReport)
def get_stability(
    test_case_id: str,
    n: int = Query(default=10, ge=2, le=100),
    db: Session = Depends(get_db),
) -> StabilityReport:
    try:
        return get_test_case_stability(db, test_case_id=test_case_id, n=n)
    except StabilityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
