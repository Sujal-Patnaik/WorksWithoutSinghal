from src.models.route import Route
from src.models.request import Request
class Solution:
    def __init__(self, routes:list[Route]=None, unassigned_requests:list[int]=None):
        self.routes = routes if routes is not None else []
        self.unassigned_requests = set(unassigned_requests) if unassigned_requests is not None else set()
        
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

    def clone(self):
        new_sol = Solution.__new__(Solution)
        new_sol.routes = [r.clone() for r in self.routes]
        new_sol.unassigned_requests = set(self.unassigned_requests)
        new_sol.total_distance = self.total_distance
        new_sol.total_time = self.total_time
        new_sol.unassigned_penalty = self.unassigned_penalty
        new_sol.global_cost = self.global_cost
        return new_sol
