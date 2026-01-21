"""
τ²-bench Language Variation Translation Script

This script translates:
1. Policy documents (policy.md) for each domain
2. Task instructions and user scenarios (tasks.json)
3. User simulator instructions

Languages:
- High-resource: Spanish (es), French (fr), Chinese (zh)
- Low-resource: Vietnamese (vi), Swahili (sw)

Things that should NOT be changed:
- Function/tool names
- Parameter names
- Parameter types
- Order IDs, user IDs, product IDs
- JSON structure
- Code/API format specifications
"""

import json
import os
import argparse
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import openai
from tqdm import tqdm
import re

MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds

# Language configurations
LANGUAGES = {
    "es": "Spanish",
    "fr": "French",
    "zh": "Chinese",
    "vi": "Vietnamese",
    "sw": "Swahili"
}

# Paths
TAU2_DATA_DIR = Path("tau2-bench/data/tau2/domains")
OUTPUT_DIR = Path("translated_tau2")

# Domains to translate
DOMAINS = ["retail", "airline", "telecom"]


def translate_text(text: str, target_lang: str, client: openai.OpenAI, preserve_ids: bool = True) -> str:
    """Translate text to target language using OpenAI API with retry logic."""
    if not text or not text.strip():
        return text
    
    preserve_note = ""
    if preserve_ids:
        preserve_note = """
IMPORTANT: Keep the following EXACTLY as they are (do not translate):
- Order IDs (e.g., #W2378156)
- User IDs, product IDs, item IDs (any alphanumeric IDs)
- Email addresses
- Zip codes
- Function/tool names
- Parameter names
- JSON keys
- Code blocks and technical specifications
- Markdown formatting (headers, bullets, bold, etc.)
"""

    prompt = f"""Translate the following text to {LANGUAGES[target_lang]}.
{preserve_note}
Only return the translated text, nothing else.

Text to translate:
{text}"""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except (openai.RateLimitError, openai.APIError, openai.PermissionDeniedError) as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"\nAPI error: {e}. Retrying in {wait_time}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                raise
    return text


def translate_policy(policy_path: Path, output_path: Path, target_lang: str, client: openai.OpenAI):
    """Translate policy markdown document."""
    print(f"Translating policy: {policy_path}")
    
    with open(policy_path, 'r') as f:
        policy_text = f.read()
    
    translated = translate_text(policy_text, target_lang, client, preserve_ids=True)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(translated)
    
    print(f"Saved translated policy to {output_path}")


def translate_task_instructions(instructions: Dict[str, Any], target_lang: str, client: openai.OpenAI) -> Dict[str, Any]:
    """Translate task instructions while preserving structure and IDs."""
    translated = instructions.copy()
    
    # Translate task_instructions
    if "task_instructions" in translated:
        translated["task_instructions"] = translate_text(
            translated["task_instructions"], target_lang, client, preserve_ids=True
        )
    
    # Translate reason_for_call
    if "reason_for_call" in translated:
        translated["reason_for_call"] = translate_text(
            translated["reason_for_call"], target_lang, client, preserve_ids=True
        )
    
    # Translate known_info
    if "known_info" in translated:
        translated["known_info"] = translate_text(
            translated["known_info"], target_lang, client, preserve_ids=True
        )
    
    # Translate unknown_info
    if "unknown_info" in translated:
        translated["unknown_info"] = translate_text(
            translated["unknown_info"], target_lang, client, preserve_ids=True
        )
    
    # Keep domain unchanged
    # "domain" should stay as is
    
    return translated


def translate_user_scenario(scenario: Dict[str, Any], target_lang: str, client: openai.OpenAI) -> Dict[str, Any]:
    """Translate user scenario."""
    if not scenario:
        return scenario
    
    translated = scenario.copy()
    
    # Translate persona if present
    if "persona" in translated and translated["persona"]:
        translated["persona"] = translate_text(translated["persona"], target_lang, client)
    
    # Translate instructions
    if "instructions" in translated:
        translated["instructions"] = translate_task_instructions(
            translated["instructions"], target_lang, client
        )
    
    return translated


def translate_task(task: Dict[str, Any], target_lang: str, client: openai.OpenAI) -> Dict[str, Any]:
    """Translate a single task entry."""
    translated = task.copy()
    
    # Translate description if it contains text
    if "description" in translated and translated["description"]:
        desc = translated["description"]
        if isinstance(desc, dict):
            for key in ["purpose", "notes"]:
                if key in desc and desc[key]:
                    desc[key] = translate_text(desc[key], target_lang, client)
            # Keep relevant_policies as is (these are policy references)
    
    # Translate user_scenario
    if "user_scenario" in translated:
        translated["user_scenario"] = translate_user_scenario(
            translated["user_scenario"], target_lang, client
        )
    
    # Keep evaluation_criteria, initial_state, actions unchanged
    # These contain function names, IDs, and technical specs
    
    return translated


def translate_tasks_file(input_path: Path, output_path: Path, target_lang: str, client: openai.OpenAI, resume: bool = False):
    """Translate tasks.json file with checkpointing."""
    print(f"Translating tasks: {input_path}")
    
    with open(input_path, 'r') as f:
        tasks = json.load(f)
    
    # Load existing progress if resuming
    translated_tasks = []
    start_idx = 0
    checkpoint_path = output_path.with_suffix('.checkpoint.json')
    
    if resume and checkpoint_path.exists():
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
            translated_tasks = checkpoint.get('translated', [])
            start_idx = len(translated_tasks)
        print(f"Resuming from task {start_idx}...")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    for i, task in enumerate(tqdm(tasks[start_idx:], desc=f"Translating tasks to {target_lang}", initial=start_idx, total=len(tasks))):
        translated_task = translate_task(task, target_lang, client)
        translated_tasks.append(translated_task)
        
        # Save checkpoint every 5 tasks
        if (start_idx + i + 1) % 5 == 0:
            with open(checkpoint_path, 'w') as f:
                json.dump({'translated': translated_tasks}, f, ensure_ascii=False)
    
    # Save final output
    with open(output_path, 'w') as f:
        json.dump(translated_tasks, f, ensure_ascii=False, indent=2)
    
    # Remove checkpoint
    if checkpoint_path.exists():
        checkpoint_path.unlink()
    
    print(f"Saved translated tasks to {output_path}")


def translate_domain(domain: str, target_lang: str, client: openai.OpenAI, resume: bool = False, tasks_only: bool = False, policy_only: bool = False):
    """Translate all files for a domain."""
    domain_input = TAU2_DATA_DIR / domain
    domain_output = OUTPUT_DIR / target_lang / domain
    
    if not domain_input.exists():
        print(f"Domain not found: {domain_input}")
        return
    
    print(f"\n=== Translating {domain} domain to {LANGUAGES[target_lang]} ===")
    
    if not tasks_only:
        # Translate policy
        policy_path = domain_input / "policy.md"
        if policy_path.exists():
            translate_policy(
                policy_path,
                domain_output / "policy.md",
                target_lang,
                client
            )
    
    if not policy_only:
        # Translate tasks
        tasks_path = domain_input / "tasks.json"
        if tasks_path.exists():
            translate_tasks_file(
                tasks_path,
                domain_output / "tasks.json",
                target_lang,
                client,
                resume
            )
    
    # Copy db.json and split_tasks.json unchanged (they contain data, not natural language)
    for fname in ["db.json", "split_tasks.json"]:
        src = domain_input / fname
        if src.exists():
            import shutil
            dst = domain_output / fname
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
            print(f"Copied {fname} (unchanged)")


def main():
    parser = argparse.ArgumentParser(description="Translate τ²-bench data for language variation experiments")
    parser.add_argument("--lang", type=str, choices=list(LANGUAGES.keys()), required=True,
                        help="Target language code")
    parser.add_argument("--domain", type=str, choices=DOMAINS + ["all"], default="all",
                        help="Domain to translate (default: all)")
    parser.add_argument("--tasks-only", action="store_true",
                        help="Only translate tasks.json")
    parser.add_argument("--policy-only", action="store_true",
                        help="Only translate policy.md")
    parser.add_argument("--api-key", type=str, default=None,
                        help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from previous progress if checkpoint exists")
    
    args = parser.parse_args()
    
    # Setup OpenAI client
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please provide OpenAI API key via --api-key or OPENAI_API_KEY env var")
    
    client = openai.OpenAI(api_key=api_key)
    
    # Translate domains
    domains_to_translate = DOMAINS if args.domain == "all" else [args.domain]
    
    for domain in domains_to_translate:
        translate_domain(
            domain,
            args.lang,
            client,
            args.resume,
            args.tasks_only,
            args.policy_only
        )
    
    print(f"\n=== Translation complete for {LANGUAGES[args.lang]} ===")


if __name__ == "__main__":
    main()

