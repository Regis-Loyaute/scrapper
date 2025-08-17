import asyncio
import httpx
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

from services.article import extract_article, ArticleSettings
from services.links import extract_links, LinkSettings
from .scope import is_content_type_allowed, is_asset_type_allowed
from .normalizer import normalize_url

logger = logging.getLogger(__name__)


async def extract_page_content(url: str, settings: Dict, browser, semaphore) -> Tuple[Dict, bool]:
    """
    Extract content from a page using the article extraction service.
    
    Args:
        url: URL to extract content from
        settings: Extraction settings
        browser: Playwright browser instance
        semaphore: Concurrency control semaphore
        
    Returns:
        Tuple of (extracted_content, success)
    """
    try:
        article_settings = ArticleSettings(
            cache=False,  # Don't use cache for crawler
            screenshot=settings.get('screenshot', False),
            full_content=settings.get('full_content', True),
            sleep_ms=settings.get('sleep_ms', 0),
            wait_until=settings.get('wait_until', 'domcontentloaded'),
            timeout_ms=settings.get('timeout_ms', 60000),
            device=settings.get('device', 'Desktop Chrome'),
            user_scripts=settings.get('user_scripts', []),
            user_scripts_timeout_ms=settings.get('user_scripts_timeout_ms', 0),
            incognito=settings.get('incognito', True),
            proxy=settings.get('proxy'),
            extra_http_headers=settings.get('extra_http_headers', {}),
            max_elems_to_parse=settings.get('max_elems_to_parse', 0),
            nb_top_candidates=settings.get('nb_top_candidates', 5),
            char_threshold=settings.get('char_threshold', 500),
        )
        
        result = await extract_article(
            url=url,
            settings=article_settings,
            browser=browser,
            semaphore=semaphore,
            host_url="",  # No host URL needed for crawler
            result_id=""  # No result ID needed for crawler
        )
        
        return result.model_dump(), True
        
    except Exception as e:
        logger.warning(f"Error extracting content from {url}: {e}")
        return {}, False


async def extract_page_links(url: str, settings: Dict, browser, semaphore) -> List[str]:
    """
    Extract links from a page using the links extraction service.
    
    Args:
        url: URL to extract links from
        settings: Extraction settings
        browser: Playwright browser instance
        semaphore: Concurrency control semaphore
        
    Returns:
        List of extracted links
    """
    try:
        link_settings = LinkSettings(
            cache=False,  # Don't use cache for crawler
            screenshot=False,
            full_content=False,
            sleep_ms=settings.get('sleep_ms', 0),
            wait_until=settings.get('wait_until', 'domcontentloaded'),
            timeout_ms=settings.get('timeout_ms', 60000),
            device=settings.get('device', 'Desktop Chrome'),
            user_scripts=settings.get('user_scripts', []),
            user_scripts_timeout_ms=settings.get('user_scripts_timeout_ms', 0),
            incognito=settings.get('incognito', True),
            proxy=settings.get('proxy'),
            extra_http_headers=settings.get('extra_http_headers', {}),
            text_len_threshold=settings.get('text_len_threshold', 40),
            words_threshold=settings.get('words_threshold', 3),
        )
        
        result = await extract_links(
            url=url,
            settings=link_settings,
            browser=browser,
            semaphore=semaphore,
            host_url="",  # No host URL needed for crawler
            result_id=""  # No result ID needed for crawler
        )
        
        # Extract URLs from the links
        links = []
        for link in result.links:
            link_url = link.get('url')
            if link_url:
                # Convert relative URLs to absolute
                absolute_url = urljoin(url, link_url)
                links.append(absolute_url)
        
        return links
        
    except Exception as e:
        logger.warning(f"Error extracting links from {url}: {e}")
        return []


async def extract_links_from_html(html_content: str, base_url: str) -> List[str]:
    """
    Extract links directly from HTML content using BeautifulSoup.
    
    Args:
        html_content: HTML content to parse
        base_url: Base URL for resolving relative links
        
    Returns:
        List of absolute URLs
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        # Find all anchor tags with href
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            
            # Skip empty hrefs, fragments, and javascript links
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(base_url, href)
            links.append(absolute_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        return unique_links
        
    except Exception as e:
        logger.warning(f"Error extracting links from HTML: {e}")
        return []


async def fetch_and_check_content_type(url: str, allowed_types: List[str], 
                                     timeout: float = 10.0) -> Tuple[Optional[str], bool]:
    """
    Fetch URL headers to check content type without downloading full content.
    
    Args:
        url: URL to check
        allowed_types: List of allowed content type patterns
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (content_type, is_allowed)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.head(url, follow_redirects=True)
            content_type = response.headers.get('content-type', '').lower()
            
            is_allowed = is_content_type_allowed(content_type, allowed_types)
            return content_type, is_allowed
            
    except Exception as e:
        logger.debug(f"Error checking content type for {url}: {e}")
        return None, False


async def download_asset(url: str, max_size_mb: int = 20, timeout: float = 30.0) -> Optional[bytes]:
    """
    Download binary asset with size limit.
    
    Args:
        url: Asset URL to download
        max_size_mb: Maximum size in megabytes
        timeout: Request timeout in seconds
        
    Returns:
        Asset bytes or None if failed/too large
    """
    try:
        max_size_bytes = max_size_mb * 1024 * 1024
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream('GET', url) as response:
                response.raise_for_status()
                
                # Check content length header
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > max_size_bytes:
                    logger.debug(f"Asset {url} too large: {content_length} bytes")
                    return None
                
                # Download with size limit
                content = b''
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    content += chunk
                    if len(content) > max_size_bytes:
                        logger.debug(f"Asset {url} exceeded size limit during download")
                        return None
                
                return content
                
    except Exception as e:
        logger.warning(f"Error downloading asset {url}: {e}")
        return None


def extract_assets_from_html(html_content: str, base_url: str, 
                           asset_types: List[str]) -> List[Tuple[str, str]]:
    """
    Extract asset URLs from HTML content.
    
    Args:
        html_content: HTML content to parse
        base_url: Base URL for resolving relative URLs
        asset_types: List of allowed asset MIME type patterns
        
    Returns:
        List of (absolute_url, mime_type_guess) tuples
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        assets = []
        
        # Image tags
        for img in soup.find_all('img', src=True):
            src = img['src'].strip()
            if src and not src.startswith('data:'):
                absolute_url = urljoin(base_url, src)
                
                # Guess MIME type from extension
                if any(absolute_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg']):
                    mime_type = 'image/jpeg'
                elif absolute_url.lower().endswith('.png'):
                    mime_type = 'image/png'
                elif absolute_url.lower().endswith('.gif'):
                    mime_type = 'image/gif'
                elif absolute_url.lower().endswith('.svg'):
                    mime_type = 'image/svg+xml'
                elif absolute_url.lower().endswith('.webp'):
                    mime_type = 'image/webp'
                else:
                    mime_type = 'image/*'
                
                if is_asset_type_allowed(mime_type, asset_types):
                    assets.append((absolute_url, mime_type))
        
        # PDF links
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if href and href.lower().endswith('.pdf'):
                absolute_url = urljoin(base_url, href)
                if is_asset_type_allowed('application/pdf', asset_types):
                    assets.append((absolute_url, 'application/pdf'))
        
        # Remove duplicates
        seen = set()
        unique_assets = []
        for asset_url, mime_type in assets:
            if asset_url not in seen:
                seen.add(asset_url)
                unique_assets.append((asset_url, mime_type))
        
        return unique_assets
        
    except Exception as e:
        logger.warning(f"Error extracting assets from HTML: {e}")
        return []


def has_nofollow_attribute(link_element) -> bool:
    """
    Check if a link has rel="nofollow" attribute.
    
    Args:
        link_element: BeautifulSoup link element
        
    Returns:
        True if link has nofollow
    """
    try:
        rel = link_element.get('rel', [])
        if isinstance(rel, str):
            rel = rel.split()
        return 'nofollow' in rel
    except Exception:
        return False


async def get_page_response_info(url: str, timeout: float = 10.0) -> Dict:
    """
    Get basic response information for a URL without downloading full content.
    
    Args:
        url: URL to check
        timeout: Request timeout
        
    Returns:
        Dictionary with status_code, content_type, content_length, final_url
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.head(url)
            
            return {
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type', ''),
                'content_length': response.headers.get('content-length'),
                'final_url': str(response.url),
                'headers': dict(response.headers)
            }
            
    except Exception as e:
        logger.debug(f"Error getting response info for {url}: {e}")
        return {
            'status_code': 0,
            'content_type': '',
            'content_length': None,
            'final_url': url,
            'headers': {},
            'error': str(e)
        }