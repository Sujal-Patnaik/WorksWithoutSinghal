import random
from src.models.solution import Solution

def regret_k_insertion(solution: Solution, problem_data, config, k: int = 2, num_to_insert: int = None, max_noise: float=0.0):
    if num_to_insert is None:
        num_to_insert = len(solution.unassigned_requests)
        
    unplanned_requests = list(solution.unassigned_requests)
    inserted_count = 0
    
    while unplanned_requests and inserted_count < num_to_insert:
        best_regret = -float('inf')
        lowest_insertion_cost = float('inf') 
        
        win_request = None
        win_route = None
        win_p_idx = None
        win_d_idx = None
        
        for req_id in unplanned_requests:
            request = problem_data.requests[req_id]
            route_options = [] 
            for route in solution.routes:
                best_cost_in_route = float('inf')
                best_p_in_route = None
                best_d_in_route = None
                for p_idx in range(1, len(route.visits)):
                    for d_idx in range(p_idx + 1, len(route.visits) + 1):
                        is_feasible, cost_increase = route.test_insertion(
                            request, p_idx, d_idx, problem_data, config.weight_distance, config.weight_time
                        )                
                        if is_feasible:
                            if max_noise > 0:
                                noise_val = random.uniform(-max_noise,max_noise)
                                cost_increase=max(0.0,cost_increase+noise_val)
                            if cost_increase < best_cost_in_route:
                                best_cost_in_route=cost_increase
                                best_p_in_route=p_idx
                                best_d_in_route=d_idx

                if best_cost_in_route != float('inf'):
                    route_options.append({
                        'cost': best_cost_in_route,
                        'route': route,
                        'p_idx': best_p_in_route,
                        'd_idx': best_d_in_route
                    })
            if not route_options:
                continue
            route_options.sort(key=lambda x: x['cost'])
            
            best_option = route_options[0]
            best_route_cost = best_option['cost']
            if len(route_options) < k:
                regret = float('inf')
            else:
                regret = sum(
                    (route_options[i]['cost'] - best_route_cost) 
                    for i in range(1, k)
                )
            if regret > best_regret:
                best_regret = regret
                lowest_insertion_cost = best_route_cost
                
                win_request = request
                win_route = best_option['route']
                win_p_idx = best_option['p_idx']
                win_d_idx = best_option['d_idx']
            elif regret == best_regret and best_route_cost < lowest_insertion_cost:
                lowest_insertion_cost = best_route_cost                
                win_request = request
                win_route = best_option['route']
                win_p_idx = best_option['p_idx']
                win_d_idx = best_option['d_idx']
        if win_request is not None:
            win_route.insert_request(win_request, win_p_idx, win_d_idx)
            unplanned_requests.remove(win_request.request_id)
            solution.unassigned_requests.remove(win_request.request_id)
            inserted_count += 1
        else:
            break
            
    solution.evaluate(
        problem_data,
        weight_distance=config.weight_distance,
        weight_time=config.weight_time
    )
    return solution