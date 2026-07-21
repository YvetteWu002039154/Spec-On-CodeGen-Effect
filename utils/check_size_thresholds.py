"""
Check all generated_code.py files under a repo directory against method size
(≤30 lines) and class size (≤75 lines) thresholds.

Usage:
    python3 utils/check_size_thresholds.py thesis_repos/<owner>__<repo>
    python3 utils/check_size_thresholds.py thesis_repos/<owner>__<repo> --verbose
    python3 utils/check_size_thresholds.py thesis_repos/
    python3 utils/check_size_thresholds.py thesis_repos/<owner>__<repo> --method 20 --class 50
"""

import argparse
import ast
import os
import sys


def count_lines(node, source_lines):
    start = node.lineno - 1
    end = node.end_lineno
    return sum(1 for line in source_lines[start:end] if line.strip())


def analyze_file(path, method_max, class_max):
    """Return (class_total, class_fail, method_total, method_fail, parse_error)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return 0, 0, 0, 0, str(e)

    source_lines = source.splitlines()
    class_total = class_fail = method_total = method_fail = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_total += 1
            if count_lines(node, source_lines) > class_max:
                class_fail += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_total += 1
            if count_lines(node, source_lines) > method_max:
                method_fail += 1

    return class_total, class_fail, method_total, method_fail, None


def find_generated_files(root):
    for dirpath, _, filenames in os.walk(root):
        for fname in sorted(filenames):
            if fname.startswith("generated_code") and fname.endswith(".py"):
                yield os.path.join(dirpath, fname)


def main():
    parser = argparse.ArgumentParser(
        description="Check generated_code.py files against method/class size thresholds."
    )
    parser.add_argument("repo_dir", nargs="?", default=".", help="Root directory to search")
    parser.add_argument("--method", type=int, default=30, metavar="N", help="Max lines per method (default: 30)")
    parser.add_argument("--class", dest="class_max", type=int, default=75, metavar="N", help="Max lines per class (default: 75)")
    parser.add_argument("--verbose", action="store_true", help="Print each failing class/method")
    args = parser.parse_args()

    files = sorted(find_generated_files(args.repo_dir))
    if not files:
        print(f"No generated_code*.py files found under {args.repo_dir!r}")
        sys.exit(0)

    print(f"Thresholds — method: <={args.method} lines, class: <={args.class_max} lines")
    print(f"Found {len(files)} file(s)\n")

    any_violation = False
    for path in files:
        rel = os.path.relpath(path, args.repo_dir)
        class_total, class_fail, method_total, method_fail, err = analyze_file(
            path, args.method, args.class_max
        )
        if err:
            print(f"⚠️  {rel}\n   Parse error: {err}\n")
            any_violation = True
            continue

        has_violation = class_fail > 0 or method_fail > 0
        icon = "❌" if has_violation else "✅"
        print(f"{icon} {rel}")
        print(f"   Class  : {class_fail}/{class_total} fail (>{args.class_max} lines)")
        print(f"   Method : {method_fail}/{method_total} fail (>{args.method} lines)")
        print()

        if has_violation:
            any_violation = True

    sys.exit(1 if any_violation else 0)


if __name__ == "__main__":
    main()
