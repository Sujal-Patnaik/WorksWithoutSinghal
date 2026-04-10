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
                self.rem_weights[i] = self.rem_weights[i]*(1-r) + r*(self.rem_scores[i]/self.rem_attempts[i])
            self.rem_scores[i] = 0.0
            self.rem_attempts[i] = 0
        
        for i in range(len(self.insertion_ops)):
            if(self.ins_attempts[i]>0):
                self.ins_weights[i] = self.ins_weights[i]*(1-r) + r*(self.ins_scores[i]/self.ins_attempts[i])
            self.ins_scores[i] = 0.0
            self.ins_attempts[i] = 0
    
    def solve(self):
        temperature=self.calc_T_start()
        self.visited_solutions.add(self.hash_solutions(self.current_solution))

        for i in range(1,self.config.iterations+1):
            rem_op, rem_idx=self.select_operator(self.removal_ops,self.rem_weights)
            ins_op, ins_idx= self.select_operator(self.insertion_ops,self.ins_weights)

            self.rem_attempts[rem_idx]+=1
            self.ins_attempts[ins_idx]+=1

            total_reqs=len(self.problem_data.requests)
            q=random.randint(max(1,int(0.1*total_reqs)),max(2,int(0.4*total_reqs)))   #To be updated later if needed for handling noise.
            
            destroyed_sol, removed_reqs=rem_op(self.current_solution, self.problem_data,q)
            repaired_sol= ins_op(destroyed_sol,self.problem_data)

            current_cost=self.current_solution.global_cost
            new_cost=repaired_sol.global_cost

            sol_hash=self.hash_solutions(repaired_sol)
            is_unvisited= sol_hash not in self.visited_solutions

            score=0
            accepted=False

            if new_cost<self.best_solution.global_cost:
                self.best_solution=copy.deepcopy(repaired_sol)
                self.current_solution=repaired_sol
                score=self.config.sigma_1
                accepted=True
            elif new_cost<current_cost:
                self.current_solution=repaired_sol
                if is_unvisited:
                    score=self.config.sigma_2
                accepted=True
            else:
                prob=math.exp(-(new_cost-current_cost)/temperature)
                if random.random()<prob:
                    self.current_solution=repaired_sol
                    if is_unvisited:
                        score=self.config.sigma_3
                    accepted=True
                
            self.rem_scores[rem_idx]+=score
            self.ins_scores[ins_idx]+=score

            if accepted:
                self.visited_solutions.add(sol_hash)
            
            if i%self.config.segment_length==0:
                self.update_segment_weights()
            
            temperature*=self.config.cooling_rate

            if i%500==0:
                print(f"Iteration {i}/{self.config.iterations} | Best Cost: {self.best_solution.global_cost:.2f} | Temp: {temperature:.2f}")

        return self.best_solution
            


