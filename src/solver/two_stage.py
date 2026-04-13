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
