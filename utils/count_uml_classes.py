"""
Count PlantUML type declarations in each repo's uml/input/classes.puml.

Recognized keywords: class, abstract class, interface, enum, protocol

Usage:
    python3 utils/count_uml_classes.py
    python3 utils/count_uml_classes.py --repo hackstarsj__AmazonCloneEcommerceProjectUsingDjangoReact
    python3 utils/count_uml_classes.py --by-kind
    python3 utils/count_uml_classes.py --csv classes.csv
"""

import argparse
import csv
import os
import re
import sys

THESIS_REPOS = os.path.join(os.path.dirname(__file__), "..", "thesis_repos")

KEYWORDS = ["abstract class", "interface", "enum", "protocol", "class"]
PATTERN = re.compile(r"^\s*(" + "|".join(re.escape(k) for k in KEYWORDS) + r")\s+")


def count_puml(path):
    counts = {k: 0 for k in KEYWORDS}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = PATTERN.match(line)
                if m:
                    counts[m.group(1)] += 1
    except FileNotFoundError:
        pass
    return counts


def find_repos(thesis_repos, repo_filter=None):
    entries = sorted(os.listdir(thesis_repos))
    for entry in entries:
        if repo_filter and entry != repo_filter:
            continue
        puml = os.path.join(thesis_repos, entry, "uml", "input", "classes.puml")
        if os.path.isfile(puml):
            yield entry, puml


def main():
    parser = argparse.ArgumentParser(
        description="Count UML type declarations in each repo's classes.puml."
    )
    parser.add_argument("--repo", metavar="NAME", help="Single repo folder name under thesis_repos/")
    parser.add_argument("--by-kind", action="store_true", help="Break counts down by keyword")
    parser.add_argument("--csv", metavar="PATH", help="Also write results to a CSV file")
    args = parser.parse_args()

    repos = list(find_repos(THESIS_REPOS, repo_filter=args.repo))
    if not repos:
        print(f"No classes.puml found", file=sys.stderr)
        sys.exit(1)

    rows = []
    for repo, puml in repos:
        counts = count_puml(puml)
        total = sum(counts.values())
        rows.append((repo, counts, total))

    if args.by_kind:
        header = f"{'repo':<55} {'total':>6}  " + "  ".join(f"{k:>14}" for k in KEYWORDS)
        print(header)
        print("-" * len(header))
        for repo, counts, total in rows:
            kind_cols = "  ".join(f"{counts[k]:>14}" for k in KEYWORDS)
            print(f"{repo:<55} {total:>6}  {kind_cols}")
    else:
        col = max(len(repo) for repo, _, _ in rows)
        print(f"{'repo':<{col}}  classes")
        print("-" * (col + 10))
        for repo, _, total in rows:
            print(f"{repo:<{col}}  {total}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if args.by_kind:
                writer.writerow(["repo", "total"] + KEYWORDS)
                for repo, counts, total in rows:
                    writer.writerow([repo, total] + [counts[k] for k in KEYWORDS])
            else:
                writer.writerow(["repo", "classes"])
                for repo, _, total in rows:
                    writer.writerow([repo, total])
        print(f"\nSaved to {args.csv}")


if __name__ == "__main__":
    main()
