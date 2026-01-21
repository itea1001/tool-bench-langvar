# τ²-bench Language Variation Experiments

This directory contains scripts and data for investigating how LLM performance on τ²-bench varies across different languages.

## Overview

τ²-bench (tau2-bench) is a benchmark from Sierra Research for evaluating conversational agents in customer service scenarios. It includes:
- **Domains**: retail, airline, telecom
- **Tasks**: Simulated customer service scenarios where agents must follow policies, use tools, and interact with simulated users

For our language variation project, we translate:
1. **Policy documents** - The rules agents must follow
2. **Task instructions** - User scenarios and what they want to accomplish  
3. **User simulator messages** - The simulated user's responses

We do NOT translate:
- Function/tool names
- Parameter names and types
- IDs (order, user, product, etc.)
- Database content

## Setup

```bash
# Clone tau2-bench
cd /home/mingxuanl/mingxuanl/simulation/brandonzhang/tool-bench-langvar
git clone https://github.com/sierra-research/tau2-bench.git

# Install dependencies
pip install openai tqdm
```

## Usage

### Translate a single domain

```bash
# Set API key
export OPENAI_API_KEY=sk-...

# Translate retail domain to Spanish
python translate_tau2bench.py --lang es --domain retail

# Translate to all languages
for lang in es fr zh vi sw; do
    python translate_tau2bench.py --lang $lang --domain retail
done
```

### Translate all domains

```bash
python translate_tau2bench.py --lang es --domain all
```

### Resume from checkpoint

If translation is interrupted, use `--resume` to continue:

```bash
python translate_tau2bench.py --lang es --domain retail --resume
```

### Options

- `--lang`: Target language (es, fr, zh, vi, sw)
- `--domain`: Domain to translate (retail, airline, telecom, all)
- `--tasks-only`: Only translate tasks.json
- `--policy-only`: Only translate policy.md
- `--resume`: Resume from checkpoint

## Languages

| Code | Language | Resource Level |
|------|----------|----------------|
| es | Spanish | High |
| fr | French | High |
| zh | Chinese | High |
| vi | Vietnamese | Low |
| sw | Swahili | Low |

## Output Structure

```
translated_tau2/
├── es/
│   ├── retail/
│   │   ├── policy.md
│   │   ├── tasks.json
│   │   ├── db.json (copied unchanged)
│   │   └── split_tasks.json (copied unchanged)
│   ├── airline/
│   └── telecom/
├── fr/
├── zh/
├── vi/
└── sw/
```

## Running Benchmarks

After translation, run the benchmark with translated data:

```bash
# Install tau2-bench
cd tau2-bench
pip install -e .

# Set data directory to translated data
export TAU2_DATA_DIR=/path/to/translated_tau2/es

# Run evaluation
tau2 run --domain retail --agent-llm gpt-4.1 --user-llm gpt-4.1 --num-trials 1
```

## References

- τ²-bench repo: https://github.com/sierra-research/tau2-bench
- Paper: https://arxiv.org/abs/2506.07982
- Leaderboard: https://taubench.com

