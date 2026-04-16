from src.solver.alns import ALNSSolver
from src.utils.config import ALNSConfig

class TwoStageSolver:
    def __init__(self, problem_data, initial_solution, removal_ops, insertion_ops, config):
        self.problem_data = problem_data
        self.initial_solution = initial_solution
        self.removal_ops = removal_ops
        self.insertion_ops = insertion_ops
        self.base_config = config

        self.best_feasible_solution = initial_solution.clone()

    def remove_smallest_route(self, solution):
        if not solution.routes:
            return solution

        route_to_remove= min(solution.routes, key=lambda r: len(r.assigned_requests))

        solution.unassigned_requests.update(route_to_remove.assigned_requests)
        solution.routes.remove(route_to_remove)

        solution.evaluate(
            self.problem_data,
            penalty_per_unassigned=self.base_config.unassigned_penalty,
            weight_distance=self.base_config.weight_distance,
            weight_time=self.base_config.weight_time
        )

        return solution
    def stage_1_minimize_fleet(self):
        print(f"--- STAGE 1: Fleet Minimization (Fast Mode) ---")
        print(f"Initial vehicles: {len(self.best_feasible_solution.routes)}")

        current_solution = self.best_feasible_solution.clone()

        stage_1_config = ALNSConfig(
            weight_distance=self.base_config.weight_distance,
            weight_time=self.base_config.weight_time,
            unassigned_penalty=100000.0,  # Very high to force feasibility
            iterations=3000,  # Increased for better fleet minimization
            segment_length=100,
            sigma_1=self.base_config.sigma_1,
            sigma_2=self.base_config.sigma_2,
            sigma_3=self.base_config.sigma_3,
            reaction_factor=self.base_config.reaction_factor,
            cooling_rate=0.99999,  # Match Stage 2 cooling
            w_param=0.05,
            eta=self.base_config.eta
        )

        initial_fleet_size = len(current_solution.routes)
        reductions = 0

        while len(current_solution.routes) > 0:
            target_vehicles = len(current_solution.routes) - 1
            print(f"Attempting fleet reduction: {len(current_solution.routes)} → {target_vehicles} vehicles...")

            # Destroy the smallest route
            destroyed_solution = self.remove_smallest_route(current_solution.clone())

            # Run ALNS with high pressure to insert the orphaned requests
            alns = ALNSSolver(
                self.problem_data,
                destroyed_solution,
                self.removal_ops,
                self.insertion_ops,
                stage_1_config
            )
            candidate_solution = alns.solve()

            # Check if ALNS successfully assigned all requests into the smaller fleet
            if len(candidate_solution.unassigned_requests) == 0:
                reductions += 1
                print(f"✅ SUCCESS: Fleet reduced to {target_vehicles} vehicles! ({reductions} reductions so far)")
                self.best_feasible_solution = candidate_solution.clone()
                current_solution = candidate_solution
            else:
                print(f"❌ FAILED: Cannot reduce below {len(current_solution.routes)} vehicles")
                print(f"Unassigned requests: {len(candidate_solution.unassigned_requests)}")
                break  # Stop stage 1

        final_fleet_size = len(self.best_feasible_solution.routes)
        print(f"Stage 1 complete: {initial_fleet_size} → {final_fleet_size} vehicles ({reductions} reductions)")
        return self.best_feasible_solution

    def stage_2_optimize_distance(self):
        print(f"\n--- STAGE 2: Distance/Time Optimization ---")
        print(f"Locked in fleet size: {len(self.best_feasible_solution.routes)} vehicles")
        print(f"Starting cost: {self.best_feasible_solution.global_cost:.2f}")
        print(f"Running {self.base_config.iterations} iterations...")
        
        # Run standard ALNS using the original config and normal weights
        alns = ALNSSolver(
            self.problem_data,
            self.best_feasible_solution,
            self.removal_ops,
            self.insertion_ops,
            self.base_config
        )

        final_solution = alns.solve()
        improvement = self.best_feasible_solution.global_cost - final_solution.global_cost
        improvement_pct = (improvement / self.best_feasible_solution.global_cost) * 100 if self.best_feasible_solution.global_cost > 0 else 0
        print(f"Stage 2 complete. Final Cost: {final_solution.global_cost:.2f}")
        print(f"Improvement: {improvement:.2f} ({improvement_pct:.2f}%)")
        return final_solution

    def solve(self):
        self.stage_1_minimize_fleet()
        return self.stage_2_optimize_distance()
