import random
import math
import copy

def _calculate_arrival_times(solution, problem_data):
    arrival_times = {}

    for route in solution.routes:
        curr_time = 0.0
        for i in range(len(route.visits) - 1):
            curr_node = problem_data.nodes[route.visits[i]]
            nxt_node = problem_data.nodes[route.visits[i + 1]]
            travel_time = (
                problem_data.distance_matrix[curr_node.node_id][nxt_node.node_id]/ problem_data.vehicles[route.vehicle_id].speed
            )
            arrival_time = curr_time + curr_node.service_time + travel_time
            arrival_time = max(arrival_time, nxt_node.TW_Early)
            arrival_times[nxt_node.node_id] = arrival_time
            curr_time = arrival_time
    return arrival_times

def _get_normalization_factors(problem_data):
    max_dist = max(
        max(row.values()) for row in problem_data.distance_matrix.values()
    ) if problem_data.distance_matrix else 1.0
    max_time = max(
        n.TW_Latest for n in problem_data.nodes.values()
    ) if problem_data.nodes else 1.0
    max_demand = max(
        abs(n.demand) for n in problem_data.nodes.values()
    ) if problem_data.nodes else 1.0
    return max(max_dist, 1.0), max(max_time, 1.0), max(max_demand, 1.0)

def _vehicle_relatedness(r1, r2):
    K1 = r1.feasible_fleet
    K2 = r2.feasible_fleet
    if not K1 or not K2:
        return 0.0  
    inter = len(set(K1) & set(K2))
    denom = min(len(K1), len(K2))
    if denom == 0:
        return 1.0
    return 1.0 - (inter / denom)

def calculate_relatedness(r1_id, r2_id, problem_data,arrival_times, norm_factors,phi, chi, psi, omega):
    r1 = problem_data.requests[r1_id]
    r2 = problem_data.requests[r2_id]
    max_dist, max_time, max_demand = norm_factors
    d_pickup = (
        problem_data.distance_matrix[r1.pickup.node_id][r2.pickup.node_id]/ max_dist
    )
    d_delivery = (
        problem_data.distance_matrix[r1.delivery.node_id][r2.delivery.node_id]/ max_dist
    )
    distance_term = d_pickup + d_delivery
    t_p1 = arrival_times.get(r1.pickup.node_id, r1.pickup.TW_Early)
    t_p2 = arrival_times.get(r2.pickup.node_id, r2.pickup.TW_Early)
    t_d1 = arrival_times.get(r1.delivery.node_id, r1.delivery.TW_Early)
    t_d2 = arrival_times.get(r2.delivery.node_id, r2.delivery.TW_Early)
    time_term = (abs(t_p1 - t_p2) + abs(t_d1 - t_d2)) / max_time
    capacity_term = abs(r1.pickup.demand - r2.pickup.demand) / max_demand
    vehicle_term = _vehicle_relatedness(r1, r2)
    return (
        phi * distance_term +
        chi * time_term +
        psi * capacity_term +
        omega * vehicle_term
    )


def shaw_removal(solution, problem_data, q, p=3.0, phi=9.0, chi=3.0, psi=2.0, omega=5.0):
    new_solution = copy.deepcopy(solution)
    assigned_requests = new_solution.get_all_assigned_requests()
    if len(assigned_requests) <= q:
        removed = list(assigned_requests)
        for route in new_solution.routes:
            vehicle = problem_data.vehicles[route.vehicle_id]
            route.visits = [vehicle.start_node_id, vehicle.end_node_id]
            route.assigned_requests.clear()
        new_solution.unassigned_requests.extend(removed)
        return new_solution, removed

    arrival_times = _calculate_arrival_times(new_solution, problem_data)
    norm_factors = _get_normalization_factors(problem_data)
    initial_r = random.choice(assigned_requests)
    removed = [initial_r] 

    while len(removed) < q:
        r = random.choice(removed)
        L = [req for req in assigned_requests if req not in removed]
        if not L:
            break
        L_with_scores = [
            (req, calculate_relatedness(
                r, req, problem_data,
                arrival_times, norm_factors,
                phi, chi, psi, omega
            ))
            for req in L
        ]

        L_with_scores.sort(key=lambda x: x[1])
        L_sorted = [x[0] for x in L_with_scores]

        y = random.random()
        idx = int((y ** p) * len(L_sorted))
        idx = min(idx, len(L_sorted) - 1)

        removed.append(L_sorted[idx]) 

    for req_id in removed:
        req_obj = problem_data.requests[req_id]
        for route in new_solution.routes:
            if req_id in route.assigned_requests:
                route.remove_request(req_obj)
                break

        if req_id not in new_solution.unassigned_requests:
            new_solution.unassigned_requests.append(req_id)

    new_solution.evaluate(problem_data)

    return new_solution, removed  



def random_removal(solution, problem_data, q):
    new_solution = copy.deepcopy(solution)
    assigned_requests = new_solution.get_all_assigned_requests()
    if len(assigned_requests) <= q:
        removed = list(assigned_requests)
        for route in new_solution.routes:
            vehicle = problem_data.vehicles[route.vehicle_id]
            route.visits = [vehicle.start_node_id, vehicle.end_node_id]
            route.assigned_requests.clear()
        new_solution.unassigned_requests.extend(removed)
        return new_solution, removed

    removed = random.sample(assigned_requests, q)

    for req_id in removed:
        req_obj = problem_data.requests[req_id]
        for route in new_solution.routes:
            if req_id in route.assigned_requests:
                route.remove_request(req_obj)
                break

        if req_id not in new_solution.unassigned_requests:
            new_solution.unassigned_requests.append(req_id)

    new_solution.evaluate(problem_data)
    return new_solution, removed



def _compute_request_cost(solution, problem_data, req_id):
    req_obj = problem_data.requests[req_id]
    for route in solution.routes:
        if req_id in route.assigned_requests:
            original_visits = list(route.visits)
            original_assigned = set(route.assigned_requests)
            original_cost = solution.global_cost
            route.remove_request(req_obj)
            solution.evaluate(problem_data)
            new_cost = solution.global_cost
            route.visits = original_visits
            route.assigned_requests = original_assigned
            solution.evaluate(problem_data)
            return original_cost - new_cost

    return 0.0

def worst_removal(solution, problem_data, q, p=3.0):
    new_solution = copy.deepcopy(solution)
    removed = []
    while q > 0:
        assigned_requests = new_solution.get_all_assigned_requests()
        if not assigned_requests:
            break
        cost_list = []
        for req_id in assigned_requests:
            cost_i = _compute_request_cost(new_solution, problem_data, req_id)
            cost_list.append((req_id, cost_i))

        cost_list.sort(key=lambda x: x[1], reverse=True)
        L = [x[0] for x in cost_list]
        y = random.random()
        idx = int((y ** p) * len(L))
        idx = min(idx, len(L) - 1)

        r = L[idx]
        req_obj = problem_data.requests[r]
        for route in new_solution.routes:
            if r in route.assigned_requests:
                route.remove_request(req_obj)
                break
        if r not in new_solution.unassigned_requests:
            new_solution.unassigned_requests.append(r)
        removed.append(r)
        q -= 1

    new_solution.evaluate(problem_data)

    return new_solution, removed