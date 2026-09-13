"""
Count README words the SAME way step0_search_repos.py does.

Usage:
    python3 utils/count_readme_words.py README.md
"""

import argparse
import re

# Kept identical to step0_search_repos.py so counts match exactly.
MIN_README_WORDS = 100
MIN_DOMAIN_WORDS = 50

_NOISE = re.compile(
    r"(?im)^##?\s*(installation|install|setup|getting started|requirements|dependencies"
    r"|usage|running|how to run|contributing|license|acknowledgements|todo|roadmap"
    r"|changelog|authors?|credits?|contact)\b"
)


def _strip_noise(text: str) -> str:
    lines, in_noise = [], False
    for line in text.split("\n"):
        if line.strip().startswith("#"):
            in_noise = bool(_NOISE.match(line))
        if not in_noise:
            lines.append(line)
    return "\n".join(lines)


def count_words(text: str) -> tuple[int, int]:
    """Return (total_words, domain_words) exactly as step0 computes them."""
    total = len(text.split())
    domain = len(_strip_noise(text).split())
    return total, domain


def main():
    parser = argparse.ArgumentParser(
        description="Count README words the same way step0_search_repos.py does."
    )
    parser.add_argument("file", help="Text file to read, e.g. README.md")
    args = parser.parse_args()

    with open(args.file, encoding="utf-8", errors="replace") as f:
        total, domain = count_words(f.read())

    print(f"Total words : {total:>6}  {'OK' if total >= MIN_README_WORDS else f'below min ({MIN_README_WORDS})'}")
    print(f"Domain words: {domain:>6}  {'OK' if domain >= MIN_DOMAIN_WORDS else f'below min ({MIN_DOMAIN_WORDS})'}")


if __name__ == "__main__":
    main()
