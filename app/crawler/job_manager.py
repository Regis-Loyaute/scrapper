"""
Job Manager - Singleton for managing crawler job lifecycle
"""
import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum

from crawler.models import CrawlJob, JobStatus
from crawler.storage import CrawlStorage
from crawler.crawler import SiteCrawler

logger = logging.getLogger(__name__)


class JobManager:
    """Singleton class for managing crawler jobs"""
    
    _instance: Optional['JobManager'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'JobManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._jobs: Dict[str, CrawlJob] = {}
            self._crawlers: Dict[str, SiteCrawler] = {}
            self._storage = CrawlStorage()
            self._lock = asyncio.Lock()
            JobManager._initialized = True
    
    async def create_job(self, params: dict) -> str:
        """Create a new crawl job"""
        async with self._lock:
            # Transform params to match expected format
            crawler_params = params.copy()
            if 'start_url' in crawler_params:
                crawler_params['url'] = crawler_params['start_url']
            
            # Convert to CrawlParams for storage
            from .models import CrawlParams
            crawl_params = CrawlParams(**crawler_params)
            
            # Use storage's new_job method to create domain-based directory
            job_id = self._storage.new_job(crawl_params)
            
            # Create job object for in-memory tracking
            job = CrawlJob(
                job_id=job_id,
                params=crawler_params,
                status=JobStatus.PENDING.value,
                created_at=datetime.now().isoformat(),
                pages_crawled=0,
                pages_found=0,
                pages_remaining=0,
                errors=[]
            )
            
            # Store job
            self._jobs[job_id] = job
            # Note: job is already saved by storage.new_job(), no need to save again
            
            logger.info(f"Created crawl job {job_id} for {params.get('start_url', 'unknown URL')}")
            return job_id
    
    async def start_job(self, job_id: str) -> bool:
        """Start a crawl job"""
        async with self._lock:
            if job_id not in self._jobs:
                logger.error(f"Job {job_id} not found")
                return False
            
            job = self._jobs[job_id]
            if job.status != JobStatus.PENDING.value:
                logger.error(f"Job {job_id} is not in pending status (current: {job.status})")
                return False
            
            try:
                # Create crawler instance
                crawler = SiteCrawler()
                self._crawlers[job_id] = crawler
                
                # Update job status
                job.status = JobStatus.RUNNING.value
                job.started_at = datetime.now().isoformat()
                await self._storage.save_job(job)
                
                # Start crawling in background
                asyncio.create_task(self._run_crawler(job_id, crawler))
                
                logger.info(f"Started crawl job {job_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start job {job_id}: {e}")
                job.status = JobStatus.FAILED.value
                job.error = str(e)
                await self._storage.save_job(job)
                return False
    
    async def _run_crawler(self, job_id: str, crawler: SiteCrawler):
        """Run the crawler and update job status"""
        try:
            job = self._jobs[job_id]
            
            # Set up progress callback
            async def progress_callback(stats: dict):
                job.pages_crawled = stats.get('pages_crawled', 0)
                job.pages_found = stats.get('pages_found', 0)
                job.pages_remaining = stats.get('pages_remaining', 0)
                await self._storage.save_job(job)
            
            # Run the crawler
            result = await crawler.crawl_site(
                params=job.params,
                job_id=job_id,
                progress_callback=progress_callback
            )
            
            # Update final status
            job.status = JobStatus.COMPLETED.value
            job.finished_at = datetime.now().isoformat()
            job.pages_crawled = result.get('total_pages', 0)
            await self._storage.save_job(job)
            
            logger.info(f"Completed crawl job {job_id} - {job.pages_crawled} pages")
            
        except Exception as e:
            logger.error(f"Crawler job {job_id} failed: {e}")
            job = self._jobs[job_id]
            job.status = JobStatus.FAILED.value
            job.error = str(e)
            job.finished_at = datetime.now().isoformat()
            await self._storage.save_job(job)
        
        finally:
            # Clean up crawler instance
            if job_id in self._crawlers:
                del self._crawlers[job_id]
    
    async def stop_job(self, job_id: str) -> bool:
        """Stop a running crawl job"""
        async with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs[job_id]
            if job.status != JobStatus.RUNNING.value:
                return False
            
            # Stop the crawler
            if job_id in self._crawlers:
                await self._crawlers[job_id].stop()
                del self._crawlers[job_id]
            
            # Update job status
            job.status = JobStatus.STOPPED.value
            job.finished_at = datetime.now().isoformat()
            await self._storage.save_job(job)
            
            logger.info(f"Stopped crawl job {job_id}")
            return True
    
    async def get_job(self, job_id: str) -> Optional[CrawlJob]:
        """Get job details"""
        if job_id in self._jobs:
            return self._jobs[job_id]
        
        # Try to load from storage
        try:
            job = await self._storage.load_job(job_id)
            if job:
                self._jobs[job_id] = job
            return job
        except Exception as e:
            logger.error(f"Failed to load job {job_id}: {e}")
            return None
    
    async def list_jobs(self, limit: int = 50, offset: int = 0) -> List[CrawlJob]:
        """List all jobs with pagination"""
        try:
            # Load jobs from storage if not in memory
            all_job_ids = await self._storage.list_jobs()
            
            # Load jobs that aren't in memory
            for job_id in all_job_ids:
                if job_id not in self._jobs:
                    job = await self._storage.load_job(job_id)
                    if job:
                        self._jobs[job_id] = job
            
            # Sort by creation time (newest first)
            jobs = sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True
            )
            
            # Apply pagination
            start = offset
            end = offset + limit
            return jobs[start:end]
            
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job and its data"""
        async with self._lock:
            try:
                # Stop job if running
                if job_id in self._jobs and self._jobs[job_id].status == JobStatus.RUNNING.value:
                    await self.stop_job(job_id)
                
                # Delete from storage
                await self._storage.delete_job(job_id)
                
                # Remove from memory
                if job_id in self._jobs:
                    del self._jobs[job_id]
                
                logger.info(f"Deleted crawl job {job_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to delete job {job_id}: {e}")
                return False
    
    async def get_job_stats(self, job_id: str) -> Optional[dict]:
        """Get detailed statistics for a job"""
        job = await self.get_job(job_id)
        if not job:
            return None
        
        try:
            # Get additional stats from storage
            pages = await self._storage.list_pages(job_id)
            
            return {
                'job_id': job_id,
                'status': job.status,
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'finished_at': job.finished_at.isoformat() if job.finished_at else None,
                'pages_crawled': job.pages_crawled,
                'pages_found': job.pages_found,
                'pages_remaining': job.pages_remaining,
                'total_pages_stored': len(pages),
                'errors': job.errors,
                'params': job.params
            }
        except Exception as e:
            logger.error(f"Failed to get stats for job {job_id}: {e}")
            return None


# Global job manager instance
job_manager = JobManager()