#!/usr/bin/env python3
import json
import sys
from collections import defaultdict
from pathlib import Path

# Add the workspace root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from generate.math_parser import parse_problem, ParseError
from generate.math_problem_graph import graph_from_dict
from generate.math_solver import solve, SolveError

def verify_cases():
    root = Path(__file__).resolve().parents[2]
    dev_path = root / "evals/gsm8k_math/dev/cases.jsonl"
    public_path = root / "evals/gsm8k_math/public/v1/cases.jsonl"
    
    cases = []
    for path in (dev_path, public_path):
        if not path.exists():
            print(f"Error: file not found at {path}")
            return False
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cases.append(json.loads(line))
                    
    if len(cases) != 200:
        print(f"Error: expected exactly 200 cases total, got {len(cases)}")
        return False
        
    # Check distributions
    depth_counts = defaultdict(int)
    op_counts = defaultdict(int)
    multi_entity_count = 0
    
    passed = 0
    for case in cases:
        case_id = case.get("id", "unknown")
        problem = case["problem"]
        expected_ans = case["expected_answer"]
        expected_unit = case["expected_unit"]
        gt_dict = case["ground_truth_graph"]
        
        try:
            # 1. Parse
            parsed_graph = parse_problem(problem)
            
            # 2. Match GT graph
            gt_graph_obj = graph_from_dict(gt_dict)
            if parsed_graph.canonical_bytes() != gt_graph_obj.canonical_bytes():
                print(f"FAIL {case_id}: Graph canonical bytes mismatch.")
                continue
                
            # 3. Solve and match answer
            trace = solve(parsed_graph)
            if trace.answer_value != expected_ans:
                print(f"FAIL {case_id}: Answer value mismatch. Expected {expected_ans}, got {trace.answer_value}")
                continue
                
            # 4. Match unit
            if trace.answer_unit != expected_unit:
                print(f"FAIL {case_id}: Answer unit mismatch. Expected {expected_unit!r}, got {trace.answer_unit!r}")
                continue
                
            passed += 1
            
            # Record stats
            depth = len(gt_dict["operations"])
            if depth == 1:
                depth_counts[1] += 1
            elif 2 <= depth <= 3:
                depth_counts["2-3"] += 1
            elif 4 <= depth <= 5:
                depth_counts["4-5"] += 1
            elif 6 <= depth <= 8:
                depth_counts["6-8"] += 1
            else:
                depth_counts["OOD"] += 1
                
            for op in gt_dict["operations"]:
                op_counts[op["kind"]] += 1
                
            if len(gt_dict["entities"]) >= 2:
                multi_entity_count += 1
                
        except (ParseError, SolveError, Exception) as e:
            print(f"FAIL {case_id}: Exception raised - {type(e).__name__}: {e}")
            continue
            
    print(f"\n--- Verification Stats ---")
    print(f"Cases parsed and solved successfully: {passed}/200")
    print(f"Depth distribution: {dict(depth_counts)}")
    print(f"Operation distribution: {dict(op_counts)}")
    print(f"Multi-entity cases: {multi_entity_count}")
    
    if passed == 200:
        print("\n200/200 OK")
        return True
    else:
        print(f"\nFAIL: Only {passed}/200 cases passed verification.")
        return False

if __name__ == "__main__":
    success = verify_cases()
    sys.exit(0 if success else 1)
