"""
BFCL Language Variation Translation Script

This script translates:
1. System prompts (persona, task, tool_call_format, etc.)
2. Function descriptions and parameter descriptions in the data files

Languages:
- High-resource: Spanish (es), French (fr), Chinese (zh)
- Low-resource: Vietnamese (vi), Swahili (sw)

Things that should NOT be changed:
- Function names
- Parameter names  
- Parameter types
- Output format structure (e.g., [func_name1(params_name1=params_value1...)])
"""

import json
import os
import argparse
import time
from pathlib import Path
from typing import Dict, List, Any
import openai
from tqdm import tqdm

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
BFCL_DATA_DIR = Path("gorilla/berkeley-function-call-leaderboard/bfcl_eval/data")
OUTPUT_DIR = Path("translated_data")

# System prompt components to translate
SYSTEM_PROMPT_COMPONENTS = {
    "persona": "You are an expert in composing functions.",
    "task": "You are given a question and a set of possible functions. Based on the question, you will need to make one or more function/tool calls to achieve the purpose. If none of the functions can be used, point it out. If the given question lacks the parameters required by the function, also point it out.",
    "tool_call_no_tag": "You should only return the function calls in your response.\n\nIf you decide to invoke any of the function(s), you MUST put it in the format of {output_format}. {param_types} You SHOULD NOT include any other text in the response.",
    "tool_call_with_tag": "You should only return the function calls in the <TOOLCALL> section. If you decide to invoke any of the function(s), you MUST put it in the format of <TOOLCALL>{output_format}</TOOLCALL>. {param_types} You SHOULD NOT include any other text in the response.",
    "multiturn_behavior": "At each turn, you should try your best to complete the tasks requested by the user within the current turn. Continue to output functions to call until you have fulfilled the user's request to the best of your ability. Once you have no more functions to call, the system will consider the current turn complete and proceed to the next turn or task.",
    "available_tools": "Here is a list of functions in {format} format that you can invoke.",
}


def translate_text(text: str, target_lang: str, client: openai.OpenAI) -> str:
    """Translate text to target language using OpenAI API with retry logic."""
    if not text or not text.strip():
        return text
    
    prompt = f"""Translate the following text to {LANGUAGES[target_lang]}. 
Keep any placeholders like {{output_format}}, {{param_types}}, {{format}}, {{functions}} exactly as they are.
Keep any XML-like tags like <TOOLCALL> exactly as they are.
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
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                print(f"\nAPI error: {e}. Retrying in {wait_time}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                raise
    return text  # Fallback


def translate_function_doc(func_doc: Dict[str, Any], target_lang: str, client: openai.OpenAI) -> Dict[str, Any]:
    """Translate function description and parameter descriptions.
    
    Does NOT change:
    - function name
    - parameter names
    - parameter types
    """
    translated = func_doc.copy()
    
    # Translate function description
    if "description" in translated:
        translated["description"] = translate_text(translated["description"], target_lang, client)
    
    # Translate parameter descriptions
    if "parameters" in translated and "properties" in translated["parameters"]:
        for param_name, param_info in translated["parameters"]["properties"].items():
            if "description" in param_info:
                param_info["description"] = translate_text(param_info["description"], target_lang, client)
    
    return translated


def translate_question(question: List[List[Dict]], target_lang: str, client: openai.OpenAI) -> List[List[Dict]]:
    """Translate user questions in the data."""
    translated = []
    for turn in question:
        translated_turn = []
        for msg in turn:
            new_msg = msg.copy()
            if msg.get("role") == "user" and "content" in msg:
                new_msg["content"] = translate_text(msg["content"], target_lang, client)
            translated_turn.append(new_msg)
        translated.append(translated_turn)
    return translated


def translate_data_file(input_path: Path, output_path: Path, target_lang: str, client: openai.OpenAI, resume: bool = False):
    """Translate a BFCL data file with checkpointing and resume support."""
    print(f"Translating {input_path.name} to {LANGUAGES[target_lang]}...")
    
    # Load existing progress if resuming
    translated_entries = []
    start_idx = 0
    if resume and output_path.exists():
        with open(output_path, 'r') as f:
            for line in f:
                translated_entries.append(json.loads(line.strip()))
        start_idx = len(translated_entries)
        print(f"Resuming from entry {start_idx}...")
    
    with open(input_path, 'r') as f:
        lines = f.readlines()
    
    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Open file in append mode if resuming, else write mode
    mode = 'a' if resume and output_path.exists() else 'w'
    
    with open(output_path, mode) as out_f:
        # If not resuming, write existing entries first
        if mode == 'w' and translated_entries:
            for entry in translated_entries:
                out_f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        for i, line in enumerate(tqdm(lines[start_idx:], desc=f"Translating to {target_lang}", initial=start_idx, total=len(lines))):
            entry = json.loads(line.strip())
            
            # Translate question
            if "question" in entry:
                entry["question"] = translate_question(entry["question"], target_lang, client)
            
            # Translate function docs
            if "function" in entry:
                entry["function"] = [translate_function_doc(f, target_lang, client) for f in entry["function"]]
            
            # Write immediately to save progress
            out_f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            out_f.flush()  # Ensure it's written to disk
    
    print(f"Saved to {output_path}")


def translate_system_prompts(target_lang: str, client: openai.OpenAI) -> Dict[str, str]:
    """Translate system prompt components."""
    translated = {}
    for key, text in SYSTEM_PROMPT_COMPONENTS.items():
        translated[key] = translate_text(text, target_lang, client)
    return translated


def main():
    parser = argparse.ArgumentParser(description="Translate BFCL data for language variation experiments")
    parser.add_argument("--lang", type=str, choices=list(LANGUAGES.keys()), required=True,
                        help="Target language code")
    parser.add_argument("--data-file", type=str, default=None,
                        help="Specific data file to translate (e.g., BFCL_v4_simple_python.json)")
    parser.add_argument("--all-single-turn", action="store_true",
                        help="Translate all single-turn data files")
    parser.add_argument("--system-prompts-only", action="store_true",
                        help="Only translate system prompts")
    parser.add_argument("--api-key", type=str, default=None,
                        help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from previous progress if output file exists")
    
    args = parser.parse_args()
    
    # Setup OpenAI client
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please provide OpenAI API key via --api-key or OPENAI_API_KEY env var")
    
    client = openai.OpenAI(api_key=api_key)
    
    # Create output directory
    lang_output_dir = OUTPUT_DIR / args.lang
    lang_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Translate system prompts
    print(f"\n=== Translating system prompts to {LANGUAGES[args.lang]} ===")
    translated_prompts = translate_system_prompts(args.lang, client)
    
    prompts_output = lang_output_dir / "system_prompts.json"
    with open(prompts_output, 'w') as f:
        json.dump(translated_prompts, f, ensure_ascii=False, indent=2)
    print(f"Saved system prompts to {prompts_output}")
    
    if args.system_prompts_only:
        return
    
    # Single-turn data files
    single_turn_files = [
        "BFCL_v4_simple_python.json",
        "BFCL_v4_simple_java.json",
        "BFCL_v4_simple_javascript.json",
        "BFCL_v4_parallel.json",
        "BFCL_v4_multiple.json",
        "BFCL_v4_parallel_multiple.json",
        "BFCL_v4_irrelevance.json",
    ]
    
    if args.all_single_turn:
        for fname in single_turn_files:
            input_path = BFCL_DATA_DIR / fname
            if input_path.exists():
                output_path = lang_output_dir / fname
                translate_data_file(input_path, output_path, args.lang, client, args.resume)
    elif args.data_file:
        input_path = BFCL_DATA_DIR / args.data_file
        if not input_path.exists():
            raise FileNotFoundError(f"Data file not found: {input_path}")
        output_path = lang_output_dir / args.data_file
        translate_data_file(input_path, output_path, args.lang, client, args.resume)
    
    print("\n=== Translation complete ===")


if __name__ == "__main__":
    main()

