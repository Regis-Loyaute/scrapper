import asyncio
from typing import Annotated

from fastapi import APIRouter, Query, Depends
from fastapi.requests import Request
from pydantic import BaseModel
from playwright.async_api import Browser

from internal import cache
from services.links import extract_links, LinkSettings
from .query_params import (
    URLParam,
    CommonQueryParams,
    BrowserQueryParams,
    ProxyQueryParams,
    LinkParserQueryParams,
)
from server.auth import AuthRequired


router = APIRouter(prefix='/api/links', tags=['links'])


class Links(BaseModel):
    id: Annotated[str, Query(description='unique result ID')]
    url: Annotated[str, Query(description='page URL after redirects, may not match the query URL')]
    domain: Annotated[str, Query(description="page's registered domain")]
    date: Annotated[str, Query(description='date of extracted article in ISO 8601 format')]
    query: Annotated[dict, Query(description='request parameters')]
    meta: Annotated[dict, Query(description='social meta tags (open graph, twitter)')]
    resultUri: Annotated[str, Query(description='URL of the current result, the data here is always taken from cache')]
    fullContent: Annotated[str | None, Query(description='full HTML contents of the page')] = None
    screenshotUri: Annotated[str | None, Query(description='URL of the screenshot of the page')] = None
    title: Annotated[str | None, Query(description='page title')] = None
    links: Annotated[list[dict], Query(description='list of links')]


@router.get('', summary='Parse news links from the given URL', response_model=Links)
async def parser_links(
    request: Request,
    url: Annotated[URLParam, Depends()],
    params: Annotated[CommonQueryParams, Depends()],
    browser_params: Annotated[BrowserQueryParams, Depends()],
    proxy_params: Annotated[ProxyQueryParams, Depends()],
    link_parser_params: Annotated[LinkParserQueryParams, Depends()],
    _: AuthRequired,
) -> dict:
    """
    Parse news links from the given URL.<br><br>
    The page from the URL should contain hyperlinks to news articles. For example, this could be the main page of a website.
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
    settings = LinkSettings(
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
        text_len_threshold=link_parser_params.text_len_threshold,
        words_threshold=link_parser_params.words_threshold,
    )

    # Extract links using service
    result = await extract_links(
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

    # save result to disk
    cache.dump_result(result_dict, key=r_id)
    return result_dict
