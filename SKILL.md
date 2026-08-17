---
name: reddit-url-analyzer
description: "Analyze any Reddit URL by fetching thread content, comments, and engagement data using the Reddit .json endpoint with a generic Python fetch script (preferred), falling back to web search only when the JSON endpoint is unavailable. Generates structured markdown reports with sentiment analysis, top comments, and discussion summaries written in plain layman's terms with verbatim quotes."
category: data-analysis
risk: safe
source: self
source_type: self
date_added: "2026-08-17"
author: 
tags: [reddit, analysis, sentiment, web-search, markdown, laymans-terms, json-endpoint, python-scripts]
tools: []
---

# Reddit URL Analyzer

## Overview

Analyze any Reddit thread URL and generate a comprehensive markdown report containing post analysis, comment sentiment breakdown, top comments, and discussion summaries. All analysis is written in plain, accessible layman's terms, with verbatim quoted text surrounded by quotation marks.

**Data reuse policy:** Before fetching, this skill checks `data/{post_id}/` for previously fetched data. If cached files exist, the skill reuses them and skips re-fetching. Fresh data is only fetched when cached data is missing or the user explicitly requests a refresh.

**Priority order for fetching data:**
1. Reuse existing cached data from `data/{post_id}/` if available.
2. If no cached data exists, use `fetch_all_comments.py` against the post's `.json` URL first (preferred — more complete, structured data).
3. Only fall back to `web_search` if the JSON endpoint is unavailable or the script cannot run.

This skill adapts proven patterns from open-source Reddit analysis tools into a simple URL-driven workflow.

## When to Use This Skill

- Use when you need to analyze a specific Reddit thread or post
- Use when you want sentiment analysis and engagement metrics for a Reddit discussion
- Use when the user asks to "analyze this Reddit URL" or "summarize this Reddit thread"
- Use when extracting insights from Reddit comments and post content
- **Always try the JSON fetch script (`fetch_all_comments.py`) before using `web_search`.**

# Expected Prompt Arguments
1. Single Reddit Link URL
2. Text File With List of Reddit URLs

# Requirements / Mandatory
1. Run sub agents for each reddit link URL in Text File of Reddit URLs
2. Run in Main Agent without sub agents when only 1 reddit link URL

## How It Works

### Step 1: Validate and Parse the URL

Accept a Reddit URL and extract the thread identifier. Supported formats:

- `https://www.reddit.com/r/subreddit/comments/{id}/title/`
- `https://reddit.com/r/subreddit/comments/{id}/title/`
- `https://www.reddit.com/comments/{id}/title/`

Extract: subreddit name, post ID, and optional title slug.

Construct the `.json` endpoint URL:
```
https://www.reddit.com/r/{subreddit}/comments/{post_id}/{slug}/.json
```

### Step 1.5: Check for Existing Cached Data

Before fetching, check whether a previous fetch already exists on disk.

Look for:
```
data/{post_id}/flat.json
data/{post_id}/full.json
data/{post_id}/initial_raw.json
```

**If all three files exist and are non-empty:**
- Reuse the cached data.
- Do **not** re-run `fetch_all_comments.py`.
- Proceed directly to analysis using the existing `data/{post_id}/flat.json`.

**If the directory is missing, or any required file is absent/empty/corrupted:**
- Treat the data as missing.
- Proceed to Step 2 to fetch fresh data with `fetch_all_comments.py`.

**Exception:** If the user explicitly requests a fresh/recreated analysis and wants to discard old data, ignore the cache and re-fetch.

### Step 2: Fetch Post Content and Comments

**Only run if cached data is missing or explicitly requested to refresh.**

**Preferred path:** Run `fetch_all_comments.py` for the thread. This single script handles both post metadata and full comment expansion.

```bash
python fetch_all_comments.py "https://www.reddit.com/r/{subreddit}/comments/{post_id}/{slug}/"
```

The script will:
- Parse the URL automatically
- Fetch the `.json` endpoint with `limit=500&raw_json=1`
- Expand all `more` nodes via `/api/morechildren`
- Save structured output files to `data/`

From the saved flat output (`data/{post_id}/flat.json`), extract post metadata from the saved initial raw JSON (`data/{post_id}/initial_raw.json`) or from the `post` field in `*_full.json`:

- **Post title**
- **Post body/selftext** (if text post)
- **External link** (if URL post — from `url` field)
- **Author** (u/username)
- **Score** (upvotes)
- **Number of comments** (`num_comments`)
- **Created timestamp** (`created_utc` — convert UTC to relative time)
- **Flair/tags** (`link_flair_text`, if present)
- **Subreddit name**

If the post is a text post, capture the full `selftext`. If it's a link post, capture the external URL and domain.

**Note:** The script requires a `requests.Session()` pre-loaded with full browser-like headers and Reddit session cookies (see "Fetch Script Usage" section below). If the script cannot be run or returns a non-200 status, fall back to `web_search`.

### Step 3: Analyze Comments

**Preferred path:** Use the flat output from `fetch_all_comments.py` (`data/{post_id}/flat.json`).

From the flat output, extract for each comment:
- **Username** (u/username — may be `[deleted]`)
- **Comment body** (full text — may be `[deleted]` or `[removed]`)
- **Score** (upvotes)
- **Permalink** (for reference)

**Important notes:**
- Reddit caps the initial `.json` response at approximately 45–404 top-level comments and hides the rest in `more` nodes.
- `fetch_all_comments.py` automatically expands these `more` nodes via `/api/morechildren` to retrieve the full thread.
- Deleted or removed comments are inaccessible via either the JSON endpoint or web search.
- Only use `web_search` if the script cannot run or is blocked (e.g., 403/429 responses, missing cookies).

### Step 4: Perform Analysis

Apply the following analysis to the collected data:

**All analysis must be written in plain, accessible layman's terms. When quoting verbatim text from the post or comments, surround the quoted text with quotation marks.**

#### 4.1 Comment Classification

Group **all** comments fetched and analyzed into thematic clusters based on content similarity. There must be **no unassigned comments** — every comment belongs to exactly one cluster. Aim for 3-6 clusters, but use more if needed to ensure total coverage. For each cluster:

- Assign a descriptive label derived from the actual thread content. Recommended cluster types to consider, but not limited to:
  - "Agreement/Support"
  - "Disagreement/Criticism"
  - "Questions/Clarifications"
  - "Humor/Off-topic"
  - "Additional Context"
  - "Personal Experience"
- Count the number of comments in the cluster
- Sum the upvotes across all comments in the cluster
- Provide a 1-2 sentence summary of the cluster's sentiment and content **in layman's terms**

**Total Coverage Rule:** The sum of all `X Comments` values across every cluster must equal the total number of comments analyzed. After clustering, verify: `Σ(cluster comment counts) = total comments analyzed`. If the totals do not match, redistribute comments until every comment is accounted for.

#### 4.2 Sentiment Analysis

Perform basic sentiment scoring on each comment:

- **Positive**: Comments expressing agreement, support, enthusiasm, or constructive feedback
- **Neutral**: Factual statements, questions, or balanced viewpoints
- **Negative**: Criticism, disagreement, complaints, or hostile language

Calculate the overall sentiment distribution as percentages. **Present these results in plain language** (e.g., "Roughly 60% of comments were positive, 25% neutral, and 15% negative").

#### 4.3 Engagement Metrics

- Total comments analyzed
- Total upvotes across analyzed comments
- Average upvotes per comment
- Most upvoted comment
- Top contributing users (by comment count and total upvotes)

**All metric descriptions must be written in layman's terms.** Avoid jargon like "engagement velocity" or "sentiment polarity" — instead use plain phrases like "how much people liked the comments" or "whether the tone was mostly positive or negative".

#### 4.4 Keyword Extraction

Identify the top 10-15 keywords/phrases that appear frequently across the post title and top comments. Focus on meaningful nouns and noun phrases. Exclude common stop words. **Explain the keyword list in plain language**, describing what the discussion was centered around.

#### 4.5 Layman's Terms Quoting Rules

When explaining or summarizing any verbatim text from the original post or comments:

- **Always surround exact quoted text with quotation marks** (`"like this"`)
- Do not paraphrase quoted material — use the exact words from the source
- Attribute quotes to the original author when possible (e.g., `u/USERNAME wrote: "exact quote"`)

### Step 5: Generate Output

Use the template structure from `@resources/reddit-template.md` to produce the final markdown report. The markdown file must be named `thread_post_id_analysis.md`. The output must follow this exact structure:

```markdown
# REDDIT POST ANALYSIS

[Concise summary of the original post in plain, accessible layman's terms. Include the post title, author, score, and key context. 3-5 sentences. When quoting exact phrases from the post, surround them with quotation marks.]

# REDDIT COMMENTS ANALYSIS

[Cluster Name 1] (X Comments - X Upvotes)
[Summary of this comment cluster in plain, accessible layman's terms. 2-3 sentences. When quoting exact phrases from comments, surround them with quotation marks.]

[Cluster Name 2] (X Comments - X Upvotes)
[Summary of this comment cluster in plain, accessible layman's terms. 2-3 sentences. When quoting exact phrases from comments, surround them with quotation marks.]

[Cluster Name 3] (X Comments - X Upvotes)
[Summary of this comment cluster in plain, accessible layman's terms. 2-3 sentences. When quoting exact phrases from comments, surround them with quotation marks.]

...

(Total: X Comments - X Upvotes)
The sum of all X Comments values above must equal the total number of comments analyzed. Every comment fetched must be assigned to exactly one cluster.

# TOP COMMENTS

Each entry below is the verbatim text of the top comment in that upvote range, copied exactly as it appears on Reddit. No summarization, paraphrasing, or layman's-terms rewriting is applied to TOP COMMENTS.

## 1M+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 900k+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 800k+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

...

## 100k+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 90k+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 80k+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

...

## 10k+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 9k+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 8k+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

...

## 1k+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 900+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 800+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 700+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

...

## 100+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 90+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 80+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

## 70+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

...

## 10+ Upvotes

u/USERNAME
"Verbatim comment text exactly as it appears on Reddit" (X Upvotes) - Reddit Comment URL

# ORIGINAL POST

"Verbatim original post text exactly as it appears on Reddit, including title and selftext. No summarization or rewriting. Preserve original formatting where possible."
```

**Output Formatting Rules:**

1. **REDDIT POST ANALYSIS and REDDIT COMMENTS ANALYSIS:** Written in plain, accessible layman's terms. When quoting verbatim text from the post or comments, surround it with quotation marks.
2. **TOP COMMENTS:** Verbatim text only. Each comment is reproduced exactly as it appears on Reddit, with no summarization, paraphrasing, or rewriting into layman's terms. The comment text is enclosed in quotation marks.
3. **ORIGINAL POST:** Verbatim text only. The full original post is reproduced exactly as written, with no summarization or rewriting. The text is enclosed in quotation marks.

**TOP COMMENTS Rules:**

1. **One comment per bucket:** Each threshold section contains exactly one comment — the highest-upvoted comment within that bucket's range.
2. **No empty buckets:** Only include threshold sections that have at least one comment. Omit empty ranges entirely.
3. **Highest bucket wins:** A comment is placed in the highest threshold bucket it qualifies for. For example, a comment with 250,000 upvotes goes in **200k+**, not 100k+.
4. **Minimum threshold:** Comments with fewer than 10 upvotes are excluded from TOP COMMENTS entirely.

**Complete Threshold Bucket Reference (highest to lowest):**

| Bucket | Range |
|--------|-------|
| 1M+ | ≥ 1,000,000 |
| 900k+ | 900,000–999,999 |
| 800k+ | 800,000–899,999 |
| ... | ... |
| 100k+ | 100,000–199,999 |
| 90k+ | 90,000–99,999 |
| 80k+ | 80,000–89,999 |
| ... | ... |
| 10k+ | 10,000–19,999 |
| 9k+ | 9,000–9,999 |
| 8k+ | 8,000–8,999 |
| ... | ... |
| 1k+ | 1,000–1,999 |
| 900+ | 900–999 |
| 800+ | 800–899 |
| ... | ... |
| 100+ | 100–199 |
| 90+ | 90–99 |
| 80+ | 80–89 |
| ... | ... |
| 10+ | 10–19 |

## Fetch Script Usage

### Primary Script

`fetch_all_comments.py` is the **only** required fetch script for this skill. It is generic and accepts any Reddit thread URL as a command-line argument. It fetches the post metadata, expands all `more` nodes, and saves structured output files.

### Running the Script

From the project root, run:

```bash
python fetch_all_comments.py "https://www.reddit.com/r/subreddit/comments/POST_ID/title/"
```

The script will:
- Parse the URL automatically
- Fetch the `.json` endpoint
- Expand all `more` nodes
- Save all results under `data/`
- Print progress and a summary when done

All fetched JSON artifacts are stored in the `data/` directory, with each thread in its own subdirectory. User can delete the entire `data/` directory or any individual thread folder at any time if user want to free up space; the script recreates directories automatically on the next run.

### How the JSON Fetch Works

The script uses the following exact pattern:

1. **`requests.Session()`** — Maintains cookies across requests.
2. **Browser-like headers** — Full set including `User-Agent`, `Sec-Ch-Ua`, `Sec-Fetch-*`, `Accept-Language`, `Upgrade-Insecure-Requests`.
3. **Reddit session cookies** — Required for the `.json` endpoint to return 200 instead of 403. The script includes a working set of cookies.
4. **Initial fetch** — `GET https://www.reddit.com/r/{subreddit}/comments/{post_id}/{slug}/.json?limit=500&raw_json=1`
5. **Tree walk** — Recursively traverses `t1` comments and collects `kind="more"` placeholders.
6. **Expand loop** — For each `more` node:
   - If empty children: re-fetches the specific thread via `comment={id}&context=0`
   - If has children: POSTs to `/api/morechildren` in batches of ≤100
   - Sleeps 1.5s between expansions; retries once after 5s on 429

**Key lesson:** The 403 errors were caused by **missing session cookies**, not by User-Agent format. Always ensure cookies are present before testing other variables.

### Output Files

`fetch_all_comments.py` writes the following files under `data/{post_id}/` (created automatically):

| File | Description |
|------|-------------|
| `data/{post_id}/initial_raw.json` | Raw initial `.json` response from Reddit |
| `data/{post_id}/full.json` | Complete thread with post + all expanded comments as nested objects |
| `data/{post_id}/flat.json` | Flat list of comments with fields: `id`, `author`, `body`, `score`, `permalink`, `parent_id`, `created_utc` |

The flat file (`flat.json`) is the easiest to consume for analysis — it contains one JSON object per comment with all fields needed for clustering and sentiment analysis.

**Note:** Each thread gets its own subdirectory under `data/`, e.g. `data/1uht2m0/`. You can safely delete the entire `data/` directory or an individual thread folder at any time if you want to reclaim disk space or start fresh. The fetch scripts will recreate the necessary directories automatically on the next run.

### Cookie and Header Requirements

`fetch_all_comments.py` uses `requests.Session()` with browser-like headers and Reddit session cookies. The following cookies are required for the `.json` endpoint to return 200 (instead of 403 or a login wall):

| Cookie | Purpose |
|--------|---------|
| `edgebucket` | Reddit A/B testing bucket |
| `csv` | Client-side feature flags |
| `reddit_supported_media_codecs` | Media codec preference |
| `eu_cookie_opted` | GDPR cookie consent |
| `ads_cookie` | Advertising consent |
| `seeker_session` | Session tracking |
| `reddit_chat_view` | Chat UI state |
| `reddit_chat_path` | Chat room path |
| `loid` | Reddit device identifier |
| `_ga` | Google Analytics |
| `_fbp` | Facebook Pixel |
| `_ga_GWE79J8M6R` | Google Analytics custom dimension |
| `g_state` | Google login state |
| `session_tracker` | Reddit session tracker |

**Important:** These cookies are session-specific and expire. If the scripts start returning 403 errors, the cookies need to be refreshed from a live browser session (export from DevTools → Application → Cookies for `reddit.com`). The scripts also require full browser headers including `User-Agent`, `Sec-Ch-Ua`, `Sec-Fetch-*`, `Accept-Language`, and `Upgrade-Insecure-Requests`.

### Debugging Protocol

When the `.json` endpoint returns 403 or unexpected HTML:

1. **First:** Test the basic request with full browser headers.
2. **Second:** If 403, check response body for clues — HTML containing "Welcome to Reddit" or login content means missing cookies, not bad User-Agent.
3. **Third:** Add/refresh session cookies. Do not loop on User-Agent changes without testing cookies first.
4. **Fourth:** If still blocked, try fallback endpoints: `old.reddit.com`, Arctic Shift API, or `web_search`.
5. **Never:** Loop on User-Agent changes without testing other variables (cookies, session state).

### Rate Limits

- The initial `.json` request is a single GET — no special throttling needed.
- For `/api/morechildren` calls: wait **1–2 seconds** between each batch request. The script uses `time.sleep(1.5)` by default.
- If a 429 (Too Many Requests) is received, the script sleeps 5 seconds and retries once.
- Do not increase concurrency — Reddit will IP-block aggressive request patterns.

### Expected Yield

For a thread with ~535 total comments on Reddit:
- The initial `.json` response typically contains **45–404** top-level comments
- The remaining comments are hidden in `more` nodes
- After full expansion, `fetch_all_comments.py` typically retrieves **403–467** real comments
- Deleted, removed, or shadowbanned comments are **not** available via either the JSON endpoint or `web_search` — they will be absent from all outputs

## Examples

### Example 1: Analyzing a Text Post

**Input:**
```
Analyze this Reddit URL: https://www.reddit.com/r/programming/comments/abc123/why_i_switched_from_vim_to_vscode/
```

**Process:**
1. Parse URL → subreddit: `programming`, post_id: `abc123`
2. Run `fetch_all_comments.py` → retrieve full comment tree, save to `data/abc123/flat.json`
3. Load flat JSON, cluster ALL comments into thematic groups based on the actual thread content. Cluster names must be derived from the thread itself — do not reuse example names from this skill.
4. Verify total coverage: `Σ(cluster comment counts) = total comments analyzed`
5. Assign each comment to its highest qualifying threshold bucket
6. Select the top comment per bucket (highest upvote within that range)
7. Write all cluster summaries and post analysis in plain, accessible layman's terms, using quotation marks around any verbatim quoted text
8. Generate markdown report following the template with threshold-organized TOP COMMENTS and total coverage verified

**Fallback:** If `fetch_all_comments.py` returns a non-200 status or raises an exception, fall back to `web_search` with `site:reddit.com/r/programming/comments/abc123`.

### Example 2: Analyzing a Link Post

**Input:**
```
Analyze this Reddit URL: https://www.reddit.com/r/technology/comments/xyz789/ai_reaches_new_milestone/
```

**Process:**
1. Parse URL → subreddit: `technology`, post_id: `xyz789`
2. Run `fetch_all_comments.py` → retrieve full comment tree, save to `data/xyz789/flat.json`
3. Load flat JSON, cluster ALL comments into thematic groups based on the actual thread content. Cluster names must be derived from the thread itself — do not reuse example names from this skill.
4. Verify total coverage: `Σ(cluster comment counts) = total comments analyzed`
5. Assign each comment to its highest qualifying threshold bucket
6. Select the top comment per bucket (highest upvote within that range)
7. Write all cluster summaries and post analysis in plain, accessible layman's terms, using quotation marks around any verbatim quoted text
8. Generate markdown report following the template with threshold-organized TOP COMMENTS and total coverage verified

**Fallback:** If the script cannot run, fall back to `web_search` with `site:reddit.com/r/technology/comments/xyz789 top comments`.

## Best Practices

- ✅ Always check `data/{post_id}/` for existing cached data before fetching. Reuse cached data when available.
- ✅ Only run `fetch_all_comments.py` when cached data is missing, corrupted, or the user explicitly requests a fresh fetch.
- ✅ Always try the JSON fetch script (`fetch_all_comments.py`) before `web_search` when fresh data is needed.
- ✅ Do not rely solely on `web_search` for comment counts or full comment text — it is incomplete by comparison.
- ✅ Use `fetch_all_comments.py` as the sole data-fetching script.
- ✅ Write the REDDIT POST ANALYSIS and REDDIT COMMENTS ANALYSIS sections in plain, accessible layman's terms. Avoid technical jargon.
- ✅ REDDIT COMMENTS ANALYSIS must include ALL comments fetched and analyzed — no comment may be omitted.
- ✅ The sum of all `X Comments` values across every cluster in REDDIT COMMENTS ANALYSIS must equal the total number of comments analyzed.
- ✅ Each comment must be assigned to exactly one cluster. Verify totals after clustering: `Σ(cluster comment counts) = total comments analyzed`.
- ✅ TOP COMMENTS and ORIGINAL POST must be verbatim text only — no summarization, paraphrasing, or rewriting into layman's terms.
- ✅ Surround all verbatim quoted text (TOP COMMENTS, ORIGINAL POST, and any quotes in the layman's terms sections) with quotation marks (`"like this"`).
- ✅ Attribute quoted text to the original author when possible (e.g., `u/USERNAME wrote: "exact quote"`).
- ✅ Extract at least 10-20 comments for meaningful analysis.
- ✅ Preserve original comment text and formatting where possible.
- ✅ Include Reddit Comment URLs for reference in the TOP COMMENTS section.
- ✅ Verify the post ID and subreddit match the requested URL before proceeding.
- ✅ Handle deleted/removed comments gracefully (skip or note as `[deleted]`).
- ✅ Organize TOP COMMENTS by threshold buckets (1M+, 900k+, 800k+, ..., 10+).
- ✅ Select exactly one comment per bucket — the highest-upvoted comment within that range.
- ✅ Omit empty buckets from the TOP COMMENTS section entirely.
- ✅ Exclude comments with fewer than 10 upvotes from TOP COMMENTS.
- ✅ If cookies expire and the script returns 403, refresh cookies from a live browser session before retrying.
- ✅ Follow the debugging protocol: test cookies before changing User-Agent; analyze response body for clues.

## Limitations

- Cached data in `data/{post_id}/` may become stale if the thread changes after the initial fetch. Re-fetch if up-to-date data is required.
- The JSON endpoint requires valid session cookies and browser-like headers; cookies expire and must be refreshed periodically.
- Web search indexing may miss comments entirely — the JSON fetch is significantly more complete.
- Very new or very obscure posts may not appear in search results (web_search fallback only).
- Comment counts and upvote counts from the JSON endpoint are real-time; web_search values are estimates based on search result snippets.
- Nested comment threads are flattened to a flat list by `fetch_all_comments.py` — reply depth is preserved in `parent_id` but not rendered as a tree in the output.
- Only the highest-upvoted comment per threshold bucket is shown in TOP COMMENTS. Other high-quality comments in the same bucket are not listed.
- Comments with fewer than 10 upvotes are excluded from TOP COMMENTS.
- Deleted or removed comments are unavailable via both the JSON endpoint and web search — they will be absent from all outputs.
- Use `fetch_all_comments.py` for all fetching.
- This skill does not replace manual review for critical or high-stakes analysis.
- Stop and ask for clarification if the URL is malformed, private, or inaccessible.

## Security & Safety Notes

- This skill only performs read-only HTTP requests. It does not authenticate to Reddit's API, post content, or modify any data.
- The scripts use session cookies for anonymous browsing access only — no login credentials or OAuth tokens are used.
- All data is fetched from publicly accessible Reddit `.json` endpoints or public search results.
- No credentials, tokens, or API keys are required or used beyond browser session cookies for anonymous access.

## Common Pitfalls

- **Problem:** Analysis uses technical jargon or complex language.
  - **Solution:** Rewrite all summaries in plain, accessible layman's terms. Avoid terms like "engagement velocity" or "sentiment polarity" — use simpler phrases instead.
- **Problem:** Verbatim text is paraphrased instead of quoted exactly.
  - **Solution:** Always use exact quotes surrounded by quotation marks. Attribute quotes to the original author when possible.
- **Problem:** Some comments are not included in REDDIT COMMENTS ANALYSIS clusters.
  - **Solution:** After clustering, verify the sum of all cluster comment counts equals the total comments analyzed. Redistribute any unassigned comments until every comment is accounted for.
- **Problem:** The sum of cluster comment counts does not match total comments.
  - **Solution:** Check for missing or double-counted comments. Ensure each comment appears in exactly one cluster. Adjust cluster boundaries if necessary.
- **Problem:** Re-fetching data unnecessarily when cached data already exists.
  **Solution:** Always check `data/{post_id}/` first. Only re-run `fetch_all_comments.py` if the cached files are missing, corrupted, or the user explicitly requests a refresh.
- **Problem:** Using stale cached data for a thread that has changed significantly.
  **Solution:** If the user needs up-to-date analysis, ask whether to reuse cached data or fetch fresh data.
  - **Solution:** The session cookies have expired. Refresh the cookies from a live browser session (DevTools → Application → Cookies for `reddit.com`) and re-run the script. Only fall back to `web_search` if cookies cannot be refreshed. Do not loop on User-Agent changes — the root cause is missing cookies, not header format.
- **Problem:** 403 errors and unsure whether it's cookies, headers, or User-Agent.
  - **Solution:** Follow the debugging protocol: (1) test basic request with browser headers, (2) inspect response body for login/HTML clues, (3) add/refresh cookies, (4) only then test User-Agent variations. Never loop on one variable without testing others.
- **Problem:** Search returns no results for the Reddit URL (web_search fallback).
  - **Solution:** Try alternative search queries with different keywords or check if the post is too recent/old to be indexed. Inform the user and ask if they want to retry.
- **Problem:** Comments are truncated or missing context.
  - **Solution:** Use `fetch_all_comments.py` to get the full flat JSON. If falling back to web_search, use multiple search queries to gather more comment data. Note any gaps in the final report.
- **Problem:** Upvote counts are inconsistent across search results.
  - **Solution:** Use the most recent search result values and note that counts are approximate. The JSON endpoint provides real-time counts.
- **Problem:** Post is removed or locked.
  - **Solution:** Report what data is available (title, score) and note that the thread is no longer accessible.

## Related Skills

- `@related-skill` - Related Skill
