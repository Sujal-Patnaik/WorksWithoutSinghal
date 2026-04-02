import copy
from src.models.route import Route

class Solution:
    def __init__(self, routes=None, unassigned_requests=None):
        self.routes = routes if routes is not None else []
        self.unassigned_requests = unassigned_requests if unassigned_requests is not None else []
        
        self.total_distance = 0.0
        self.total_time = 0.0
        self.unassigned_penalty = 0.0
        self.global_cost = 0.0

    def evaluate(self, problem_data, penalty_per_unassigned=10000.0, weight_distance=1.0, weight_time=1.0):
        self.total_distance = 0.0
        self.total_time = 0.0
        
        for route in self.routes:
            if len(route.visits) > 2:
                self.total_distance += route.route_length(problem_data)
                self.total_time += route.route_time(problem_data)
        
        self.unassigned_penalty = len(self.unassigned_requests) * penalty_per_unassigned
        
        self.global_cost = (self.total_distance * weight_distance) + (self.total_time * weight_time) + self.unassigned_penalty
        
        return self.global_cost

    def get_all_assigned_requests(self):
        assigned = []
        for route in self.routes:
            assigned.extend(list(route.assigned_requests))
        return assigned

    def __deepcopy__(self, memo):
        new_solution = Solution(
            routes=copy.deepcopy(self.routes, memo),
            unassigned_requests=copy.copy(self.unassigned_requests)
        )
        new_solution.total_distance = self.total_distance
        new_solution.total_time = self.total_time
        new_solution.unassigned_penalty = self.unassigned_penalty
        new_solution.global_cost = self.global_cost
        
        memo[id(self)] = new_solution
        return new_solution
