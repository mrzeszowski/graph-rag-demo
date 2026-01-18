#!/usr/bin/env zsh

# Create one shared result file for this whole run.
export RUN_RESULTS_PATH="$(python3 run_result_writer.py --start-session --header 'run.sh batch')"
echo "Writing all results to: $RUN_RESULTS_PATH"

scripts=(
  "graph_rag/query.py"
  "rag/query.py"
)

questions=(
    "What’s our current event streaming platform?"
    "Which ADRs are related to service-to-service auth?"
    "What alternatives were considered for authentication?"
    "Which services are impacted by auth decisions?"
    "Timeline of messaging platform decisions?"
)

for q in "${questions[@]}"; do
  for s in "${scripts[@]}"; do
    python3 "$s" --question "$q"
  done
done

# python3 verify_latest_run.py