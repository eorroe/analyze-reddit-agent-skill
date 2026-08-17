# Reddit Analyzer

A skill and resource bundle for analyzing Reddit discussion threads and producing structured markdown reports.

## What's Included

### `SKILL.md`
The skill configuration that defines the end-to-end analysis workflow. When invoked with a Reddit URL, it produces a markdown report with the following sections:

- **REDDIT POST ANALYSIS** — a plain-language summary of the original post, including title, author, score, and key context.
- **REDDIT COMMENTS ANALYSIS** — all fetched comments grouped into thematic clusters, each with a count, upvote total, and plain-language summary.
- **TOP COMMENTS** — the highest-upvoted comment from each upvote threshold bucket, reproduced verbatim.
- **ORIGINAL POST** — the full original post text reproduced verbatim.

### `resources/`
Supporting assets used by the skill:

- **`reddit-template.md`** — the output template that defines the exact markdown structure for generated reports.

## How It Works

1. **Parse the URL** — extract the subreddit and post ID from a supported Reddit thread URL.
2. **Fetch the post** — use web search to locate the thread and extract post metadata such as title, author, score, comment count, and body text.
3. **Fetch comments** — use web search to retrieve top-level comments from the thread, along with usernames, upvote counts, and permalinks.
4. **Analyze and report** — cluster comments thematically, calculate sentiment and engagement metrics, then render everything into a markdown report using the template.

## Requirements

- Read-only web search access to fetch Reddit content.
- No Reddit API credentials or authentication needed.

## Limitations

- Depends on search engine indexing; very new or obscure posts may not return results.
- Nested comment threads are flattened to top-level comments only.
- Upvote counts are approximate based on search results.
