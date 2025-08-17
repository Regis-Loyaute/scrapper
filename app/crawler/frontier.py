import asyncio
from typing import Dict, Set, Optional, Tuple
import logging

from .normalizer import normalize_url

logger = logging.getLogger(__name__)


class CrawlFrontier:
    """
    Async frontier queue for managing URLs to crawl with deduplication.
    
    This class manages the queue of URLs to be crawled, ensuring no duplicates
    and providing stats about the crawl progress.
    """
    
    def __init__(self, ignore_query_patterns: Optional[list] = None):
        """
        Initialize the frontier.
        
        Args:
            ignore_query_patterns: Query parameters to ignore when normalizing URLs
        """
        self._queue = asyncio.Queue()
        self._visited: Set[str] = set()
        self._in_frontier: Set[str] = set()
        self._ignore_query_patterns = ignore_query_patterns or []
        
        # Statistics
        self._stats = {
            'queued': 0,
            'visited': 0,
            'ok': 0,
            'failed': 0,
            'skipped': 0,
            'enqueued': 0
        }
        
    async def enqueue(self, url: str, depth: int) -> bool:
        """
        Add a URL to the crawl frontier if not already seen.
        
        Args:
            url: URL to add
            depth: Crawl depth of this URL
            
        Returns:
            True if URL was added, False if already seen/queued
        """
        try:
            # Normalize URL for deduplication
            normalized_url = normalize_url(url, ignore_query_patterns=self._ignore_query_patterns)
            
            # Check if already visited or in frontier
            if normalized_url in self._visited or normalized_url in self._in_frontier:
                return False
            
            # Add to frontier
            self._in_frontier.add(normalized_url)
            await self._queue.put((normalized_url, depth))
            self._stats['enqueued'] += 1
            self._stats['queued'] += 1
            
            logger.debug(f"Enqueued URL: {normalized_url} (depth: {depth})")
            return True
            
        except Exception as e:
            logger.warning(f"Error enqueuing URL {url}: {e}")
            return False
    
    async def dequeue(self) -> Optional[Tuple[str, int]]:
        """
        Get the next URL to crawl from the frontier.
        
        Returns:
            Tuple of (url, depth) or None if frontier is empty
        """
        try:
            url, depth = await self._queue.get()
            
            # Move from frontier to visited
            self._in_frontier.discard(url)
            self._visited.add(url)
            
            self._stats['queued'] -= 1
            self._stats['visited'] += 1
            
            logger.debug(f"Dequeued URL: {url} (depth: {depth})")
            return url, depth
            
        except asyncio.CancelledError:
            return None
        except Exception as e:
            logger.warning(f"Error dequeuing URL: {e}")
            return None
    
    def mark_success(self, url: str):
        """Mark a URL as successfully processed."""
        normalized_url = normalize_url(url, ignore_query_patterns=self._ignore_query_patterns)
        if normalized_url in self._visited:
            self._stats['ok'] += 1
    
    def mark_failure(self, url: str, reason: str = ""):
        """Mark a URL as failed to process."""
        normalized_url = normalize_url(url, ignore_query_patterns=self._ignore_query_patterns)
        if normalized_url in self._visited:
            self._stats['failed'] += 1
            if reason:
                logger.debug(f"URL failed: {url} - {reason}")
    
    def mark_skipped(self, url: str, reason: str = ""):
        """Mark a URL as skipped."""
        self._stats['skipped'] += 1
        if reason:
            logger.debug(f"URL skipped: {url} - {reason}")
    
    def is_visited(self, url: str) -> bool:
        """Check if URL has already been visited."""
        normalized_url = normalize_url(url, ignore_query_patterns=self._ignore_query_patterns)
        return normalized_url in self._visited
    
    def is_in_frontier(self, url: str) -> bool:
        """Check if URL is currently in the frontier queue."""
        normalized_url = normalize_url(url, ignore_query_patterns=self._ignore_query_patterns)
        return normalized_url in self._in_frontier
    
    def is_seen(self, url: str) -> bool:
        """Check if URL has been seen before (visited or in frontier)."""
        return self.is_visited(url) or self.is_in_frontier(url)
    
    def size(self) -> int:
        """Get current size of the frontier queue."""
        return self._queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if frontier is empty."""
        return self._queue.empty()
    
    def get_stats(self) -> Dict[str, int]:
        """Get frontier statistics."""
        return self._stats.copy()
    
    def clear(self):
        """Clear the frontier and reset stats."""
        # Clear the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        # Clear sets
        self._visited.clear()
        self._in_frontier.clear()
        
        # Reset stats
        self._stats = {
            'queued': 0,
            'visited': 0,
            'ok': 0,
            'failed': 0,
            'skipped': 0,
            'enqueued': 0
        }
    
    async def wait_for_urls(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for URLs to become available in the frontier.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if URLs are available, False if timeout
        """
        try:
            if timeout is None:
                # Wait indefinitely
                await asyncio.wait_for(self._queue.join(), timeout=None)
                return True
            else:
                await asyncio.wait_for(self._queue.join(), timeout=timeout)
                return True
        except asyncio.TimeoutError:
            return False
    
    def add_bulk_urls(self, urls_with_depth: list) -> int:
        """
        Add multiple URLs to the frontier efficiently.
        
        Args:
            urls_with_depth: List of (url, depth) tuples
            
        Returns:
            Number of URLs actually added (excluding duplicates)
        """
        added_count = 0
        
        for url, depth in urls_with_depth:
            try:
                # Normalize URL for deduplication
                normalized_url = normalize_url(url, ignore_query_patterns=self._ignore_query_patterns)
                
                # Check if already seen
                if normalized_url in self._visited or normalized_url in self._in_frontier:
                    continue
                
                # Add to frontier
                self._in_frontier.add(normalized_url)
                self._queue.put_nowait((normalized_url, depth))
                self._stats['enqueued'] += 1
                self._stats['queued'] += 1
                added_count += 1
                
            except asyncio.QueueFull:
                logger.warning(f"Frontier queue full, cannot add URL: {url}")
                break
            except Exception as e:
                logger.warning(f"Error adding URL {url} to frontier: {e}")
        
        logger.debug(f"Added {added_count} URLs to frontier from bulk operation")
        return added_count
    
    def get_visited_urls(self) -> Set[str]:
        """Get copy of all visited URLs."""
        return self._visited.copy()
    
    def get_frontier_urls(self) -> Set[str]:
        """Get copy of all URLs currently in frontier."""
        return self._in_frontier.copy()
    
    def total_seen(self) -> int:
        """Get total number of unique URLs seen (visited + in frontier)."""
        return len(self._visited) + len(self._in_frontier)