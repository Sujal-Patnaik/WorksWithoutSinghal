import os
from src.operators.initial_solution import build_initial_greedy_solution
import optuna

# --- Models ---
from src.models.route import Route
from src.models.solution import Solution

# --- Operators ---
from src.operators.insertion import regret_k_insertion
from src.operators.removal import random_removal, worst_removal, shaw_removal

# --- Solver ---
from src.solver.two_stage import TwoStageSolver

# --- Main Imports ---
from main import parse_li_lim_benchmark
from src.utils.config import ALNSConfig

# 1. Define our "Validation Set" using the hard Random datasets
# We avoid LC (Clustered) files because they are too easy and cause overfitting
VALIDATION_FILES = ["LR1_2_1.txt", "LRC1_2_1.txt"]

def objective(trial):
    """
    Optuna will run this function over and over, passing in different
    'trial' parameters. Our goal is to return the lowest possible cost.
    """
    # Let Optuna intelligently guess the parameters
    tune_cooling = trial.suggest_float("cooling_rate", 0.9900, 0.9999, log=True)
    tune_reaction = trial.suggest_float("reaction_factor", 0.05, 0.5)
    tune_sigma_1 = trial.suggest_int("sigma_1", 20, 50)
    tune_sigma_2 = trial.suggest_int("sigma_2", 5, 20)
    tune_sigma_3 = trial.suggest_int("sigma_3", 5, 20)
    tune_w = trial.suggest_float("w_param", 0.01, 0.1)

    total_cost = 0.0

    # Test these parameters across our validation files
    for filename in VALIDATION_FILES:
        filepath = os.path.join("pdp_200", filename)
        
        try:
            problem_data = parse_li_lim_benchmark(filepath)
        except FileNotFoundError:
            print(f"[!] Could not find {filepath}. Make sure pdp_200 folder is set up correctly.")
            raise optuna.exceptions.TrialPruned()

        config = ALNSConfig(
            weight_distance=1.0,
            weight_time=0.0,         # CRITICAL: Keep at 0.0 to optimize physical distance
            unassigned_penalty=10000.0,
            iterations=1000,         # SPEED UP: 1000 iterations for fast tuning
            segment_length=100,
            sigma_1=float(tune_sigma_1),
            sigma_2=float(tune_sigma_2),
            sigma_3=float(tune_sigma_3),
            reaction_factor=tune_reaction,
            cooling_rate=tune_cooling,
            w_param=tune_w,
            eta=0.025
        )

        # Build initial empty solution
        initial_routes = [Route(vehicle_id=v_id, problem_data=problem_data) for v_id in problem_data.vehicles.keys()]
        initial_sol = Solution(routes=initial_routes, unassigned_requests=list(problem_data.requests.keys()))
        initial_sol = build_initial_greedy_solution(initial_sol, problem_data, config)
        # Initialize Solver
        solver = TwoStageSolver(
            problem_data=problem_data,
            initial_solution=initial_sol,
            removal_ops=[random_removal, shaw_removal, worst_removal],
            insertion_ops=[regret_k_insertion],
            config=config
        )

        # Run the solver
        try:
            final_solution = solver.solve()
            
            # Add a massive penalty if the parameters caused the engine to fail to assign requests
            if len(final_solution.unassigned_requests) > 0:
                total_cost += (len(final_solution.unassigned_requests) * 20000)
            else:
                total_cost += final_solution.global_cost
                
        except Exception as e:
            # If a parameter combination causes a math error, we penalize it and move on
            print(f"Trial failed mathematically: {e}")
            return float('inf')

    # Return the average cost across the files
    return total_cost / len(VALIDATION_FILES)


def main():
    print("ALNS hyperparameter tuning")
    print(f"Validation datasets: {len(VALIDATION_FILES)}")
    
    # Suppress extreme console spam to make it readable
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    # Create an Optuna study to MINIMIZE the returned cost
    study = optuna.create_study(direction="minimize")
    
    print("Running 20 trials...\n")
    
    # Run the optimization
    for i in range(20):  
        study.optimize(objective, n_trials=1)
        print(f"Trial {i+1}/20 Complete | Current Best Average Cost: {study.best_value:.2f}")
    
    print("\nTuning complete")
    print(f"Best average cost: {study.best_value:.2f}\n")
    print("Best parameters for ALNSConfig:")
    
    for key, value in study.best_params.items():
        if isinstance(value, float):
            print(f"  {key} = {value:.4f}")
        else:
            print(f"  {key} = {value}")
    print("Done")

if __name__ == "__main__":
    main()