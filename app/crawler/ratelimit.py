import asyncio
import time
from typing import Dict, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    """
    
    def __init__(self, rate: float, capacity: Optional[int] = None):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens per second to add to bucket
            capacity: Maximum tokens in bucket (defaults to rate)
        """
        self.rate = rate
        self.capacity = capacity or max(1, int(rate))
        self.tokens = self.capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens from bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False if insufficient tokens
        """
        async with self._lock:
            now = time.time()
            
            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def wait_for_tokens(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Wait until tokens are available.
        
        Args:
            tokens: Number of tokens needed
            timeout: Maximum time to wait
            
        Returns:
            True if tokens acquired, False if timeout
        """
        start_time = time.time()
        
        while True:
            if await self.acquire(tokens):
                return True
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False
            
            # Wait a bit before trying again
            await asyncio.sleep(0.1)
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get estimated wait time for tokens.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Estimated wait time in seconds
        """
        if self.tokens >= tokens:
            return 0.0
        
        needed_tokens = tokens - self.tokens
        return needed_tokens / self.rate


class DomainRateLimiter:
    """
    Per-domain rate limiter using token buckets.
    """
    
    def __init__(self, default_rate: float = 1.0):
        """
        Initialize domain rate limiter.
        
        Args:
            default_rate: Default requests per second per domain
        """
        self.default_rate = default_rate
        self._buckets: Dict[str, TokenBucket] = {}
        self._domain_rates: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return "unknown"
    
    def set_domain_rate(self, domain: str, rate: float):
        """
        Set custom rate limit for a specific domain.
        
        Args:
            domain: Domain name
            rate: Requests per second for this domain
        """
        domain = domain.lower()
        self._domain_rates[domain] = rate
        
        # Update existing bucket if it exists
        if domain in self._buckets:
            self._buckets[domain].rate = rate
    
    async def acquire(self, url: str) -> bool:
        """
        Try to acquire permission to request URL.
        
        Args:
            url: URL to request
            
        Returns:
            True if permission granted, False if rate limited
        """
        domain = self._extract_domain(url)
        
        async with self._lock:
            if domain not in self._buckets:
                rate = self._domain_rates.get(domain, self.default_rate)
                self._buckets[domain] = TokenBucket(rate)
        
        bucket = self._buckets[domain]
        success = await bucket.acquire()
        
        if success:
            logger.debug(f"Rate limit acquired for {domain}")
        else:
            logger.debug(f"Rate limited for {domain}")
        
        return success
    
    async def wait_for_permission(self, url: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for permission to request URL.
        
        Args:
            url: URL to request
            timeout: Maximum time to wait
            
        Returns:
            True if permission granted, False if timeout
        """
        domain = self._extract_domain(url)
        
        async with self._lock:
            if domain not in self._buckets:
                rate = self._domain_rates.get(domain, self.default_rate)
                self._buckets[domain] = TokenBucket(rate)
        
        bucket = self._buckets[domain]
        success = await bucket.wait_for_tokens(timeout=timeout)
        
        if success:
            logger.debug(f"Rate limit permission granted for {domain}")
        else:
            logger.debug(f"Rate limit timeout for {domain}")
        
        return success
    
    def get_wait_time(self, url: str) -> float:
        """
        Get estimated wait time for URL.
        
        Args:
            url: URL to check
            
        Returns:
            Estimated wait time in seconds
        """
        domain = self._extract_domain(url)
        
        if domain not in self._buckets:
            return 0.0
        
        return self._buckets[domain].get_wait_time()
    
    def get_stats(self) -> Dict[str, Dict]:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with per-domain stats
        """
        stats = {}
        
        for domain, bucket in self._buckets.items():
            rate = self._domain_rates.get(domain, self.default_rate)
            stats[domain] = {
                'rate': rate,
                'tokens': bucket.tokens,
                'capacity': bucket.capacity,
                'wait_time': bucket.get_wait_time()
            }
        
        return stats
    
    def clear_domain(self, domain: str):
        """
        Clear rate limiter state for a domain.
        
        Args:
            domain: Domain to clear
        """
        domain = domain.lower()
        if domain in self._buckets:
            del self._buckets[domain]
        if domain in self._domain_rates:
            del self._domain_rates[domain]
    
    def clear_all(self):
        """Clear all rate limiter state."""
        self._buckets.clear()
        self._domain_rates.clear()


class GlobalRateLimiter:
    """
    Global rate limiter for overall crawl speed control.
    """
    
    def __init__(self, rate: float):
        """
        Initialize global rate limiter.
        
        Args:
            rate: Global requests per second
        """
        self.bucket = TokenBucket(rate)
    
    async def acquire(self) -> bool:
        """Try to acquire global rate limit permission."""
        return await self.bucket.acquire()
    
    async def wait_for_permission(self, timeout: Optional[float] = None) -> bool:
        """Wait for global rate limit permission."""
        return await self.bucket.wait_for_tokens(timeout=timeout)
    
    def get_wait_time(self) -> float:
        """Get estimated wait time."""
        return self.bucket.get_wait_time()
    
    def set_rate(self, rate: float):
        """Update the global rate."""
        self.bucket.rate = rate


class CrawlRateLimiter:
    """
    Combined rate limiter with both per-domain and global limits.
    """
    
    def __init__(self, global_rate: Optional[float] = None, default_domain_rate: float = 1.0):
        """
        Initialize combined rate limiter.
        
        Args:
            global_rate: Global requests per second (None for no global limit)
            default_domain_rate: Default per-domain requests per second
        """
        self.domain_limiter = DomainRateLimiter(default_domain_rate)
        self.global_limiter = GlobalRateLimiter(global_rate) if global_rate else None
    
    async def acquire(self, url: str) -> bool:
        """
        Try to acquire permission for URL under both global and domain limits.
        
        Args:
            url: URL to request
            
        Returns:
            True if permission granted under both limits
        """
        # Check global limit first (if enabled)
        if self.global_limiter:
            if not await self.global_limiter.acquire():
                return False
        
        # Check domain limit
        return await self.domain_limiter.acquire(url)
    
    async def wait_for_permission(self, url: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for permission under both global and domain limits.
        
        Args:
            url: URL to request
            timeout: Maximum time to wait
            
        Returns:
            True if permission granted, False if timeout
        """
        start_time = time.time()
        
        # Wait for global permission first (if enabled)
        if self.global_limiter:
            remaining_timeout = timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                remaining_timeout = max(0, timeout - elapsed)
            
            if not await self.global_limiter.wait_for_permission(remaining_timeout):
                return False
        
        # Wait for domain permission
        remaining_timeout = timeout
        if timeout is not None:
            elapsed = time.time() - start_time
            remaining_timeout = max(0, timeout - elapsed)
        
        return await self.domain_limiter.wait_for_permission(url, remaining_timeout)
    
    def set_domain_rate(self, domain: str, rate: float):
        """Set rate for specific domain."""
        self.domain_limiter.set_domain_rate(domain, rate)
    
    def set_global_rate(self, rate: Optional[float]):
        """Set global rate limit."""
        if rate is None:
            self.global_limiter = None
        elif self.global_limiter:
            self.global_limiter.set_rate(rate)
        else:
            self.global_limiter = GlobalRateLimiter(rate)
    
    def get_stats(self) -> Dict:
        """Get combined rate limiter statistics."""
        stats = {
            'domains': self.domain_limiter.get_stats()
        }
        
        if self.global_limiter:
            stats['global'] = {
                'rate': self.global_limiter.bucket.rate,
                'tokens': self.global_limiter.bucket.tokens,
                'capacity': self.global_limiter.bucket.capacity,
                'wait_time': self.global_limiter.get_wait_time()
            }
        
        return stats