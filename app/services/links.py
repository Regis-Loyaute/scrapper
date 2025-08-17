import asyncio
import datetime
import hashlib
from collections import defaultdict
from operator import itemgetter
from statistics import median
from typing import Optional, Mapping, Sequence

import tldextract
from playwright.async_api import Browser
from pydantic import BaseModel

from internal import util, cache
from internal.browser import (
    new_context,
    page_processing,
    get_screenshot,
)
from internal.errors import LinksParsingError
from router.query_params import (
    CommonQueryParams,
    BrowserQueryParams,
    ProxyQueryParams,
    LinkParserQueryParams,
)
from settings import PARSER_SCRIPTS_DIR


class LinkSettings(BaseModel):
    """Settings for link extraction"""
    cache: bool = True
    screenshot: bool = False
    full_content: bool = False
    sleep_ms: int = 0
    wait_until: str = "domcontentloaded"
    timeout_ms: int = 60000
    device: str = "Desktop Chrome"
    user_scripts: list[str] = []
    user_scripts_timeout_ms: int = 0
    incognito: bool = True
    proxy: Optional[str] = None
    extra_http_headers: dict[str, str] = {}
    text_len_threshold: int = 40
    words_threshold: int = 3


class LinkExtractionResult(BaseModel):
    """Result of link extraction"""
    id: str
    url: str
    domain: str
    date: str
    query: dict = {}
    meta: dict = {}
    resultUri: str = ""
    fullContent: Optional[str] = None
    screenshotUri: Optional[str] = None
    title: Optional[str] = None
    links: list[dict] = []


async def extract_links(
    url: str,
    settings: LinkSettings,
    browser: Browser,
    semaphore: asyncio.Semaphore,
    host_url: str = "",
    result_id: str = ""
) -> LinkExtractionResult:
    """
    Extract links from a URL.
    
    Args:
        url: The URL to extract links from
        settings: Link extraction settings
        browser: Playwright browser instance
        semaphore: Concurrency control semaphore
        host_url: Base host URL for result URIs
        result_id: Unique result ID for caching
        
    Returns:
        LinkExtractionResult containing extracted links
        
    Raises:
        LinksParsingError: If link extraction fails
    """
    # Convert settings to internal format
    common_params = CommonQueryParams(
        cache=settings.cache,
        screenshot=settings.screenshot,
        full_content=settings.full_content,
        user_scripts=','.join(settings.user_scripts) if settings.user_scripts else None,
        user_scripts_timeout=settings.user_scripts_timeout_ms,
    )
    
    browser_params = BrowserQueryParams(
        incognito=settings.incognito,
        timeout=settings.timeout_ms,
        wait_until=settings.wait_until,
        sleep=settings.sleep_ms,
        device=settings.device,
        extra_http_headers=list(f"{k}:{v}" for k, v in settings.extra_http_headers.items()) if settings.extra_http_headers else None,
    )
    
    proxy_params = ProxyQueryParams(
        proxy_server=settings.proxy,
        proxy_bypass=None,
        proxy_username=None,
        proxy_password=None,
    )
    
    link_parser_params = LinkParserQueryParams(
        text_len_threshold=settings.text_len_threshold,
        words_threshold=settings.words_threshold,
    )

    # create a new browser context
    async with semaphore:
        async with new_context(browser, browser_params, proxy_params) as context:
            page = await context.new_page()
            await page_processing(
                page=page,
                url=url,
                params=common_params,
                browser_params=browser_params,
            )
            page_content = await page.content()
            screenshot = await get_screenshot(page) if settings.screenshot else None
            page_url = page.url
            title = await page.title()

            # evaluating JavaScript: parse DOM and extract links of articles
            parser_args = {}
            with open(PARSER_SCRIPTS_DIR / 'links.js', encoding='utf-8') as f:
                links = await page.evaluate(f.read() % parser_args)

    # parser error: links are not extracted, result has 'err' field
    if 'err' in links:
        raise LinksParsingError(page_url, links['err'])

    # filter links by domain
    domain = tldextract.extract(url).domain
    links = [x for x in links if allowed_domain(x['href'], domain)]

    links_dict = group_links(links)

    # get stat for groups of links and filter groups with
    # median length of text and words more than 40 and 3
    filtered_links = []
    for _, group in links_dict.items():
        stat = get_stat(
            group,
            text_len_threshold=link_parser_params.text_len_threshold,
            words_threshold=link_parser_params.words_threshold,
        )
        if stat['approved']:
            filtered_links.extend(group)

    # sort links by 'pos' field, to show links in the same order as they are on the page
    # ('pos' is position of link in DOM)
    filtered_links.sort(key=itemgetter('pos'))
    processed_links = list(map(util.improve_link, map(link_fields, filtered_links)))

    # set common fields
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result_domain = tldextract.extract(page_url).registered_domain

    result = LinkExtractionResult(
        id=result_id or cache.make_key(url),
        url=page_url,
        domain=result_domain,
        date=now,
        resultUri=f'{host_url}/result/{result_id or cache.make_key(url)}' if host_url else '',
        query={},
        links=processed_links,
        title=title,
        meta=util.social_meta_tags(page_content),
    )

    if settings.full_content:
        result.fullContent = page_content
    if settings.screenshot:
        result.screenshotUri = f'{host_url}/screenshot/{result.id}' if host_url else ''

    return result


def allowed_domain(href: str, domain: str) -> bool:
    """Check if the link is from the same domain"""
    if href.startswith('http'):
        # absolute link
        return tldextract.extract(href).domain == domain
    return True  # relative link


def group_links(links: Sequence[Mapping]) -> dict:
    """Group links by CSS selector, color, font, parent padding, parent margin and parent background color properties"""
    links_dict = defaultdict(list)
    for link in links:
        links_dict[make_key(link)].append(link)
    return links_dict


def make_key(link: Mapping) -> str:
    """Make key from CSS selector, color, font, parent padding, parent margin and parent background color properties"""
    props = (
        link['cssSel'],
        link['color'],
        link['font'],
        link['parentPadding'],
        link['parentMargin'],
        link['parentBgColor'],
    )
    s = '|'.join(props)
    return hashlib.sha1(s.encode()).hexdigest()[:7]  # because 7 chars is enough for uniqueness


def get_stat(links: Sequence[Mapping], text_len_threshold: int, words_threshold: int) -> dict:
    """Get stat for group of links"""
    median_text_len = median([len(x['text']) for x in links])
    median_words_count = median([len(x['words']) for x in links])
    approved = median_text_len > text_len_threshold and median_words_count > words_threshold
    return {
        'count': len(links),
        'median_text_len': median_text_len,
        'median_words_count': median_words_count,
        'approved': approved,
    }


def link_fields(link: Mapping) -> dict:
    """Extract relevant fields from link"""
    return {
        'url': link['url'],
        'text': link['text'],
    }