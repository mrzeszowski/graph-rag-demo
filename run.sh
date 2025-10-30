#!/usr/bin/env zsh

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
    python "$s" --question "$q"
  done
done

# python graph_rag/query.py --question "Who is Maria Zielińska?"
# python rag/query.py --question "Who is Maria Zielińska?"

# python graph_rag/query.py --question "Who works at CarTech?"
# python rag/query.py --question "Who works at CarTech?"

# python graph_rag/query.py --question "Who sold the car to Anna?"
# python rag/query.py --question "Who sold the car to Anna?"

# python graph_rag/query.py --question "What is the connection between Anna and Jan?"
# python rag/query.py --question "What is the connection between Anna and Jan?"

# python graph_rag/query.py --question "Which organizations collaborate with CarTech?"
# python rag/query.py --question "Which organizations collaborate with CarTech?"

# python graph_rag/query.py --question "What’s the shortest connection path between Anna Kowalska and Laura Chen and which relations are used?"
# python rag/query.py --question "What’s the shortest connection path between Anna Kowalska and Laura Chen and which relations are used?"

# python graph_rag/query.py --question "Who collaborated with CarTech and also has a direct relationship with Anna?"
# python rag/query.py --question "Who collaborated with CarTech and also has a direct relationship with Anna?"

# Worked
# python graph_rag/query.py --question "List organizations that partner with CarTech but are not located in Warsaw."
# python rag/query.py --question "List organizations that partner with CarTech but are not located in Warsaw."

# python graph_rag/query.py --question "Which people worked at AutoWorld before joining QuickFix?"
# python rag/query.py --question "Which people worked at AutoWorld before joining QuickFix?"

# Worked
# python graph_rag/query.py --question "How many unique organizations are connected to Anna within two hops? Group by relation type."
# python rag/query.py --question "How many unique organizations are connected to Anna within two hops? Group by relation type."

# python graph_rag/query.py --question "Which CarTech employees are connected to GreenEnergy through any project? Return names and roles."
# python rag/query.py --question "Which CarTech employees are connected to GreenEnergy through any project? Return names and roles."

# python graph_rag/query.py --question "What’s the connection of CarTech with Warsaw?"
# python rag/query.py --question "What’s the connection of CarTech with Warsaw?"
