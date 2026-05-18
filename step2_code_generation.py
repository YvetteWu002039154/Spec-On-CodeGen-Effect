"""
Step 2 — Generate code for each repo using multiple LLMs.

Usage:
    python step2_code_generation.py                     # all repos
    python step2_code_generation.py --repo ecopeque__new_banking_system
    python step2_code_generation.py --repo foo --condition nl
    python step2_code_generation.py --repo foo --models claude gpt

Reads:
    thesis_repos/<repo>/nl/input/description.txt
    thesis_repos/<repo>/uml/input/classes.puml

Writes per (condition, model):
    thesis_repos/<repo>/<condition>/outputcode/<model>/generated_code.py
    thesis_repos/<repo>/<condition>/outputcode/<model>/metadata.json

Writes per repo:
    thesis_repos/<repo>/generation_summary.json

Tests are NOT generated here — place ground-truth test files manually in:
    thesis_repos/<repo>/<condition>/tests/test_<model>.py

Required env vars (only for the models you use):
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

# ---------------------------------------------------------------------------
# Model registry — edit display names / litellm model IDs here
# ---------------------------------------------------------------------------
MODELS: dict[str, dict] = {
    "claude": {
        "display": "Claude Sonnet 4.6",
        "litellm_id": "claude-sonnet-4-6",
    },
    "gpt": {
        "display": "GPT-5.4",
        "litellm_id": "gpt-5.4",
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
THESIS_REPOS = os.path.join(os.path.dirname(__file__), "thesis_repos")

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    timeout: int = 180,
) -> tuple[str, int, float]:
    """
    Returns (response_text, output_tokens, latency_seconds).
    Raises on timeout or API error so the caller can record the failure.
    """
    import litellm  # noqa: PLC0415

    litellm.drop_params = True

    model_id = MODELS[model_key]["litellm_id"]
    t0 = time.monotonic()
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


def _find_repos(thesis_repos: str) -> list[str]:
    return sorted(
        d for d in os.listdir(thesis_repos)
        if os.path.isdir(os.path.join(thesis_repos, d)) and not d.startswith(".")
    )


# ---------------------------------------------------------------------------
# Core generation logic
# ---------------------------------------------------------------------------

def generate_for_repo(
    repo_dir: Path,
    conditions: list[str],
    model_keys: list[str],
) -> dict:
    repo_name = repo_dir.name
    summary_results = []
    started_at = datetime.now(timezone.utc).isoformat()
    ok_count = failed_count = 0

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

        for model_key in model_keys:
            label = f"{condition}/{model_key}"
            print(f"  Generating {label} ...")

            if condition == "nl":
                user_prompt = NL_USER_PROMPT.format(project_description=input_text)
            else:
                user_prompt = UML_USER_PROMPT.format(uml_code=input_text)

            entry: dict = {"repo": repo_name, "condition": condition, "model": model_key}
            try:
                raw_code, out_tokens, latency = _call_llm(
                    model_key, SYSTEM_PROMPT, user_prompt
                )
                code = _strip_fences(raw_code)

                out_dir = repo_dir / condition / "outputcode" / model_key
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "generated_code.py").write_text(code, encoding="utf-8")

                meta = {
                    "code": code,
                    "model": MODELS[model_key]["display"],
                    "output_tokens": out_tokens,
                    "latency_s": latency,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
                (out_dir / "metadata.json").write_text(
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

    summary = {
        "started_at": started_at,
        "repos": 1,
        "conditions": conditions,
        "models": {k: MODELS[k]["display"] for k in model_keys},
        "total_runs": len(summary_results),
        "results": summary_results,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "ok_count": ok_count,
        "failed_count": failed_count,
    }
    (repo_dir / "generation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate code for thesis repos using LLMs."
    )
    parser.add_argument(
        "--repo",
        metavar="FOLDER_NAME",
        help="Process a single repo folder (e.g. ecopeque__new_banking_system). "
             "Omit to process all repos in thesis_repos/.",
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
    args = parser.parse_args()

    conditions = ["nl", "uml"] if args.condition == "both" else [args.condition]

    if args.repo:
        repo_dirs = [Path(THESIS_REPOS) / args.repo]
    else:
        repo_dirs = [
            Path(THESIS_REPOS) / name
            for name in _find_repos(THESIS_REPOS)
        ]

    for repo_dir in repo_dirs:
        if not repo_dir.is_dir():
            print(f"ERROR: {repo_dir} does not exist", file=sys.stderr)
            continue
        print(f"\n→ {repo_dir.name}")
        summary = generate_for_repo(repo_dir, conditions, args.models)
        print(
            f"  Done: {summary['ok_count']} ok, {summary['failed_count']} failed  "
            f"→ generation_summary.json"
        )
        print(f"  Next: place ground-truth tests in thesis_repos/{repo_dir.name}/<condition>/tests/")
        print(f"        then run: python step3_passatk.py --repo {repo_dir.name}")


if __name__ == "__main__":
    main()
