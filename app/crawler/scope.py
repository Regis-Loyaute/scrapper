import re
from typing import Dict, Any
from urllib.parse import urlparse

from .models import CrawlParams
from .normalizer import get_url_components


def in_scope(url: str, params: CrawlParams, seed_components: Dict[str, Any]) -> bool:
    """
    Check if a URL is within the crawl scope based on configured rules.
    
    Args:
        url: URL to check
        params: Crawl parameters defining scope rules
        seed_components: Components of the seed URL for comparison
        
    Returns:
        True if URL is in scope, False otherwise
    """
    # Get URL components
    url_components = get_url_components(url)
    
    # Check protocol restriction
    if params.same_protocol_only:
        if url_components['scheme'] != seed_components['scheme']:
            return False
    
    # Check basic scope rules
    if params.scope == "domain":
        if url_components['domain'] != seed_components['domain']:
            return False
    elif params.scope == "host":
        if url_components['host'] != seed_components['host']:
            return False
    elif params.scope == "path_prefix":
        if url_components['host'] != seed_components['host']:
            return False
        if params.path_prefix and not url_components['path'].startswith(params.path_prefix):
            return False
    elif params.scope == "custom":
        # Custom scope uses only include/exclude patterns
        pass
    
    # Check include patterns (if any are specified, URL must match at least one)
    if params.include:
        matches_include = False
        for pattern in params.include:
            if re.search(pattern, url):
                matches_include = True
                break
        if not matches_include:
            return False
    
    # Check exclude patterns (if URL matches any, it's excluded)
    for pattern in params.exclude:
        if re.search(pattern, url):
            return False
    
    return True


def should_follow_link(url: str, params: CrawlParams, seed_components: Dict[str, Any], 
                      link_has_nofollow: bool = False) -> bool:
    """
    Determine if a link should be followed based on scope and nofollow rules.
    
    Args:
        url: URL to check
        params: Crawl parameters
        seed_components: Seed URL components
        link_has_nofollow: Whether the link has rel="nofollow"
        
    Returns:
        True if link should be followed
    """
    # Check nofollow rules
    if link_has_nofollow and not params.follow_nofollow:
        return False
    
    # Check if in scope
    return in_scope(url, params, seed_components)


def is_content_type_allowed(content_type: str, allowed_types: list) -> bool:
    """
    Check if content type is allowed based on configured patterns.
    
    Args:
        content_type: MIME type to check (e.g., "text/html; charset=utf-8")
        allowed_types: List of allowed patterns (supports wildcards)
        
    Returns:
        True if content type is allowed
    """
    if not content_type:
        return False
    
    # Extract main content type (remove charset and other parameters)
    main_type = content_type.split(';')[0].strip().lower()
    
    for allowed_pattern in allowed_types:
        allowed_pattern = allowed_pattern.lower().strip()
        
        # Support wildcard matching
        if '*' in allowed_pattern:
            # Convert glob pattern to regex
            regex_pattern = allowed_pattern.replace('*', '.*')
            if re.match(f'^{regex_pattern}$', main_type):
                return True
        else:
            # Exact match
            if main_type == allowed_pattern:
                return True
    
    return False


def is_asset_type_allowed(content_type: str, allowed_asset_types: list) -> bool:
    """
    Check if asset content type is allowed for capture.
    
    Args:
        content_type: MIME type to check
        allowed_asset_types: List of allowed asset patterns
        
    Returns:
        True if asset type should be captured
    """
    return is_content_type_allowed(content_type, allowed_asset_types)


def get_default_exclude_patterns() -> list:
    """
    Get default URL exclude patterns to avoid spider traps and irrelevant content.
    
    Returns:
        List of regex patterns for common excludes
    """
    return [
        r'\.(?:css|js|ico|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)$',  # Static assets
        r'/(?:wp-admin|admin|login|logout|register)/',  # Admin areas
        r'\?(?:.*&)?(?:print|share|email)=',  # Print/share versions
        r'\.(?:pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|tar|gz)$',  # Documents (unless specifically wanted)
        r'/(?:calendar|search|tag|category)/',  # Dynamic content that may cause loops
        r'\?(?:.*&)?(?:year|month|day)=\d+',  # Date-based pagination
        r'#',  # Fragment-only URLs
    ]


def apply_default_excludes(params: CrawlParams) -> CrawlParams:
    """
    Apply default exclude patterns if none are specified.
    
    Args:
        params: Original crawl parameters
        
    Returns:
        Updated parameters with default excludes added
    """
    if not params.exclude:
        # Create a copy with default excludes
        updated_params = params.model_copy()
        updated_params.exclude = get_default_exclude_patterns()
        return updated_params
    
    return params


def validate_scope_config(params: CrawlParams) -> list:
    """
    Validate scope configuration and return any errors.
    
    Args:
        params: Crawl parameters to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check path_prefix requirement
    if params.scope == "path_prefix" and not params.path_prefix:
        errors.append("path_prefix is required when scope is 'path_prefix'")
    
    # Validate regex patterns
    for i, pattern in enumerate(params.include):
        try:
            re.compile(pattern)
        except re.error as e:
            errors.append(f"Invalid include pattern {i}: {pattern} - {e}")
    
    for i, pattern in enumerate(params.exclude):
        try:
            re.compile(pattern)
        except re.error as e:
            errors.append(f"Invalid exclude pattern {i}: {pattern} - {e}")
    
    # Check custom scope requirements
    if params.scope == "custom" and not params.include and not params.exclude:
        errors.append("Custom scope requires at least one include or exclude pattern")
    
    return errors


def get_scope_description(params: CrawlParams, seed_url: str) -> str:
    """
    Generate human-readable description of crawl scope.
    
    Args:
        params: Crawl parameters
        seed_url: Seed URL for context
        
    Returns:
        Description string
    """
    seed_components = get_url_components(seed_url)
    
    if params.scope == "domain":
        desc = f"Domain: {seed_components['domain']}"
    elif params.scope == "host":
        desc = f"Host: {seed_components['host']}"
    elif params.scope == "path_prefix":
        desc = f"Host: {seed_components['host']}, Path prefix: {params.path_prefix or '/'}"
    else:  # custom
        desc = "Custom scope"
    
    if params.include:
        desc += f", Include patterns: {len(params.include)}"
    
    if params.exclude:
        desc += f", Exclude patterns: {len(params.exclude)}"
    
    if params.same_protocol_only:
        desc += f", Protocol: {seed_components['scheme']} only"
    
    return desc