import math
import random

from src.solver.policies import (
    PolicyContext,
    RouletteSelectionPolicy,
)

class ALNSSolver:
    def __init__(
        self,
        problem_data,
        initial_solution,
        removal_ops,
        insertion_ops,
        config,
        selection_policy=None,
        iteration_logger=None,
        stage_name="stage2",
        rng=None,
    ):
        self.problem_data = problem_data
        self.best_solution = initial_solution.clone()
        self.current_solution = initial_solution.clone()
        self.config = config
        self.stage_name = stage_name

        self.removal_ops = removal_ops
        self.insertion_ops = insertion_ops

        self.rem_weights = [1.0]*(len(removal_ops))
        self.ins_weights = [1.0]*(len(insertion_ops))

        self.rem_scores = [0.0]*(len(removal_ops))
        self.ins_scores = [0.0]*(len(insertion_ops))

        self.rem_attempts = [0]*len(removal_ops)
        self.ins_attempts = [0]*len(insertion_ops)

        self.noise_weights=[1.0,1.0]
        self.noise_scores=[0.0,0.0]
        self.noise_attempts=[0,0]

        self.visited_solutions = set()
        self.iteration_logger = iteration_logger

        self.rng = rng if rng is not None else random
        self.selection_policy = selection_policy if selection_policy is not None else RouletteSelectionPolicy(self.rng)
    
    def solution_key(self, solution):
        routes = tuple(sorted(tuple(r.visits) for r in solution.routes))
        unassigned = tuple(sorted(solution.unassigned_requests))
        return routes, unassigned
    
    def calc_T_start(self):
        z_prime = self.current_solution.total_distance * self.config.weight_distance + \
               (self.current_solution.total_time * self.config.weight_time)
        if z_prime==0:
            z_prime=1000
        return ((-self.config.w_param*z_prime)/math.log(0.5))

    def build_state_vector(self, temperature, iteration):
        total_reqs = max(1, len(self.problem_data.requests))
        progress = iteration / max(1, self.config.iterations)
        assigned_ratio = 1.0 - (len(self.current_solution.unassigned_requests) / total_reqs)
        unassigned_ratio = len(self.current_solution.unassigned_requests) / total_reqs

        return [
            progress,
            min(temperature / 10000.0, 1.0),
            assigned_ratio,
            unassigned_ratio,
            self.current_solution.total_distance / max(1.0, total_reqs),
            self.current_solution.total_time / max(1.0, total_reqs),
            self.current_solution.global_cost / max(1.0, total_reqs),
            len(self.current_solution.routes) / max(1.0, total_reqs),
            1.0 if self.stage_name == "stage1" else 0.0,
            1.0 if self.stage_name == "stage2" else 0.0,
        ]

    def compute_reward(self, prev_solution, new_solution):
        prev_dist = max(1e-9, prev_solution.total_distance)
        prev_cost = max(1e-9, prev_solution.global_cost)
        total_reqs = max(1, len(self.problem_data.requests))

        distance_gain = (prev_solution.total_distance - new_solution.total_distance) / prev_dist
        cost_gain = (prev_solution.global_cost - new_solution.global_cost) / prev_cost
        unassigned_gain = (
            len(prev_solution.unassigned_requests) - len(new_solution.unassigned_requests)
        ) / total_reqs

        return (0.7 * distance_gain) + (0.2 * cost_gain) + (0.1 * unassigned_gain)
    
    def select_operator(self,operators,weights):
        selected_op = self.rng.choices(operators,weights=weights,k=1)[0]
        return selected_op,operators.index(selected_op)

    def _apply_removal(self, rem_op, solution, q):
        try:
            return rem_op(solution, self.problem_data, q, config=self.config, rng=self.rng)
        except TypeError:
            return rem_op(solution, self.problem_data, q)

    def _apply_insertion(self, ins_op, solution, max_noise_val):
        try:
            return ins_op(solution, self.problem_data, self.config, max_noise=max_noise_val, rng=self.rng)
        except TypeError:
            return ins_op(solution, self.problem_data, self.config, max_noise=max_noise_val)
    
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

        for i in range(2):
            if self.noise_attempts[i]>0:
                self.noise_weights[i]=self.noise_weights[i]*(1-r) + r*(self.noise_scores[i]/self.noise_attempts[i])
            self.noise_scores[i]=0.0
            self.noise_attempts[i]=0
    
    def solve(self):
        temperature=self.calc_T_start()
        self.visited_solutions.add(self.solution_key(self.current_solution))
        self.selection_policy.begin_run()
        
        # Diagnostics
        improvement_count = 0
        accepted_count = 0
        same_cost_count = 0
        worse_count = 0
        unassigned_count = 0
        iterations_stuck = 0  # Track iterations without improvement

        for i in range(1,self.config.iterations+1):
            prev_solution_snapshot = self.current_solution.clone()
            state_vector = self.build_state_vector(temperature, i)
            policy_context = PolicyContext(
                rem_weights=self.rem_weights,
                ins_weights=self.ins_weights,
                noise_weights=self.noise_weights,
                iteration=i,
                stage=self.stage_name,
            )

            rem_idx, ins_idx, noise_idx = self.selection_policy.select(
                state_vector,
                len(self.removal_ops),
                len(self.insertion_ops),
                policy_context,
            )

            if rem_idx < 0 or rem_idx >= len(self.removal_ops):
                rem_idx = self.rng.randrange(len(self.removal_ops))
            if ins_idx < 0 or ins_idx >= len(self.insertion_ops):
                ins_idx = self.rng.randrange(len(self.insertion_ops))
            if noise_idx not in (0, 1):
                noise_idx = self.rng.choice([0, 1])

            rem_op = self.removal_ops[rem_idx]
            ins_op = self.insertion_ops[ins_idx]
            use_noise=(noise_idx==1)

            self.rem_attempts[rem_idx]+=1
            self.ins_attempts[ins_idx]+=1
            self.noise_attempts[noise_idx]+=1

            total_reqs=len(self.problem_data.requests)
            # Removal size: 4-12% for balance
            q=self.rng.randint(max(1,int(0.04*total_reqs)),max(1,int(0.12*total_reqs)))
            
            destroyed_sol, removed_reqs = self._apply_removal(rem_op, self.current_solution, q)
            max_noise_val=self.config.eta*self.problem_data.max_distance if use_noise else 0.0
            repaired_sol = self._apply_insertion(ins_op, destroyed_sol, max_noise_val)

            current_cost=self.current_solution.global_cost
            new_cost=repaired_sol.global_cost

            sol_hash=self.solution_key(repaired_sol)
            is_unvisited= sol_hash not in self.visited_solutions

            score=0
            accepted=False
            is_new_best = new_cost < self.best_solution.global_cost

            if is_new_best:
                self.best_solution=repaired_sol.clone()
                self.current_solution=repaired_sol
                score=self.config.sigma_1
                accepted=True
                improvement_count += 1
                iterations_stuck = 0
            elif new_cost<current_cost:
                self.current_solution=repaired_sol
                if is_unvisited:
                    score=self.config.sigma_2
                accepted=True
                improvement_count += 1
                iterations_stuck = 0
            else:
                # DIVERSIFICATION: if stuck, increase temperature temporarily to accept worse solutions
                effective_temp = temperature
                if iterations_stuck > 1000:
                    effective_temp = temperature * 2.0  # Boost temperature for diversity
                    
                prob=math.exp(-(new_cost-current_cost)/effective_temp) if effective_temp > 0 else 0
                if self.rng.random()<prob:
                    self.current_solution=repaired_sol
                    if is_unvisited:
                        score=self.config.sigma_3
                    accepted=True
                    worse_count += 1
                    iterations_stuck = 0
                else:
                    same_cost_count += 1
                    iterations_stuck += 1
                
            if len(repaired_sol.unassigned_requests) > 0:
                unassigned_count += 1
                
            if accepted:
                accepted_count += 1
                self.visited_solutions.add(sol_hash)
                self.rem_scores[rem_idx] += score
                self.ins_scores[ins_idx] += score
                self.noise_scores[noise_idx] += score

            reward = self.compute_reward(prev_solution_snapshot, repaired_sol)
            self.selection_policy.observe(
                state_vector,
                reward,
                accepted,
                is_new_best,
            )

            if self.iteration_logger is not None:
                self.iteration_logger.log(
                    {
                        "stage": self.stage_name,
                        "iteration": i,
                        "temperature": temperature,
                        "current_cost": current_cost,
                        "new_cost": new_cost,
                        "best_cost": self.best_solution.global_cost,
                        "current_distance": self.current_solution.total_distance,
                        "best_distance": self.best_solution.total_distance,
                        "accepted": int(accepted),
                        "reward": reward,
                        "rem_idx": rem_idx,
                        "ins_idx": ins_idx,
                        "noise_idx": noise_idx,
                        "q_removed": q,
                        "unassigned": len(self.current_solution.unassigned_requests),
                        "is_unvisited": int(is_unvisited),
                    }
                )
            
            if i%self.config.segment_length==0:
                self.update_segment_weights()
            
            temperature*=self.config.cooling_rate

            # Smart logging: show progress proportionally
            log_interval = max(100, self.config.iterations // 10)  # Show ~10 updates
            if i%log_interval==0:
                print(f"Iteration {i}/{self.config.iterations} | Best Cost: {self.best_solution.global_cost:.2f} | Temp: {temperature:.2f} | Stuck: {iterations_stuck}")
        
        # Final diagnostics
        print(f"\n=== ALNS Diagnostics ===")
        print(f"Improvements found: {improvement_count}")
        print(f"Accepted moves: {accepted_count} ({100*accepted_count/self.config.iterations:.1f}%)")
        print(f"Worse solutions accepted: {worse_count}")
        print(f"Rejected same-cost moves: {same_cost_count}")
        print(f"Solutions with unassigned: {unassigned_count}")
        print(f"=== End Diagnostics ===")

        return self.best_solution
            


