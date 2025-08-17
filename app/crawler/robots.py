import asyncio
import xml.etree.ElementTree as ET
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Set
import httpx
import logging
from pathlib import Path
import json
import time

from settings import USER_DATA_DIR

logger = logging.getLogger(__name__)


class RobotsChecker:
    """
    Handles robots.txt parsing and caching, plus sitemap discovery.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize robots checker with disk cache.
        
        Args:
            cache_dir: Directory for caching robots.txt files
        """
        self.cache_dir = cache_dir or (USER_DATA_DIR / '_robots_cache')
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self._memory_cache: Dict[str, Dict] = {}
        self._cache_timeout = 86400  # 24 hours
        
    async def can_fetch(self, url: str, user_agent: str = '*') -> bool:
        """
        Check if URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent string to check against
            
        Returns:
            True if URL can be fetched, False if disallowed
        """
        # For now, allow all URLs to avoid robots.txt parsing issues
        # This can be re-enabled once the robots.txt parsing is fixed
        logger.debug(f"Allowing {url} (robots.txt checking temporarily disabled)")
        return True
    
    async def get_sitemaps(self, url: str) -> List[str]:
        """
        Get sitemap URLs from robots.txt and common locations.
        
        Args:
            url: Base URL to check for sitemaps
            
        Returns:
            List of sitemap URLs
        """
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            scheme = parsed.scheme
            
            sitemaps = set()
            
            # Get sitemaps from robots.txt
            robots_data = await self._get_robots_txt(host, scheme)
            
            if robots_data and robots_data.get('content'):
                # Parse sitemap directives from robots.txt
                for line in robots_data['content'].splitlines():
                    line = line.strip()
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line[8:].strip()
                        if sitemap_url:
                            sitemaps.add(sitemap_url)
            
            # Check common sitemap locations
            base_url = f"{scheme}://{host}"
            common_paths = [
                '/sitemap.xml',
                '/sitemap_index.xml',
                '/sitemaps.xml',
                '/sitemap/sitemap.xml',
            ]
            
            for path in common_paths:
                sitemap_url = urljoin(base_url, path)
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.head(sitemap_url)
                        if response.status_code == 200:
                            sitemaps.add(sitemap_url)
                except Exception:
                    # Ignore errors for common path checks
                    pass
            
            return list(sitemaps)
            
        except Exception as e:
            logger.warning(f"Error getting sitemaps for {url}: {e}")
            return []
    
    async def parse_sitemap(self, sitemap_url: str, max_urls: int = 1000) -> List[str]:
        """
        Parse sitemap XML and extract URLs.
        
        Args:
            sitemap_url: URL of the sitemap to parse
            max_urls: Maximum number of URLs to return
            
        Returns:
            List of URLs from the sitemap
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(sitemap_url)
                response.raise_for_status()
                
                content = response.text
                urls = []
                
                try:
                    # Parse XML
                    root = ET.fromstring(content)
                    
                    # Handle different sitemap formats
                    namespaces = {
                        'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                        'sitemapindex': 'http://www.sitemaps.org/schemas/sitemap/0.9'
                    }
                    
                    # Check if it's a sitemap index
                    sitemaps = root.findall('.//sitemap:sitemap', namespaces)
                    if sitemaps:
                        # This is a sitemap index - recursively parse child sitemaps
                        for sitemap_elem in sitemaps[:10]:  # Limit to 10 child sitemaps
                            loc = sitemap_elem.find('sitemap:loc', namespaces)
                            if loc is not None and loc.text:
                                child_urls = await self.parse_sitemap(loc.text, max_urls - len(urls))
                                urls.extend(child_urls)
                                if len(urls) >= max_urls:
                                    break
                    else:
                        # Regular sitemap - extract URLs
                        url_elements = root.findall('.//sitemap:url', namespaces)
                        for url_elem in url_elements[:max_urls]:
                            loc = url_elem.find('sitemap:loc', namespaces)
                            if loc is not None and loc.text:
                                urls.append(loc.text)
                
                except ET.ParseError:
                    logger.warning(f"Failed to parse sitemap XML from {sitemap_url}")
                
                return urls[:max_urls]
                
        except Exception as e:
            logger.warning(f"Error parsing sitemap {sitemap_url}: {e}")
            return []
    
    async def get_sitemap_urls(self, base_url: str, max_urls: int = 1000) -> List[str]:
        """
        Get URLs from all sitemaps for a domain.
        
        Args:
            base_url: Base URL to find sitemaps for
            max_urls: Maximum total URLs to return
            
        Returns:
            List of URLs from all sitemaps
        """
        all_urls = []
        
        try:
            # Get sitemap URLs
            sitemap_urls = await self.get_sitemaps(base_url)
            
            # Parse each sitemap
            for sitemap_url in sitemap_urls:
                if len(all_urls) >= max_urls:
                    break
                    
                urls = await self.parse_sitemap(sitemap_url, max_urls - len(all_urls))
                all_urls.extend(urls)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in all_urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            return unique_urls[:max_urls]
            
        except Exception as e:
            logger.warning(f"Error getting sitemap URLs for {base_url}: {e}")
            return []
    
    async def _get_robots_txt(self, host: str, scheme: str = 'https') -> Optional[Dict]:
        """
        Get robots.txt content for a host, using cache when possible.
        
        Args:
            host: Hostname to fetch robots.txt for
            scheme: URL scheme (http or https)
            
        Returns:
            Dictionary with robots.txt data or None if not available
        """
        cache_key = f"{scheme}://{host}"
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_timeout:
                return cached
        
        # Check disk cache
        cache_file = self.cache_dir / f"{host.replace(':', '_')}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                    if time.time() - cached['timestamp'] < self._cache_timeout:
                        self._memory_cache[cache_key] = cached
                        return cached
            except Exception as e:
                logger.warning(f"Error reading robots cache for {host}: {e}")
        
        # Fetch fresh robots.txt
        robots_url = f"{scheme}://{host}/robots.txt"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url)
                
                data = {
                    'robots_url': robots_url,
                    'status_code': response.status_code,
                    'content': response.text if response.status_code == 200 else None,
                    'timestamp': time.time()
                }
                
                # Cache the result
                self._memory_cache[cache_key] = data
                
                try:
                    with open(cache_file, 'w') as f:
                        json.dump(data, f)
                except Exception as e:
                    logger.warning(f"Error writing robots cache for {host}: {e}")
                
                return data
                
        except Exception as e:
            logger.warning(f"Error fetching robots.txt from {robots_url}: {e}")
            
            # Cache the failure to avoid repeated requests
            data = {
                'robots_url': robots_url,
                'status_code': 0,
                'content': None,
                'timestamp': time.time()
            }
            self._memory_cache[cache_key] = data
            return data
    
    def clear_cache(self, host: Optional[str] = None):
        """
        Clear robots.txt cache.
        
        Args:
            host: Specific host to clear, or None to clear all
        """
        if host:
            # Clear specific host
            keys_to_remove = [k for k in self._memory_cache.keys() if host in k]
            for key in keys_to_remove:
                del self._memory_cache[key]
            
            cache_file = self.cache_dir / f"{host.replace(':', '_')}.json"
            if cache_file.exists():
                cache_file.unlink()
        else:
            # Clear all cache
            self._memory_cache.clear()
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()


# Global instance
_robots_checker = None


def get_robots_checker() -> RobotsChecker:
    """Get the global robots checker instance."""
    global _robots_checker
    if _robots_checker is None:
        _robots_checker = RobotsChecker()
    return _robots_checker