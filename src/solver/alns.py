import math
import random
import copy

class ALNSSolver:
    def __init__(self,problem_data,initial_solution,removal_ops,insertion_ops,config):
        self.problem_data = problem_data
        self.best_solution = copy.deepcopy(initial_solution)
        self.current_solution = copy.deepcopy(initial_solution)
        self.config = config

        self.removal_ops = removal_ops
        self.insertion_ops = insertion_ops

        self.rem_weights = [1.0]*(len(removal_ops))
        self.ins_weights = [1.0]*(len(insertion_ops))

        self.rem_scores = [0.0]*(len(removal_ops))
        self.ins_scores = [0.0]*(len(insertion_ops))

        self.rem_attempts = [0]*len(removal_ops)
        self.ins_attempts = [0]*len(insertion_ops)
        self.visited_solutions = set()
    
    def hash_solutions(self,solution):
        routes = tuple(sorted(tuple(r.visits) for r in solution.routes))
        unassigned = tuple(sorted(solution.unassigned_requests))
        return hash((routes,unassigned))
    
    def calc_T_start(self):
        z_prime = self.current_solution.total_distance * self.config.weight_distance + \
               (self.current_solution.total_time * self.config.weight_time)
        if z_prime==0:
            z_prime=1000
        return ((-self.config.w_param*z_prime)/math.log(0.5))
    
    def select_operator(self,operators,weights):
        selected_op = random.choices(operators,weights=weights,k=1)[0]
        return selected_op,operators.index(selected_op)
    
    def update_segment_weights(self):
        r=self.config.reaction_factor
        for i in range(len(self.removal_ops)):
            if(self.rem_attempts[i]>0):
                self.rem_weights[i] = self.rem_weights[i]*(1-r) + r*(self.rem_scores/self.rem_attempts[i])
            self.rem_scores[i] = 0.0
            self.rem_attempts = 0
        
        for i in range(len(self.insertion_ops)):
            if(self.ins_attempts[i]>0):
                self.ins_weights[i] = self.ins_weights[i]*(1-r) + r*(self.ins_scores/self.ins_attempts[i])
            self.ins_scores[i] = 0.0
            self.ins_attempts = 0