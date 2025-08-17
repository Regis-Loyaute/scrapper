import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from typing import List, Optional
from bs4 import BeautifulSoup


def normalize_url(url: str, base: Optional[str] = None, ignore_query_patterns: List[str] = None) -> str:
    """
    Canonicalize URLs by:
    - Converting to lowercase host
    - Removing fragments
    - Dropping default ports (80 for HTTP, 443 for HTTPS)
    - Normalizing path (removing ./ and ../, trailing slash handling)
    - Removing ignored query parameters (support wildcards)
    - Sorting remaining query parameters
    
    Args:
        url: URL to normalize
        base: Base URL for resolving relative URLs
        ignore_query_patterns: List of query parameter patterns to ignore (supports * wildcards)
        
    Returns:
        Normalized URL string
    """
    if ignore_query_patterns is None:
        ignore_query_patterns = []
    
    # Handle relative URLs
    if base and not url.startswith(('http://', 'https://', '//')):
        from urllib.parse import urljoin
        url = urljoin(base, url)
    
    # Parse URL
    parsed = urlparse(url)
    
    # Normalize scheme (lowercase)
    scheme = parsed.scheme.lower() if parsed.scheme else 'http'
    
    # Normalize netloc (hostname to lowercase, remove default ports)
    netloc = parsed.netloc.lower()
    if ':' in netloc:
        host, port = netloc.rsplit(':', 1)
        try:
            port_int = int(port)
            # Remove default ports
            if (scheme == 'http' and port_int == 80) or (scheme == 'https' and port_int == 443):
                netloc = host
        except ValueError:
            pass  # Keep original if port is not a number
    
    # Normalize path
    path = normalize_path(parsed.path)
    
    # Filter and sort query parameters
    query = normalize_query(parsed.query, ignore_query_patterns)
    
    # Remove fragment
    fragment = ''
    
    # Reconstruct URL
    return urlunparse((scheme, netloc, path, parsed.params, query, fragment))


def normalize_path(path: str) -> str:
    """
    Normalize URL path by:
    - Resolving . and .. components
    - Ensuring it starts with /
    - Removing unnecessary trailing slashes (except for root)
    """
    if not path:
        return '/'
    
    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path
    
    # Split path into components
    components = path.split('/')
    
    # Resolve . and .. components
    resolved = []
    for component in components:
        if component == '' or component == '.':
            continue
        elif component == '..':
            if resolved:
                resolved.pop()
        else:
            resolved.append(component)
    
    # Reconstruct path
    result = '/' + '/'.join(resolved)
    
    # Keep trailing slash for directories if it was there originally
    # But remove it for files (simple heuristic: no extension = directory)
    if path.endswith('/') and result != '/' and not resolved[-1].count('.'):
        result += '/'
    
    return result


def normalize_query(query: str, ignore_patterns: List[str] = None) -> str:
    """
    Normalize query string by:
    - Removing parameters matching ignore patterns (supports * wildcards)
    - Sorting remaining parameters by key
    
    Args:
        query: Query string to normalize
        ignore_patterns: List of parameter patterns to ignore (supports * wildcards)
        
    Returns:
        Normalized query string
    """
    if not query:
        return ''
    
    if ignore_patterns is None:
        ignore_patterns = []
    
    # Parse query parameters
    params = parse_qs(query, keep_blank_values=True)
    
    # Filter out ignored parameters
    filtered_params = {}
    for key, values in params.items():
        should_ignore = False
        for pattern in ignore_patterns:
            if match_pattern(key, pattern):
                should_ignore = True
                break
        
        if not should_ignore:
            filtered_params[key] = values
    
    # Sort parameters and reconstruct query string
    if not filtered_params:
        return ''
    
    sorted_items = []
    for key in sorted(filtered_params.keys()):
        values = filtered_params[key]
        for value in sorted(values):
            sorted_items.append((key, value))
    
    return urlencode(sorted_items, doseq=False)


def match_pattern(text: str, pattern: str) -> bool:
    """
    Check if text matches pattern with * wildcard support.
    
    Args:
        text: Text to match
        pattern: Pattern with * wildcards
        
    Returns:
        True if text matches pattern
    """
    # Convert glob pattern to regex
    regex_pattern = pattern.replace('*', '.*')
    regex_pattern = f'^{regex_pattern}$'
    
    return bool(re.match(regex_pattern, text))


def extract_canonical_url(html_content: str, base_url: str) -> Optional[str]:
    """
    Extract canonical URL from HTML <link rel="canonical"> tag.
    
    Args:
        html_content: HTML content to parse
        base_url: Base URL for resolving relative canonical URLs
        
    Returns:
        Canonical URL if found, None otherwise
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        canonical_link = soup.find('link', rel='canonical')
        
        if canonical_link and canonical_link.get('href'):
            canonical_url = canonical_link['href']
            
            # Resolve relative URLs
            if not canonical_url.startswith(('http://', 'https://')):
                from urllib.parse import urljoin
                canonical_url = urljoin(base_url, canonical_url)
            
            return normalize_url(canonical_url)
    except Exception:
        # If parsing fails, return None
        pass
    
    return None


def urls_equivalent(url1: str, url2: str, ignore_query_patterns: List[str] = None) -> bool:
    """
    Check if two URLs are equivalent after normalization.
    
    Args:
        url1: First URL
        url2: Second URL
        ignore_query_patterns: Query parameters to ignore when comparing
        
    Returns:
        True if URLs are equivalent
    """
    norm1 = normalize_url(url1, ignore_query_patterns=ignore_query_patterns)
    norm2 = normalize_url(url2, ignore_query_patterns=ignore_query_patterns)
    return norm1 == norm2


def get_url_components(url: str) -> dict:
    """
    Extract URL components for scope checking.
    
    Args:
        url: URL to parse
        
    Returns:
        Dictionary with scheme, netloc, host, domain, path components
    """
    import tldextract
    
    parsed = urlparse(url)
    extracted = tldextract.extract(url)
    
    return {
        'scheme': parsed.scheme.lower(),
        'netloc': parsed.netloc.lower(),
        'host': extracted.fqdn.lower(),
        'domain': extracted.registered_domain.lower(),
        'subdomain': extracted.subdomain.lower(),
        'path': parsed.path,
        'full_url': url,
        'normalized_url': normalize_url(url)
    }