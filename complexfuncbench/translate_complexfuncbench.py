# -*- coding: utf-8 -*-
"""
Translation script for ComplexFuncBench language variation experiments.

Translates user queries while preserving function calls and technical elements.
Function arguments are NOT translated to maintain consistency with expected
API responses.
"""

import json
import argparse
import os
from pathlib import Path
from typing import Dict, Any, List
import openai
from tqdm import tqdm
import time

# Language codes and their full names
LANGUAGES = {
    "es": "Spanish",
    "fr": "French", 
    "zh": "Chinese",
    "vi": "Vietnamese",
    "sw": "Swahili",
}


def translate_text(text: str, target_lang: str, client: openai.OpenAI) -> str:
    """Translate text to target language, preserving technical elements."""
    if not text or not text.strip():
        return text
    
    prompt = f"""Translate the following text to {LANGUAGES[target_lang]}. 
Keep any technical terms, numbers, dates, times, coordinates, and proper nouns in their original form.
Only output the translation, nothing else.

Text to translate:
{text}"""

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                print(f"Translation failed after 3 attempts: {e}")
                return text


def translate_conversation(conversation: List[Dict], target_lang: str, client: openai.OpenAI) -> List[Dict]:
    """Translate a conversation, only translating user messages.
    
    Function calls and their arguments are kept in English to match
    expected API responses and ground truth values.
    """
    translated_conv = []
    
    for turn in conversation:
        translated_turn = {"role": turn["role"]}
        
        if turn["role"] == "user":
            # Translate user content
            if isinstance(turn["content"], str):
                translated_turn["content"] = translate_text(turn["content"], target_lang, client)
            else:
                translated_turn["content"] = turn["content"]
                
        elif turn["role"] == "assistant":
            # Keep assistant content as-is
            if "content" in turn:
                translated_turn["content"] = turn["content"]
            
            # Keep function calls as-is (don't translate arguments)
            if "function_call" in turn:
                translated_turn["function_call"] = turn["function_call"]
                
        elif turn["role"] == "observation":
            # Keep observations as-is (API responses)
            translated_turn["content"] = turn["content"]
        
        translated_conv.append(translated_turn)
    
    return translated_conv


def translate_example(example: Dict, target_lang: str, client: openai.OpenAI) -> Dict:
    """Translate a single ComplexFuncBench example."""
    translated = {
        "id": example["id"],
        "conversations": translate_conversation(
            example["conversations"], target_lang, client
        )
    }
    
    # Copy any other fields
    for key in example:
        if key not in ["id", "conversations"]:
            translated[key] = example[key]
    
    return translated


def main():
    parser = argparse.ArgumentParser(description="Translate ComplexFuncBench to other languages")
    parser.add_argument("--lang", type=str, required=True, choices=list(LANGUAGES.keys()),
                        help="Target language code")
    parser.add_argument("--input", type=str, default="data/ComplexFuncBench.jsonl",
                        help="Input JSONL file")
    parser.add_argument("--output-dir", type=str, default="data/translated",
                        help="Output directory for translated files")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of examples to translate (for testing)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last checkpoint")
    args = parser.parse_args()
    
    # Initialize OpenAI client
    client = openai.OpenAI()
    
    # Setup paths
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"ComplexFuncBench_{args.lang}.jsonl"
    
    # Load input data
    print(f"Loading data from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        examples = [json.loads(line) for line in f]
    
    if args.limit:
        examples = examples[:args.limit]
    
    # Check for existing progress
    translated_ids = set()
    if args.resume and output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                ex = json.loads(line)
                translated_ids.add(ex["id"])
        print(f"Resuming from {len(translated_ids)} already translated examples")
    
    # Filter out already translated
    examples = [ex for ex in examples if ex["id"] not in translated_ids]
    
    print(f"Translating {len(examples)} examples to {LANGUAGES[args.lang]}...")
    
    # Translate
    mode = 'a' if args.resume else 'w'
    with open(output_path, mode, encoding='utf-8') as f:
        for example in tqdm(examples, desc=f"Translating to {args.lang}"):
            translated = translate_example(example, args.lang, client)
            f.write(json.dumps(translated, ensure_ascii=False) + "\n")
            f.flush()
    
    print(f"Done! Output saved to {output_path}")


if __name__ == "__main__":
    main()
