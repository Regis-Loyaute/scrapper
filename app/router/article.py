import asyncio
from typing import Annotated

from fastapi import APIRouter, Query, Depends
from fastapi.requests import Request
from pydantic import BaseModel
from playwright.async_api import Browser

from internal import cache
from services.article import extract_article, ArticleSettings
from .query_params import (
    URLParam,
    CommonQueryParams,
    BrowserQueryParams,
    ProxyQueryParams,
    ReadabilityQueryParams,
)
from server.auth import AuthRequired


router = APIRouter(prefix='/api/article', tags=['article'])


class Article(BaseModel):
    byline: Annotated[str | None, Query(description='author metadata')]
    content: Annotated[str | None, Query(description='HTML string of processed article content')]
    dir: Annotated[str | None, Query(description='content direction')]
    excerpt: Annotated[str | None, Query(description='article description, or short excerpt from the content')]
    id: Annotated[str, Query(description='unique result ID')]
    url: Annotated[str, Query(description='page URL after redirects, may not match the query URL')]
    domain: Annotated[str, Query(description="page's registered domain")]
    lang: Annotated[str | None, Query(description='content language')]
    length: Annotated[int | None, Query(description='length of extracted article, in characters')]
    date: Annotated[str, Query(description='date of extracted article in ISO 8601 format')]
    query: Annotated[dict, Query(description='request parameters')]
    meta: Annotated[dict, Query(description='social meta tags (open graph, twitter)')]
    resultUri: Annotated[str, Query(description='URL of the current result, the data here is always taken from cache')]
    fullContent: Annotated[str | None, Query(description='full HTML contents of the page')] = None
    screenshotUri: Annotated[str | None, Query(description='URL of the screenshot of the page')] = None
    siteName: Annotated[str | None, Query(description='name of the site')]
    textContent: Annotated[str | None, Query(description='text content of the article, with all the HTML tags removed')]
    title: Annotated[str | None, Query(description='article title')]
    publishedTime: Annotated[str | None, Query(description='article publication time')]


@router.get('', summary='Parse article from the given URL', response_model=Article)
async def parse_article(
    request: Request,
    url: Annotated[URLParam, Depends()],
    params: Annotated[CommonQueryParams, Depends()],
    browser_params: Annotated[BrowserQueryParams, Depends()],
    proxy_params: Annotated[ProxyQueryParams, Depends()],
    readability_params: Annotated[ReadabilityQueryParams, Depends()],
    _: AuthRequired,
) -> dict:
    """
    Parse article from the given URL.<br><br>
    The page from the URL should contain the text of the article that needs to be extracted.
    """
    from internal import util
    
    # split URL into parts: host with scheme, path with query, query params as a dict
    host_url, full_path, query_dict = util.split_url(request.url)

    # get cache data if exists
    r_id = cache.make_key(full_path)  # unique result ID
    if params.cache:
        data = cache.load_result(key=r_id)
        if data:
            return data

    browser: Browser = request.state.browser
    semaphore: asyncio.Semaphore = request.state.semaphore

    # Convert parameters to service settings
    settings = ArticleSettings(
        cache=params.cache,
        screenshot=params.screenshot,
        full_content=params.full_content,
        sleep_ms=browser_params.sleep,
        wait_until=browser_params.wait_until,
        timeout_ms=browser_params.timeout,
        device=browser_params.device,
        user_scripts=params.user_scripts or [],
        user_scripts_timeout_ms=params.user_scripts_timeout,
        incognito=browser_params.incognito,
        proxy=proxy_params.proxy_server,
        extra_http_headers=browser_params.extra_http_headers or {},
        max_elems_to_parse=readability_params.max_elems_to_parse,
        nb_top_candidates=readability_params.nb_top_candidates,
        char_threshold=readability_params.char_threshold,
    )

    # Extract article using service
    result = await extract_article(
        url=url.url,
        settings=settings,
        browser=browser,
        semaphore=semaphore,
        host_url=str(host_url),
        result_id=r_id
    )

    # Update with route-specific fields
    result_dict = result.model_dump()
    result_dict['query'] = query_dict

    # save result to disk (including screenshot handling from service)
    cache.dump_result(result_dict, key=r_id)
    return result_dict
