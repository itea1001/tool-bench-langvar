# -*- coding: utf-8 -*-
"""
Simplified language variation evaluation for ComplexFuncBench.

This is a simplified version that only uses rule-based matching to avoid
heavy dependencies. Used for quick testing of the language variation pipeline.
"""

import json
import argparse
import os
from pathlib import Path
from openai import OpenAI
from tqdm import tqdm

LANGUAGES = ["en", "es", "fr", "zh", "vi", "sw"]


def load_jsonl(path):
    """Load a JSONL file."""
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data


def get_functions_from_example(example):
    """Extract function definitions from example."""
    return example.get('functions', [])


def call_model(client, messages, functions, model_name):
    """Call the model with function calling."""
    tools = [{"type": "function", "function": func} for func in functions]
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        return response.choices[0]
    except Exception as e:
        print(f"API Error: {e}")
        return None


def rule_based_match(predicted, golden):
    """Simple rule-based matching of function calls."""
    if predicted['name'] != golden['name']:
        return False
    
    pred_args = predicted.get('arguments', {})
    gold_args = golden.get('arguments', {})
    
    if set(pred_args.keys()) != set(gold_args.keys()):
        return False
    
    for key in gold_args:
        if pred_args.get(key) != gold_args[key]:
            return False
    
    return True


def evaluate_example(client, example, model_name, verbose=False):
    """Evaluate a single example."""
    conversations = example['conversations']
    functions = get_functions_from_example(example)
    
    if not functions:
        return {"id": example['id'], "status": "no_functions", "correct": 0, "total": 0}
    
    # Get user query
    user_query = conversations[0]['content']
    
    # Get golden function calls
    golden_calls = []
    for turn in conversations:
        if turn['role'] == 'assistant' and 'function_call' in turn:
            golden_calls.extend(turn['function_call'])
    
    if not golden_calls:
        return {"id": example['id'], "status": "no_golden", "correct": 0, "total": 0}
    
    # Call model
    messages = [{"role": "user", "content": user_query}]
    response = call_model(client, messages, functions, model_name)
    
    if response is None:
        return {"id": example['id'], "status": "api_error", "correct": 0, "total": len(golden_calls)}
    
    # Extract predicted function calls
    predicted_calls = []
    if response.message.tool_calls:
        for tool_call in response.message.tool_calls:
            try:
                predicted_calls.append({
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments)
                })
            except json.JSONDecodeError:
                pass
    
    if verbose:
        print(f"Example {example['id']}:")
        print(f"  Query: {user_query[:100]}...")
        print(f"  Golden: {golden_calls[0] if golden_calls else 'None'}")
        print(f"  Predicted: {predicted_calls[0] if predicted_calls else 'None'}")
    
    # Compare first turn only (simplified)
    correct = 0
    total = min(len(golden_calls), 1)  # Just compare first call for simplicity
    
    for pred in predicted_calls[:1]:
        for gold in golden_calls[:1]:
            if rule_based_match(pred, gold):
                correct += 1
                break
    
    status = "success" if correct == total else "fail"
    
    return {
        "id": example['id'],
        "status": status,
        "correct": correct,
        "total": total,
        "predicted": predicted_calls[:1] if predicted_calls else [],
        "golden": golden_calls[:1] if golden_calls else [],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="gpt-4.1-mini")
    parser.add_argument("--lang", type=str, default="en", choices=LANGUAGES)
    parser.add_argument("--input_dir", type=str, default="data")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    
    # Set input file
    if args.lang == "en":
        input_file = os.path.join(args.input_dir, "ComplexFuncBench.jsonl")
    else:
        input_file = os.path.join(args.input_dir, "translated", f"ComplexFuncBench_{args.lang}.jsonl")
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return
    
    # Load data
    print(f"Loading data from {input_file}...")
    data = load_jsonl(input_file)
    
    if args.limit:
        data = data[:args.limit]
    
    print(f"Evaluating {len(data)} examples on {args.lang}...")
    
    # Initialize client
    client = OpenAI()
    
    # Evaluate
    results = []
    correct_count = 0
    total_count = 0
    
    for example in tqdm(data, desc=f"Evaluating {args.lang}"):
        result = evaluate_example(client, example, args.model_name, args.verbose)
        results.append(result)
        correct_count += result['correct']
        total_count += result['total']
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Language: {args.lang}")
    print(f"Model: {args.model_name}")
    print(f"Total examples: {len(results)}")
    print(f"Correct calls: {correct_count}/{total_count}")
    if total_count > 0:
        print(f"Accuracy: {correct_count/total_count*100:.1f}%")
    
    # Save results
    output_dir = Path(f"result/{args.model_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"langvar-{args.lang}-simple.jsonl"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    
    print(f"Results saved to {output_file}")
    
    return results


if __name__ == "__main__":
    main()

