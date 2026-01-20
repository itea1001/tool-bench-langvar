# Tool-Bench Language Variation - BFCL

Investigation of how LLM performance in function-calling benchmarks changes with language.

## Overview

This project translates the Berkeley Function Calling Leaderboard (BFCL) benchmark into multiple languages to study:
- How well LLMs perform function calling in non-English languages
- Differences between high-resource and low-resource languages

## Languages

**High-resource:**
- Spanish (es)
- French (fr)
- Chinese (zh)

**Low-resource:**
- Vietnamese (vi)
- Swahili (sw)

## What Gets Translated

1. **System prompts** - The instructions telling the model how to call functions
2. **User queries** - The questions/requests in the benchmark
3. **Function descriptions** - The descriptions of what each function does
4. **Parameter descriptions** - The descriptions of function parameters

## What Stays the Same (Control Variables)

- Function names (e.g., `calculate_triangle_area`)
- Parameter names (e.g., `base`, `height`)
- Parameter types (e.g., `integer`, `string`)
- Output format structure (e.g., `[func_name(param=value)]`)

## Directory Structure

```
tool-bench-langvar/
├── gorilla/                    # Cloned BFCL repo
├── translated_data/            # Translated benchmark data
│   ├── es/                     # Spanish
│   ├── fr/                     # French
│   ├── zh/                     # Chinese
│   ├── vi/                     # Vietnamese
│   └── sw/                     # Swahili
├── translate_bfcl.py           # Translation script
├── requirements.txt
└── README.md
```

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Translate system prompts only
python translate_bfcl.py --lang es --system-prompts-only

# Translate a specific data file
python translate_bfcl.py --lang es --data-file BFCL_v4_simple_python.json

# Translate all single-turn data files
python translate_bfcl.py --lang es --all-single-turn
```

## Single-Turn Test Categories

- `simple_python` - Simple Python function calls
- `simple_java` - Simple Java function calls
- `simple_javascript` - Simple JavaScript function calls
- `parallel` - Multiple function calls in parallel
- `multiple` - Multiple function calls in sequence
- `parallel_multiple` - Both parallel and sequential calls
- `irrelevance` - Function calls with irrelevant function documentation


