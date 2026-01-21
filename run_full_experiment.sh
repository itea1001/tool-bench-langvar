#!/bin/bash
# Run full language variation experiment across all languages and domains

set -e

# Configuration
AGENT_LLM="${AGENT_LLM:-gpt-4.1-mini}"
USER_LLM="${USER_LLM:-gpt-4.1-mini}"
NUM_TRIALS="${NUM_TRIALS:-1}"
NUM_TASKS="${NUM_TASKS:-}"  # Empty = all tasks
MAX_CONCURRENCY="${MAX_CONCURRENCY:-5}"

LANGUAGES="en es fr zh vi sw"
DOMAINS="retail airline"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate conda
source /home/mingxuanl/miniconda3/etc/profile.d/conda.sh
conda activate tool-bench-langvar-01

# Set API keys
export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-svcacct-YTWyBnrCVylFHrAmtm7hT3BlbkFJ86XwFnwus57NHGek99xT}"

echo "=============================================="
echo "Running Full Language Variation Experiment"
echo "Agent LLM: $AGENT_LLM"
echo "User LLM: $USER_LLM"
echo "Trials: $NUM_TRIALS"
echo "Tasks: ${NUM_TASKS:-all}"
echo "Languages: $LANGUAGES"
echo "Domains: $DOMAINS"
echo "=============================================="

# Build task limit arg if specified
TASK_ARG=""
if [ -n "$NUM_TASKS" ]; then
    TASK_ARG="--num-tasks $NUM_TASKS"
fi

# Run experiments
for lang in $LANGUAGES; do
    for domain in $DOMAINS; do
        echo ""
        echo ">>> Running $lang - $domain"
        echo "=============================================="
        
        python run_langvar_tau2.py \
            --lang "$lang" \
            --domain "$domain" \
            --agent-llm "$AGENT_LLM" \
            --user-llm "$USER_LLM" \
            --num-trials "$NUM_TRIALS" \
            --max-concurrency "$MAX_CONCURRENCY" \
            $TASK_ARG \
            --save-results
        
        echo ">>> Completed $lang - $domain"
        echo ""
    done
done

echo ""
echo "=============================================="
echo "All experiments completed!"
echo "Results saved in: $SCRIPT_DIR/benchmark_results/"
echo "=============================================="

# Generate summary
python -c "
import json
from pathlib import Path
import glob

results_dir = Path('benchmark_results')
summary = []

for lang_dir in sorted(results_dir.iterdir()):
    if not lang_dir.is_dir():
        continue
    lang = lang_dir.name
    for domain_dir in sorted(lang_dir.iterdir()):
        if not domain_dir.is_dir():
            continue
        domain = domain_dir.name
        # Get most recent result file
        result_files = sorted(domain_dir.glob('results_*.json'), reverse=True)
        if result_files:
            with open(result_files[0]) as f:
                data = json.load(f)
            sim = data.get('simulation_results', {}).get('data', {})
            if isinstance(sim, dict):
                metrics = sim.get('metrics', {})
                avg_reward = metrics.get('avg_reward', 'N/A')
                pass1 = metrics.get('pass_k', {}).get('1', 'N/A')
            else:
                avg_reward = 'N/A'
                pass1 = 'N/A'
            summary.append({
                'lang': lang,
                'domain': domain,
                'avg_reward': avg_reward,
                'pass_1': pass1
            })

print('\n=== Results Summary ===')
print(f'{'Language':<12} {'Domain':<10} {'Avg Reward':<12} {'Pass@1':<10}')
print('-' * 44)
for row in summary:
    print(f\"{row['lang']:<12} {row['domain']:<10} {row['avg_reward']:<12} {row['pass_1']:<10}\")
"

