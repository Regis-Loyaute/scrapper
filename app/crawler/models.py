from pydantic import BaseModel, AnyHttpUrl, Field
from typing import List, Optional, Literal, Dict
from enum import Enum
from datetime import datetime


class CrawlParams(BaseModel):
    """Parameters for crawl job configuration"""
    url: AnyHttpUrl
    scope: Literal["domain", "host", "path_prefix", "custom"] = "domain"
    path_prefix: Optional[str] = None   # used if scope == "path_prefix"
    include: List[str] = []             # regex patterns (applied to absolute URL)
    exclude: List[str] = []
    max_depth: int = 3
    max_pages: int = 1000
    max_duration_sec: int = 3600
    concurrency: int = 4
    rate_limit_per_domain_per_sec: float = 1.0
    respect_robots: bool = True
    follow_nofollow: bool = False
    same_protocol_only: bool = True
    ignore_query_params: List[str] = ["utm_*", "fbclid"]
    content_types: List[str] = ["text/html"]
    capture_assets: bool = False
    capture_asset_types: List[str] = ["image/*", "application/pdf"]
    max_asset_size_mb: int = 20
    screenshot: bool = False
    full_content: bool = True
    sleep_ms: int = 0
    wait_until: Literal["load","domcontentloaded","networkidle","commit"] = "domcontentloaded"
    timeout_ms: int = 60000
    device: str = "Desktop Chrome"
    user_scripts: List[str] = []
    user_scripts_timeout_ms: int = 0
    incognito: bool = True
    proxy: Optional[str] = None
    extra_http_headers: Dict[str, str] = {}


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class CrawlStatusDetail(BaseModel):
    """Detailed status information for a crawl job"""
    state: Literal["queued","running","paused","done","error","canceled"]
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    elapsed_sec: float = 0
    stats: Dict[str,int] = {}  # queued, visited, ok, failed, skipped, enqueued
    last_error: Optional[str] = None


class CrawlJob(BaseModel):
    """A crawl job with status and metadata"""
    job_id: str
    params: dict
    status: str  # Store as string instead of enum
    created_at: str  # Store as ISO string
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    pages_crawled: int = 0
    pages_found: int = 0
    pages_remaining: int = 0
    errors: List[str] = []
    error: Optional[str] = None


class PageSummary(BaseModel):
    """Summary information about a crawled page"""
    url: str
    depth: int
    status_code: Optional[int] = None
    ok: bool = False
    length: Optional[int] = None
    title: Optional[str] = None
    reason_if_skipped: Optional[str] = None


# Duplicate CrawlJob class removed - using the one above


class JobSummary(BaseModel):
    """Summary of a crawl job for listing"""
    job_id: str
    url: str
    state: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    pages_count: int = 0
    stats: Dict[str, int] = {}


class CrawlRequest(BaseModel):
    """Request to create a new crawl job"""
    job_id: str
    status_url: str
    ui_url: str


class PageDetail(BaseModel):
    """Detailed page information including article content"""
    url: str
    depth: int
    status_code: Optional[int] = None
    ok: bool = False
    title: Optional[str] = None
    content: Optional[str] = None
    text_content: Optional[str] = None
    length: Optional[int] = None
    meta: Dict = {}
    screenshot_uri: Optional[str] = None
    full_content: Optional[str] = None
    assets: Dict[str, str] = {}  # original_url -> local_blob_path
    crawl_metadata: Dict = {}  # crawl-specific metadata


class ExportFormat(str):
    """Available export formats"""
    JSONL = "jsonl"
    ZIP = "zip"