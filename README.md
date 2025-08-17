# Scrapper

<div markdown="1">

[![Build](https://github.com/amerkurev/scrapper/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/amerkurev/scrapper/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/amerkurev/scrapper/badge.svg?branch=master)](https://coveralls.io/github/amerkurev/scrapper?branch=master)
[![Docker pulls](https://img.shields.io/docker/pulls/amerkurev/scrapper.svg)](https://hub.docker.com/r/amerkurev/scrapper)
[![License](https://img.shields.io/badge/license-mit-blue.svg)](https://github.com/amerkurev/scrapper/blob/master/LICENSE)
</div>

Scrapper is a comprehensive web scraping platform that offers both single-page article extraction and full website crawling capabilities. The application provides a powerful REST API and intuitive web interface for downloading, processing, and managing web content at scale.

## Quick start

### Single-Page Scraping
Start a Scrapper instance with:
```console
docker run -d -p 3000:3000 --name scrapper amerkurev/scrapper:latest
```

### Website Crawling (Recommended)
For crawling entire websites, use Docker Compose with volume mapping:
```console
# Create docker-compose.yml (see Configuration section)
docker-compose up -d
```

Scrapper will be available at http://localhost:3000/. For more details, see [Usage](#usage)

### Web Interface Overview
- **Home Page** (`/`) - Single-page scraping and crawl job creation
- **Jobs Dashboard** (`/jobs`) - Monitor and manage all crawl jobs  
- **Content Library** (`/library`) - Browse and search crawled content
- **Job Details** (`/job?id={job_id}`) - Detailed job monitoring and logs


## Demo
Watch a 30-second demo reel showcasing the web interface of Scrapper.

https://user-images.githubusercontent.com/28217522/225941167-633576fa-c9e2-4c63-b1fd-879be2d137fa.mp4


## Features

### Core Web Scraping
- **Built-in headless browser** - Integrates with [Playwright](https://github.com/microsoft/playwright) to handle JavaScript-heavy websites, cookie consent forms, and other interactive elements.
- **Read mode parsing** - Uses Mozilla's [Readability.js](https://github.com/mozilla/readability) library to extract article content similar to browser "Reader View" functionality.
- **News link extraction** - Identifies and extracts links to news articles from website main pages.

### Website Crawling Engine
- **Recursive site crawling** - Systematically discovers and processes multiple pages across entire websites
- **Domain-based organization** - Automatically organizes crawled content by domain with timestamped job folders
- **Intelligent scope control** - Configurable crawling scope (domain, host, path, or custom regex patterns)
- **Rate limiting** - Respectful crawling with configurable per-domain rate limits
- **Robots.txt compliance** - Optional robots.txt respect for ethical crawling
- **Real-time progress tracking** - Live monitoring of crawl progress with detailed statistics
- **Job management system** - Complete lifecycle management for crawl jobs (start, stop, monitor, delete)

### Web Interface & User Experience
- **Dual-mode interface** - Choose between single-page scraping or full website crawling
- **Real-time dashboard** - Live progress monitoring with auto-refreshing job status
- **Content library** - Browse and search crawled content through an intuitive web interface
- **Job details view** - Comprehensive job monitoring with configuration, logs, and page listings
- **Jobs management** - Central hub for managing all crawl jobs with filtering and sorting
- **Dark theme support** - Built with the [Pico](https://github.com/picocss/pico) CSS framework

### API & Integration
- **Comprehensive REST API** - Full API coverage for both single-page and crawling operations
- **Simple integration** - Straightforward API requiring minimal parameters
- **Structured data output** - JSON-formatted results with extracted content and metadata
- **Export capabilities** - Export crawled data in JSONL and ZIP formats

### Technical Capabilities
- **Result caching** - Caches parsing results to disk for faster retrieval
- **Page screenshots** - Captures visual representation of pages as seen by the parser
- **Session management** - Configurable incognito mode or persistent sessions
- **Proxy support** - Compatible with HTTP, SOCKS4, and SOCKS5 proxies
- **Advanced customization** - Control for HTTP headers, viewport settings, Readability parser parameters, and more
- **Concurrent processing** - Multi-threaded crawling with configurable concurrency limits
- **Error handling & resilience** - Robust error handling with retry mechanisms and detailed logging
- **Docker delivery** - Packaged as a Docker image for simple deployment
- **Open-source license** - Available under MIT license


## Usage

### Getting Scrapper
The Scrapper Docker image includes Playwright and all necessary browser dependencies, resulting in an image size of approximately 2 GB. Ensure sufficient disk space is available, particularly if storing screenshots.

To download the latest version:
```console
docker pull amerkurev/scrapper:latest
```

### Creating directories
Scrapper requires two directories:
1. `user_data`: Stores browser session data and caches parsing results
2. `user_scripts`: Contains custom JavaScript scripts that can be injected into pages

Scrapper runs under UID `1001` rather than root. Set appropriate permissions on mounted directories:

```console
mkdir -p user_data user_scripts
chown 1001:1001 user_data/ user_scripts/
ls -l
```

The output should show:
```
drwxr-xr-x 2 1001 1001 4096 Mar 17 23:23 user_data
drwxr-xr-x 2 1001 1001 4096 Mar 17 23:23 user_scripts
```

> **Important note for macOS users**
>
> If you're running Scrapper on macOS, **do not** set ownership to UID 1001:1001 for the directories. Simply create the folders and Scrapper will work with your current user permissions:
>
> ```console
> mkdir -p user_data user_scripts
> ```
>
> Setting `chown 1001:1001` on macOS will prevent Scrapper from writing to these directories!


### Managing Scrapper Cache
The Scrapper cache is stored in the `user_data/_res` directory. For automated cache management, configure periodic cleanup:

```console
find /path/to/user_data/_res -ctime +7 -delete
```

This example deletes cache files older than 7 days.

### Using Scrapper
After preparing directories, run Scrapper:
```console
docker run -d -p 3000:3000 -v $(pwd)/user_data:/home/pwuser/user_data -v $(pwd)/user_scripts:/home/pwuser/user_scripts --name scrapper amerkurev/scrapper:latest
```

Access the web interface at http://localhost:3000/

Monitor logs with:
```console
docker logs -f scrapper
```


## Configuration Options

Scrapper can be configured using environment variables. You can set these either directly when running the container or through an environment file passed with `--env-file=.env`.

### General Settings
| Environment Variable | Description | Default |
| ------------------------- | ------------------------------------------------------------------ | --------------------- |
| HOST | Interface address to bind the server to | 0.0.0.0 |
| PORT | Web interface port number | 3000 |
| LOG_LEVEL | Logging detail level (debug, info, warning, error, critical) | info |
| BASIC_HTPASSWD | Path to the htpasswd file for basic authentication | /.htpasswd |
| UVICORN_WORKERS | Number of web server worker processes | 2 |
| DEBUG | Enable debug mode | false |

### Browser Settings
| Environment Variable | Description | Default |
| ------------------------- | ------------------------------------------------------------------ | --------------------- |
| BROWSER_TYPE | Browser type to use (chromium, firefox, webkit) | chromium |
| BROWSER_CONTEXT_LIMIT | Maximum number of browser contexts (tabs) | 20 |
| SCREENSHOT_TYPE | Screenshot type (jpeg or png) | jpeg |
| SCREENSHOT_QUALITY | Screenshot quality (0-100) | 80 |

### Crawler Settings
| Environment Variable | Description | Default |
| ------------------------- | ------------------------------------------------------------------ | --------------------- |
| CRAWL_MAX_CONCURRENCY | Maximum number of concurrent crawling tasks | 4 |
| CRAWL_DEFAULT_RATE_PER_DOMAIN | Default rate limit per domain (requests per second) | 1.0 |
| CRAWL_HARD_PAGE_LIMIT | Hard limit on maximum pages per crawl job | 1000 |
| CRAWL_HARD_DURATION_SEC | Hard limit on maximum crawl duration in seconds | 3600 |
| CRAWL_ENABLE_ASSET_CAPTURE | Enable capturing of assets (images, CSS, JS) | true |

### Example .env file

```ini
LOG_LEVEL=info
BROWSER_TYPE=chromium
SCREENSHOT_TYPE=jpeg
SCREENSHOT_QUALITY=90
UVICORN_WORKERS=4
DEBUG=false

# Crawler settings
CRAWL_MAX_CONCURRENCY=6
CRAWL_DEFAULT_RATE_PER_DOMAIN=2.0
CRAWL_HARD_PAGE_LIMIT=5000
CRAWL_HARD_DURATION_SEC=7200
CRAWL_ENABLE_ASSET_CAPTURE=false
```

### Docker Compose Configuration (Recommended)

Create a `docker-compose.yml` file for easier deployment with volume mapping:

```yaml
version: '3.8'

services:
  scrapper:
    image: amerkurev/scrapper:latest
    container_name: scrapper
    ports:
      - "3000:3000"
    volumes:
      # Save crawled data to local directory
      - ./user_data:/home/pwuser/user_data
      - ./user_scripts:/home/pwuser/user_scripts
    environment:
      # General settings
      - HOST=0.0.0.0
      - PORT=3000
      - LOG_LEVEL=info
      - DEBUG=false
      
      # Browser settings
      - BROWSER_TYPE=chromium
      - BROWSER_CONTEXT_LIMIT=20
      - SCREENSHOT_TYPE=jpeg
      - SCREENSHOT_QUALITY=80
      
      # Crawler settings
      - CRAWL_MAX_CONCURRENCY=4
      - CRAWL_DEFAULT_RATE_PER_DOMAIN=1.0
      - CRAWL_HARD_PAGE_LIMIT=1000
      - CRAWL_HARD_DURATION_SEC=3600
      - CRAWL_ENABLE_ASSET_CAPTURE=true
      
      # Security
      - BASIC_HTPASSWD=/.htpasswd
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:3000/ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    mem_limit: 2g
    cpus: 1.0
```

Start with Docker Compose:
```bash
docker-compose up -d
```

Or use an environment file with Docker:
```bash
docker run -d --name scrapper --env-file=.env -v $(pwd)/user_data:/home/pwuser/user_data -v $(pwd)/user_scripts:/home/pwuser/user_scripts -p 3000:3000 amerkurev/scrapper:latest
```


## Basic Authentication

Scrapper supports HTTP basic authentication to secure access to the web interface. Follow these steps to enable it:

1. Create an htpasswd file with bcrypt-encrypted passwords:
```bash
htpasswd -cbB .htpasswd admin yourpassword
```

Add additional users with:
```bash
htpasswd -bB .htpasswd another_user anotherpassword
```

2. Mount the htpasswd file when running Scrapper:
```bash
docker run -d --name scrapper \
    -v $(pwd)/user_data:/home/pwuser/user_data \
    -v $(pwd)/user_scripts:/home/pwuser/user_scripts \
    -v $(pwd)/.htpasswd:/.htpasswd \
    -p 3000:3000 \
    amerkurev/scrapper:latest
```

3. If you want to use a custom path for the htpasswd file, specify it with the `BASIC_HTPASSWD` environment variable:
```bash
docker run -d --name scrapper \
    -v $(pwd)/user_data:/home/pwuser/user_data \
    -v $(pwd)/user_scripts:/home/pwuser/user_scripts \
    -v $(pwd)/custom/path/.htpasswd:/auth/.htpasswd \
    -e BASIC_HTPASSWD=/auth/.htpasswd \
    -p 3000:3000 \
    amerkurev/scrapper:latest
```

Authentication will be required for all requests to Scrapper once enabled.


## HTTPS Support
Scrapper supports HTTPS connections with SSL certificates for secure access to the web interface. Follow these steps to enable it:

1. Prepare your SSL certificate and key files:
```bash
# Example of generating a self-signed certificate (for testing only)
openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365 -subj '/CN=localhost'
```
2. Mount the SSL files when running Scrapper:
```bash
docker run -d --name scrapper \
    -v $(pwd)/user_data:/home/pwuser/user_data \
    -v $(pwd)/user_scripts:/home/pwuser/user_scripts \
    -v $(pwd)/cert.pem:/.ssl/cert.pem \
    -v $(pwd)/key.pem:/.ssl/key.pem \
    -p 3000:3000 \
    amerkurev/scrapper:latest
```

When SSL certificates are detected, Scrapper automatically enables HTTPS mode. You can then access the secure interface at https://localhost:3000/.

For production use, always use properly signed certificates from a trusted certificate authority.


## API Reference

Scrapper provides comprehensive REST APIs for both single-page extraction and website crawling operations.

### Crawler API

#### POST /api/crawl/
Start a new website crawl job.

**Request Body:**
```json
{
  "start_url": "https://example.com",
  "max_pages": 50,
  "max_duration": 3600,
  "scope": "domain",
  "rate_limit": 1.0,
  "respect_robots": true,
  "include_assets": false,
  "custom_patterns": []
}
```

**Parameters:**
| Parameter | Description | Default | Type |
| :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------- | :--- |
| `start_url` | Starting URL for the crawl | Required | string |
| `max_pages` | Maximum pages to crawl (1-5000) | 50 | integer |
| `max_duration` | Maximum crawl duration in seconds (60-43200) | 3600 | integer |
| `scope` | Crawl scope: 'domain', 'host', 'path', or regex pattern | domain | string |
| `rate_limit` | Requests per second per domain (0.1-10.0) | 1.0 | float |
| `respect_robots` | Respect robots.txt | true | boolean |
| `include_assets` | Include assets (images, CSS, JS) | false | boolean |
| `custom_patterns` | Custom URL patterns to include/exclude | [] | array |

**Response:**
```json
{
  "job_id": "abc123def456",
  "status": "running",
  "message": "Started crawling https://example.com/",
  "estimated_pages": null
}
```

#### GET /api/crawl/
List all crawl jobs with pagination and filtering.

**Parameters:**
| Parameter | Description | Default | Type |
| :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------- | :--- |
| `limit` | Maximum jobs to return (1-100) | 20 | integer |
| `offset` | Number of jobs to skip | 0 | integer |
| `status` | Filter by job status | null | string |

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "abc123def456",
      "status": "running",
      "created_at": "2024-01-01T12:00:00Z",
      "started_at": "2024-01-01T12:00:01Z",
      "finished_at": null,
      "pages_crawled": 25,
      "pages_found": 100,
      "pages_remaining": 75,
      "errors": [],
      "progress_percent": 25.0
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 20
}
```

#### GET /api/crawl/{job_id}
Get detailed status for a specific crawl job.

**Response:**
```json
{
  "job_id": "abc123def456",
  "status": "running",
  "created_at": "2024-01-01T12:00:00Z",
  "started_at": "2024-01-01T12:00:01Z",
  "finished_at": null,
  "pages_crawled": 25,
  "pages_found": 100,
  "pages_remaining": 75,
  "errors": [],
  "progress_percent": 25.0
}
```

#### POST /api/crawl/{job_id}/stop
Stop a running crawl job.

**Response:**
```json
{
  "message": "Job abc123def456 stopped successfully"
}
```

#### DELETE /api/crawl/{job_id}
Delete a crawl job and all its associated data.

**Response:**
```json
{
  "message": "Job abc123def456 deleted successfully"
}
```

#### GET /api/crawl/{job_id}/logs
Get logs for a specific crawl job.

**Response:**
```
[2024-01-01T12:00:01] Starting crawl from https://example.com/
[2024-01-01T12:00:03] Successfully processed https://example.com/ (depth: 0, links: 25)
[2024-01-01T12:00:05] Successfully processed https://example.com/page1 (depth: 1, links: 10)
```

#### GET /api/crawl/{job_id}/pages
List pages crawled by a specific job.

**Parameters:**
| Parameter | Description | Default | Type |
| :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------- | :--- |
| `limit` | Maximum pages to return (1-100) | 20 | integer |
| `offset` | Number of pages to skip | 0 | integer |

**Response:**
```json
{
  "job_id": "abc123def456",
  "pages": [
    {
      "url": "https://example.com/",
      "depth": 0,
      "status_code": 200,
      "ok": true,
      "length": 1500,
      "title": "Example Page",
      "reason_if_skipped": null
    }
  ],
  "total": 25,
  "offset": 0,
  "limit": 20
}
```

#### GET /api/crawl/{job_id}/stats
Get comprehensive statistics for a crawl job.

**Response:**
```json
{
  "job_id": "abc123def456",
  "status": "completed",
  "created_at": "2024-01-01T12:00:00Z",
  "started_at": "2024-01-01T12:00:01Z",
  "finished_at": "2024-01-01T12:15:30Z",
  "duration_seconds": 929.0,
  "pages_crawled": 50,
  "pages_found": 50,
  "pages_remaining": 0,
  "total_pages_stored": 50,
  "average_page_size": 2048,
  "crawl_rate": 3.2,
  "errors": [],
  "params": {
    "start_url": "https://example.com",
    "max_pages": 50,
    "scope": "domain"
  }
}
```

### Single-Page Extraction API

#### GET /api/article?url=...
The Scrapper API provides a straightforward interface accessible through a single endpoint:

```console
curl -X GET "localhost:3000/api/article?url=https://en.wikipedia.org/wiki/web_scraping"
```

Use the GET method on the `/api/article` endpoint with the required `url` parameter specifying the target webpage. Scrapper will load the page in a browser, extract the article text, and return it in JSON format.

All other parameters are optional with default values. The web interface provides a visual query builder to assist with parameter configuration.

### Request Parameters

#### Scrapper settings
| Parameter | Description | Default |
| :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------- |
| `url` | Page URL. The page should contain the text of the article that needs to be extracted. |   |
| `cache` | All scraping results are always saved to disk. This parameter determines whether to retrieve results from cache or execute a new request. When set to true, existing cached results will be returned if available. By default, cache reading is disabled, so each request is processed anew. | `false` |
| `full-content` | If this option is set to true, the result will have the full HTML contents of the page (`fullContent` field in the response). | `false` |
| `screenshot` | If this option is set to true, the result will have the link to the screenshot of the page (`screenshot` field in the response). Scrapper initially attempts to take a screenshot of the entire scrollable page. If it fails because the image is too large, it will only capture the currently visible viewport. | `false` |
| `user-scripts` | To use your JavaScript scripts on a webpage, put your script files into the `user_scripts` directory. Then, list the scripts you need in the `user-scripts` parameter, separating them with commas. These scripts will run after the page loads but before the article parser starts. This means you can use these scripts to do things like remove ad blocks or automatically click the cookie acceptance button. Keep in mind, script names cannot include commas, as they are used for separation.<br>For example, you might pass `remove-ads.js, click-cookie-accept-button.js`.<br>If you plan to run asynchronous long-running scripts, check `user-scripts-timeout` parameter. | |
| `user-scripts-timeout` | Waits for the given timeout in milliseconds after users scripts injection. For example if you want to navigate through page to specific content, set a longer period (higher value). The default value is 0, which means no sleep. | `0` |

#### Browser settings
| Parameter | Description | Default |
| :---------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------- |
| `incognito` | Allows creating `incognito` browser contexts. Incognito browser contexts don't write any browsing data to disk. | `true` |
| `timeout` | Maximum operation time to navigate to the page in milliseconds; defaults to 60000 (60 seconds). Pass 0 to disable the timeout. | `60000` |
| `wait-until` | When to consider navigation succeeded, defaults to `domcontentloaded`. Events can be either:<br/>`load` - consider operation to be finished when the `load` event is fired.<br/>`domcontentloaded` - consider operation to be finished when the DOMContentLoaded event is fired.<br/>`networkidle` - consider operation to be finished when there are no network connections for at least 500 ms.<br/>`commit` - consider operation to be finished when network response is received and the document started loading. | `domcontentloaded` |
| `sleep` | Waits for the given timeout in milliseconds before parsing the article, and after the page has loaded. In many cases, a sleep timeout is not necessary. However, for some websites, it can be quite useful. Other waiting mechanisms, such as waiting for selector visibility, are not currently supported. The default value is 0, which means no sleep. | `0` |
| `resource` | List of resource types allowed to be loaded on the page. All other resources will not be allowed, and their network requests will be aborted. **By default, all resource types are allowed.** The following resource types are supported: `document`, `stylesheet`, `image`, `media`, `font`, `script`, `texttrack`, `xhr`, `fetch`, `eventsource`, `websocket`, `manifest`, `other`. Example: `document,stylesheet,fetch`. |   |
| `viewport-width` | The viewport width in pixels. It's better to use the `device` parameter instead of specifying it explicitly. |   |
| `viewport-height` | The viewport height in pixels. It's better to use the `device` parameter instead of specifying it explicitly. |   |
| `screen-width` | The page width in pixels. Emulates consistent window screen size available inside web page via window.screen. Is only used when the viewport is set. |   |
| `screen-height` | The page height in pixels. |   |
| `device` | Simulates browser behavior for a specific device, such as user agent, screen size, viewport, and whether it has touch enabled.<br/>Individual parameters like `user-agent`, `viewport-width`, and `viewport-height` can also be used; in such cases, they will override the `device` settings.<br/>List of [available devices](https://github.com/amerkurev/scrapper/blob/master/app/internal/deviceDescriptorsSource.json). | `Desktop Chrome` |
| `scroll-down` | Scroll down the page by a specified number of pixels. This is particularly useful when dealing with lazy-loading pages (pages that are loaded only as you scroll down). This parameter is used in conjunction with the `sleep` parameter. Make sure to set a positive value for the `sleep` parameter, otherwise, the scroll function won't work. | `0` |
| `ignore-https-errors` | Whether to ignore HTTPS errors when sending network requests. The default setting is to ignore HTTPS errors. | `true` |
| `user-agent` | Specific user agent. It's better to use the `device` parameter instead of specifying it explicitly. |   |
| `locale` | Specify user locale, for example en-GB, de-DE, etc. Locale will affect navigator.language value, Accept-Language request header value as well as number and date formatting rules. |   |
| `timezone` | Changes the timezone of the context. See ICU's metaZones.txt for a list of supported timezone IDs. |   |
| `http-credentials` | Credentials for HTTP authentication (string containing username and password separated by a colon, e.g. `username:password`). |   |
| `extra-http-headers` | Contains additional HTTP headers to be sent with every request. Example: `X-API-Key:123456;X-Auth-Token:abcdef`. |   |

#### Network proxy settings
| Parameter | Description | Default |
| :------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------- |
| `proxy-server` | Proxy to be used for all requests. HTTP and SOCKS proxies are supported, for example http://myproxy.com:3128 or socks5://myproxy.com:3128. Short form myproxy.com:3128 is considered an HTTP proxy. | |
| `proxy-bypass` | Optional comma-separated domains to bypass proxy, for example `.com, chromium.org, .domain.com`. |   |
| `proxy-username` | Optional username to use if HTTP proxy requires authentication. |   |
| `proxy-password` | Optional password to use if HTTP proxy requires authentication. |   |

#### Readability settings
| Parameter | Description | Default |
| :------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------- |
| `max-elems-to-parse` | The maximum number of elements to parse. The default value is 0, which means no limit. | 0 |
| `nb-top-candidates` | The number of top candidates to consider when analysing how tight the competition is among candidates. | 5 |
| `char-threshold` | The number of characters an article must have in order to return a result. | 500 |

### Response fields
The response to the `/api/article` request returns a JSON object containing the following fields:

| Parameter | Description | Type |
| :---------------- | :-------------------------------------------------------------------- | :------------ |
| `byline` | author metadata | null or str |
| `content` | HTML string of processed article content | null or str |
| `dir` | content direction | null or str |
| `excerpt` | article description, or short excerpt from the content | null or str |
| `fullContent` | full HTML contents of the page | null or str |
| `id` | unique result ID | str |
| `url` | page URL after redirects, may not match the query URL | str |
| `domain` | page's registered domain | str |
| `lang` | content language | null or str |
| `length` | length of extracted article, in characters | null or int |
| `date` | date of extracted article in ISO 8601 format | str |
| `query` | request parameters | object |
| `meta` | social meta tags (open graph, twitter) | object |
| `resultUri` | URL of the current result, the data here is always taken from cache | str |
| `screenshotUri` | URL of the screenshot of the page | null or str |
| `siteName` | name of the site | null or str |
| `textContent` | text content of the article, with all the HTML tags removed | null or str |
| `title` | article title | null or str |
| `publishedTime` | article publication time | null or str |

### Error handling
Error responses follow this structure:
```json
{
  "detail": [
    {
      "type": "error_type",
      "msg": "some message"
    }
  ]
}
```
For detailed error information, consult the Docker container logs.

### GET /api/links?url=...
To collect news article links from website main pages:

```console
curl -X GET "localhost:3000/api/links?url=https://www.cnet.com/"
```

#### Link parser settings
| Parameter | Description | Default |
| :------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------- |
| `text-len-threshold` | The median (middle value) of the link text length in characters. The default value is 40 characters. Hyperlinks must adhere to this criterion to be included in the results. However, this criterion is not a strict threshold value, and some links may ignore it. | 40 |
| `words-threshold` | The median (middle value) of the number of words in the link text. The default value is 3 words. Hyperlinks must adhere to this criterion to be included in the results. However, this criterion is not a strict threshold value, and some links may ignore it. | 3 |

### Response fields
The response to the `/api/links` request returns a JSON object that contains fields, which are described in the table below.

| Parameter | Description | Type |
| :---------------- |:-------------------------------------------------------------------- | :--------- |
| `fullContent` | full HTML contents of the page | str |
| `id` | unique result ID | str |
| `url` | page URL after redirects, may not match the query URL | str |
| `domain` | page's registered domain | str |
| `date` | date when the links were collected in ISO 8601 format | str |
| `query` | request parameters | object |
| `meta` | social meta tags (open graph, twitter) | object |
| `resultUri` | URL of the current result, the data here is always taken from cache | str |
| `screenshotUri` | URL of the screenshot of the page | str |
| `links` | list of collected links | list |
| `title` | page title | str |

## Supported architectures

- linux/amd64
- linux/arm64

## Status
The project is under active development and may have breaking changes until `v1` is released. 
As of version `v0.17.0`, Scrapper is considered production-ready, with multiple installations running in production environments.

## License

[MIT](LICENSE)
