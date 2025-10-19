
import sys
import json
sys.path.insert(0, r"C:\\Users\\Hlib\\Desktop\\algoflow\\AlgoFlow")

from ai_agent.agent import process_strategy

# Read input
with open(r"C:\\Users\\Hlib\\Desktop\\algoflow\\AlgoFlow\\temp\\input-1760862822772.json", "r") as f:
    data = json.load(f)

# Process
result = process_strategy(
    user_input=data["instruction"],
    registry_json=data.get("registry_json"),
    diagram_json=data.get("current_diagram"),
    model="gpt-4o-mini"
)

# Write output
with open(r"C:\\Users\\Hlib\\Desktop\\algoflow\\AlgoFlow\\temp\\output-1760862822772.json", "w") as f:
    json.dump(result, f, indent=2)

print("SUCCESS")
