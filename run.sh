#!/usr/bin/env zsh

# Create one shared result file for this whole run.
export RUN_RESULTS_PATH="$(python3 run_result_writer.py --start-session --header 'run.sh batch')"
echo "Writing all results to: $RUN_RESULTS_PATH"

scripts=(
  "rag/query.py"
  "graph_rag/query.py"
)

questions=(
    "What is our current event streaming platform, and which ADR superseded the previous one? (ids + dates)"
    "Given we switched to Pub/Sub, what ADR(s) still govern event contract/schema governance, and what tooling do we use?"
    "Timeline of messaging platform decisions?"
    
    #"Which changes would be required to fully remove mTLS: list affected services, the governing ADR(s), and the downstream policy artifacts we must update (trust graph / service-call-policy)."
    #"Find all ADRs that mention event streaming and schema governance, and reconcile them into one ‘operating model’ (platform + schema tool + enforcement point)."
    #"What is the set of services impacted by the messaging platform migration, and why? (Use the dependency map/event streams to justify impact, not just a narrative summary.)"
    #"Impact analysis: If we change the schema of orders.created, who must be involved (services + teams), and which ADR defines the compatibility/tooling requirements?"
)

for q in "${questions[@]}"; do
  for s in "${scripts[@]}"; do
    python3 "$s" --question "$q"
  done
done

# python3 verify_latest_run.py