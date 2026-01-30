# -*- coding: utf-8 -*-
"""
Create a version of ComplexFuncBench with nonsense descriptions.

This tests whether models rely on function names vs descriptions.
"""

import json
import argparse
import random
from pathlib import Path

LOREM_IPSUM = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa.",
    "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit.",
    "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet.",
    "Consectetur, adipisci velit, sed quia non numquam eius modi tempora.",
    "Ut aliquip ex ea commodo consequat duis aute irure dolor.",
    "Quis autem vel eum iure reprehenderit qui in ea voluptate velit.",
]

def get_random_nonsense():
    """Return a random lorem ipsum sentence."""
    return random.choice(LOREM_IPSUM)


def replace_descriptions(example):
    """Replace all descriptions in functions with nonsense."""
    import copy
    result = copy.deepcopy(example)
    
    if "functions" in result:
        for func in result["functions"]:
            # Replace function description
            if "description" in func:
                func["description"] = get_random_nonsense()
            
            # Replace parameter descriptions
            if "parameters" in func and "properties" in func["parameters"]:
                for param_name, param_def in func["parameters"]["properties"].items():
                    if "description" in param_def:
                        param_def["description"] = get_random_nonsense()
    
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/ComplexFuncBench.jsonl")
    parser.add_argument("--output", default="data/ComplexFuncBench_nonsense.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    
    random.seed(args.seed)
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    print(f"Loading from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        examples = [json.loads(line) for line in f]
    
    print(f"Replacing descriptions with nonsense...")
    nonsense_examples = [replace_descriptions(ex) for ex in examples]
    
    print(f"Saving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        for ex in nonsense_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    print(f"Done! Created {len(nonsense_examples)} examples with nonsense descriptions.")


if __name__ == "__main__":
    main()

