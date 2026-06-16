import json

with open('/Users/kaizenpro/Projects/core/.system-map/raw_nodes.json', 'r') as f:
    data = json.load(f)

for node in data.get('nodes', []):
    if node['zone_id'] == 'L6-chat-runtime':
        if "inline realization" not in node['what_it_does']:
            node['what_it_does'] += " Additionally, handles inline realization (Step B-1), surface determination (Step B-2), and enforces edge-deployment budget gates per-turn."
    if node['zone_id'] == 'L5-cognition':
        if "ASK serving" not in node['what_it_does']:
            node['what_it_does'] += " Integrating ASK serving scope and Q1-B missing_* reclassification carve-outs."

with open('/Users/kaizenpro/Projects/core/.system-map/raw_nodes.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Patched raw_nodes.json successfully.")
