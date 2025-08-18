from typing import Optional, List
from urllib.parse import urlparse
import json
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import settings
from server.auth import AuthRequired
from crawler.storage import get_storage


router = APIRouter(prefix='/library', tags=['library'])
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)

# Add datetime filter for templates
from datetime import datetime
def datetime_filter(timestamp):
    try:
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
        elif isinstance(timestamp, str):
            # Try to parse ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        return str(timestamp)
    except:
        return str(timestamp)

templates.env.filters['datetime'] = datetime_filter


@router.get('/', response_class=HTMLResponse, include_in_schema=False)
async def library_home(request: Request, _: AuthRequired):
    """Display the main library page with all domains."""
    storage = get_storage()
    
    try:
        # Get all domain directories
        domains = []
        if storage.base_dir.exists():
            for item in storage.base_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Count crawls for this domain
                    crawl_count = len([d for d in item.iterdir() if d.is_dir()])
                    if crawl_count > 0:
                        domains.append({
                            'name': item.name,
                            'crawl_count': crawl_count,
                            'last_modified': item.stat().st_mtime
                        })
        
        # Sort by last modified (most recent first)
        domains.sort(key=lambda x: x['last_modified'], reverse=True)
        
        context = {
            'request': request,
            'revision': settings.REVISION,
            'domains': domains
        }
        return templates.TemplateResponse(request=request, name='library/index.html', context=context)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading library: {str(e)}")


@router.get('/domain/{domain_name}', response_class=HTMLResponse, include_in_schema=False)
async def domain_crawls(request: Request, domain_name: str, _: AuthRequired):
    """Display all crawls for a specific domain."""
    storage = get_storage()
    
    try:
        domain_dir = storage.base_dir / domain_name
        if not domain_dir.exists():
            raise HTTPException(status_code=404, detail="Domain not found")
        
        # Get all crawls for this domain
        crawls = []
        for crawl_dir in domain_dir.iterdir():
            if crawl_dir.is_dir():
                manifest_file = crawl_dir / 'manifest.json'
                if manifest_file.exists():
                    try:
                        with open(manifest_file, 'r') as f:
                            manifest = json.load(f)
                        
                        # Count pages efficiently
                        pages_dir = crawl_dir / 'pages'
                        page_count = 0
                        if pages_dir.exists():
                            # More efficient counting without loading files into memory
                            page_count = sum(1 for _ in pages_dir.glob('*.json'))
                        
                        crawls.append({
                            'folder_name': crawl_dir.name,
                            'job_id': manifest.get('job_id', ''),
                            'created_at': manifest.get('created_at', ''),
                            'status': manifest.get('status', {}).get('state', 'unknown'),
                            'pages_count': page_count,
                            'url': manifest.get('params', {}).get('url', ''),
                            'size_mb': sum(f.stat().st_size for f in crawl_dir.rglob('*') if f.is_file()) / (1024 * 1024)
                        })
                    except Exception as e:
                        # Skip invalid crawls
                        continue
        
        # Sort by creation time (most recent first)
        crawls.sort(key=lambda x: x['created_at'], reverse=True)
        
        context = {
            'request': request,
            'revision': settings.REVISION,
            'domain_name': domain_name,
            'crawls': crawls
        }
        return templates.TemplateResponse(request=request, name='library/domain.html', context=context)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading domain crawls: {str(e)}")


@router.get('/crawl/{domain_name}/{folder_name}', response_class=HTMLResponse, include_in_schema=False)
async def crawl_details(request: Request, domain_name: str, folder_name: str, 
                       page: int = Query(1, ge=1), 
                       limit: int = Query(50, ge=1, le=200),
                       _: AuthRequired = None):
    """Display details and pages for a specific crawl."""
    storage = get_storage()
    
    try:
        crawl_dir = storage.base_dir / domain_name / folder_name
        if not crawl_dir.exists():
            raise HTTPException(status_code=404, detail="Crawl not found")
        
        # Load manifest
        manifest_file = crawl_dir / 'manifest.json'
        if not manifest_file.exists():
            raise HTTPException(status_code=404, detail="Crawl manifest not found")
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        # Get pages with pagination
        pages = []
        total_pages_count = 0
        pages_dir = crawl_dir / 'pages'
        
        if pages_dir.exists():
            # Get all page files and count them efficiently
            page_files = list(pages_dir.glob('*.json'))
            total_pages_count = len(page_files)
            
            # Sort page files by modification time (newest first) - avoid loading JSON for sorting
            page_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Apply pagination
            offset = (page - 1) * limit
            paginated_files = page_files[offset:offset + limit]
            
            # Load only the paginated page data
            for page_file in paginated_files:
                try:
                    with open(page_file, 'r') as f:
                        page_data = json.load(f)
                    
                    article = page_data.get('article_result', {})
                    pages.append({
                        'url': page_data.get('url', ''),
                        'title': article.get('title', 'Untitled'),
                        'depth': page_data.get('depth', 0),
                        'status_code': page_data.get('status_code'),
                        'ok': page_data.get('ok', False),
                        'length': article.get('length', 0),
                        'timestamp': page_data.get('timestamp', ''),
                        'file_id': page_file.stem
                    })
                except Exception:
                    continue
        
        # Calculate pagination info
        total_pagination_pages = (total_pages_count + limit - 1) // limit if total_pages_count > 0 else 1
        has_next = page < total_pagination_pages
        has_prev = page > 1
        
        context = {
            'request': request,
            'revision': settings.REVISION,
            'domain_name': domain_name,
            'folder_name': folder_name,
            'manifest': manifest,
            'pages': pages,
            'crawl_dir': crawl_dir,
            # Pagination info
            'current_page': page,
            'total_pages': total_pagination_pages,
            'has_next': has_next,
            'has_prev': has_prev,
            'total_pages_count': total_pages_count,
            'showing_count': len(pages),
            'page_limit': limit
        }
        return templates.TemplateResponse(request=request, name='library/crawl.html', context=context)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading crawl details: {str(e)}")


@router.get('/page/{domain_name}/{folder_name}/{file_id}', response_class=HTMLResponse, include_in_schema=False)
async def page_content(request: Request, domain_name: str, folder_name: str, file_id: str, _: AuthRequired):
    """Display the content of a specific crawled page."""
    storage = get_storage()
    
    try:
        page_file = storage.base_dir / domain_name / folder_name / 'pages' / f'{file_id}.json'
        if not page_file.exists():
            raise HTTPException(status_code=404, detail="Page not found")
        
        with open(page_file, 'r') as f:
            page_data = json.load(f)
        
        article = page_data.get('article_result', {})
        
        context = {
            'request': request,
            'revision': settings.REVISION,
            'domain_name': domain_name,
            'folder_name': folder_name,
            'page_data': page_data,
            'article': article,
            'url': page_data.get('url', ''),
            'title': article.get('title', 'Untitled'),
            'content': article.get('content', ''),
            'text_content': article.get('textContent', ''),
            'meta': article.get('meta', {}),
            'screenshot_uri': article.get('screenshotUri', ''),
            'full_content': article.get('fullContent', '')
        }
        return templates.TemplateResponse(request=request, name='library/page.html', context=context)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading page content: {str(e)}")


@router.get('/api/search', response_class=JSONResponse)
async def search_pages(
    q: str = Query(..., description="Search query"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    _: AuthRequired = None
):
    """Search through crawled page content."""
    storage = get_storage()
    
    try:
        results = []
        search_terms = q.lower().split()
        
        # Search through all domains or specific domain
        domains_to_search = [domain] if domain else [d.name for d in storage.base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        for domain_name in domains_to_search:
            domain_dir = storage.base_dir / domain_name
            if not domain_dir.exists():
                continue
                
            # Search through all crawls in this domain
            for crawl_dir in domain_dir.iterdir():
                if not crawl_dir.is_dir():
                    continue
                    
                pages_dir = crawl_dir / 'pages'
                if not pages_dir.exists():
                    continue
                
                # Search through all pages
                for page_file in pages_dir.glob('*.json'):
                    try:
                        with open(page_file, 'r') as f:
                            page_data = json.load(f)
                        
                        article = page_data.get('article_result', {})
                        title = article.get('title', '').lower()
                        content = article.get('textContent', '').lower()
                        url = page_data.get('url', '').lower()
                        
                        # Check if all search terms are found in title, content, or URL
                        text_to_search = f"{title} {content} {url}"
                        if all(term in text_to_search for term in search_terms):
                            results.append({
                                'domain': domain_name,
                                'folder': crawl_dir.name,
                                'file_id': page_file.stem,
                                'url': page_data.get('url', ''),
                                'title': article.get('title', 'Untitled'),
                                'snippet': article.get('textContent', '')[:200] + '...' if len(article.get('textContent', '')) > 200 else article.get('textContent', ''),
                                'timestamp': page_data.get('timestamp', '')
                            })
                    except Exception:
                        continue
        
        # Sort by relevance (title matches first, then content matches)
        def relevance_score(result):
            score = 0
            title_lower = result['title'].lower()
            for term in search_terms:
                if term in title_lower:
                    score += 10
                if term in result['snippet'].lower():
                    score += 1
            return score
        
        results.sort(key=relevance_score, reverse=True)
        
        return {'results': results[:50]}  # Limit to 50 results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")