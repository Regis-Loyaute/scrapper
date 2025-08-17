import json
import shutil
import hashlib
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlparse
import logging
import mimetypes

from .models import CrawlParams, PageSummary, CrawlJob, JobSummary, PageDetail
from settings import USER_DATA_DIR

logger = logging.getLogger(__name__)


class CrawlStorage:
    """
    Handles persistence of crawl jobs, pages, and assets to disk.
    
    Directory structure:
    user_data/crawls/{domain}/{timestamp_jobid}/
        manifest.json        # job params, status, stats, timestamps
        pages/               # one JSON per page
            <sha256>.json
        blobs/               # optional assets, referenced by sha256.ext
            <sha256>.<ext>
        logs.txt            # crawl logs
        exports/            # generated exports
            results.jsonl
            results.zip
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize crawl storage.
        
        Args:
            base_dir: Base directory for crawl storage (defaults to user_data/crawls)
        """
        self.base_dir = base_dir or (USER_DATA_DIR / 'crawls')
        self.base_dir.mkdir(exist_ok=True, parents=True)
        
        # Job registry for domain-based directory mapping
        self._job_registry_file = self.base_dir / '.job_registry.json'
        self._job_registry = self._load_job_registry()
    
    def new_job(self, params: CrawlParams) -> str:
        """
        Create a new crawl job with unique ID.
        
        Args:
            params: Crawl parameters
            
        Returns:
            Generated job ID
        """
        try:
            # Generate job ID based on URL and timestamp
            timestamp = datetime.utcnow().isoformat()
            job_id_input = f"{params.url}_{timestamp}"
            job_id = hashlib.sha256(job_id_input.encode()).hexdigest()[:16]
            
            logger.info(f"Creating new job {job_id} for URL: {params.url}")
            
            # Extract domain from URL
            parsed_url = urlparse(str(params.url))
            domain = parsed_url.netloc.lower()
            # Remove 'www.' prefix for cleaner folder names
            if domain.startswith('www.'):
                domain = domain[4:]
            
            logger.debug(f"Job {job_id}: extracted domain '{domain}'")
            
            # Create timestamp-based folder name for this crawl
            timestamp_str = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            folder_name = f"{timestamp_str}_{job_id[:8]}"
            
            # Create domain-based directory structure
            domain_dir = self.base_dir / domain
            domain_dir.mkdir(exist_ok=True, parents=True)
            
            job_dir = domain_dir / folder_name
            job_dir.mkdir(exist_ok=True)
            (job_dir / 'pages').mkdir(exist_ok=True)
            (job_dir / 'blobs').mkdir(exist_ok=True)
            (job_dir / 'exports').mkdir(exist_ok=True)
            
            logger.debug(f"Job {job_id}: created directories at {job_dir}")
            
            # Initialize manifest
            manifest = {
                'job_id': job_id,
                'created_at': timestamp,
                'params': params.model_dump(mode='json'),  # Ensure URL is serialized as string
                'status': {
                    'state': 'queued',
                    'started_at': None,
                    'finished_at': None,
                    'elapsed_sec': 0,
                    'stats': {'queued': 0, 'visited': 0, 'ok': 0, 'failed': 0, 'skipped': 0, 'enqueued': 0},
                    'last_error': None
                }
            }
            
            # Save manifest to the domain-based directory
            manifest_file = job_dir / 'manifest.json'
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logger.debug(f"Job {job_id}: saved manifest")
            
            # Register the job with its domain-based directory
            self._register_job(job_id, domain, timestamp_str)
            
            logger.info(f"Created new crawl job: {job_id} in domain '{domain}'")
            return job_id
            
        except Exception as e:
            logger.error(f"Error creating new job for {params.url}: {e}")
            raise
    
    def _get_job_dir(self, job_id: str) -> Path:
        """
        Get the job directory path, handling both new domain-based and legacy formats.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Path to job directory
        """
        # Reload job registry to ensure we have the latest data
        self._load_job_registry()
        
        # Check job registry first for domain-based directories
        if job_id in self._job_registry:
            job_info = self._job_registry[job_id]
            domain_dir = self.base_dir / job_info['domain']
            folder_name = f"{job_info['timestamp']}_{job_id[:8]}"
            domain_based_dir = domain_dir / folder_name
            if domain_based_dir.exists():
                return domain_based_dir
        
        # Fallback: try to find existing job directory in legacy format
        legacy_dir = self.base_dir / job_id
        if legacy_dir.exists():
            return legacy_dir
        
        # If not found, search in domain subdirectories to find the job
        for domain_dir in self.base_dir.iterdir():
            if domain_dir.is_dir() and not domain_dir.name.startswith('.'):
                for job_dir in domain_dir.iterdir():
                    if job_dir.is_dir() and job_id in job_dir.name:
                        # Update registry with discovered path
                        domain = domain_dir.name
                        timestamp_str = job_dir.name.split('_')[0] + '_' + job_dir.name.split('_')[1] + '_' + job_dir.name.split('_')[2]
                        self._register_job(job_id, domain, timestamp_str)
                        return job_dir
        
        # If still not found, return legacy path (might be for a new job)
        return legacy_dir
    
    def _get_job_dir_for_domain(self, job_id: str, domain: str, timestamp_str: str) -> Path:
        """
        Get the domain-based job directory path for a specific job.
        
        Args:
            job_id: Job identifier
            domain: Domain name
            timestamp_str: Timestamp string
            
        Returns:
            Path to domain-based job directory
        """
        # Clean domain name for folder
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Create domain-based directory structure
        domain_dir = self.base_dir / domain
        folder_name = f"{timestamp_str}_{job_id[:8]}"
        return domain_dir / folder_name
    
    def save_status(self, job_id: str, status) -> None:
        """
        Update job status in manifest.
        
        Args:
            job_id: Job identifier
            status: Current status
        """
        try:
            manifest = self._load_manifest(job_id)
            if manifest:
                manifest['status'] = status.model_dump()
                self._save_manifest(job_id, manifest)
        except Exception as e:
            logger.error(f"Error saving status for job {job_id}: {e}")
    
    async def save_job(self, job: 'CrawlJob') -> None:
        """
        Save or update a job in storage.
        
        Args:
            job: CrawlJob object to save
        """
        try:
            job_id = job.job_id
            
            # Register new jobs with domain-based directory structure
            if job_id not in self._job_registry and hasattr(job, 'params') and 'start_url' in job.params:
                from datetime import datetime
                parsed_url = urlparse(job.params['start_url'])
                domain = parsed_url.netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                # Create timestamp for new job
                created_time = datetime.fromisoformat(job.created_at.replace('Z', '+00:00')) if 'T' in job.created_at else datetime.utcnow()
                timestamp_str = created_time.strftime('%Y-%m-%d_%H-%M-%S')
                
                # Register the job
                self._register_job(job_id, domain, timestamp_str)
            
            # Create directory if it doesn't exist
            job_dir = self._get_job_dir(job_id)
            job_dir.mkdir(exist_ok=True)
            (job_dir / 'pages').mkdir(exist_ok=True)
            (job_dir / 'blobs').mkdir(exist_ok=True)
            (job_dir / 'exports').mkdir(exist_ok=True)
            
            # Convert job to manifest format
            manifest = {
                'job_id': job.job_id,
                'created_at': job.created_at,
                'params': job.params,
                'status': {
                    'state': job.status,
                    'started_at': job.started_at,
                    'finished_at': job.finished_at,
                    'elapsed_sec': 0,
                    'stats': {
                        'queued': 0, 
                        'visited': job.pages_crawled, 
                        'ok': job.pages_crawled, 
                        'failed': 0, 
                        'skipped': 0, 
                        'enqueued': job.pages_found
                    },
                    'last_error': job.error
                }
            }
            
            self._save_manifest(job_id, manifest)
            logger.debug(f"Saved job {job_id}")
            
        except Exception as e:
            logger.error(f"Error saving job {job.job_id}: {e}")
    
    def get_job(self, job_id: str) -> Optional[CrawlJob]:
        """
        Get complete job information.
        
        Args:
            job_id: Job identifier
            
        Returns:
            CrawlJob object or None if not found
        """
        try:
            manifest = self._load_manifest(job_id)
            if not manifest:
                return None
            
            pages_count = self._count_pages(job_id)
            
            return CrawlJob(
                job_id=job_id,
                params=manifest['params'],
                status=manifest['status']['state'],
                created_at=manifest['created_at'],
                started_at=manifest['status'].get('started_at'),
                finished_at=manifest['status'].get('finished_at'),
                pages_crawled=manifest['status']['stats'].get('visited', 0),
                pages_found=manifest['status']['stats'].get('enqueued', 0),
                pages_remaining=manifest['status']['stats'].get('queued', 0),
                errors=[],
                error=manifest['status'].get('last_error')
            )
        except Exception as e:
            logger.error(f"Error loading job {job_id}: {e}")
            return None
    
    async def load_job(self, job_id: str) -> Optional['CrawlJob']:
        """Async version of get_job for compatibility"""
        return self.get_job(job_id)
    
    async def list_jobs(self) -> List[str]:
        """List all job IDs"""
        try:
            if not self.base_dir.exists():
                return []
            
            job_ids = []
            for job_dir in self.base_dir.iterdir():
                if job_dir.is_dir() and (job_dir / 'manifest.json').exists():
                    job_ids.append(job_dir.name)
            
            return sorted(job_ids)
        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            return []
    
    async def delete_job(self, job_id: str) -> None:
        """Delete a job and all its data"""
        try:
            job_dir = self._get_job_dir(job_id)
            if job_dir.exists():
                import shutil
                shutil.rmtree(job_dir)
                logger.info(f"Deleted job {job_id}")
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {e}")
    
    async def list_pages(self, job_id: str) -> List[str]:
        """List all page files for a job"""
        try:
            pages_dir = self._get_job_dir(job_id) / 'pages'
            if not pages_dir.exists():
                return []
            
            pages = []
            for page_file in pages_dir.glob('*.json'):
                pages.append(page_file.stem)
            
            return sorted(pages)
        except Exception as e:
            logger.error(f"Error listing pages for job {job_id}: {e}")
            return []
    
    def list_jobs(self, limit: int = 100, offset: int = 0) -> List[JobSummary]:
        """
        List all crawl jobs with summary information.
        
        Args:
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of job summaries
        """
        jobs = []
        
        try:
            # Get all job directories from domain-based structure
            all_job_dirs = []
            
            # Iterate through domain directories
            for domain_dir in self.base_dir.iterdir():
                if domain_dir.is_dir() and not domain_dir.name.startswith('.'):
                    # Look for job directories within each domain
                    for job_dir in domain_dir.iterdir():
                        if job_dir.is_dir() and (job_dir / 'manifest.json').exists():
                            all_job_dirs.append(job_dir)
            
            # Sort by modification time (most recent first)
            all_job_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Apply pagination
            for job_dir in all_job_dirs[offset:offset + limit]:
                # Load manifest and extract job_id
                manifest = self._load_manifest_from_path(job_dir)
                
                if not manifest:
                    continue
                
                job_id = manifest.get('job_id', job_dir.name)
                params = manifest['params']
                status = manifest['status']
                pages_count = self._count_pages_from_path(job_dir)
                
                jobs.append(JobSummary(
                    job_id=job_id,
                    url=params.get('start_url', params.get('url', '')),
                    state=status['state'],
                    created_at=manifest['created_at'],
                    started_at=status.get('started_at'),
                    finished_at=status.get('finished_at'),
                    pages_count=pages_count,
                    stats=status.get('stats', {})
                ))
        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
        
        return jobs

    def _load_manifest_from_path(self, job_dir: Path) -> Optional[dict]:
        """Load manifest from a specific job directory path."""
        try:
            manifest_file = job_dir / 'manifest.json'
            if manifest_file.exists():
                with open(manifest_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading manifest from {job_dir}: {e}")
        return None

    def _count_pages_from_path(self, job_dir: Path) -> int:
        """Count pages in a specific job directory path."""
        try:
            pages_dir = job_dir / 'pages'
            if pages_dir.exists():
                return len(list(pages_dir.glob('*.json')))
        except Exception as e:
            logger.error(f"Error counting pages in {job_dir}: {e}")
        return 0
    
    def list_pages(self, job_id: str, offset: int = 0, limit: int = 50, 
                   status: Optional[str] = None) -> List[PageSummary]:
        """
        List pages for a job with pagination and filtering.
        
        Args:
            job_id: Job identifier
            offset: Number of pages to skip
            limit: Maximum pages to return
            status: Filter by status (ok/error/all)
            
        Returns:
            List of page summaries
        """
        pages = []
        
        try:
            pages_dir = self._get_job_dir(job_id) / 'pages'
            if not pages_dir.exists():
                return pages
            
            # Get all page files
            page_files = list(pages_dir.glob('*.json'))
            page_files.sort(key=lambda x: x.stat().st_mtime)  # Oldest first (crawl order)
            
            # Apply pagination and filtering
            count = 0
            skipped = 0
            
            for page_file in page_files:
                if skipped < offset:
                    skipped += 1
                    continue
                
                if count >= limit:
                    break
                
                try:
                    with open(page_file, 'r') as f:
                        page_data = json.load(f)
                    
                    # Apply status filter
                    page_ok = page_data.get('ok', False)
                    if status == 'ok' and not page_ok:
                        continue
                    elif status == 'error' and page_ok:
                        continue
                    
                    pages.append(PageSummary(
                        url=page_data.get('url', ''),
                        depth=page_data.get('depth', 0),
                        status_code=page_data.get('status_code'),
                        ok=page_ok,
                        length=page_data.get('length'),
                        title=page_data.get('title'),
                        reason_if_skipped=page_data.get('reason') if not page_ok else None
                    ))
                    
                    count += 1
                
                except Exception as e:
                    logger.warning(f"Error reading page file {page_file}: {e}")
        
        except Exception as e:
            logger.error(f"Error listing pages for job {job_id}: {e}")
        
        return pages
    
    def save_page(self, job_id: str, url: str, depth: int, article_result: Dict, 
                  status_code: Optional[int], ok: bool, reason: Optional[str] = None) -> str:
        """
        Save page data to storage.
        
        Args:
            job_id: Job identifier
            url: Page URL
            depth: Crawl depth
            article_result: Extracted article data
            status_code: HTTP status code
            ok: Whether page was successfully processed
            reason: Reason for failure (if any)
            
        Returns:
            Page ID (filename without extension)
        """
        try:
            # Generate page ID
            page_id = hashlib.sha256(url.encode()).hexdigest()
            
            # Prepare page data
            page_data = {
                'url': url,
                'depth': depth,
                'status_code': status_code,
                'ok': ok,
                'timestamp': datetime.utcnow().isoformat(),
                'article_result': article_result,
                'crawl_metadata': {
                    'job_id': job_id,
                    'depth': depth,
                    'crawled_at': datetime.utcnow().isoformat()
                }
            }
            
            if reason:
                page_data['reason'] = reason
            
            # Extract common fields for easier access
            if article_result:
                page_data['title'] = article_result.get('title')
                page_data['length'] = article_result.get('length')
            
            # Save to pages directory
            pages_dir = self._get_job_dir(job_id) / 'pages'
            page_file = pages_dir / f'{page_id}.json'
            
            with open(page_file, 'w') as f:
                json.dump(page_data, f, indent=2, ensure_ascii=False)
            
            return page_id
            
        except Exception as e:
            logger.error(f"Error saving page {url} for job {job_id}: {e}")
            raise
    
    def get_page(self, job_id: str, url: str) -> Optional[PageDetail]:
        """
        Get detailed page information by URL.
        
        Args:
            job_id: Job identifier
            url: Page URL
            
        Returns:
            PageDetail object or None if not found
        """
        try:
            page_id = hashlib.sha256(url.encode()).hexdigest()
            page_file = self._get_job_dir(job_id) / 'pages' / f'{page_id}.json'
            
            if not page_file.exists():
                return None
            
            with open(page_file, 'r') as f:
                page_data = json.load(f)
            
            article_result = page_data.get('article_result', {})
            
            return PageDetail(
                url=page_data.get('url', ''),
                depth=page_data.get('depth', 0),
                status_code=page_data.get('status_code'),
                ok=page_data.get('ok', False),
                title=article_result.get('title'),
                content=article_result.get('content'),
                text_content=article_result.get('textContent'),
                length=article_result.get('length'),
                meta=article_result.get('meta', {}),
                screenshot_uri=article_result.get('screenshotUri'),
                full_content=article_result.get('fullContent'),
                assets=page_data.get('assets', {}),
                crawl_metadata=page_data.get('crawl_metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Error getting page {url} for job {job_id}: {e}")
            return None
    
    def save_asset(self, job_id: str, url: str, content_bytes: bytes, mime_type: str) -> str:
        """
        Save binary asset to storage.
        
        Args:
            job_id: Job identifier
            url: Asset URL
            content_bytes: Asset content
            mime_type: MIME type
            
        Returns:
            Asset blob ID/path
        """
        try:
            # Generate blob ID
            blob_id = hashlib.sha256(content_bytes).hexdigest()
            
            # Determine file extension
            ext = mimetypes.guess_extension(mime_type) or ''
            if ext.startswith('.'):
                ext = ext[1:]  # Remove leading dot
            
            # Save to blobs directory
            blobs_dir = self._get_job_dir(job_id) / 'blobs'
            blob_file = blobs_dir / f'{blob_id}.{ext}' if ext else blobs_dir / blob_id
            
            with open(blob_file, 'wb') as f:
                f.write(content_bytes)
            
            logger.debug(f"Saved asset {url} as {blob_file.name}")
            return str(blob_file.name)
            
        except Exception as e:
            logger.error(f"Error saving asset {url} for job {job_id}: {e}")
            raise
    
    def export_jsonl(self, job_id: str) -> Path:
        """
        Export job results as JSONL file.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Path to generated JSONL file
        """
        try:
            export_file = self._get_job_dir(job_id) / 'exports' / 'results.jsonl'
            pages_dir = self._get_job_dir(job_id) / 'pages'
            
            with open(export_file, 'w') as f:
                for page_file in pages_dir.glob('*.json'):
                    try:
                        with open(page_file, 'r') as pf:
                            page_data = json.load(pf)
                        
                        # Create export record
                        export_record = {
                            'url': page_data.get('url'),
                            'depth': page_data.get('depth'),
                            'ok': page_data.get('ok'),
                            'status_code': page_data.get('status_code'),
                            'timestamp': page_data.get('timestamp'),
                            **page_data.get('article_result', {})
                        }
                        
                        f.write(json.dumps(export_record, ensure_ascii=False) + '\n')
                    
                    except Exception as e:
                        logger.warning(f"Error processing page file {page_file}: {e}")
            
            logger.info(f"Exported job {job_id} to JSONL: {export_file}")
            return export_file
            
        except Exception as e:
            logger.error(f"Error exporting job {job_id} to JSONL: {e}")
            raise
    
    def export_zip(self, job_id: str) -> Path:
        """
        Export job results as ZIP file including pages and assets.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Path to generated ZIP file
        """
        try:
            export_file = self._get_job_dir(job_id) / 'exports' / 'results.zip'
            job_dir = self._get_job_dir(job_id)
            
            with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add JSONL export
                jsonl_file = self.export_jsonl(job_id)
                zf.write(jsonl_file, 'results.jsonl')
                
                # Add all page JSON files
                pages_dir = job_dir / 'pages'
                if pages_dir.exists():
                    for page_file in pages_dir.glob('*.json'):
                        zf.write(page_file, f'pages/{page_file.name}')
                
                # Add all blob files
                blobs_dir = job_dir / 'blobs'
                if blobs_dir.exists():
                    for blob_file in blobs_dir.iterdir():
                        if blob_file.is_file():
                            zf.write(blob_file, f'blobs/{blob_file.name}')
                
                # Add manifest
                manifest_file = job_dir / 'manifest.json'
                if manifest_file.exists():
                    zf.write(manifest_file, 'manifest.json')
            
            logger.info(f"Exported job {job_id} to ZIP: {export_file}")
            return export_file
            
        except Exception as e:
            logger.error(f"Error exporting job {job_id} to ZIP: {e}")
            raise
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a crawl job and all associated data.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if successfully deleted
        """
        try:
            job_dir = self._get_job_dir(job_id)
            if job_dir.exists():
                shutil.rmtree(job_dir)
                logger.info(f"Deleted crawl job: {job_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {e}")
            return False
    
    def job_exists(self, job_id: str) -> bool:
        """Check if job exists."""
        return self._get_job_dir(job_id).exists()
    
    def append_log(self, job_id: str, message: str):
        """Append message to job log file."""
        try:
            log_file = self._get_job_dir(job_id) / 'logs.txt'
            timestamp = datetime.utcnow().isoformat()
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            logger.warning(f"Error writing to log for job {job_id}: {e}")
    
    def _load_manifest(self, job_id: str) -> Optional[Dict]:
        """Load job manifest from disk."""
        try:
            manifest_file = self._get_job_dir(job_id) / 'manifest.json'
            if manifest_file.exists():
                with open(manifest_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading manifest for job {job_id}: {e}")
        return None
    
    def _save_manifest(self, job_id: str, manifest: Dict):
        """Save job manifest to disk."""
        try:
            manifest_file = self._get_job_dir(job_id) / 'manifest.json'
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving manifest for job {job_id}: {e}")
            raise
    
    def _count_pages(self, job_id: str) -> int:
        """Count number of pages for a job."""
        try:
            pages_dir = self._get_job_dir(job_id) / 'pages'
            if pages_dir.exists():
                return len(list(pages_dir.glob('*.json')))
        except Exception:
            pass
        return 0
    
    def _load_job_registry(self) -> Dict[str, Dict]:
        """Load job registry from disk."""
        try:
            if self._job_registry_file.exists():
                with open(self._job_registry_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading job registry: {e}")
        return {}
    
    def _save_job_registry(self):
        """Save job registry to disk."""
        try:
            with open(self._job_registry_file, 'w') as f:
                json.dump(self._job_registry, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving job registry: {e}")
    
    def _register_job(self, job_id: str, domain: str, timestamp_str: str):
        """Register a job with its domain-based directory information."""
        # Clean domain name for folder
        if domain.startswith('www.'):
            domain = domain[4:]
        
        self._job_registry[job_id] = {
            'domain': domain,
            'timestamp': timestamp_str,
            'created_at': datetime.utcnow().isoformat()
        }
        self._save_job_registry()


# Global storage instance
_storage = None


def get_storage() -> CrawlStorage:
    """Get the global storage instance."""
    global _storage
    if _storage is None:
        _storage = CrawlStorage()
    return _storage