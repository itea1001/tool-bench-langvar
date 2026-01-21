#!/usr/bin/env python3
"""
Run tau2-bench with translated task descriptions for language variation experiments.

This script:
1. Swaps in translated tasks.json files
2. Runs tau2 benchmark
3. Collects and saves results
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Project paths
PROJECT_ROOT = Path(__file__).parent
TAU2_ROOT = PROJECT_ROOT / "tau2-bench"
TRANSLATED_DIR = PROJECT_ROOT / "translated_tau2"
RESULTS_DIR = PROJECT_ROOT / "benchmark_results"

# Original task paths in tau2-bench
ORIGINAL_TASKS = {
    "retail": TAU2_ROOT / "data/tau2/domains/retail/tasks.json",
    "airline": TAU2_ROOT / "data/tau2/domains/airline/tasks.json",
}

# Language codes we support
LANGUAGES = ["es", "fr", "zh", "vi", "sw"]
LANGUAGE_NAMES = {
    "es": "Spanish",
    "fr": "French", 
    "zh": "Chinese",
    "vi": "Vietnamese",
    "sw": "Swahili",
    "en": "English"
}


def backup_original_tasks():
    """Backup original task files."""
    for domain, path in ORIGINAL_TASKS.items():
        backup_path = path.with_suffix(".json.original")
        if not backup_path.exists() and path.exists():
            shutil.copy(path, backup_path)
            print(f"Backed up {domain} tasks to {backup_path}")


def restore_original_tasks():
    """Restore original task files from backup."""
    for domain, path in ORIGINAL_TASKS.items():
        backup_path = path.with_suffix(".json.original")
        if backup_path.exists():
            shutil.copy(backup_path, path)
            print(f"Restored {domain} tasks from backup")


def swap_translated_tasks(lang: str, domain: str):
    """Swap in translated tasks for a language/domain combo."""
    translated_path = TRANSLATED_DIR / lang / domain / "tasks.json"
    original_path = ORIGINAL_TASKS[domain]
    
    if not translated_path.exists():
        raise FileNotFoundError(f"Translated tasks not found: {translated_path}")
    
    shutil.copy(translated_path, original_path)
    print(f"Swapped {domain} tasks with {LANGUAGE_NAMES.get(lang, lang)} translation")


def run_tau2_benchmark(domain: str, agent_llm: str, user_llm: str, 
                       num_trials: int = 1, num_tasks: int = None,
                       max_concurrency: int = 5) -> dict:
    """Run tau2 benchmark and return results."""
    cmd = [
        "tau2", "run",
        "--domain", domain,
        "--agent-llm", agent_llm,
        "--user-llm", user_llm,
        "--num-trials", str(num_trials),
        "--max-concurrency", str(max_concurrency),
    ]
    
    if num_tasks:
        cmd.extend(["--num-tasks", str(num_tasks)])
    
    print(f"Running: {' '.join(cmd)}")
    
    # Run from tau2-bench directory
    result = subprocess.run(
        cmd,
        cwd=TAU2_ROOT,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error running tau2: {result.stderr}")
        return {"error": result.stderr, "stdout": result.stdout}
    
    print(result.stdout)
    return {"success": True, "stdout": result.stdout}


def run_language_benchmark(lang: str, domain: str, agent_llm: str, user_llm: str,
                          num_trials: int = 1, num_tasks: int = None,
                          max_concurrency: int = 5) -> dict:
    """Run benchmark for a specific language/domain combination."""
    try:
        # Backup originals first time
        backup_original_tasks()
        
        # Swap in translated tasks (skip for English)
        if lang != "en":
            swap_translated_tasks(lang, domain)
        else:
            restore_original_tasks()
        
        # Run benchmark
        result = run_tau2_benchmark(
            domain=domain,
            agent_llm=agent_llm,
            user_llm=user_llm,
            num_trials=num_trials,
            num_tasks=num_tasks,
            max_concurrency=max_concurrency
        )
        
        return result
        
    finally:
        # Always restore original tasks after run
        restore_original_tasks()


def collect_results(lang: str, domain: str) -> dict:
    """Collect and parse results from the most recent simulation."""
    sim_dir = TAU2_ROOT / "data/tau2/simulations"
    if not sim_dir.exists():
        return {"error": "No simulations directory found"}
    
    # Find most recent simulation file for this domain
    sim_files = sorted(sim_dir.glob(f"*{domain}*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not sim_files:
        return {"error": f"No simulation files found for {domain}"}
    
    latest = sim_files[0]
    with open(latest) as f:
        data = json.load(f)
    
    return {
        "file": str(latest),
        "data": data
    }


def main():
    parser = argparse.ArgumentParser(description="Run tau2-bench with translated tasks")
    parser.add_argument("--lang", type=str, required=True, 
                       help=f"Language code: en, {', '.join(LANGUAGES)}")
    parser.add_argument("--domain", type=str, required=True,
                       choices=["retail", "airline"],
                       help="Domain to evaluate")
    parser.add_argument("--agent-llm", type=str, default="gpt-4.1",
                       help="Agent LLM model")
    parser.add_argument("--user-llm", type=str, default="gpt-4.1",
                       help="User simulator LLM model")
    parser.add_argument("--num-trials", type=int, default=1,
                       help="Number of trials per task")
    parser.add_argument("--num-tasks", type=int, default=None,
                       help="Limit number of tasks (for testing)")
    parser.add_argument("--max-concurrency", type=int, default=5,
                       help="Max concurrent simulations")
    parser.add_argument("--save-results", action="store_true",
                       help="Save results to file")
    
    args = parser.parse_args()
    
    if args.lang != "en" and args.lang not in LANGUAGES:
        print(f"Error: Unsupported language '{args.lang}'. Supported: en, {', '.join(LANGUAGES)}")
        sys.exit(1)
    
    # Check translated tasks exist
    if args.lang != "en":
        translated_path = TRANSLATED_DIR / args.lang / args.domain / "tasks.json"
        if not translated_path.exists():
            print(f"Error: Translated tasks not found at {translated_path}")
            print("Run translate_tau2bench.py first to generate translations.")
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"Running tau2-bench Language Variation Experiment")
    print(f"Language: {LANGUAGE_NAMES.get(args.lang, args.lang)}")
    print(f"Domain: {args.domain}")
    print(f"Agent LLM: {args.agent_llm}")
    print(f"User LLM: {args.user_llm}")
    print(f"{'='*60}\n")
    
    # Run the benchmark
    result = run_language_benchmark(
        lang=args.lang,
        domain=args.domain,
        agent_llm=args.agent_llm,
        user_llm=args.user_llm,
        num_trials=args.num_trials,
        num_tasks=args.num_tasks,
        max_concurrency=args.max_concurrency
    )
    
    if args.save_results:
        # Collect and save results
        sim_results = collect_results(args.lang, args.domain)
        
        results_dir = RESULTS_DIR / args.lang / args.domain
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"results_{args.agent_llm}_{timestamp}.json"
        
        output = {
            "language": args.lang,
            "language_name": LANGUAGE_NAMES.get(args.lang, args.lang),
            "domain": args.domain,
            "agent_llm": args.agent_llm,
            "user_llm": args.user_llm,
            "num_trials": args.num_trials,
            "num_tasks": args.num_tasks,
            "timestamp": timestamp,
            "run_result": result,
            "simulation_results": sim_results
        }
        
        with open(results_file, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()

