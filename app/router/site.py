from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

import settings
from server.auth import AuthRequired


router = APIRouter(tags=['common'])
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)


@router.get('/favicon.ico', response_class=FileResponse, include_in_schema=False)
async def favicon():
    return FileResponse(settings.ICON_PATH, media_type='image/vnd.microsoft.icon')


@router.get('/', response_class=HTMLResponse, include_in_schema=False)
@router.get('/links', response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request, _: AuthRequired):
    for_example = (
        'cache=no',
        'full-content=no',
        'screenshot=no',
        'incognito=yes',
        'timeout=60000',
        'wait-until=domcontentloaded',
        'sleep=0',
        'device=Desktop Chrome',
    )
    context = {
        'request': request,
        'revision': settings.REVISION,
        'for_example': '&#10;'.join(for_example),
    }
    return templates.TemplateResponse(request=request, name='index.html', context=context)


@router.get('/jobs', response_class=HTMLResponse, include_in_schema=False)
async def jobs_page(request: Request, _: AuthRequired):
    """Display the jobs management page."""
    context = {
        'request': request,
        'revision': settings.REVISION,
    }
    return templates.TemplateResponse(request=request, name='jobs.html', context=context)


@router.get('/jobs/{job_id}', response_class=HTMLResponse, include_in_schema=False)
async def job_detail_page(request: Request, job_id: str, _: AuthRequired):
    """Display the detailed job view page."""
    context = {
        'request': request,
        'revision': settings.REVISION,
        'job_id': job_id,
    }
    return templates.TemplateResponse(request=request, name='job_detail.html', context=context)


@router.get('/job', response_class=HTMLResponse, include_in_schema=False)
async def job_details_page(request: Request, _: AuthRequired):
    """Display the job details page."""
    context = {
        'request': request,
        'revision': settings.REVISION,
    }
    return templates.TemplateResponse(request=request, name='job_details.html', context=context)
