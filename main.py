import os
import time
import glob
from dataclasses import dataclass

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

@dataclass
class ALNSConfig:
    weight_distance: float = 1.0
    weight_time: float = 0.0        # CRITICAL: Keep at 0.0 to optimize physical distance
    unassigned_penalty: float = 10000.0

    iterations: int = 5000          # INCREASED: Need more iterations to improve routes
    segment_length: int = 100       # Match paper (update weights every 100 iters)
    sigma_1: float = 33.0
    sigma_2: float = 9.0
    sigma_3: float = 13.0
    reaction_factor: float = 0.1    # Paper uses 0.1
    cooling_rate: float = 0.9985    # Slower cooling for 5000 iterations
    w_param: float = 0.05
    eta: float = 0.025


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


def main():
    print("=== PDPTW Two-Stage ALNS Batch Engine ===")
    config = ALNSConfig()

    folder_name = "pdp_200"
    output_folder = "results"

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Find all .txt files in the pdp_200 folder
    file_paths = glob.glob(os.path.join(folder_name, "*.txt"))
    
    if not file_paths:
        print(f"[!] No benchmark files found in '{folder_name}'. Check your directory!")
        return

    print(f"Found {len(file_paths)} benchmark instances. Starting batch processing...\n")

    # Loop through every file
    for filepath in file_paths:
        file_name = os.path.basename(filepath)
        out_filename = file_name.replace('.txt', '_results.txt')
        out_filepath = os.path.join(output_folder, out_filename)

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
            solver = TwoStageSolver(
                problem_data=problem_data,
                initial_solution=initial_sol,
                removal_ops=removal_ops,
                insertion_ops=insertion_ops,
                config=config
            )

            start_time = time.time()
            final_solution = solver.solve()
            end_time = time.time()
            execution_time = end_time - start_time

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