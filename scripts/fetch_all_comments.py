import requests
import json
import sys
import io
import os
import re
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DATA_DIR = "data"

# All fetched Reddit data is stored under DATA_DIR in per-thread subdirectories:
#   data/{post_id}/initial_raw.json  : raw initial .json response from Reddit
#   data/{post_id}/full.json         : post + all expanded comments (nested)
#   data/{post_id}/flat.json         : flat comment list for analysis
#
# You can safely delete the entire DATA_DIR or any individual thread folder
# at any time if you want to reclaim space. The script will recreate the
# necessary directories automatically on the next run.


def parse_reddit_url(raw_url):
    raw_url = raw_url.strip()
    if raw_url.endswith("/"):
        raw_url = raw_url[:-1]

    patterns = [
        r"https?://(?:www\.)?reddit\.com/r/(?P<subreddit>[^/]+)/comments/(?P<post_id>[^/]+)(?:/(?P<slug>[^/]+))?/?$",
        r"https?://(?:www\.)?reddit\.com/comments/(?P<post_id>[^/]+)(?:/(?P<slug>[^/]+))?/?$",
    ]

    for pattern in patterns:
        match = re.match(pattern, raw_url)
        if match:
            data = match.groupdict()
            subreddit = data.get("subreddit")
            post_id = data["post_id"]
            slug = data.get("slug") or ""
            return subreddit, post_id, slug

    return None, None, None


def build_json_url(subreddit, post_id, slug):
    if subreddit:
        return f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/{slug}/.json"
    return f"https://www.reddit.com/comments/{post_id}/{slug}/.json"


session = requests.Session()

session.headers.update({
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Priority": "u=0, i",
    "Sec-Ch-Ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
})

cookies = {
    "edgebucket": "n4qwReMG1TumBRVXDV",
    "csv": "2",
    "_gcl_au": "1.1.1913234310.1782182731",
    "reddit_supported_media_codecs": "video/avc%2Cvideo/vp9",
    "eu_cookie_opted": "1",
    "ads_cookie": "1",
    "seeker_session": "true",
    "reddit_chat_view": "closed",
    "reddit_chat_path": "/room/!2HqUjnvcNQ4X5awBNdYwshavCsTSPQeyi6u2CVxDYnQ%253Areddit.com",
    "loid": "0000000000000wq6lh.2.1459233436895.Z0FBQUFBQnFPZk5QTlJXU3ZEaG41eEdtSkliZmphYXZpUkJ1ejk3TUJxWTlaRGphSUphSTd6T2RWMUE3TzJhUnVqam02WFhRbjlEaXR1N1U5SGJFXzZmRXZJNE51dVlqaC1FOHpiaTF2R25oUklkOGV2Njk0TjRDZTZ0TE9CMDV5OXh0NDhEdURSQlA",
    "_ga": "GA1.1.1092365446.1786983740",
    "_fbp": "fb.1.1786983741146.267528639278473463",
    "_ga_GWE79J8M6R": "GS2.1.s1786983739$o1$g1$t1786983966$j60$l0$h0",
    "g_state": '{"i_l":0,"i_ll":1786987476396,"i_e":{"enable_itp_optimization":24},"i_et":1786987476396,"i_b":"Sr67QRaMAgjPcAPXnwAKIi5rwf5LybI/og8BH5G5+P4"}',
    "session_tracker": "kkolojnoollnahjngc.0.1786987557893.Z0FBQUFBQnFnMFFsMXdYeWh3X2F6MEhIMnVCa0JocFZpQWNpaGZwRFNTcDJZVGFWbDVCbDMyMnY4TTNwZWM1SGNWcTloYmw2ejhnYmZuaWJiXzNiNk01MmVGbUJ6ck1DT19tUXc5ZV9YNDI5UzhIc3Faa2NobXFoV2MyUE9jM1piZWtsM3NyaUx5b20",
}

session.cookies.update(cookies)


def fetch_initial(json_url):
    params = {"limit": 500, "raw_json": 1}
    r = session.get(json_url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def collect_nodes(nodes, flat_comments, more_nodes):
    for node in nodes:
        kind = node.get("kind")
        if kind == "t1":
            cid = node["data"]["id"]
            flat_comments[cid] = node
            replies = node["data"].get("replies")
            if replies and isinstance(replies, dict):
                collect_nodes(replies["data"]["children"], flat_comments, more_nodes)
        elif kind == "more":
            more_nodes.append(node)


def expand_more_node(more_node, link_id):
    children = more_node["data"].get("children", [])
    parent_id = more_node["data"].get("parent_id", "")

    if not children:
        if parent_id.startswith("t1_"):
            comment_id = parent_id.split("_", 1)[1]
            url = f"https://www.reddit.com/comments/{link_id.split('_', 1)[1]}/_/{comment_id}.json"
            params = {"context": 0, "raw_json": 1}
            r = session.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if len(data) > 1:
                more_nodes = []
                flat_comments = {}
                collect_nodes(data[1]["data"]["children"], flat_comments, more_nodes)
                return more_nodes, flat_comments
        return [], {}

    all_comments = {}
    all_more = []

    for i in range(0, len(children), 100):
        batch = children[i:i+100]
        mc_params = {
            "api_type": "json",
            "link_id": link_id,
            "children": ",".join(batch),
            "sort": "confidence",
            "raw_json": 1,
        }
        r = session.post(
            "https://www.reddit.com/api/morechildren",
            data=mc_params,
            timeout=30,
        )
        if r.status_code == 429:
            time.sleep(5)
            r = session.post(
                "https://www.reddit.com/api/morechildren",
                data=mc_params,
                timeout=30,
            )
        r.raise_for_status()
        mc_data = r.json()
        things = mc_data.get("json", {}).get("data", {}).get("things", [])

        for thing in things:
            if thing["kind"] == "t1":
                cid = thing["data"]["id"]
                all_comments[cid] = thing
                replies = thing["data"].get("replies")
                if replies and isinstance(replies, dict):
                    nested_more = []
                    nested_comments = {}
                    collect_nodes(replies["data"]["children"], nested_comments, nested_more)
                    all_comments.update(nested_comments)
                    all_more.extend(nested_more)
            elif thing["kind"] == "more":
                all_more.append(thing)

        if i + 100 < len(children):
            time.sleep(1.2)

    return all_more, all_comments


def fetch_all(json_url, post_id):
    print("Fetching initial thread data...", flush=True)
    data = fetch_initial(json_url)

    thread_dir = os.path.join(DATA_DIR, post_id)
    os.makedirs(thread_dir, exist_ok=True)

    initial_path = os.path.join(thread_dir, "initial_raw.json")
    with open(initial_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved initial raw JSON to {initial_path}", flush=True)
    print(f"(All fetched data for this thread is stored in '{thread_dir}/'. Delete that folder anytime to reclaim space.)", flush=True)

    post_data = data[0]["data"]["children"][0]["data"]
    link_id = post_data["name"]

    flat_comments = {}
    more_nodes = []
    collect_nodes(data[1]["data"]["children"], flat_comments, more_nodes)

    print(f"Initial comments: {len(flat_comments)}", flush=True)
    print(f"Initial more nodes: {len(more_nodes)}", flush=True)

    total_expanded = 0
    while more_nodes:
        more = more_nodes.pop(0)
        children_count = len(more["data"].get("children", []))
        print(f"Expanding more node ({children_count} children)...", flush=True)

        try:
            new_more, new_comments = expand_more_node(more, link_id)
        except Exception as e:
            print(f"  Failed to expand: {e}", flush=True)
            continue

        flat_comments.update(new_comments)
        more_nodes.extend(new_more)
        total_expanded += len(new_comments)

        print(
            f"  Added {len(new_comments)} comments, {len(new_more)} new more nodes. Total: {len(flat_comments)}",
            flush=True,
        )
        time.sleep(1.5)

    deleted_count = sum(
        1 for c in flat_comments.values() if c.get("data", {}).get("author") == "[deleted]"
    )
    top_comments = sorted(
        flat_comments.values(),
        key=lambda c: c.get("data", {}).get("score", 0),
        reverse=True,
    )[:5]

    final_data = {
        "post": post_data,
        "comments": list(flat_comments.values()),
    }

    full_path = os.path.join(thread_dir, "full.json")
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Total comments fetched: {len(flat_comments)}", flush=True)
    print(f"Total expanded from more nodes: {total_expanded}", flush=True)
    print(f"Deleted comments: {deleted_count}", flush=True)
    print(f"Real comment count: {len(flat_comments) - deleted_count}", flush=True)

    print("\nTop 5 comments by score:", flush=True)
    for i, c in enumerate(top_comments, 1):
        d = c.get("data", {})
        author = d.get("author", "[deleted]")
        score = d.get("score", 0)
        body_preview = (d.get("body", "") or "")[:120].replace("\n", " ")
        print(f"  {i}. [{score}] u/{author}: {body_preview}...", flush=True)

    flat_list = []
    for cid, c in flat_comments.items():
        d = c.get("data", {})
        flat_list.append({
            "id": d.get("id"),
            "author": d.get("author", "[deleted]"),
            "body": d.get("body", "[deleted]"),
            "score": d.get("score", 0),
            "permalink": d.get("permalink", ""),
            "parent_id": d.get("parent_id", ""),
            "created_utc": d.get("created_utc", 0),
        })

    flat_path = os.path.join(thread_dir, "flat.json")
    with open(flat_path, "w", encoding="utf-8") as f:
        json.dump(flat_list, f, ensure_ascii=False, indent=2)

    print(f"\nSaved flat comment list to {flat_path}", flush=True)
    print(f"All JSON artifacts for this thread are in '{thread_dir}/'. You can delete that directory at any time if you want to free up space.", flush=True)

    return flat_comments


if __name__ == "__main__":
    try:
        if len(sys.argv) < 2:
            print("Error: No Reddit thread URL provided.", flush=True)
            print("Usage: python fetch_all_comments.py <reddit_thread_url>", flush=True)
            print("Example:", flush=True)
            print('  python fetch_all_comments.py "https://www.reddit.com/r/LocalLLaMA/comments/1uht2m0/were_probably_going_to_need_that_soon/"', flush=True)
            sys.exit(1)

        raw_url = sys.argv[1]
        subreddit, post_id, slug = parse_reddit_url(raw_url)

        if not post_id:
            print("Error: URL does not match expected Reddit thread patterns.", flush=True)
            print("Supported formats:", flush=True)
            print("  https://www.reddit.com/r/subreddit/comments/POST_ID/title/", flush=True)
            print("  https://reddit.com/r/subreddit/comments/POST_ID/title/", flush=True)
            print("  https://www.reddit.com/comments/POST_ID/title/", flush=True)
            sys.exit(1)

        json_url = build_json_url(subreddit, post_id, slug)

        print(f"Subreddit:  r/{subreddit}" if subreddit else "Subreddit:  (none)", flush=True)
        print(f"Post ID:    {post_id}", flush=True)
        print(f"Slug:       {slug or '(none)'}", flush=True)
        print(f"JSON URL:   {json_url}", flush=True)
        print("", flush=True)

        fetch_all(json_url, post_id)
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
