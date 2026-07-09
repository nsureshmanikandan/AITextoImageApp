# Requirements Document

## Introduction

Live Breaking News Mode is an autonomous RSS/news feed monitoring system for VernacularCast that continuously watches configurable news sources, detects new and breaking stories, and automatically triggers the existing article-to-video pipeline to generate regional Indian language videos. The system operates 24/7 without human input while maintaining editorial control through an approval queue and dashboard.

This feature adds a scheduling/monitoring layer on top of the existing scraper, script generator, TTS, and video renderer services. Target users are regional news organizations that want to automate multilingual video production from their existing RSS/article feeds.

## Glossary

- **Feed_Monitor**: The background service that periodically polls configured RSS feeds and news APIs for new articles
- **Feed_Configuration**: A stored record defining an RSS/news source URL, its polling interval, associated language preferences, priority keywords, and trust level
- **Content_Queue**: The ordered list of auto-generated videos awaiting editorial approval or rejection
- **Deduplication_Engine**: The component responsible for identifying and filtering duplicate or already-processed articles across feeds
- **Approval_Dashboard**: The frontend interface showing monitoring status, content queue, and publishing controls for editorial staff
- **Pipeline_Trigger**: The mechanism that creates a new Job from a detected article and dispatches it to the existing article pipeline
- **Priority_Rule**: A configurable rule that assigns processing priority based on keywords, topics, or source trust level
- **Auto_Approve_Policy**: A policy that allows videos from trusted sources to bypass the editorial approval queue
- **Article_Fingerprint**: A unique identifier derived from an article's URL and content hash used for deduplication

## Requirements

### Requirement 1: RSS Feed Configuration Management

**User Story:** As a newsroom editor, I want to configure multiple RSS feeds and news API sources with per-feed settings, so that the system monitors only the sources relevant to my regional audience.

#### Acceptance Criteria

1. WHEN a valid RSS feed URL is submitted with language and polling interval, THE Feed_Monitor SHALL store the Feed_Configuration and begin polling within one polling cycle
2. WHEN an editor updates an existing Feed_Configuration, THE Feed_Monitor SHALL apply the new settings on the next polling cycle without restarting the service
3. WHEN an editor deletes a Feed_Configuration, THE Feed_Monitor SHALL stop polling that feed within one polling cycle and retain historical data for previously processed articles
4. THE Feed_Configuration SHALL support the following fields: feed URL, display name, polling interval (minimum 60 seconds), target language (ta-IN, hi-IN, te-IN, kn-IN, en-IN), priority keywords list, trust level (trusted, standard, untrusted), and enabled/disabled status
5. IF an invalid RSS feed URL is submitted, THEN THE Feed_Monitor SHALL return a descriptive validation error identifying the problem

### Requirement 2: Automated Feed Polling and Article Detection

**User Story:** As a newsroom editor, I want the system to automatically poll configured feeds at defined intervals, so that new articles are detected without manual intervention.

#### Acceptance Criteria

1. WHILE a Feed_Configuration is enabled, THE Feed_Monitor SHALL poll the feed URL at the configured polling interval
2. WHEN a new article entry is detected in a feed response, THE Feed_Monitor SHALL extract the article title, URL, publication date, and summary from the RSS entry
3. WHEN a feed poll returns an HTTP error or malformed XML, THE Feed_Monitor SHALL log the error, increment a failure counter, and retry on the next polling cycle
4. IF a feed fails for 5 consecutive polling cycles, THEN THE Feed_Monitor SHALL mark the Feed_Configuration as degraded and emit a WebSocket notification to connected Approval_Dashboard clients
5. WHEN a feed recovers after being marked degraded, THE Feed_Monitor SHALL reset the failure counter and restore the active status

### Requirement 3: Article Deduplication

**User Story:** As a newsroom editor, I want the system to detect and skip duplicate articles across multiple feeds, so that the same story is not processed into multiple identical videos.

#### Acceptance Criteria

1. WHEN a new article is detected, THE Deduplication_Engine SHALL compute an Article_Fingerprint from the normalized article URL
2. WHEN an Article_Fingerprint matches an already-processed or in-progress article, THE Deduplication_Engine SHALL skip the article and log the deduplication event
3. THE Deduplication_Engine SHALL retain Article_Fingerprints for a configurable retention period (default 7 days) to prevent reprocessing of recently seen articles
4. WHEN two feeds publish the same story under different URLs with identical titles, THE Deduplication_Engine SHALL detect the similarity using title normalization and skip the duplicate

### Requirement 4: Automatic Pipeline Triggering

**User Story:** As a newsroom editor, I want detected articles to automatically trigger video generation in the configured regional language, so that videos are produced without manual job creation.

#### Acceptance Criteria

1. WHEN a new non-duplicate article is detected, THE Pipeline_Trigger SHALL create a new Job with mode "article", the article URL, and the target language from the Feed_Configuration
2. WHEN multiple articles are detected in a single poll, THE Pipeline_Trigger SHALL queue them in publication-date order (newest first)
3. WHILE more than 10 jobs are in pending or processing status, THE Pipeline_Trigger SHALL hold new articles in a waiting state and resume triggering when the active count drops below 10
4. THE Pipeline_Trigger SHALL tag each auto-generated Job with the source Feed_Configuration ID and a "live_news" origin marker for audit purposes

### Requirement 5: Priority and Keyword Routing

**User Story:** As a newsroom editor, I want to define priority keywords and topics so that breaking news matching those keywords is processed before routine stories.

#### Acceptance Criteria

1. WHEN a detected article title or summary contains one or more Priority_Rule keywords, THE Pipeline_Trigger SHALL assign the job a high priority, placing it at the front of the processing queue
2. WHEN no Priority_Rule keywords match, THE Pipeline_Trigger SHALL assign standard priority and queue the job in publication-date order
3. THE Priority_Rule SHALL support comma-separated keyword lists per Feed_Configuration, with case-insensitive matching
4. WHEN a Priority_Rule keyword matches, THE Feed_Monitor SHALL emit a WebSocket notification indicating a breaking news detection to connected Approval_Dashboard clients

### Requirement 6: Editorial Approval Queue

**User Story:** As a newsroom editor, I want auto-generated videos to appear in an approval queue where I can review, approve, or reject them before publishing, so that editorial quality is maintained.

#### Acceptance Criteria

1. WHEN an auto-generated video reaches "awaiting_review" status, THE Content_Queue SHALL display the video with its source article title, source feed name, language, generation timestamp, and a video preview
2. WHEN an editor approves a video in the Content_Queue, THE Content_Queue SHALL transition the Job status to "approved" and make the video available for publishing
3. WHEN an editor rejects a video in the Content_Queue, THE Content_Queue SHALL transition the Job status to "rejected" and record the rejection reason
4. THE Content_Queue SHALL display items sorted by priority (high first), then by creation time (newest first)
5. WHERE an Auto_Approve_Policy is configured for a trusted source, THE Content_Queue SHALL automatically transition videos from that source to "approved" status without editorial review

### Requirement 7: Auto-Approve Policy for Trusted Sources

**User Story:** As a newsroom editor, I want to configure certain trusted feeds to bypass the approval queue, so that breaking news from reliable sources is published faster.

#### Acceptance Criteria

1. WHEN a Feed_Configuration has trust level set to "trusted" and Auto_Approve_Policy is enabled, THE Content_Queue SHALL automatically approve videos generated from that feed
2. WHEN an Auto_Approve_Policy auto-approves a video, THE Content_Queue SHALL log the auto-approval event with the source feed and article details for audit
3. WHEN an editor disables Auto_Approve_Policy on a Feed_Configuration, THE Content_Queue SHALL require manual approval for all subsequent videos from that feed

### Requirement 8: Live Monitoring Dashboard

**User Story:** As a newsroom editor, I want a real-time dashboard showing feed health, processing status, and queue metrics, so that I can monitor the autonomous system at a glance.

#### Acceptance Criteria

1. THE Approval_Dashboard SHALL display the following metrics: total active feeds, feeds in degraded state, articles detected in the last hour, videos in queue awaiting review, videos auto-approved in the last hour, and active processing jobs count
2. WHEN feed status changes or a new video enters the Content_Queue, THE Approval_Dashboard SHALL update in real time via WebSocket without requiring a page refresh
3. THE Approval_Dashboard SHALL display a per-feed status list showing feed name, last polled timestamp, articles processed count, current health status, and next poll time
4. WHEN an editor clicks on a feed entry in the Approval_Dashboard, THE Approval_Dashboard SHALL display the recent articles detected from that feed with their processing status

### Requirement 9: Feed Monitoring Lifecycle Control

**User Story:** As a newsroom editor, I want to start, pause, and stop the overall monitoring system, so that I can control resource usage during off-hours or maintenance.

#### Acceptance Criteria

1. WHEN an editor activates the monitoring system, THE Feed_Monitor SHALL begin polling all enabled Feed_Configurations within their configured intervals
2. WHEN an editor pauses the monitoring system, THE Feed_Monitor SHALL stop polling all feeds while retaining Feed_Configurations and queue state
3. WHEN an editor resumes after a pause, THE Feed_Monitor SHALL resume polling from the current time without reprocessing articles published during the pause
4. THE Approval_Dashboard SHALL display the current monitoring state (active, paused, stopped) and provide controls to change it

### Requirement 10: Concurrency and Rate Limiting

**User Story:** As a system administrator, I want the monitoring system to respect rate limits and manage concurrent processing, so that the system does not overload external services or internal resources.

#### Acceptance Criteria

1. THE Feed_Monitor SHALL enforce a minimum polling interval of 60 seconds per feed to avoid excessive requests to news sources
2. WHILE the number of concurrent pipeline jobs exceeds 5, THE Pipeline_Trigger SHALL queue additional articles without triggering new jobs until a slot becomes available
3. WHEN a feed source returns an HTTP 429 (Too Many Requests) response, THE Feed_Monitor SHALL double the polling interval for that feed until a successful response is received
4. THE Feed_Monitor SHALL stagger initial poll times across configured feeds to avoid burst traffic at startup
