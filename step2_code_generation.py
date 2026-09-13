"""
Generate code for each repo using multiple LLMs.

Usage:
    python step2_code_generation.py                     # all repos, 1 run (run0)
    python step2_code_generation.py --repo ecopque__new_banking_system
    python step2_code_generation.py --repo foo --condition nl
    python step2_code_generation.py --repo foo --models claude gpt
    python step2_code_generation.py --runs 10           # runs 0..9 
    python step2_code_generation.py --run-index 3 5 --skip-existing   # (re)fill only runs 3 and 5
    python step2_code_generation.py --runs 10 --skip-existing         # fill any missing of 0..9

Reads:
    repos/<repo>/nl/input/description.txt
    repos/<repo>/uml/input/classes.puml

Writes per (condition, model, run):
    repos/<repo>/<condition>/outputcode/<model>.run<N>.py
    repos/<repo>/<condition>/outputcode/<model>.run<N>.metadata.json

Required env vars:
    ANTHROPIC_API_KEY
    OPENAI_API_KEY
    GOOGLE_API_KEY
    DEEPSEEK_API_KEY
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

MODELS: dict[str, dict] = {
    "claude": {
        "display": "Claude Sonnet 4.6",
        "litellm_id": "claude-sonnet-4-6",
    },
    "gpt": {
        "display": "GPT-5.2",
        "litellm_id": "gpt-5.2",
    },
    "gemini": 
    {
    "display": "Gemini 3.1 Pro",
    "litellm_id": "gemini/gemini-3.1-pro-preview",
    },
    "deepseek": {
        "display": "DeepSeek V4-Pro",
        "litellm_id": "deepseek/deepseek-v4-pro",
    },
}

CONDITIONS = ("nl", "uml")
REPOS_DIR = os.path.join(os.path.dirname(__file__), "repos")

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert Python software engineer.
Generate a complete, working Python implementation based on the specification provided.
Requirements:
- Implement ALL classes, methods, and relationships described in the specification
- Follow Python OOP best practices (proper __init__, encapsulation, inheritance)
- Include all business logic rules mentioned (e.g. validation, limits, history)
- Use type hints where appropriate
- Do NOT add features not described in the specification
- Do NOT include explanations, comments describing your approach, or markdown fences
- Output ONLY valid, runnable Python code\
"""

NL_USER_PROMPT = """\
Implement the following Python system from this natural language specification:

{project_description}

Generate the complete Python implementation now:\
"""

UML_USER_PROMPT = """\
Implement the following Python system from this natural language specification:

{uml_code}

The @startuml / @enduml block is a PlantUML class diagram showing all classes, \
attributes, methods, and relationships. Implement every class and relationship shown.
Generate the complete Python implementation now:\
"""


# -------------------------------Helpers-------------------------------------

def _strip_fences(text: str) -> str:
    """Remove leading/trailing ```python ... ``` fences if present."""
    text = text.strip()
    text = re.sub(r"^```(?:python)?\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _call_llm(
    model_key: str,
    system: str,
    user: str,
    timeout: int = 600,
    max_retries: int = 2,
) -> tuple[str, int, float]:
    """
    Returns (response_text, output_tokens, latency_seconds).
    Raises after max_retries+1 failed attempts.
    """
    import litellm  # noqa: PLC0415

    litellm.drop_params = True
    model_id = MODELS[model_key]["litellm_id"]

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0:
            backoff = 5 * (2 ** (attempt - 1))
            print(
                f"    retry {attempt}/{max_retries} in {backoff}s "
                f"({type(last_exc).__name__}: {last_exc})",
                file=sys.stderr,
            )
            time.sleep(backoff)

        t0 = time.monotonic()
        try:
            resp = litellm.completion(
                model=model_id,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                request_timeout=timeout,
            )
            latency = round(time.monotonic() - t0, 2)
            text = resp.choices[0].message.content or ""
            tokens = (resp.usage.completion_tokens or 0) if resp.usage else 0
            return text, tokens, latency
        except Exception as exc:
            last_exc = exc

    raise last_exc


def _find_repos(repos: str) -> list[str]:
    return sorted(
        d for d in os.listdir(repos)
        if os.path.isdir(os.path.join(repos, d)) and not d.startswith(".")
    )

# ---------------------------------------------------------------------------

def generate_for_repo(
    repo_dir: Path,
    conditions: list[str],
    model_keys: list[str],
    run_indices: list[int],
    skip_existing: bool = False,
    timeout: int = 600,
    max_retries: int = 2,
) -> dict:
    repo_name = repo_dir.name
    summary_results = []
    started_at = datetime.now(timezone.utc).isoformat()
    ok_count = failed_count = skipped_count = 0

    for condition in conditions:
        input_file = (
            repo_dir / condition / "input" / (
                "description.txt" if condition == "nl" else "classes.puml"
            )
        )
        if not input_file.exists():
            print(f"  [skip {condition}] {input_file} not found")
            continue

        input_text = input_file.read_text(encoding="utf-8")
        out_dir = repo_dir / condition / "outputcode"

        if condition == "nl":
            user_prompt = NL_USER_PROMPT.format(project_description=input_text)
        else:
            user_prompt = UML_USER_PROMPT.format(uml_code=input_text)

        for model_key in model_keys:
            for run in run_indices:
                label = f"{condition}/{model_key}.run{run}"
                out_file = out_dir / f"{model_key}.run{run}.py"
                meta_file = out_dir / f"{model_key}.run{run}.metadata.json"

                if skip_existing and out_file.exists() and out_file.stat().st_size > 100:
                    print(f"  Skipping {label} (exists)")
                    skipped_count += 1
                    summary_results.append({
                        "repo": repo_name, "condition": condition,
                        "model": model_key, "run": run,
                        "status": "cached", "code_chars": out_file.stat().st_size,
                    })
                    continue
                print(f"  Generating {label} ...")

                entry: dict = {
                    "repo": repo_name, "condition": condition,
                    "model": model_key, "run": run,
                }
                try:
                    raw_code, out_tokens, latency = _call_llm(
                        model_key, SYSTEM_PROMPT, user_prompt,
                        timeout=timeout, max_retries=max_retries,
                    )
                    code = _strip_fences(raw_code)

                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_file.write_text(code, encoding="utf-8")

                    meta = {
                        "code": code,
                        "model": MODELS[model_key]["display"],
                        "run": run,
                        "output_tokens": out_tokens,
                        "latency_s": latency,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    meta_file.write_text(
                        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
                    )

                    entry.update(
                        status="ok",
                        output_tokens=out_tokens,
                        latency_s=latency,
                        code_chars=len(code),
                    )
                    ok_count += 1
                    print(f"    ✓ {label}  ({out_tokens} tokens, {latency}s)")

                except Exception as exc:
                    entry.update(status="error", error=str(exc))
                    failed_count += 1
                    print(f"    ✗ {label}  ERROR: {exc}", file=sys.stderr)

                summary_results.append(entry)

    # This summary is returned only for the run's console output.
    summary = {
        "started_at": started_at,
        "repos": 1,
        "conditions": conditions,
        "models": {k: MODELS[k]["display"] for k in model_keys},
        "run_indices": run_indices,
        "total_runs": len(summary_results),
        "results": summary_results,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "ok_count": ok_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
    }
    return summary

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate code for thesis repos using LLMs."
    )
    parser.add_argument(
        "--repo",
        metavar="FOLDER_NAME",
        help="Process a single repo folder (e.g. ecopque__new_banking_system). "
             "Omit to process all repos in repos/.",
    )
    parser.add_argument(
        "--condition",
        choices=["nl", "uml", "both"],
        default="both",
        help="Which condition to generate (default: both)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        choices=list(MODELS),
        default=list(MODELS),
        metavar="MODEL",
        help=f"Models to use (default: all). Choices: {', '.join(MODELS)}",
    )
    parser.add_argument(
        "--runs", type=int, default=1, metavar="N",
        help="Generate N runs per (condition, model), indexed 0..N-1 "
             "(default: 1). Use for internal-quality sampling, e.g. --runs 10.",
    )
    parser.add_argument(
        "--run-index", type=int, nargs="+", default=None, metavar="K",
        help="Generate only these specific run indices (e.g. --run-index 3 5). "
             "Overrides --runs; use to refill runs that failed previously.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip (condition, model, run) triples whose .run<N>.py already "
             "exists. Combine with --runs/--run-index to fill only missing runs.",
    )
    parser.add_argument(
        "--timeout", type=int, default=600,
        help="Per-request timeout in seconds (default: 600).",
    )
    parser.add_argument(
        "--max-retries", type=int, default=2,
        help="Retries on transient API errors with exponential backoff (default: 2).",
    )
    args = parser.parse_args()

    conditions = ["nl", "uml"] if args.condition == "both" else [args.condition]

    if args.run_index is not None:
        run_indices = sorted(set(args.run_index))
    else:
        run_indices = list(range(args.runs))

    if args.repo:
        repo_dirs = [Path(REPOS_DIR) / args.repo]
    else:
        repo_dirs = [
            Path(REPOS_DIR) / name
            for name in _find_repos(REPOS_DIR)
        ]

    for repo_dir in repo_dirs:
        if not repo_dir.is_dir():
            print(f"ERROR: {repo_dir} does not exist", file=sys.stderr)
            continue
        print(f"\n→ {repo_dir.name}  (runs: {run_indices})")
        summary = generate_for_repo(
            repo_dir, conditions, args.models, run_indices,
            skip_existing=args.skip_existing,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )
        print(
            f"  Done: {summary['ok_count']} ok, {summary['failed_count']} failed, "
            f"{summary.get('skipped_count', 0)} skipped  → per-run metadata.json"
        )
        print(f"  Next: place ground-truth tests in repos/{repo_dir.name}/<condition>/tests/")
        print(f"        then run: python step3_functional_correctness.py --repo {repo_dir.name}")
        print(f"              and: python step3_structural_fidelity.py --repo {repo_dir.name}")


if __name__ == "__main__":
    main()
