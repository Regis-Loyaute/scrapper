# Crawler API Reference

Scrapper provides a comprehensive REST API for managing website crawling operations. The crawler API allows you to start crawl jobs, monitor progress, and manage crawled content programmatically.

## Base URL

All crawler API endpoints are prefixed with `/api/crawl/`:

```
http://localhost:3000/api/crawl/
```

## Authentication

If basic authentication is enabled, include credentials in your requests:

```bash
curl -u username:password http://localhost:3000/api/crawl/
```

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/crawl/` | Start a new crawl job |
| GET | `/api/crawl/` | List all crawl jobs |
| GET | `/api/crawl/{job_id}` | Get job status |
| GET | `/api/crawl/{job_id}/stats` | Get detailed job statistics |
| POST | `/api/crawl/{job_id}/stop` | Stop a running job |
| DELETE | `/api/crawl/{job_id}` | Delete a job |
| GET | `/api/crawl/{job_id}/logs` | Get job logs |
| GET | `/api/crawl/{job_id}/pages` | List crawled pages |

## Job Management

### Start Crawl Job

**POST /api/crawl/**

Creates and starts a new crawl job.

#### Request Body

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

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_url` | string | Required | Starting URL for the crawl |
| `max_pages` | integer | 50 | Maximum pages to crawl (1-5000) |
| `max_duration` | integer | 3600 | Maximum duration in seconds (60-43200) |
| `scope` | string | "domain" | Crawl scope: 'domain', 'host', 'path', or regex |
| `rate_limit` | float | 1.0 | Requests per second per domain (0.1-10.0) |
| `respect_robots` | boolean | true | Whether to respect robots.txt |
| `include_assets` | boolean | false | Include assets (images, CSS, JS) |
| `custom_patterns` | array | [] | Custom URL patterns to include/exclude |

#### Scope Options

- **domain**: Crawl entire domain (e.g., `example.com` and `subdomain.example.com`)
- **host**: Crawl specific host only (e.g., `www.example.com` only)
- **path**: Crawl specific path and subdirectories
- **regex:pattern**: Custom regex pattern for URL matching

#### Response

```json
{
  "job_id": "abc123def456",
  "status": "running",
  "message": "Started crawling https://example.com/",
  "estimated_pages": null
}
```

#### Example

```bash
curl -X POST http://localhost:3000/api/crawl/ \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "max_pages": 100,
    "scope": "domain",
    "rate_limit": 2.0
  }'
```

### List Jobs

**GET /api/crawl/**

Returns a list of all crawl jobs with pagination support.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Maximum jobs to return (1-100) |
| `offset` | integer | 0 | Number of jobs to skip |
| `status` | string | null | Filter by status: 'running', 'completed', 'failed', 'stopped' |

#### Response

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

#### Example

```bash
# Get first 10 running jobs
curl "http://localhost:3000/api/crawl/?limit=10&status=running"
```

### Get Job Status

**GET /api/crawl/{job_id}**

Returns detailed status information for a specific crawl job.

#### Response

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

#### Job Status Values

- **pending**: Job created but not started
- **running**: Job actively crawling
- **completed**: Job finished successfully
- **failed**: Job encountered fatal error
- **stopped**: Job manually stopped

#### Example

```bash
curl http://localhost:3000/api/crawl/abc123def456
```

## Job Control

### Stop Job

**POST /api/crawl/{job_id}/stop**

Stops a running crawl job.

#### Response

```json
{
  "message": "Job abc123def456 stopped successfully"
}
```

#### Example

```bash
curl -X POST http://localhost:3000/api/crawl/abc123def456/stop
```

### Delete Job

**DELETE /api/crawl/{job_id}**

Deletes a crawl job and all its associated data permanently.

#### Response

```json
{
  "message": "Job abc123def456 deleted successfully"
}
```

#### Example

```bash
curl -X DELETE http://localhost:3000/api/crawl/abc123def456
```

## Job Data Access

### Get Job Statistics

**GET /api/crawl/{job_id}/stats**

Returns comprehensive statistics and performance metrics for a crawl job.

#### Response

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
    "scope": "domain",
    "rate_limit": 2.0
  }
}
```

### Get Job Logs

**GET /api/crawl/{job_id}/logs**

Returns the full log output for a crawl job.

#### Response

```
[2024-01-01T12:00:01] Starting crawl from https://example.com/
[2024-01-01T12:00:03] Successfully processed https://example.com/ (depth: 0, links: 25)
[2024-01-01T12:00:05] Successfully processed https://example.com/page1 (depth: 1, links: 10)
[2024-01-01T12:00:07] Successfully processed https://example.com/page2 (depth: 1, links: 8)
```

#### Example

```bash
curl http://localhost:3000/api/crawl/abc123def456/logs
```

### List Crawled Pages

**GET /api/crawl/{job_id}/pages**

Returns a list of pages that were crawled as part of a job.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Maximum pages to return (1-100) |
| `offset` | integer | 0 | Number of pages to skip |

#### Response

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
    },
    {
      "url": "https://example.com/about",
      "depth": 1,
      "status_code": 200,
      "ok": true,
      "length": 1200,
      "title": "About Us",
      "reason_if_skipped": null
    }
  ],
  "total": 25,
  "offset": 0,
  "limit": 20
}
```

#### Example

```bash
# Get next 50 pages starting from offset 20
curl "http://localhost:3000/api/crawl/abc123def456/pages?offset=20&limit=50"
```

## Error Handling

All API endpoints return standard HTTP status codes:

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request parameters
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

### Error Response Format

```json
{
  "detail": "Job not found"
}
```

### Common Error Scenarios

1. **Invalid job ID**: Returns 404 if job doesn't exist
2. **Invalid parameters**: Returns 400 with validation errors
3. **Job already stopped**: Returns appropriate error when trying to stop completed job
4. **Rate limit exceeded**: Server may return 429 if too many requests

## Data Storage Structure

Crawled data is organized in a domain-based directory structure:

```
user_data/crawls/
├── example.com/
│   ├── 2024-01-01_12-00-00_abc123de/
│   │   ├── manifest.json          # Job configuration and status
│   │   ├── logs.txt               # Crawl logs
│   │   ├── pages/                 # Extracted page content
│   │   │   ├── {hash1}.json
│   │   │   └── {hash2}.json
│   │   ├── blobs/                 # Assets (if enabled)
│   │   └── exports/               # Generated exports
│   └── 2024-01-01_13-00-00_def456gh/
└── another-site.com/
```

Each page JSON file contains:

```json
{
  "url": "https://example.com/page1",
  "depth": 1,
  "status_code": 200,
  "ok": true,
  "timestamp": "2024-01-01T12:00:03Z",
  "title": "Page Title",
  "length": 1500,
  "article_result": {
    "title": "Page Title",
    "content": "<article>...</article>",
    "textContent": "Plain text content...",
    "length": 1500,
    "meta": {...}
  },
  "crawl_metadata": {
    "job_id": "abc123def456",
    "depth": 1,
    "crawled_at": "2024-01-01T12:00:03Z"
  }
}
```

## Rate Limiting and Performance

### Rate Limiting

- Configurable per-domain rate limits (0.1-10.0 requests/second)
- Automatic throttling based on server response times
- Respectful crawling with configurable delays

### Performance Tuning

- **Concurrency**: Control parallel requests with `CRAWL_MAX_CONCURRENCY`
- **Rate limits**: Balance speed vs. server respect with `rate_limit` parameter
- **Scope control**: Limit crawl scope to reduce unnecessary requests
- **Page limits**: Set reasonable `max_pages` limits for large sites

### Best Practices

1. **Start small**: Begin with low page limits to test site compatibility
2. **Respect robots.txt**: Keep `respect_robots: true` for ethical crawling
3. **Monitor progress**: Use real-time monitoring to track crawl health
4. **Set reasonable rates**: Use 1-2 requests/second for most sites
5. **Clean up**: Delete completed jobs when data no longer needed

## SDK Examples

### Python Example

```python
import requests
import time

# Start a crawl job
response = requests.post("http://localhost:3000/api/crawl/", json={
    "start_url": "https://example.com",
    "max_pages": 100,
    "scope": "domain",
    "rate_limit": 1.5
})

job_id = response.json()["job_id"]
print(f"Started job: {job_id}")

# Monitor progress
while True:
    status = requests.get(f"http://localhost:3000/api/crawl/{job_id}")
    job_data = status.json()
    
    if job_data["status"] in ["completed", "failed", "stopped"]:
        print(f"Job finished with status: {job_data['status']}")
        break
    
    print(f"Progress: {job_data['pages_crawled']}/{job_data['pages_found']} pages")
    time.sleep(5)

# Get final results
pages = requests.get(f"http://localhost:3000/api/crawl/{job_id}/pages")
print(f"Crawled {len(pages.json()['pages'])} pages")
```

### JavaScript Example

```javascript
// Start a crawl job
const startCrawl = async (url, maxPages = 50) => {
  const response = await fetch('http://localhost:3000/api/crawl/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_url: url,
      max_pages: maxPages,
      scope: 'domain',
      rate_limit: 1.0
    })
  });
  
  const result = await response.json();
  return result.job_id;
};

// Monitor job progress
const monitorJob = async (jobId) => {
  const checkStatus = async () => {
    const response = await fetch(`http://localhost:3000/api/crawl/${jobId}`);
    return await response.json();
  };
  
  const status = await checkStatus();
  if (['completed', 'failed', 'stopped'].includes(status.status)) {
    return status;
  }
  
  console.log(`Progress: ${status.pages_crawled}/${status.pages_found} pages`);
  setTimeout(() => monitorJob(jobId), 5000);
};

// Usage
const jobId = await startCrawl('https://example.com', 100);
await monitorJob(jobId);
```