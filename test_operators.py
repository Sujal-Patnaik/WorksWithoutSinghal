#!/usr/bin/env python3
"""
Quick test to see if removal + insertion creates better neighbors or just shuffles
"""

import sys
sys.path.insert(0, '.')

from src.models.solution import Solution
from src.models.route import Route
from src.models.request import Request
from src.operators.removal import random_removal, shaw_removal, worst_removal
from src.operators.insertion import regret_k_insertion
from main import ALNSConfig, parse_li_lim_benchmark

# Load real problem
import os
os.chdir(r'c:\Users\sujal\WorksWithoutSinghal')
problem_data = parse_li_lim_benchmark("pdp_200/LC1_2_1.txt")
config = ALNSConfig()

print(f"Testing on: {len(problem_data.requests)} requests, {len(problem_data.vehicles)} vehicles")

# Create initial solution using regret-k for fair test
sol = Solution([Route() for _ in range(len(problem_data.vehicles))], set(problem_data.requests.keys()))
best_sol = regret_k_insertion(sol, problem_data, config)
best_sol.evaluate(problem_data, config.penalty_per_unassigned, config.weight_distance, config.weight_time)

print(f"\nInitial solution cost: {best_sol.global_cost:.2f}")
print(f"  Distance: {best_sol.total_distance:.2f}")
print(f"  Time: {best_sol.total_time:.2f}")
print(f"  Unassigned: {len(best_sol.unassigned_requests)}")

# Test 100 destruction/repair cycles
better_count = 0
same_count = 0
worse_count = 0
improvement_sum = 0
cost_diffs = []

print("\nTesting 100 destruction/repair cycles...")
for cycle in range(100):
    # Random removal of 8 requests
    destroyed, _ = random_removal(best_sol, problem_data, 8)
    
    # Repair with regret-k
    repaired = regret_k_insertion(destroyed, problem_data, config)
    repaired.evaluate(problem_data, config.penalty_per_unassigned, config.weight_distance, config.weight_time)
    
    cost_diff = repaired.global_cost - best_sol.global_cost
    cost_diffs.append(cost_diff)
    
    if cost_diff < -0.01:  # Better
        better_count += 1
        improvement_sum += abs(cost_diff)
    elif cost_diff <= 0.01:  # Same
        same_count += 1
    else:  # Worse
        worse_count += 1

print(f"\nResults of 100 removal+insertion cycles:")
print(f"  Better: {better_count} ({100*better_count/100:.1f}%)")
print(f"  Same:   {same_count} ({100*same_count/100:.1f}%)")
print(f"  Worse:  {worse_count} ({100*worse_count/100:.1f}%)")
print(f"  Avg improvement when better: {improvement_sum/max(1,better_count):.2f}")
print(f"  Min cost diff: {min(cost_diffs):.2f}")
print(f"  Max cost diff: {max(cost_diffs):.2f}")

print(f"\nConclusion:")
if better_count < 5:
    print("  ⚠️  PROBLEM: Removal+insertion rarely creates better neighbors (<5%)")
    print("  This explains why Stage 2 can't improve!")
elif better_count < 20:
    print("  ⚠️  LIMITED: Few improving neighbors (~10%), needs larger removal or different strategy")
else:
    print("  ✓ Acceptable: Removal+insertion finding improving neighbors regularly")
