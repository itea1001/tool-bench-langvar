#!/usr/bin/env python3
"""
Run tau2-bench with multilingual user simulator.

This script modifies the user simulator to speak in the target language
by patching the simulation guidelines at runtime.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path

# Language codes and full names
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "zh": "Chinese",
    "vi": "Vietnamese",
    "sw": "Swahili",
}

LANGUAGE_INSTRUCTION = """
## Language
You MUST respond in {language} only. All your messages should be in {language}.
Do not switch to English or any other language.
"""

def patch_simulation_guidelines(lang: str, tau2_bench_path: Path):
    """
    Create a patched version of simulation guidelines that includes language instruction.
    """
    guidelines_path = tau2_bench_path / "data" / "tau2" / "user_simulator" / "simulation_guidelines.md"
    guidelines_tools_path = tau2_bench_path / "data" / "tau2" / "user_simulator" / "simulation_guidelines_tools.md"
    
    # Read original guidelines
    with open(guidelines_path, 'r') as f:
        original = f.read()
    
    # Create backup if not exists
    backup_path = guidelines_path.with_suffix('.md.backup')
    if not backup_path.exists():
        with open(backup_path, 'w') as f:
            f.write(original)
    
    # Add language instruction
    language_name = LANGUAGES[lang]
    patched = original + "\n" + LANGUAGE_INSTRUCTION.format(language=language_name)
    
    with open(guidelines_path, 'w') as f:
        f.write(patched)
    
    # Do the same for tools version if exists
    if guidelines_tools_path.exists():
        with open(guidelines_tools_path, 'r') as f:
            original_tools = f.read()
        
        backup_tools_path = guidelines_tools_path.with_suffix('.md.backup')
        if not backup_tools_path.exists():
            with open(backup_tools_path, 'w') as f:
                f.write(original_tools)
        
        patched_tools = original_tools + "\n" + LANGUAGE_INSTRUCTION.format(language=language_name)
        with open(guidelines_tools_path, 'w') as f:
            f.write(patched_tools)
    
    print(f"Patched simulation guidelines for {language_name}")


def restore_simulation_guidelines(tau2_bench_path: Path):
    """
    Restore original simulation guidelines from backup.
    """
    guidelines_path = tau2_bench_path / "data" / "tau2" / "user_simulator" / "simulation_guidelines.md"
    guidelines_tools_path = tau2_bench_path / "data" / "tau2" / "user_simulator" / "simulation_guidelines_tools.md"
    
    backup_path = guidelines_path.with_suffix('.md.backup')
    if backup_path.exists():
        with open(backup_path, 'r') as f:
            original = f.read()
        with open(guidelines_path, 'w') as f:
            f.write(original)
        print("Restored simulation guidelines")
    
    backup_tools_path = guidelines_tools_path.with_suffix('.md.backup')
    if backup_tools_path.exists():
        with open(backup_tools_path, 'r') as f:
            original = f.read()
        with open(guidelines_tools_path, 'w') as f:
            f.write(original)


def main():
    parser = argparse.ArgumentParser(description="Run tau2-bench with multilingual user")
    parser.add_argument("--lang", type=str, required=True, choices=list(LANGUAGES.keys()),
                        help="Target language for user simulator")
    parser.add_argument("--domain", type=str, default="retail",
                        choices=["retail", "airline", "telecom"],
                        help="Domain to run")
    parser.add_argument("--agent-llm", type=str, default="gpt-4.1-mini",
                        help="Agent LLM model")
    parser.add_argument("--user-llm", type=str, default="gpt-4.1-mini",
                        help="User simulator LLM model")
    parser.add_argument("--num-tasks", type=int, default=5,
                        help="Number of tasks to run")
    parser.add_argument("--restore-only", action="store_true",
                        help="Only restore guidelines, don't run")
    args = parser.parse_args()
    
    # Find tau2-bench path
    script_dir = Path(__file__).parent
    tau2_bench_path = script_dir / "tau2-bench"
    
    if args.restore_only:
        restore_simulation_guidelines(tau2_bench_path)
        return
    
    try:
        # Patch guidelines for target language
        if args.lang != "en":
            patch_simulation_guidelines(args.lang, tau2_bench_path)
        
        # Build tau2 run command
        cmd = [
            "tau2", "run",
            "--domain", args.domain,
            "--agent-llm", args.agent_llm,
            "--user-llm", args.user_llm,
            "--num-tasks", str(args.num_tasks),
        ]
        
        print(f"Running: {' '.join(cmd)}")
        print(f"Language: {LANGUAGES[args.lang]}")
        
        # Run tau2
        result = subprocess.run(cmd, cwd=tau2_bench_path)
        
    finally:
        # Always restore original guidelines
        if args.lang != "en":
            restore_simulation_guidelines(tau2_bench_path)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

