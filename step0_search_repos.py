"""
Usage:
    python step0_search_repos.py
    python step0_search_repos.py --max-results 20
    python step0_search_repos.py --min-stars 20 --max-stars 200

Environment variables (loaded from .env):
    GITHUB_TOKEN   GitHub personal access token
"""

import json
import os
import re
import base64
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_API   = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

SEARCH_QUERIES = [
    "library management system language:Python",
    "bank account system language:Python",
    "hotel booking system language:Python",
    "student management system language:Python",
    "inventory management system language:Python",
    "online shop oop language:Python",
    "restaurant management system language:Python",
    "task management system language:Python",
]

MIN_README_WORDS  = 100
MIN_DOMAIN_WORDS  = 50

_NOISE = re.compile(
    r"(?im)^##?\s*(installation|install|setup|getting started|requirements|dependencies"
    r"|usage|running|how to run|contributing|license|acknowledgements|todo|roadmap"
    r"|changelog|authors?|credits?|contact)\b"
)


def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def search_repos(query: str, per_page: int, min_stars: int, max_stars: int) -> list[dict]:
    resp = requests.get(
        f"{GITHUB_API}/search/repositories",
        headers=_gh_headers(),
        params={
            "q": f"{query} stars:{min_stars}..{max_stars}",
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"  Search failed ({resp.status_code}): {resp.text[:200]}")
        return []
    return resp.json().get("items", [])


def fetch_readme(full_name: str) -> Optional[str]:
    resp = requests.get(
        f"{GITHUB_API}/repos/{full_name}/readme",
        headers=_gh_headers(),
        timeout=10,
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    content = data.get("content", "")
    if data.get("encoding") == "base64":
        return base64.b64decode(content).decode("utf-8", errors="replace")
    return content


def _strip_noise(text: str) -> str:
    lines, in_noise = [], False
    for line in text.split("\n"):
        if line.strip().startswith("#"):
            in_noise = bool(_NOISE.match(line))
        if not in_noise:
            lines.append(line)
    return "\n".join(lines)


def readme_quality(readme: Optional[str]) -> tuple[bool, str]:
    if not readme:
        return False, "no README"
    total = len(readme.split())
    if total < MIN_README_WORDS:
        return False, f"too short ({total} words)"
    domain = len(_strip_noise(readme).split())
    if domain < MIN_DOMAIN_WORDS:
        return False, f"too few domain words ({domain})"
    return True, f"{total} words total, {domain} domain words"


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Search GitHub for thesis repo candidates and check README quality."
    )
    parser.add_argument("--max-results", type=int, default=10,
                        help="Max results to fetch per search query (default: 10)")
    parser.add_argument("--min-stars",   type=int, default=10,
                        help="Minimum star count (default: 10)")
    parser.add_argument("--max-stars",   type=int, default=500,
                        help="Maximum star count (default: 500)")
    parser.add_argument("--save",        type=str, default=None, metavar="FILE",
                        help="Save candidate list to a JSON file")
    args = parser.parse_args()

    print("=" * 60)
    print("REPO CANDIDATE SEARCH")
    print(f"  Stars       : {args.min_stars}..{args.max_stars}")
    print(f"  Per query   : {args.max_results}")
    print(f"  GitHub token: {'set' if GITHUB_TOKEN else 'NOT SET (rate-limited to 10 req/min)'}")
    print("=" * 60)

    candidates = []
    seen = set()

    for query in SEARCH_QUERIES:
        print(f"\nSearching: {query}")
        repos = search_repos(query, args.max_results, args.min_stars, args.max_stars)
        print(f"  {len(repos)} results")

        for repo in repos:
            full_name = repo["full_name"]
            if full_name in seen:
                continue
            seen.add(full_name)

            readme = fetch_readme(full_name)
            ok, reason = readme_quality(readme)
            status = "✓" if ok else "✗"
            print(f"  {status} {full_name:<45} {repo['stargazers_count']:>4}★  {reason}")

            if ok:
                candidates.append({
                    "repo":        full_name,
                    "url":         repo["html_url"],
                    "stars":       repo["stargazers_count"],
                    "description": repo.get("description", ""),
                    "readme_note": reason,
                })

    print("\n" + "=" * 60)
    print(f"CANDIDATES PASSING README FILTER: {len(candidates)}")
    print("=" * 60)

    for i, c in enumerate(candidates, 1):
        print(f"\n  {i:>2}. {c['repo']}  ({c['stars']} ★)")
        print(f"      {c['url']}")
        if c["description"]:
            print(f"      {c['description'][:80]}")
        print(f"      README: {c['readme_note']}")

    if candidates:
        print("\nTo download and scaffold a repo:")
        print("  python step1_repo_pipeline.py <github-url>")

    if args.save:
        Path(args.save).write_text(json.dumps(candidates, indent=2), encoding="utf-8")
        print(f"\nSaved to {args.save}")


if __name__ == "__main__":
    main()
