"""
Count PlantUML type declarations in a repo's uml/input/classes.puml.

Usage:
    python3 utils/count_uml_classes.py --repo hackstarsj__AmazonCloneEcommerceProjectUsingDjangoReact
"""

import argparse
import os
import re
import sys

REPOS_DIR = os.path.join(os.path.dirname(__file__), "..", "repos")

KEYWORDS = ["abstract class", "interface", "enum", "protocol", "entity", "class"]
PATTERN = re.compile(r"^\s*(" + "|".join(re.escape(k) for k in KEYWORDS) + r")\s+")


def count_puml(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return sum(1 for line in f if PATTERN.match(line))


def main():
    parser = argparse.ArgumentParser(
        description="Count UML type declarations in a repo's classes.puml."
    )
    parser.add_argument("--repo", required=True, metavar="NAME", help="Repo folder name under repos/")
    args = parser.parse_args()

    puml = os.path.join(REPOS_DIR, args.repo, "uml", "input", "classes.puml")
    if not os.path.isfile(puml):
        print(f"No classes.puml found for {args.repo}", file=sys.stderr)
        sys.exit(1)

    print(f"{args.repo}  {count_puml(puml)}")


if __name__ == "__main__":
    main()
