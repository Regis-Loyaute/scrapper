# Web Interface User Guide

Scrapper provides an intuitive web interface for managing both single-page scraping and website crawling operations. This guide covers all the features and functionality available through the web interface.

## Getting Started

Access the Scrapper web interface at: `http://localhost:3000/`

The interface includes four main sections:
- **Home Page** (`/`) - Single-page scraping and crawl job creation
- **Jobs Dashboard** (`/jobs`) - Monitor and manage all crawl jobs
- **Content Library** (`/library`) - Browse and search crawled content
- **Job Details** (`/job?id={job_id}`) - Detailed job monitoring and logs

## Home Page - Dual Scraping Interface

The home page provides two distinct scraping modes:

### Single-Page Scraping

**📄 Scrape Page Button**
- Extracts content from a single webpage
- Uses Mozilla's Readability.js for article extraction
- Returns structured JSON data immediately
- Ideal for individual articles or pages

**Usage:**
1. Enter the target URL in the input field
2. Click **📄 Scrape Page**
3. View extracted content immediately
4. Results are cached for faster subsequent access

### Website Crawling

**🕷️ Crawl Website Button**
- Recursively crawls entire websites
- Discovers and processes multiple pages
- Organized by domain with timestamped folders
- Provides real-time progress monitoring

**Basic Crawl:**
1. Enter the starting URL
2. Click **🕷️ Crawl Website**
3. Monitor progress in the live activity log
4. View results in the Jobs dashboard

### Advanced Crawl Options

Click the **⚙️ Advanced Options** button to access detailed crawl configuration:

#### Basic Settings
- **Max Pages**: Limit the number of pages to crawl (1-5000)
- **Max Duration**: Set time limit in seconds (60-43200)
- **Rate Limit**: Control crawling speed (0.1-10.0 requests/second)

#### Scope Control
- **Domain**: Crawl entire domain including subdomains
- **Host**: Crawl specific host only
- **Path**: Crawl specific path and subdirectories
- **Custom Regex**: Use regex pattern for URL matching

#### Ethical Settings
- **Respect Robots.txt**: Honor website crawling guidelines
- **Include Assets**: Download images, CSS, and JavaScript files
- **Custom Patterns**: Include/exclude specific URL patterns

### Live Progress Monitoring

The home page features a real-time activity log that shows:
- Job creation notifications
- Crawl progress updates
- Page processing status
- Error notifications
- Completion alerts

**Progress Indicators:**
- **Job ID**: Unique identifier for tracking
- **Status**: Current job state (running, completed, failed)
- **Pages Found**: Total pages discovered
- **Pages Crawled**: Successfully processed pages
- **Elapsed Time**: Duration since job start

## Jobs Dashboard

Navigate to `/jobs` to access the comprehensive jobs management interface.

### Job List View

The jobs dashboard displays all crawl jobs in a card-based layout with:

#### Job Cards
Each job card shows:
- **Domain Name**: Website being crawled
- **Job ID**: Unique identifier (truncated)
- **Status Badge**: Color-coded status indicator
- **Progress Statistics**: Pages found, crawled, and completion percentage
- **Duration**: Time elapsed or total runtime
- **Progress Bar**: Visual completion indicator

#### Status Indicators
- 🟢 **Running**: Job actively crawling
- 🔵 **Completed**: Job finished successfully
- 🔴 **Failed**: Job encountered errors
- ⚫ **Stopped**: Job manually terminated
- 🟡 **Pending**: Job queued but not started

### Job Management Actions

Each job card includes action buttons based on job status:

#### For Running Jobs:
- **⏹️ Stop**: Immediately halt the crawl
- **👁️ Details**: View detailed job information

#### For Completed Jobs:
- **👁️ Details**: View detailed job information
- **📚 View Results**: Browse crawled content in library
- **🗑️ Delete**: Remove job and all data

### Filtering and Organization

#### Status Filter
Use the dropdown to filter jobs by status:
- All Jobs
- Running
- Completed
- Failed
- Stopped
- Pending

#### Auto-Refresh
- **Toggle**: Enable/disable automatic updates (5-second interval)
- **Manual Refresh**: Force immediate update
- **Real-time Updates**: Live status changes without page reload

## Job Details View

Access detailed job information at `/job?id={job_id}` or click **👁️ Details** on any job card.

### Job Overview Section

**Header Information:**
- **Domain Name**: Primary domain being crawled
- **Full URL**: Complete starting URL
- **Job ID**: Full unique identifier
- **Status Badge**: Current job state with color coding

**Real-time Controls:**
- **🔄 Refresh**: Manual data refresh
- **Auto-refresh Toggle**: 3-second automatic updates
- **Job Actions**: Stop, delete, or view in library

### Progress Monitoring

**Statistics Cards:**
- **Pages Found**: Total pages discovered during crawl
- **Pages Crawled**: Successfully processed pages
- **Progress Percentage**: Completion ratio with visual indicator
- **Duration**: Elapsed time with real-time updates

**Progress Bar:**
- Visual representation of crawl completion
- Updates in real-time as job progresses
- Color-coded based on job status

### Configuration Display

View complete job configuration in an organized grid:
- **Target URL**: Starting point for crawl
- **Max Pages**: Page limit setting
- **Max Duration**: Time limit configuration
- **Scope**: Crawling scope (domain/host/path)
- **Rate Limit**: Requests per second setting
- **Respect Robots**: Robots.txt compliance setting
- **Include Assets**: Asset capture configuration
- **Concurrency**: Parallel request limit

### Live Logs Section

**Real-time Log Display:**
- **Color-coded entries**: Success (green), errors (red), info (default)
- **Auto-scroll**: Automatically scroll to latest entries
- **Clear function**: Remove log display (doesn't affect stored logs)
- **Timestamp information**: Precise timing for each log entry

**Log Entry Types:**
- Job start/completion notifications
- Page processing success/failure
- Error messages and warnings
- Rate limiting notifications
- Progress milestones

### Crawled Pages List

**Page Information Display:**
- **URL**: Full page address
- **Depth**: Crawl depth level (0 = starting page)
- **Status Code**: HTTP response code
- **Success Indicator**: ✅ Success or ❌ Failed
- **Content Length**: Size of extracted content

**Filtering Options:**
- **All Pages**: Show complete list
- **Successful Only**: Filter to successful pages
- **Errors Only**: Show failed pages

**Page Status Indicators:**
- **Green border**: Successfully processed page
- **Red border**: Failed or error page
- **Metadata**: Depth, status code, content length

## Content Library

Navigate to `/library` to browse and search all crawled content.

### Library Overview

The content library provides a hierarchical view of all crawled websites:

#### Domain-Level Navigation
- **Domain List**: All crawled domains with job counts
- **Job Listings**: All crawl jobs for each domain
- **Timestamp Organization**: Jobs sorted by creation date

#### Search and Filtering
- **Domain Search**: Find specific domains
- **Date Filtering**: Filter by crawl date ranges
- **Content Search**: Search within crawled content

### Browsing Crawled Content

#### Domain View
- List of all crawled domains
- Job count for each domain
- Last crawl date information
- Quick access to recent jobs

#### Job View
- All crawl jobs for a domain
- Job metadata and statistics
- Direct access to crawled pages
- Export options for job data

#### Page View
- Individual page content display
- Extracted article content
- Original URL and metadata
- Reading mode formatting

### Content Export Features

#### Export Formats
- **JSON**: Structured data export
- **JSONL**: Line-delimited JSON for processing
- **ZIP**: Complete archive with assets

#### Export Options
- **Single Page**: Export individual page
- **Complete Job**: Export all pages from a job
- **Domain Archive**: Export entire domain content

## Navigation and User Interface

### Global Navigation
- **🏠 Home**: Return to main scraping interface
- **📚 Library**: Access content library
- **🕷️ Jobs**: View jobs dashboard
- **GitHub Link**: Access project repository

### Theme Support
- **Automatic Dark Mode**: Follows system preference
- **Manual Toggle**: Switch between light and dark themes
- **Consistent Styling**: Unified design across all pages

### Responsive Design
- **Mobile Friendly**: Optimized for mobile devices
- **Tablet Support**: Adapted layout for tablets
- **Desktop Experience**: Full feature set on desktop

### Keyboard Shortcuts
- **Enter**: Submit forms and start operations
- **Escape**: Close modals and dialogs
- **Ctrl+R**: Refresh current page data

## Tips and Best Practices

### Getting Started
1. **Test with Small Sites**: Start with small websites to understand the interface
2. **Use Advanced Options**: Configure appropriate limits for your use case
3. **Monitor Progress**: Watch the live logs to understand crawl behavior
4. **Check Results**: Always verify results in the library after completion

### Performance Optimization
1. **Set Reasonable Limits**: Use appropriate page and time limits
2. **Control Rate Limits**: Balance speed with server respect
3. **Use Scope Wisely**: Limit scope to avoid unnecessary pages
4. **Monitor Resources**: Keep an eye on system resource usage

### Content Management
1. **Regular Cleanup**: Delete old jobs to save disk space
2. **Export Important Data**: Backup critical crawl results
3. **Organize by Domain**: Use the domain-based organization effectively
4. **Review Logs**: Check logs for any issues or warnings

### Troubleshooting
1. **Check Job Status**: Monitor job details for error information
2. **Review Logs**: Examine logs for specific error messages
3. **Verify URLs**: Ensure target URLs are accessible
4. **Adjust Settings**: Modify rate limits or scope if needed

## Advanced Features

### Real-time Updates
- **WebSocket Integration**: Live updates without page refresh
- **Progress Streaming**: Real-time progress information
- **Status Notifications**: Immediate status change alerts

### Batch Operations
- **Multiple Job Management**: Start multiple jobs simultaneously
- **Bulk Actions**: Stop or delete multiple jobs
- **Queue Management**: Manage job execution order

### Integration Features
- **API Access**: Direct API endpoints for all operations
- **Export Integration**: Multiple export formats for data integration
- **Webhook Support**: Notifications for job completion (if configured)

The Scrapper web interface provides a comprehensive, user-friendly experience for all your web scraping and crawling needs. Whether you're extracting single pages or crawling entire websites, the interface adapts to your workflow and provides the tools you need for successful data extraction.