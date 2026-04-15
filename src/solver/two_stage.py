import copy
from src.solver.alns import ALNSSolver

class TwoStageSolver:
    def __init__(self, problem_data, initial_solution, removal_ops, insertion_ops, config):
        self.problem_data = problem_data
        self.initial_solution = initial_solution
        self.removal_ops = removal_ops
        self.insertion_ops = insertion_ops
        self.base_config = config

        self.best_feasible_solution = copy.deepcopy(initial_solution)

    def remove_smallest_route(self, solution):
        if not solution.routes:
            return solution

        route_to_remove= min(solution.routes, key=lambda r: len(r.assigned_requests))

        solution.unassigned_requests.extend(list(route_to_remove.assigned_requests))
        solution.routes.remove(route_to_remove)

        solution.evaluate(
            self.problem_data,
            penalty_per_unassigned=self.base_config.unassigned_penalty,
            weight_distance=self.base_config.weight_distance,
            weight_time=self.base_config.weight_time
        )

        return solution
    def stage_1_minimize_fleet(self):
        print(f"--- STAGE 1: Fleet Minimization ---")
        print(f"Initial vehicles: {len(self.best_feasible_solution.routes)}")
        
        current_solution = copy.deepcopy(self.best_feasible_solution)
        
       
        stage_1_config = copy.deepcopy(self.base_config)
        stage_1_config.unassigned_penalty = 100000.0  
        stage_1_config.w_param = 0.35                 
        stage_1_config.cooling_rate = 0.9999          
        
        stage_1_config.iterations = min(5000, self.base_config.iterations) 

        while len(current_solution.routes) > 0:
            target_vehicles = len(current_solution.routes) - 1
            print(f"\nAttempting to reduce fleet to {target_vehicles} vehicles...")
            
            # Destroy the smallest route
            destroyed_solution = self._remove_smallest_route(copy.deepcopy(current_solution))
            
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
                print(f"SUCCESS: Fleet reduced to {target_vehicles} vehicles!")
                self.best_feasible_solution = copy.deepcopy(candidate_solution)
                current_solution = candidate_solution
            else:
                print(f"FAILED: Could not fit all requests into {target_vehicles} vehicles.")
                print(f"Leftover unassigned requests: {len(candidate_solution.unassigned_requests)}")
                break # Stop stage 1, revert to the last known best_feasible_solution

        return self.best_feasible_solution

    def stage_2_optimize_distance(self):
        print(f"\n--- STAGE 2: Distance/Time Optimization ---")
        print(f"Locked in fleet size: {len(self.best_feasible_solution.routes)} vehicles")
        
        # Run standard ALNS using the original config and normal weights
        alns = ALNSSolver(
            self.problem_data, 
            self.best_feasible_solution, 
            self.removal_ops, 
            self.insertion_ops, 
            self.base_config
        )
        
        final_solution = alns.solve()
        print(f"Optimization complete. Final Cost: {final_solution.global_cost:.2f}")
        return final_solution

    def solve(self):
        self.stage_1_minimize_fleet()
        return self.stage_2_optimize_distance()
