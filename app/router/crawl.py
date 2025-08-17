"""
Crawl Router - REST API endpoints for site crawling
"""
from typing import Annotated, Optional, List
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.requests import Request
from pydantic import BaseModel, Field, HttpUrl, validator

from crawler.job_manager import job_manager
from crawler.models import JobStatus
from server.auth import AuthRequired

import logging
logger = logging.getLogger(__name__)


router = APIRouter(prefix='/api/crawl', tags=['crawl'])


class CrawlRequest(BaseModel):
    """Request to start a new crawl"""
    start_url: HttpUrl = Field(description="Starting URL for the crawl")
    max_pages: int = Field(default=50, ge=1, le=5000, description="Maximum pages to crawl")
    max_duration: int = Field(default=3600, ge=60, le=43200, description="Maximum crawl duration in seconds")
    scope: str = Field(default="domain", description="Crawl scope: 'domain', 'host', 'path', or regex pattern")
    rate_limit: float = Field(default=1.0, ge=0.1, le=10.0, description="Requests per second per domain")
    respect_robots: bool = Field(default=True, description="Respect robots.txt")
    include_assets: bool = Field(default=False, description="Include assets (images, CSS, JS)")
    custom_patterns: List[str] = Field(default_factory=list, description="Custom URL patterns to include/exclude")
    
    @validator('scope')
    def validate_scope(cls, v):
        if v not in ['domain', 'host', 'path'] and not v.startswith('regex:'):
            raise ValueError('Scope must be "domain", "host", "path", or start with "regex:"')
        return v


class CrawlResponse(BaseModel):
    """Response when starting a crawl"""
    job_id: str = Field(description="Unique job identifier")
    status: str = Field(description="Current job status")
    message: str = Field(description="Human-readable message")
    estimated_pages: Optional[int] = Field(description="Estimated number of pages to crawl")


class JobStatus(BaseModel):
    """Job status response"""
    job_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    pages_crawled: int = 0
    pages_found: int = 0
    pages_remaining: int = 0
    errors: List[str] = []
    progress_percent: Optional[float] = None


class JobList(BaseModel):
    """List of jobs response"""
    jobs: List[JobStatus]
    total: int
    offset: int
    limit: int


class JobStats(BaseModel):
    """Detailed job statistics"""
    job_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    pages_crawled: int = 0
    pages_found: int = 0
    pages_remaining: int = 0
    total_pages_stored: int = 0
    average_page_size: Optional[int] = None
    crawl_rate: Optional[float] = None
    errors: List[str] = []
    params: dict


@router.post('/', summary='Start a new crawl job', response_model=CrawlResponse)
async def start_crawl(
    request: CrawlRequest,
    _: AuthRequired,
) -> CrawlResponse:
    """
    Start a new site crawl job.<br><br>
    
    This endpoint creates and starts a recursive crawl of a website starting from the given URL.
    The crawler will discover and extract content from multiple pages within the specified scope.
    """
    try:
        # Convert request to crawler parameters
        params = {
            'start_url': str(request.start_url),
            'max_pages': request.max_pages,
            'max_duration': request.max_duration,
            'scope': request.scope,
            'rate_limit': request.rate_limit,
            'respect_robots': request.respect_robots,
            'include_assets': request.include_assets,
            'custom_patterns': request.custom_patterns,
        }
        
        # Create job
        job_id = await job_manager.create_job(params)
        
        # Start job
        success = await job_manager.start_job(job_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start crawl job")
        
        return CrawlResponse(
            job_id=job_id,
            status="running",
            message=f"Started crawling {request.start_url}",
            estimated_pages=None  # Could implement estimation logic
        )
        
    except Exception as e:
        logger.error(f"Failed to start crawl: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/', summary='List all crawl jobs', response_model=JobList)
async def list_jobs(
    _: AuthRequired,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: Annotated[Optional[str], Query()] = None,
) -> JobList:
    """
    List all crawl jobs with optional filtering and pagination.
    """
    try:
        jobs = await job_manager.list_jobs(limit=limit, offset=offset)
        
        # Filter by status if specified
        if status:
            jobs = [job for job in jobs if job.status.value == status]
        
        # Convert to response format
        job_statuses = []
        for job in jobs:
            progress = None
            if job.pages_found > 0:
                progress = (job.pages_crawled / job.pages_found) * 100
            
            job_statuses.append(JobStatus(
                job_id=job.id,
                status=job.status.value,
                created_at=job.created_at.isoformat(),
                started_at=job.started_at.isoformat() if job.started_at else None,
                finished_at=job.finished_at.isoformat() if job.finished_at else None,
                pages_crawled=job.pages_crawled,
                pages_found=job.pages_found,
                pages_remaining=job.pages_remaining,
                errors=job.errors,
                progress_percent=progress,
            ))
        
        return JobList(
            jobs=job_statuses,
            total=len(job_statuses),
            offset=offset,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{job_id}', summary='Get job status', response_model=JobStatus)
async def get_job_status(
    job_id: str,
    _: AuthRequired,
) -> JobStatus:
    """
    Get detailed status information for a specific crawl job.
    """
    try:
        job = await job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        progress = None
        if job.pages_found > 0:
            progress = (job.pages_crawled / job.pages_found) * 100
        
        return JobStatus(
            job_id=job.id,
            status=job.status.value,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            finished_at=job.finished_at.isoformat() if job.finished_at else None,
            pages_crawled=job.pages_crawled,
            pages_found=job.pages_found,
            pages_remaining=job.pages_remaining,
            errors=job.errors,
            progress_percent=progress,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{job_id}/stats', summary='Get detailed job statistics', response_model=JobStats)
async def get_job_stats(
    job_id: str,
    _: AuthRequired,
) -> JobStats:
    """
    Get comprehensive statistics and details for a crawl job.
    """
    try:
        stats = await job_manager.get_job_stats(job_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Calculate additional metrics
        duration = None
        crawl_rate = None
        if stats['started_at'] and stats['finished_at']:
            start = datetime.fromisoformat(stats['started_at'])
            end = datetime.fromisoformat(stats['finished_at'])
            duration = (end - start).total_seconds()
            
            if duration > 0 and stats['pages_crawled'] > 0:
                crawl_rate = stats['pages_crawled'] / duration
        
        return JobStats(
            job_id=stats['job_id'],
            status=stats['status'],
            created_at=stats['created_at'],
            started_at=stats['started_at'],
            finished_at=stats['finished_at'],
            duration_seconds=duration,
            pages_crawled=stats['pages_crawled'],
            pages_found=stats['pages_found'],
            pages_remaining=stats['pages_remaining'],
            total_pages_stored=stats['total_pages_stored'],
            crawl_rate=crawl_rate,
            errors=stats['errors'],
            params=stats['params'],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/{job_id}/stop', summary='Stop a running crawl job')
async def stop_job(
    job_id: str,
    _: AuthRequired,
) -> dict:
    """
    Stop a currently running crawl job.
    """
    try:
        success = await job_manager.stop_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or not running")
        
        return {"message": f"Job {job_id} stopped successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{job_id}', summary='Delete a crawl job')
async def delete_job(
    job_id: str,
    _: AuthRequired,
) -> dict:
    """
    Delete a crawl job and all its associated data.
    """
    try:
        success = await job_manager.delete_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"message": f"Job {job_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{job_id}/pages', summary='List pages crawled by job')
async def list_job_pages(
    job_id: str,
    _: AuthRequired,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """
    List all pages that were crawled as part of a job.
    """
    try:
        job = await job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get pages from storage
        from crawler.storage import CrawlStorage
        storage = CrawlStorage()
        pages = await storage.list_pages(job_id)
        
        # Apply pagination
        total = len(pages)
        start = offset
        end = offset + limit
        page_slice = pages[start:end]
        
        return {
            "job_id": job_id,
            "pages": page_slice,
            "total": total,
            "offset": offset,
            "limit": limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list job pages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/{job_id}/export', summary='Export crawl results')
async def export_job_results(
    job_id: str,
    _: AuthRequired,
    format: Annotated[str, Query()] = "jsonl",
):
    """
    Export crawl results in various formats (jsonl, zip).
    """
    try:
        job = await job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Export using storage
        from crawler.storage import CrawlStorage
        storage = CrawlStorage()
        
        if format == "jsonl":
            export_path = await storage.export_jsonl(job_id)
        elif format == "zip":
            export_path = await storage.export_zip(job_id)
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
        
        return {
            "job_id": job_id,
            "format": format,
            "export_path": str(export_path),
            "download_url": f"/api/crawl/{job_id}/download/{format}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export job results: {e}")
        raise HTTPException(status_code=500, detail=str(e))