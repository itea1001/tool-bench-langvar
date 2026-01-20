#!/usr/bin/env python3
"""
Runner script for BFCL Language Variation benchmarks.
Swaps translated data files into BFCL and runs the benchmark.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
TRANSLATED_DATA_DIR = PROJECT_ROOT / "translated_data"
BFCL_DATA_DIR = PROJECT_ROOT / "gorilla" / "berkeley-function-call-leaderboard" / "bfcl_eval" / "data"
BACKUP_DIR = PROJECT_ROOT / "original_data_backup"

# Test categories and their data files
TEST_CATEGORIES = {
    "simple_python": "BFCL_v4_simple_python.json",
    "parallel": "BFCL_v4_parallel.json",
    "multiple": "BFCL_v4_multiple.json",
    "parallel_multiple": "BFCL_v4_parallel_multiple.json",
    "irrelevance": "BFCL_v4_irrelevance.json",
    "simple_java": "BFCL_v4_simple_java.json",
    "simple_javascript": "BFCL_v4_simple_javascript.json",
}

LANGUAGES = ["es", "fr", "zh", "vi", "sw"]


def backup_original_data():
    """Backup original BFCL data files."""
    BACKUP_DIR.mkdir(exist_ok=True)
    for category, filename in TEST_CATEGORIES.items():
        src = BFCL_DATA_DIR / filename
        dst = BACKUP_DIR / filename
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            print(f"Backed up: {filename}")


def restore_original_data():
    """Restore original BFCL data files from backup."""
    for category, filename in TEST_CATEGORIES.items():
        src = BACKUP_DIR / filename
        dst = BFCL_DATA_DIR / filename
        if src.exists():
            shutil.copy2(src, dst)
            print(f"Restored: {filename}")


def swap_to_language(lang: str, categories: list[str]):
    """Swap BFCL data files to translated versions for a given language."""
    for category in categories:
        filename = TEST_CATEGORIES[category]
        src = TRANSLATED_DATA_DIR / lang / filename
        dst = BFCL_DATA_DIR / filename
        if src.exists():
            shutil.copy2(src, dst)
            print(f"Swapped {filename} to {lang}")
        else:
            print(f"Warning: {src} not found!")


def clear_cached_results(model: str, categories: list[str]):
    """Clear cached results to force regeneration."""
    result_dir = BFCL_DATA_DIR.parent.parent / "result" / model / "non_live"
    if result_dir.exists():
        for cat in categories:
            result_file = result_dir / f"BFCL_v4_{cat}_result.json"
            if result_file.exists():
                result_file.unlink()
                print(f"Cleared cache: {result_file.name}")


def run_bfcl_generate(model: str, categories: list[str], num_threads: int = 1):
    """Run BFCL generation for given categories."""
    # Clear cached results first
    clear_cached_results(model, categories)
    
    cats = ",".join(categories)
    cmd = [
        "bfcl", "generate",
        "--model", model,
        "--test-category", cats,
        "--num-threads", str(num_threads),
        "--include-input-log"
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(BFCL_DATA_DIR.parent.parent))
    return result.returncode


def run_bfcl_evaluate(model: str, categories: list[str]):
    """Run BFCL evaluation for given categories."""
    cats = ",".join(categories)
    cmd = [
        "bfcl", "evaluate",
        "--model", model,
        "--test-category", cats
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(BFCL_DATA_DIR.parent.parent))
    return result.returncode


def save_results(lang: str, model: str, categories: list[str]):
    """Save results to a language-specific directory."""
    results_dir = PROJECT_ROOT / "benchmark_results" / lang
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy score files
    score_dir = BFCL_DATA_DIR.parent.parent / "score"
    for csv_file in score_dir.glob("*.csv"):
        shutil.copy2(csv_file, results_dir / csv_file.name)
    
    # Copy model result files
    result_dir = BFCL_DATA_DIR.parent.parent / "result" / model
    if result_dir.exists():
        model_results = results_dir / "model_results"
        model_results.mkdir(exist_ok=True)
        for cat in categories:
            result_file = result_dir / f"BFCL_v4_{cat}_result.json"
            if result_file.exists():
                shutil.copy2(result_file, model_results / result_file.name)
    
    print(f"Results saved to {results_dir}")


def main():
    parser = argparse.ArgumentParser(description="Run BFCL with language variation")
    parser.add_argument("--lang", choices=LANGUAGES + ["en"], required=True,
                        help="Language to test (en for original English)")
    parser.add_argument("--model", required=True,
                        help="Model to test (e.g., gpt-4o-2024-11-20-FC)")
    parser.add_argument("--categories", nargs="+", default=list(TEST_CATEGORIES.keys()),
                        help="Test categories to run")
    parser.add_argument("--num-threads", type=int, default=1,
                        help="Number of threads for API calls")
    parser.add_argument("--generate-only", action="store_true",
                        help="Only generate, don't evaluate")
    parser.add_argument("--evaluate-only", action="store_true",
                        help="Only evaluate, don't generate")
    parser.add_argument("--restore", action="store_true",
                        help="Restore original data files and exit")
    
    args = parser.parse_args()
    
    # Validate categories
    for cat in args.categories:
        if cat not in TEST_CATEGORIES:
            print(f"Error: Unknown category {cat}")
            print(f"Available: {list(TEST_CATEGORIES.keys())}")
            sys.exit(1)
    
    # Restore mode
    if args.restore:
        restore_original_data()
        return
    
    # Backup original data
    backup_original_data()
    
    try:
        # Swap data files
        if args.lang == "en":
            restore_original_data()
            print("Using original English data")
        else:
            swap_to_language(args.lang, args.categories)
        
        # Run benchmark
        if not args.evaluate_only:
            ret = run_bfcl_generate(args.model, args.categories, args.num_threads)
            if ret != 0:
                print(f"Generation failed with code {ret}")
                return
        
        if not args.generate_only:
            run_bfcl_evaluate(args.model, args.categories)
        
        # Save results
        save_results(args.lang, args.model, args.categories)
    
    finally:
        # Always restore original data
        restore_original_data()


if __name__ == "__main__":
    main()

