#!/usr/bin/env python3
"""Refresh the contribution counts in content/pages/contributions.rst.

A contribution is a commit authored, signed off or co-authored by Thomas
Perrot. Counts are read from each project's own forge (GitHub, GitLab, cgit,
Patchwork and MediaWiki). Run it from anywhere:

    python3 scripts/update_contributions.py
    python3 scripts/update_contributions.py --check

Set GITHUB_TOKEN to raise the GitHub API rate limit; when it is unset the
script falls back to `gh auth token` if the GitHub CLI is installed.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "curl/8.5.0"
GITHUB_USER = os.environ.get("GITHUB_USER", "tprrt")
AUTHOR_NAME = os.environ.get("CONTRIBUTION_AUTHOR", "Thomas Perrot")
AUTHOR_QUERY = "thomas.perrot"
TRAILERS = ("Signed-off-by", "Co-authored-by")
ROW_RE = re.compile(r"^(\s*)\* - (.*)$")
ITEM_RE = re.compile(r"^(\s*)- (.*)$")
URL_RE = re.compile(r"<((?:https?://)[^>]+)>")
COUNT_RE = re.compile(r"^(-{1,2}|\d+)$")
CGIT_ID_RE = re.compile(r"commit/\?id=([0-9a-f]{7,40})")
REPO_RE = re.compile(r"repo:([^\s/]+/[^\s]+)")


def curl(url, headers=None):
    command = ["curl", "-sSL", "--max-time", "60"]
    for key, value in (headers or {}).items():
        command += ["-H", f"{key}: {value}"]
    command.append(url)
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if result.returncode != 0:
        raise urllib.error.URLError(result.stderr.strip() or "curl failed")
    return result.stdout


def fetch(url, headers=None):
    headers = {"User-Agent": UA, **(headers or {})}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8", "replace")
        response_headers = response.headers
    if "you're not a bot" in body or "you&#39;re not a bot" in body:
        if not shutil.which("curl"):
            raise urllib.error.URLError("anti-bot challenge, curl not available")
        return curl(url, headers), response_headers
    return body, response_headers


def fetch_retry(url, headers=None, attempts=5):
    for attempt in range(attempts):
        try:
            return fetch(url, headers)
        except urllib.error.HTTPError as error:
            if error.code not in (403, 429) or attempt + 1 == attempts:
                raise
            delay = error.headers.get("Retry-After") or 15
            time.sleep(min(float(delay), 60))


def with_param(url, name, value):
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query = [(key, val) for key, val in query if key != name]
    query.append((name, str(value)))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def next_link(headers):
    link = headers.get("Link") or ""
    for part in link.split(","):
        if 'rel="next"' in part:
            return part.split("<", 1)[1].split(">", 1)[0]
    return None


def json_pages(url, headers=None):
    total = 0
    while url:
        body, response_headers = fetch_retry(url, headers)
        data = json.loads(body)
        if not isinstance(data, list):
            raise ValueError(f"unexpected API response from {url}")
        total += len(data)
        url = next_link(response_headers)
    return total


def json_sha_pages(url, headers=None):
    shas = set()
    while url:
        body, response_headers = fetch_retry(url, headers)
        data = json.loads(body)
        items = data if isinstance(data, list) else data.get("items", [])
        shas.update(item["sha"] for item in items)
        url = next_link(response_headers)
    return shas


def github_headers():
    token = os.environ.get("GITHUB_TOKEN")
    if not token and shutil.which("gh"):
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
        )
        token = result.stdout.strip() if result.returncode == 0 else None
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_search_headers():
    headers = github_headers()
    headers["Accept"] = "application/vnd.github.cloak-preview+json"
    return headers


def github_search(repo, phrase):
    query = f'repo:{repo} "{phrase}: {AUTHOR_NAME}"'
    url = "https://api.github.com/search/commits?" + urllib.parse.urlencode(
        {"q": query, "per_page": 100}
    )
    return json_sha_pages(url, github_search_headers())


def github_union(repo):
    url = (
        f"https://api.github.com/repos/{repo}/commits"
        f"?author={urllib.parse.quote(GITHUB_USER)}&per_page=100"
    )
    shas = json_sha_pages(url, github_headers())
    for trailer in TRAILERS:
        shas |= github_search(repo, trailer)
    return len(shas)


def github_repo(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.path.startswith("/search"):
        query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
        match = REPO_RE.search(query)
        return match.group(1) if match else None
    parts = parsed.path.strip("/").split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else None


def github_count(url):
    repo = github_repo(url)
    return github_union(repo) if repo else None


def gitlab_count(url):
    parsed = urllib.parse.urlsplit(url)
    project = parsed.path.split("/-/", 1)[0].strip("/")
    query = urllib.parse.parse_qs(parsed.query)
    author = query.get("author_username", [None])[0]
    if not project or not author:
        return None
    api = (
        "https://gitlab.com/api/v4/projects/"
        f"{urllib.parse.quote(project, safe='')}/merge_requests"
        f"?author_username={urllib.parse.quote(author)}"
        "&scope=all&state=all&per_page=100"
    )
    headers = {}
    token = os.environ.get("GITLAB_TOKEN")
    if token:
        headers["PRIVATE-TOKEN"] = token
    return json_pages(api, headers)


def patchwork_count(url):
    parsed = urllib.parse.urlsplit(url)
    match = re.search(r"/project/([^/]+)/", parsed.path)
    query = urllib.parse.parse_qs(parsed.query)
    submitter = query.get("submitter", [None])[0]
    if not match or not submitter:
        return None
    api = (
        "https://patchwork.ozlabs.org/api/1.2/patches/"
        f"?project={urllib.parse.quote(match.group(1))}"
        f"&submitter={urllib.parse.quote(submitter)}&per_page=100"
    )
    return json_pages(api)


def cgit_log(url):
    parsed = urllib.parse.urlsplit(url)
    base = parsed.path.split("/log/", 1)[0].rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{base}/log/"


def cgit_ids(log_url, query_type, query):
    ids = set()
    offset = 0
    while True:
        url = with_param(log_url, "qt", query_type)
        url = with_param(url, "q", query)
        url = with_param(url, "ofs", offset)
        body, _ = fetch(url)
        found = CGIT_ID_RE.findall(body)
        if not found:
            break
        before = len(ids)
        ids.update(found)
        offset += len(found)
        if len(ids) == before:
            break
    return ids


def cgit_count(url):
    log_url = cgit_log(url)
    ids = cgit_ids(log_url, "author", AUTHOR_QUERY)
    for trailer in TRAILERS:
        ids |= cgit_ids(log_url, "grep", f"{trailer}: {AUTHOR_NAME}")
    return len(ids)


def wiki_count(url):
    body, _ = fetch(with_param(url, "limit", 500))
    count = len(re.findall(r"data-mw-revid", body))
    if count == 500:
        print(f"warning: {url} may be paginated ({count} edits)", file=sys.stderr)
    return count


def count_for(url):
    host = urllib.parse.urlsplit(url).netloc.lower()
    if host in {"github.com", "www.github.com"}:
        return github_count(url)
    if host == "gitlab.com":
        return gitlab_count(url)
    if host == "patchwork.ozlabs.org":
        return patchwork_count(url)
    if host in {"git.kernel.org", "git.openembedded.org", "git.yoctoproject.org"}:
        return cgit_count(url)
    if "Special:Contributions" in url:
        return wiki_count(url)
    return None


def rows(lines):
    index = 0
    while index < len(lines):
        match = ROW_RE.match(lines[index])
        if not match:
            index += 1
            continue
        indent = len(match.group(1)) + 2
        items = [(index, match.group(2))]
        cursor = index + 1
        while cursor < len(lines):
            item = ITEM_RE.match(lines[cursor])
            if not item or len(item.group(1)) != indent:
                break
            items.append((cursor, item.group(2)))
            cursor += 1
        yield items
        index = cursor


def label(value):
    text = URL_RE.sub("", value)
    return text.strip().strip("`_").strip()


def main():
    parser = argparse.ArgumentParser(description="Refresh contribution counts")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "content/pages/contributions.rst",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report outdated counts and exit non-zero without writing",
    )
    args = parser.parse_args()

    lines = args.file.read_text(encoding="utf-8").split("\n")
    changes = []

    for items in rows(lines):
        if len(items) < 3:
            continue
        _, first_value = items[0]
        count_line, count_value = items[-1]
        if not COUNT_RE.match(count_value.strip()):
            continue
        found = URL_RE.search(first_value)
        if not found:
            continue
        name = label(first_value)
        try:
            count = count_for(found.group(1))
        except (urllib.error.URLError, ValueError, TimeoutError) as error:
            print(f"warning: {name}: {error}", file=sys.stderr)
            continue
        if count is None:
            print(f"warning: {name}: unsupported link", file=sys.stderr)
            continue
        if int(count_value) == count:
            continue
        indent = ITEM_RE.match(lines[count_line]).group(1)
        changes.append((name, count_value, count))
        lines[count_line] = f"{indent}- {count}"

    if not changes:
        print("Counts are up to date.")
        return 0
    for name, old, new in changes:
        print(f"{name}: {old} -> {new}")
    if args.check:
        return 1
    args.file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Updated {args.file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
