import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
import logging

from playwright.async_api import Browser

from .models import CrawlParams
from .frontier import CrawlFrontier
from .scope import in_scope, should_follow_link, get_url_components, apply_default_excludes
from .robots import get_robots_checker
from .ratelimit import CrawlRateLimiter
from .storage import get_storage
from .normalizer import normalize_url
from .extract import (
    extract_page_content, 
    extract_page_links, 
    extract_links_from_html,
    fetch_and_check_content_type,
    download_asset,
    extract_assets_from_html
)
import settings

logger = logging.getLogger(__name__)


class CrawlWorker:
    """
    Individual crawler worker that processes URLs from the frontier.
    """
    
    def __init__(self, worker_id: int, job_id: str, params: CrawlParams, 
                 frontier: CrawlFrontier, rate_limiter: CrawlRateLimiter,
                 browser: Browser, semaphore: asyncio.Semaphore):
        """
        Initialize crawler worker.
        
        Args:
            worker_id: Unique worker identifier
            job_id: Crawl job ID
            params: Crawl parameters
            frontier: URL frontier
            rate_limiter: Rate limiter
            browser: Playwright browser
            semaphore: Concurrency semaphore
        """
        self.worker_id = worker_id
        self.job_id = job_id
        self.params = params
        self.frontier = frontier
        self.rate_limiter = rate_limiter
        self.browser = browser
        self.semaphore = semaphore
        
        # Get global instances
        self.storage = get_storage()
        self.robots_checker = get_robots_checker()
        
        # Worker state
        self.is_running = False
        self.should_stop = False
        
        # Get seed URL components for scope checking
        self.seed_components = get_url_components(str(params.url))
        
        logger.debug(f"Initialized crawler worker {worker_id} for job {job_id}")
    
    async def run(self):
        """Run the crawler worker main loop."""
        self.is_running = True
        logger.info(f"Worker {self.worker_id} starting for job {self.job_id}")
        
        try:
            while not self.should_stop and self.is_running:
                # Get next URL from frontier
                url_depth = await self.frontier.dequeue()
                if url_depth is None:
                    # No more URLs or cancelled
                    break
                
                url, depth = url_depth
                
                try:
                    await self._process_url(url, depth)
                except Exception as e:
                    logger.error(f"Worker {self.worker_id} error processing {url}: {e}")
                    self.frontier.mark_failure(url, str(e))
                    self.storage.append_log(self.job_id, f"Worker {self.worker_id} failed to process {url}: {e}")
        
        except asyncio.CancelledError:
            logger.info(f"Worker {self.worker_id} cancelled")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} unexpected error: {e}")
        finally:
            self.is_running = False
            logger.info(f"Worker {self.worker_id} stopped")
    
    def stop(self):
        """Signal worker to stop."""
        self.should_stop = True
        logger.debug(f"Worker {self.worker_id} stop requested")
    
    async def _process_url(self, url: str, depth: int):
        """Process a single URL."""
        logger.debug(f"Worker {self.worker_id} processing {url} at depth {depth}")
        
        # Check robots.txt if enabled
        if self.params.respect_robots:
            if not await self.robots_checker.can_fetch(url):
                self.frontier.mark_skipped(url, "Robots.txt disallowed")
                self.storage.append_log(self.job_id, f"Skipped {url}: robots.txt disallowed")
                return
        
        # Rate limiting
        if not await self.rate_limiter.wait_for_permission(url, timeout=30.0):
            self.frontier.mark_failure(url, "Rate limit timeout")
            self.storage.append_log(self.job_id, f"Failed {url}: rate limit timeout")
            return
        
        # Check content type first
        content_type, is_allowed = await fetch_and_check_content_type(url, self.params.content_types)
        if not is_allowed:
            self.frontier.mark_skipped(url, f"Content type not allowed: {content_type}")
            self.storage.append_log(self.job_id, f"Skipped {url}: content type {content_type} not allowed")
            return
        
        # Extract page content
        extraction_settings = {
            'screenshot': self.params.screenshot,
            'full_content': self.params.full_content,
            'sleep_ms': self.params.sleep_ms,
            'wait_until': self.params.wait_until,
            'timeout_ms': self.params.timeout_ms,
            'device': self.params.device,
            'user_scripts': self.params.user_scripts,
            'user_scripts_timeout_ms': self.params.user_scripts_timeout_ms,
            'incognito': self.params.incognito,
            'proxy': self.params.proxy,
            'extra_http_headers': self.params.extra_http_headers,
        }
        
        article_result, success = await extract_page_content(
            url, extraction_settings, self.browser, self.semaphore
        )
        
        if not success:
            self.frontier.mark_failure(url, "Content extraction failed")
            self.storage.save_page(self.job_id, url, depth, {}, None, False, "Content extraction failed")
            return
        
        # Extract links if we haven't reached max depth
        new_links = []
        if depth < self.params.max_depth:
            try:
                # Try to extract links using the service first
                new_links = await extract_page_links(
                    url, extraction_settings, self.browser, self.semaphore
                )
                
                # If that fails, try extracting from the HTML content directly
                if not new_links and article_result.get('fullContent'):
                    new_links = await extract_links_from_html(article_result['fullContent'], url)
                    
            except Exception as e:
                logger.warning(f"Error extracting links from {url}: {e}")
        
        # Filter and enqueue new links
        for link_url in new_links:
            try:
                # Normalize the link
                normalized_link = normalize_url(link_url, ignore_query_patterns=self.params.ignore_query_params)
                
                # Check if in scope and should be followed
                if should_follow_link(normalized_link, self.params, self.seed_components):
                    await self.frontier.enqueue(normalized_link, depth + 1)
                    
            except Exception as e:
                logger.debug(f"Error processing link {link_url}: {e}")
        
        # Handle asset capture if enabled
        assets = {}
        if self.params.capture_assets and settings.CRAWL_ENABLE_ASSET_CAPTURE:
            assets = await self._capture_assets(url, article_result.get('fullContent', ''))
        
        # Save the page
        status_code = 200  # Assume success if we got content
        self.storage.save_page(self.job_id, url, depth, article_result, status_code, True)
        
        # Update page with assets if any were captured
        if assets:
            # This would require updating the saved page with asset information
            # For now, we'll log it
            self.storage.append_log(self.job_id, f"Captured {len(assets)} assets for {url}")
        
        self.frontier.mark_success(url)
        self.storage.append_log(self.job_id, f"Successfully processed {url} (depth: {depth}, links: {len(new_links)})")
    
    async def _capture_assets(self, page_url: str, html_content: str) -> Dict[str, str]:
        """Capture assets from a page."""
        assets = {}
        
        if not html_content:
            return assets
        
        try:
            # Extract asset URLs from HTML
            asset_urls = extract_assets_from_html(html_content, page_url, self.params.capture_asset_types)
            
            for asset_url, mime_type in asset_urls:
                try:
                    # Check if asset is in scope (same domain rules as pages)
                    if not should_follow_link(asset_url, self.params, self.seed_components):
                        continue
                    
                    # Download asset
                    asset_content = await download_asset(asset_url, self.params.max_asset_size_mb)
                    if asset_content:
                        # Save asset to storage
                        blob_path = self.storage.save_asset(self.job_id, asset_url, asset_content, mime_type)
                        assets[asset_url] = blob_path
                        
                except Exception as e:
                    logger.debug(f"Error capturing asset {asset_url}: {e}")
        
        except Exception as e:
            logger.warning(f"Error in asset capture for {page_url}: {e}")
        
        return assets


class SiteCrawler:
    """
    Main site crawler orchestrator that manages workers and job state.
    """
    
    def __init__(self):
        """Initialize site crawler with minimal setup."""
        self.job_id = None
        self.params = None
        self.browser = None
        self.semaphore = None
        
        # Components will be initialized later
        self.frontier = None
        self.rate_limiter = None
        self.storage = get_storage()
        self.robots_checker = get_robots_checker()
        
        # Crawler state
        self.workers: List[CrawlWorker] = []
        self.worker_tasks: List[asyncio.Task] = []
        self.is_running = False
        self.is_paused = False
        self.should_stop = False
        self.start_time: Optional[float] = None
        
        logger.debug("Initialized site crawler (components will be set up during crawl)")
    
    async def crawl_site(self, params: dict, job_id: str, progress_callback=None):
        """Main entry point for crawling a site with given parameters."""
        # Set up the crawler with the provided parameters
        self.job_id = job_id
        
        # Convert params dict to CrawlParams object
        from .models import CrawlParams
        if isinstance(params, dict):
            self.params = CrawlParams(**params)
        else:
            self.params = params
        
        # Initialize components now that we have params
        self.frontier = CrawlFrontier(ignore_query_patterns=self.params.ignore_query_params)
        self.rate_limiter = CrawlRateLimiter(
            default_domain_rate=self.params.rate_limit_per_domain_per_sec
        )
        
        # Set up browser and semaphore (these should be provided by the caller in a real implementation)
        # For now, we'll create them here
        from playwright.async_api import async_playwright
        import asyncio
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.semaphore = asyncio.Semaphore(self.params.concurrency)
        
        try:
            # Start the actual crawl
            await self.start()
            
            # Return crawl results
            stats = self.frontier.get_stats() if self.frontier else {}
            return {
                'total_pages': stats.get('visited', 0),
                'stats': stats
            }
        finally:
            # Clean up browser
            if self.browser:
                await self.browser.close()
                await playwright.stop()
    
    async def start(self):
        """Start the crawl."""
        if self.is_running:
            logger.warning(f"Crawler for job {self.job_id} is already running")
            return
        
        logger.info(f"Starting crawl for job {self.job_id}")
        self.start_time = time.time()
        self.is_running = True
        self.should_stop = False
        
        try:
            # Update status to running
            await self._update_status("running", started_at=datetime.utcnow().isoformat())
            
            # Seed the frontier
            await self._seed_frontier()
            
            # Start worker tasks
            await self._start_workers()
            
            # Monitor the crawl
            await self._monitor_crawl()
            
        except asyncio.CancelledError:
            logger.info(f"Crawl for job {self.job_id} cancelled")
            await self._update_status("canceled")
        except Exception as e:
            logger.error(f"Crawl for job {self.job_id} failed: {e}")
            await self._update_status("error", last_error=str(e))
        finally:
            await self._cleanup()
            await self._update_status_if_not_terminal()
    
    async def pause(self):
        """Pause the crawl."""
        if not self.is_running or self.is_paused:
            return
        
        logger.info(f"Pausing crawl for job {self.job_id}")
        self.is_paused = True
        
        # Stop workers
        for worker in self.workers:
            worker.stop()
        
        # Cancel worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        await self._update_status("paused")
    
    async def resume(self):
        """Resume the crawl."""
        if not self.is_running or not self.is_paused:
            return
        
        logger.info(f"Resuming crawl for job {self.job_id}")
        self.is_paused = False
        
        # Restart workers
        await self._start_workers()
        await self._update_status("running")
    
    async def stop(self):
        """Stop the crawl."""
        logger.info(f"Stopping crawl for job {self.job_id}")
        self.should_stop = True
        self.is_running = False
        
        # Stop workers
        for worker in self.workers:
            worker.stop()
        
        # Cancel worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        await self._update_status("canceled")
        await self._cleanup()
    
    async def _seed_frontier(self):
        """Seed the frontier with initial URLs."""
        # Add only the seed URL - let recursive discovery find other pages
        seed_url = str(self.params.url)
        await self.frontier.enqueue(seed_url, 0)
        self.storage.append_log(self.job_id, f"Starting crawl from {seed_url}")
        
        # Note: Sitemap URLs are disabled to ensure true recursive discovery
        # Instead of pre-loading sitemap URLs, we let the crawler discover links organically
    
    async def _start_workers(self):
        """Start crawler worker tasks."""
        self.workers.clear()
        self.worker_tasks.clear()
        
        for i in range(self.params.concurrency):
            worker = CrawlWorker(
                worker_id=i,
                job_id=self.job_id,
                params=self.params,
                frontier=self.frontier,
                rate_limiter=self.rate_limiter,
                browser=self.browser,
                semaphore=self.semaphore
            )
            
            task = asyncio.create_task(worker.run())
            
            self.workers.append(worker)
            self.worker_tasks.append(task)
        
        logger.info(f"Started {len(self.workers)} workers for job {self.job_id}")
    
    async def _monitor_crawl(self):
        """Monitor crawl progress and enforce limits."""
        while self.is_running and not self.should_stop:
            try:
                # Check time limit
                if self.start_time and time.time() - self.start_time > self.params.max_duration_sec:
                    logger.info(f"Crawl for job {self.job_id} reached time limit")
                    break
                
                # Check page limit
                stats = self.frontier.get_stats()
                if stats['visited'] >= self.params.max_pages:
                    logger.info(f"Crawl for job {self.job_id} reached page limit")
                    break
                
                # Check if frontier is empty and all workers are idle
                if self.frontier.is_empty() and all(not worker.is_running for worker in self.workers):
                    logger.info(f"Crawl for job {self.job_id} completed - no more URLs")
                    break
                
                # Update status periodically
                await self._update_status_with_stats()
                
                # Pause if requested
                if self.is_paused:
                    await asyncio.sleep(1)
                    continue
                
                # Sleep before next check
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in crawl monitor for job {self.job_id}: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup(self):
        """Clean up resources."""
        # Wait for workers to finish
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.workers.clear()
        self.worker_tasks.clear()
        self.is_running = False
        
        logger.info(f"Cleaned up crawler for job {self.job_id}")
    
    async def _update_status(self, state: str, **kwargs):
        """Update job status."""
        try:
            job = self.storage.get_job(self.job_id)
            if job:
                # job.status is just a string, so update it directly
                job.status = state
                
                if 'started_at' in kwargs:
                    job.started_at = kwargs['started_at']
                
                if state in ['done', 'error', 'canceled']:
                    job.finished_at = datetime.utcnow().isoformat()
                
                if 'last_error' in kwargs:
                    job.error = kwargs['last_error']
                
                # Save the updated job
                await self.storage.save_job(job)
                
        except Exception as e:
            logger.error(f"Error updating status for job {self.job_id}: {e}")
    
    async def _update_status_with_stats(self):
        """Update status with current stats."""
        try:
            job = await self.storage.load_job(self.job_id)
            if job:
                # Update stats in the job
                stats = self.frontier.get_stats()
                job.pages_crawled = stats.get('visited', 0)
                job.pages_found = stats.get('enqueued', 0)
                job.pages_remaining = stats.get('queued', 0)
                
                # Save the updated job
                await self.storage.save_job(job)
                
        except Exception as e:
            logger.debug(f"Error updating stats for job {self.job_id}: {e}")
    
    async def _update_status_if_not_terminal(self):
        """Update status to done if not already in terminal state."""
        try:
            job = await self.storage.load_job(self.job_id)
            if job and job.status not in ['error', 'canceled']:
                await self._update_status("completed")
                
        except Exception as e:
            logger.error(f"Error finalizing status for job {self.job_id}: {e}")