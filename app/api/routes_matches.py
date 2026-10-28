"""The two required endpoints. Plain `def`: FastAPI runs them in its thread pool,
which suits the synchronous psycopg pool."""
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from app.api import schemas
from app.services.matching_service import MatchingService

router = APIRouter()

ERRORS = {404: {"model": schemas.ErrorResponse}, 422: {"model": schemas.ErrorResponse},
          503: {"model": schemas.ErrorResponse}}

MinScore = Annotated[Decimal, Query(ge=0, le=100, allow_inf_nan=False,
                                    description="Drop matches whose unrounded score is below this (0–100)")]
MinCoverage = Annotated[Decimal, Query(ge=0, le=100, allow_inf_nan=False,
                                       description="Drop matches whose required-skill coverage % is below this (0–100)")]
EntityId = Annotated[int, Path(ge=1, le=2_147_483_647)]
AvailabilityFilter = Annotated[Optional[list[schemas.Availability]], Query(
    description="Repeatable: ?availability=immediate&availability=two_weeks")]


def get_service(request: Request) -> MatchingService:
    return request.app.state.matching_service


@router.get("/health", response_model=schemas.HealthResponse,
            responses={503: {"model": schemas.HealthResponse}}, summary="Service and database health")
def health(response: Response, service: MatchingService = Depends(get_service)):
    if service.database_ok():
        return schemas.HealthResponse(status="ok", database="ok")
    response.status_code = 503
    return schemas.HealthResponse(status="degraded", database="unavailable")


@router.get("/jobs", response_model=schemas.JobListResponse, responses={503: ERRORS[503]},
            summary="All jobs")
def list_jobs(service: MatchingService = Depends(get_service)):
    return schemas.job_list_response(service.list_jobs())


@router.get("/candidates", response_model=schemas.CandidateListResponse,
            responses={422: ERRORS[422], 503: ERRORS[503]}, summary="All candidates")
def list_candidates(availability: AvailabilityFilter = None,
                    service: MatchingService = Depends(get_service)):
    avail = sorted({a.value for a in availability}) if availability else None
    return schemas.candidate_list_response(service.list_candidates(avail),
                                           schemas.CandidateListFiltersOut(availability=avail))


@router.get("/jobs/{job_id}/matches", response_model=schemas.JobMatchesResponse, responses=ERRORS,
            summary="Ranked candidates for a job")
def job_matches(
    job_id: EntityId,
    min_score: MinScore = Decimal(0),
    min_skill_coverage: MinCoverage = Decimal(0),
    availability: AvailabilityFilter = None,
    service: MatchingService = Depends(get_service),
):
    avail = sorted({a.value for a in availability}) if availability else None
    result = service.matches_for_job(job_id, min_score=min_score, min_skill_coverage=min_skill_coverage,
                                     availabilities=avail)
    filters = schemas.JobFiltersOut(min_score=float(min_score), min_skill_coverage=float(min_skill_coverage),
                                    availability=avail)
    return schemas.job_matches_response(result, filters)


@router.get("/candidates/{candidate_id}/matches", response_model=schemas.CandidateMatchesResponse,
            responses=ERRORS, summary="Ranked jobs for a candidate")
def candidate_matches(
    candidate_id: EntityId,
    min_score: MinScore = Decimal(0),
    min_skill_coverage: MinCoverage = Decimal(0),
    service: MatchingService = Depends(get_service),
):
    result = service.matches_for_candidate(candidate_id, min_score=min_score,
                                           min_skill_coverage=min_skill_coverage)
    filters = schemas.CandidateFiltersOut(min_score=float(min_score), min_skill_coverage=float(min_skill_coverage))
    return schemas.candidate_matches_response(result, filters)
