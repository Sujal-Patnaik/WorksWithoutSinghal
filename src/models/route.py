import math
from src.models.request import Node
from src.models.request import Request

class Vehicle:
  def __init__(self, vehicle_id, speed, capacity, start_node_id, end_node_id):
    self.vehicle_id = vehicle_id
    self.capacity = capacity
    self.speed = speed
    self.start_node_id = start_node_id
    self.end_node_id = end_node_id

class ProblemData:
    def __init__(self, nodes, requests, vehicles):
        self.nodes = {n.node_id: n for n in nodes}
        self.requests = {r.request_id: r for r in requests}
        self.vehicles = {v.vehicle_id: v for v in vehicles}
        self.distance_matrix = self._build_distance_matrix()
        self.max_distance = max(max(row) for row in self.distance_matrix) if self.distance_matrix else 1.0

    def _build_distance_matrix(self):
        # Find the max node ID to size the matrix correctly
        max_id = max(self.nodes.keys()) if self.nodes else 0
        
        # Initialize a 2D list with zeros
        matrix = [[0.0] * (max_id + 1) for _ in range(max_id + 1)]
        
        for i_id, n_i in self.nodes.items():
            for j_id, n_j in self.nodes.items():
                if i_id != j_id:
                    dist = math.hypot(n_i.x - n_j.x, n_i.y - n_j.y)
                    matrix[i_id][j_id] = dist
        return matrix

class Route:
    def __init__(self, vehicle_id: int, problem_data: ProblemData):
        self.vehicle_id = vehicle_id
        vehicle = problem_data.vehicles[vehicle_id]
        self.visits = [vehicle.start_node_id, vehicle.end_node_id]
        self.assigned_requests = set()
    def insert_request(self, request: Request, pickup_idx: int, delivery_idx: int):
        self.visits.insert(pickup_idx, request.pickup.node_id)
        self.visits.insert(delivery_idx, request.delivery.node_id)
        self.assigned_requests.add(request.request_id)
    def remove_request(self, request: Request):
        self.visits.remove(request.pickup.node_id)
        self.visits.remove(request.delivery.node_id)
        self.assigned_requests.remove(request.request_id)
    def route_length(self,problem_data):
        dist = 0.0
        for i in range(len(self.visits)-1):
          dist += problem_data.distance_matrix[self.visits[i]][self.visits[i+1]]
        return dist
    def route_time(self, problem_data):  
        curr_time = 0.0
        for i in range(len(self.visits)-1):
            curr_node = problem_data.nodes[self.visits[i]]
            nxt_node = problem_data.nodes[self.visits[i+1]]
            travel_time = problem_data.distance_matrix[curr_node.node_id][nxt_node.node_id] / problem_data.vehicles[self.vehicle_id].speed
            arrival_time = curr_time + curr_node.service_time + travel_time
            arrival_time = max(arrival_time, nxt_node.TW_Early)           
            curr_time = arrival_time          
        return curr_time
    def test_insertion(self, request, pickup_idx : int, delivery_idx : int, problem_data, weight_distance, weight_time, curr_route_length=None, curr_route_time=None):
        dummy_list = list(self.visits)
        dummy_list.insert(pickup_idx, request.pickup.node_id)
        dummy_list.insert(delivery_idx, request.delivery.node_id)
        curr_load = 0.0
        curr_time = 0.0
        new_dist = 0.0
        for i in range(len(dummy_list)-1):
          curr_node = problem_data.nodes[dummy_list[i]]
          nxt_node = problem_data.nodes[dummy_list[i+1]]
          curr_load += curr_node.demand
          if(curr_load > problem_data.vehicles[self.vehicle_id].capacity):
             return False, float('inf')
          travel_time = problem_data.distance_matrix[curr_node.node_id][nxt_node.node_id] / problem_data.vehicles[self.vehicle_id].speed
          arrival_time = curr_node.service_time + travel_time + curr_time
          arrival_time = max(arrival_time, nxt_node.TW_Early)
          if(arrival_time > nxt_node.TW_Latest):
            return False, float('inf')
          curr_time = arrival_time
          new_dist += problem_data.distance_matrix[curr_node.node_id][nxt_node.node_id]
        
        if curr_route_length is None:
            curr_route_length = self.route_length(problem_data)
        if curr_route_time is None:
            curr_route_time = self.route_time(problem_data)

        dist_increases = new_dist - curr_route_length
        time_increases = curr_time - curr_route_time
        cost_increases = (weight_distance) * dist_increases + (weight_time) * time_increases
        return True, cost_increases
    
    def clone(self):
        new_route = Route.__new__(Route)
        new_route.vehicle_id = self.vehicle_id
        new_route.visits = list(self.visits) # Fast list slice
        new_route.assigned_requests = set(self.assigned_requests) # Fast set copy
        return new_route
