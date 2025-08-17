import asyncio
import datetime
from typing import Optional

import tldextract
from playwright.async_api import Browser
from pydantic import BaseModel

from internal import util, cache
from internal.browser import (
    new_context,
    page_processing,
    get_screenshot,
)
from internal.errors import ArticleParsingError
from router.query_params import (
    CommonQueryParams,
    BrowserQueryParams,
    ProxyQueryParams,
    ReadabilityQueryParams,
)
from settings import READABILITY_SCRIPT, PARSER_SCRIPTS_DIR


class ArticleSettings(BaseModel):
    """Settings for article extraction"""
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
    max_elems_to_parse: int = 0
    nb_top_candidates: int = 5
    char_threshold: int = 500


class ArticleResult(BaseModel):
    """Result of article extraction"""
    byline: Optional[str] = None
    content: Optional[str] = None
    dir: Optional[str] = None
    excerpt: Optional[str] = None
    id: str
    url: str
    domain: str
    lang: Optional[str] = None
    length: Optional[int] = None
    date: str
    query: dict = {}
    meta: dict = {}
    resultUri: str = ""
    fullContent: Optional[str] = None
    screenshotUri: Optional[str] = None
    siteName: Optional[str] = None
    textContent: Optional[str] = None
    title: Optional[str] = None
    publishedTime: Optional[str] = None


async def extract_article(
    url: str,
    settings: ArticleSettings,
    browser: Browser,
    semaphore: asyncio.Semaphore,
    host_url: str = "",
    result_id: str = ""
) -> ArticleResult:
    """
    Extract article content from a URL.
    
    Args:
        url: The URL to extract article from
        settings: Article extraction settings
        browser: Playwright browser instance
        semaphore: Concurrency control semaphore
        host_url: Base host URL for result URIs
        result_id: Unique result ID for caching
        
    Returns:
        ArticleResult containing extracted content
        
    Raises:
        ArticleParsingError: If article extraction fails
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
    
    readability_params = ReadabilityQueryParams(
        max_elems_to_parse=settings.max_elems_to_parse,
        nb_top_candidates=settings.nb_top_candidates,
        char_threshold=settings.char_threshold,
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
                init_scripts=[READABILITY_SCRIPT],
            )
            page_content = await page.content()
            screenshot = await get_screenshot(page) if settings.screenshot else None
            page_url = page.url

            # evaluating JavaScript: parse DOM and extract article content
            parser_args = {
                # Readability options:
                'maxElemsToParse': readability_params.max_elems_to_parse,
                'nbTopCandidates': readability_params.nb_top_candidates,
                'charThreshold': readability_params.char_threshold,
            }
            with open(PARSER_SCRIPTS_DIR / 'article.js', encoding='utf-8') as f:
                article = await page.evaluate(f.read() % parser_args)

    if article is None:
        raise ArticleParsingError(page_url, "The page doesn't contain any articles.")

    # parser error: article is not extracted, result has 'err' field
    if 'err' in article:
        raise ArticleParsingError(page_url, article['err'])

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()  # ISO 8601 format
    domain = tldextract.extract(page_url).registered_domain

    # set common fields
    article['id'] = result_id or cache.make_key(url)
    article['url'] = page_url
    article['domain'] = domain
    article['date'] = now
    article['resultUri'] = f'{host_url}/result/{article["id"]}' if host_url else ''
    article['query'] = {}
    article['meta'] = util.social_meta_tags(page_content)

    if settings.full_content:
        article['fullContent'] = page_content
    if settings.screenshot:
        article['screenshotUri'] = f'{host_url}/screenshot/{article["id"]}' if host_url else ''

    if 'title' in article and 'content' in article:
        article['content'] = util.improve_content(
            title=article['title'],
            content=article['content'],
        )

    if 'textContent' in article:
        article['textContent'] = util.improve_text_content(article['textContent'])
        article['length'] = len(article['textContent']) - article['textContent'].count('\n')

    return ArticleResult(**article)