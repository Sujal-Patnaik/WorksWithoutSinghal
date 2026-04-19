import random
from src.models.solution import Solution

def regret_k_insertion(solution: Solution, problem_data, config, k: int = 2, num_to_insert: int = None, max_noise: float = 0.0, rng=None):
    rng = rng if rng is not None else random

    if num_to_insert is None:
        num_to_insert = len(solution.unassigned_requests)
    
    initial_unassigned = len(solution.unassigned_requests)
        
    unplanned_requests = list(solution.unassigned_requests)
    inserted_count = 0
    
    # ADD THIS: The Cache Dictionary
    cost_cache = {} 
    
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
                route_signature = (route.vehicle_id, tuple(route.visits))
                cache_key = (req_id, route_signature)
                
                if cache_key in cost_cache:
                    cached_cost, cached_p, cached_d = cost_cache[cache_key]
                    if cached_cost != float('inf'):
                        route_options.append({
                            'cost': cached_cost, 'route': route, 'p_idx': cached_p, 'd_idx': cached_d
                        })
                    continue # Skip the heavy math!

                # --- YOUR EXISTING HEAVY MATH LOOPS ---
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
                                noise_val = rng.uniform(-max_noise, max_noise)
                                cost_increase = max(0.0, cost_increase + noise_val)
                            if cost_increase < best_cost_in_route:
                                best_cost_in_route = cost_increase
                                best_p_in_route = p_idx
                                best_d_in_route = d_idx
                
                # ADD THIS: Save the result to the cache for next time
                cost_cache[cache_key] = (best_cost_in_route, best_p_in_route, best_d_in_route)

                if best_cost_in_route != float('inf'):
                    route_options.append({
                        'cost': best_cost_in_route, 'route': route, 'p_idx': best_p_in_route, 'd_idx': best_d_in_route
                    })
            
            # ... (Keep your existing Regret Sorting and winning logic here) ...
            if not route_options:
                continue
            
            route_options.sort(key=lambda x: x['cost'])
            best_option = route_options[0]
            best_route_cost = best_option['cost']
            
            if len(route_options) <= 1:
                regret = float('inf')
            else:
                max_rank = min(k, len(route_options))
                regret = sum((route_options[i]['cost'] - best_route_cost) for i in range(1, max_rank))
                
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

        # FINAL STEP: Insert and invalidate cache
        if win_request is not None:
            win_route.insert_request(win_request, win_p_idx, win_d_idx)
            unplanned_requests.remove(win_request.request_id)
            solution.unassigned_requests.remove(win_request.request_id)
            inserted_count += 1
            
            # Invalidate all cached insertion plans for the modified route.
            mod_vehicle_id = win_route.vehicle_id
            keys_to_delete = [cache_key for cache_key in cost_cache.keys() if cache_key[1][0] == mod_vehicle_id]
            for cache_key in keys_to_delete:
                del cost_cache[cache_key]
        else:
            break
            
    solution.evaluate(
        problem_data,
        penalty_per_unassigned=config.unassigned_penalty,
        weight_distance=config.weight_distance,
        weight_time=config.weight_time,
    )
    return solution