import os
import time
import glob
import argparse
import random

# --- Models ---
from src.models.route import ProblemData, Vehicle, Route
from src.models.request import Node, Request
from src.models.solution import Solution

# --- Operators ---
from src.operators.insertion import regret_k_insertion
from src.operators.removal import random_removal, worst_removal, shaw_removal
from src.operators.initial_solution import build_initial_greedy_solution

# --- Solvers ---
from src.solver.two_stage import TwoStageSolver
from src.benchmark.csv_logger import IterationCSVLogger
from src.utils.config import ALNSConfig


def parse_li_lim_benchmark(filepath: str) -> ProblemData:
    """Parses a standard Li & Lim PDPTW text file into ProblemData."""
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    header = lines[0].split()
    num_vehicles = int(header[0])
    capacity = float(header[1])
    speed = float(header[2]) if len(header) > 2 else 1.0

    nodes = []
    parsed_rows = {}

    for line in lines[1:]:
        parts = line.split()
        node_id = int(parts[0])
        x = float(parts[1])
        y = float(parts[2])
        demand = float(parts[3])
        tw_early = float(parts[4])
        tw_latest = float(parts[5])
        service_time = float(parts[6])
        pickup_idx = int(parts[7])
        delivery_idx = int(parts[8])
        
        node = Node(
            node_id=node_id, 
            x=x, 
            y=y, 
            demand=demand, 
            TW_Early=tw_early, 
            TW_Latest=tw_latest, 
            service_time=service_time
        )
        nodes.append(node)
        
        parsed_rows[node_id] = {
            'node': node,
            'pickup_idx': pickup_idx,
            'delivery_idx': delivery_idx
        }

    requests = []
    req_id_counter = 1
    for node_id, data in parsed_rows.items():
        if node_id == 0:
            continue
        node = data['node']
        if node.demand > 0 and data['delivery_idx'] != 0:
            delivery_id = data['delivery_idx']
            delivery_node = parsed_rows[delivery_id]['node']
            req = Request(request_id=req_id_counter, pickup=node, delivery=delivery_node)
            requests.append(req)
            req_id_counter += 1

    vehicles = []
    for i in range(num_vehicles):
        v = Vehicle(vehicle_id=i, speed=speed, capacity=capacity, start_node_id=0, end_node_id=0)
        vehicles.append(v)

    return ProblemData(nodes=nodes, requests=requests, vehicles=vehicles)


def parse_args():
    parser = argparse.ArgumentParser(description="PDPTW Two-Stage ALNS Runner")
    parser.add_argument("--policy", choices=["roulette", "bandit"], default="roulette")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-folder", default="results")
    parser.add_argument("--instances-folder", default="pdp_200")
    parser.add_argument("--max-instances", type=int, default=0)
    parser.add_argument("--log-iterations", action="store_true")
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--stage1-iterations", type=int, default=3000)
    parser.add_argument("--bandit-alpha", type=float, default=0.8)
    parser.add_argument("--bandit-epsilon", type=float, default=0.05)
    return parser.parse_args()


def main():
    args = parse_args()
    print("=== PDPTW Two-Stage ALNS Batch Engine ===")
    config = ALNSConfig()
    config.iterations = args.iterations
    config.stage1_iterations = args.stage1_iterations
    config.policy_mode = args.policy
    config.bandit_alpha = args.bandit_alpha
    config.bandit_epsilon = args.bandit_epsilon

    folder_name = args.instances_folder
    output_folder = args.output_folder

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Find all .txt files in the pdp_200 folder
    file_paths = sorted(glob.glob(os.path.join(folder_name, "*.txt")))

    if args.max_instances > 0:
        file_paths = file_paths[:args.max_instances]
    
    if not file_paths:
        print(f"[!] No benchmark files found in '{folder_name}'. Check your directory!")
        return

    print(f"Policy mode: {args.policy} | Seed: {args.seed}")
    print(f"Found {len(file_paths)} benchmark instances. Starting batch processing...\n")

    # Loop through every file
    for file_idx, filepath in enumerate(file_paths):
        file_name = os.path.basename(filepath)
        out_filename = file_name.replace('.txt', '_results.txt')
        out_filepath = os.path.join(output_folder, out_filename)

        run_seed = args.seed + file_idx
        random.seed(run_seed)
        run_rng = random.Random(run_seed)

        print(f"\n{'='*50}")
        print(f" PROCESSING: {file_name}")
        print(f"{'='*50}")

        try:
            # 1. Parse Data
            problem_data = parse_li_lim_benchmark(filepath)
            print(f"Loaded {len(problem_data.requests)} requests and {len(problem_data.vehicles)} vehicles.")

            # 2. Build Initial Solution
            print("Generating initial solution...")
            initial_routes = [Route(vehicle_id=v_id, problem_data=problem_data) for v_id in problem_data.vehicles.keys()]
            initial_sol = Solution(routes=initial_routes, unassigned_requests=list(problem_data.requests.keys()))
            initial_sol = build_initial_greedy_solution(initial_sol, problem_data, config)

            # 3. Setup Operators
            removal_ops = [random_removal, shaw_removal, worst_removal]
            insertion_ops = [regret_k_insertion]

            # 4. Initialize & Run Solver
            iter_logger = None
            if args.log_iterations:
                csv_name = file_name.replace(
                    ".txt", f"_{args.policy}_seed{run_seed}_iterations.csv"
                )
                iter_logger = IterationCSVLogger(os.path.join(output_folder, csv_name))

            solver = TwoStageSolver(
                problem_data=problem_data,
                initial_solution=initial_sol,
                removal_ops=removal_ops,
                insertion_ops=insertion_ops,
                config=config,
                policy_mode=args.policy,
                iteration_logger=iter_logger,
                rng=run_rng,
            )

            start_time = time.time()
            final_solution = solver.solve()
            end_time = time.time()
            execution_time = end_time - start_time

            if iter_logger is not None:
                iter_logger.close()

            # 5. Build Result String
            vehicles_used = len(final_solution.routes) if final_solution and hasattr(final_solution, 'routes') else "N/A"
            total_dist = f"{final_solution.total_distance:.2f}" if final_solution else "N/A"
            total_time = f"{final_solution.total_time:.2f}" if final_solution else "N/A"
            unassigned = len(final_solution.unassigned_requests) if final_solution else "N/A"
            global_cost = f"{final_solution.global_cost:.2f}" if final_solution else "N/A"

            result_str = (
                f"=============================================\n"
                f"             FINAL RESULTS\n"
                f"=============================================\n"
                f"File Tested:           {file_name}\n"
                f"Policy Mode:           {args.policy}\n"
                f"Seed:                  {run_seed}\n"
                f"Total Execution Time:  {execution_time:.2f} seconds\n"
                f"Vehicles Used:         {vehicles_used}\n"
                f"Total Distance:        {total_dist}\n"
                f"Total Time:            {total_time}\n"
                f"Unassigned Requests:   {unassigned}\n"
                f"Global Cost:           {global_cost}\n"
                f"=============================================\n"
            )

            # Print to console
            print("\n" + result_str)

            # Write to output file
            with open(out_filepath, 'w') as f:
                f.write(result_str)
                # You can also loop through final_solution.routes here and write out 
                # the exact order of nodes visited if you want to save the actual paths!
            
            print(f"[*] Successfully saved results to: {out_filepath}")

        except Exception as e:
            print(f"\n[!] Error processing file {file_name}: {e}")
            # The loop will gracefully skip to the next file if an error occurs

    print("\n=== BATCH PROCESSING COMPLETE ===")

if __name__ == "__main__":
    main()