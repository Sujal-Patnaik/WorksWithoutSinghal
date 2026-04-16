from src.models.solution import Solution
from src.models.route import Route,Vehicle,ProblemData
from src.models.request import Node,Request

def build_initial_greedy_solution(solution: Solution, problem_data: ProblemData, config):
    unplanned_requests = list(solution.unassigned_requests)
    while(unplanned_requests):
        best_cost = float('inf')
        best_request = None
        best_route = None
        best_p_idx = None
        best_d_idx = None

        for req_id in unplanned_requests:
            request = problem_data.requests[req_id]
            for route in solution.routes:
                curr_len = route.route_length(problem_data)
                curr_t = route.route_time(problem_data)
                for p_idx in range(1,len(route.visits)):
                    for d_idx in range(p_idx+1, len(route.visits)+1):
                        is_feasible, cost_increases = route.test_insertion(request,p_idx,d_idx,problem_data,config.weight_distance,config.weight_time,curr_len,curr_t)
                        if(is_feasible and cost_increases<best_cost):
                            best_cost = cost_increases
                            best_request = request
                            best_route = route
                            best_p_idx = p_idx
                            best_d_idx = d_idx
        if best_request is not None:
            best_route.insert_request(best_request,best_p_idx,best_d_idx)
            unplanned_requests.remove(best_request.request_id)
            solution.unassigned_requests.remove(best_request.request_id)
            print("Inserted Request",best_request.request_id,"into Vehicle",
                  best_route.vehicle_id,"Cost :",best_cost)
        else:
            print("Stopping early : ",len(unplanned_requests),"requests are completely infeasible")
            break
    solution.evaluate(problem_data)
    return solution