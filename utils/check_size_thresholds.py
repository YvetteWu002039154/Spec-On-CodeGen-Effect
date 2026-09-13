"""
Check a generated code file against method size (<=30 lines) and class size (<=75 lines) thresholds.

Usage:
    python3 utils/check_size_thresholds.py repos/<owner>__<repo> --run 0 --model claude --track uml
"""

import argparse
import ast
import os
import sys

METHOD_MAX = 30
CLASS_MAX = 75


def count_lines(node, source_lines):
    return sum(1 for line in source_lines[node.lineno - 1 : node.end_lineno] if line.strip())


def analyze_file(path):
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
            if count_lines(node, source_lines) > CLASS_MAX:
                class_fail += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method_total += 1
            if count_lines(node, source_lines) > METHOD_MAX:
                method_fail += 1

    return class_total, class_fail, method_total, method_fail, None


def main():
    parser = argparse.ArgumentParser(
        description="Check a generated code file against method/class size thresholds."
    )
    parser.add_argument("repo", help="Repo dir, e.g. repos/<owner>__<repo>")
    parser.add_argument("--run", type=int, required=True, metavar="N", help="Run index")
    parser.add_argument("--model", required=True, metavar="NAME", help="Model name")
    parser.add_argument("--track", required=True, choices=["nl", "uml"], help="Track")
    args = parser.parse_args()

    # <model>.run<N>.py, as written by step2_code_generation.
    path = os.path.join(args.repo, args.track, "outputcode", f"{args.model}.run{args.run}.py")
    if not os.path.isfile(path):
        print(f"Not found: {path}")
        sys.exit(1)

    print(f"Thresholds — method: <={METHOD_MAX} lines, class: <={CLASS_MAX} lines")

    class_total, class_fail, method_total, method_fail, err = analyze_file(path)
    if err:
        print(f"⚠️  {path}\n   Parse error: {err}")
        sys.exit(1)

    has_violation = class_fail > 0 or method_fail > 0
    print(f"{'❌' if has_violation else '✅'} {path}")
    print(f"   Class  : {class_fail}/{class_total} fail (>{CLASS_MAX} lines)")
    print(f"   Method : {method_fail}/{method_total} fail (>{METHOD_MAX} lines)")

    sys.exit(1 if has_violation else 0)


if __name__ == "__main__":
    main()
