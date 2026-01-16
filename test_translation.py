"""
Quick test to validate translation approach on a few samples.
"""

import json
import os
from pathlib import Path

# Check if we can load the data properly
data_path = Path("gorilla/berkeley-function-call-leaderboard/bfcl_eval/data/BFCL_v4_simple_python.json")

print("Loading sample data...")
with open(data_path, 'r') as f:
    lines = f.readlines()[:3]  # Just first 3 entries

for i, line in enumerate(lines):
    entry = json.loads(line.strip())
    print(f"\n=== Entry {i} ===")
    print(f"ID: {entry['id']}")
    print(f"Question: {entry['question'][0][0]['content'][:100]}...")
    print(f"Function name: {entry['function'][0]['name']}")
    print(f"Function description: {entry['function'][0]['description'][:100]}...")
    
    if 'parameters' in entry['function'][0]:
        params = entry['function'][0]['parameters'].get('properties', {})
        print(f"Parameters: {list(params.keys())}")
        for pname, pinfo in list(params.items())[:2]:
            print(f"  - {pname}: {pinfo.get('description', 'N/A')[:50]}...")

print("\n\n=== Data structure validated ===")
print(f"Total entries in simple_python: {len(open(data_path).readlines())}")

