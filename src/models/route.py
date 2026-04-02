import copy
from src.models.request import Node
from src.models.request import Request

class Vehicle:
  def __init__(self, vehicle_id, capacity, start_node_id, end_node_id):
    self.vehicle_id = vehicle_id
    self.capacity = capacity
    self.start_node_id = start_node_id
    self.end_node_id = end_node_id

class ProblemData:
    def __init__(self, nodes, requests, vehicles):
        self.nodes = {n.node_id: n for n in nodes}
        self.requests = {r.request_id: r for r in requests}
        self.vehicles = {v.vehicle_id: v for v in vehicles}
        self.distance_matrix = self._build_distance_matrix()

    def _build_distance_matrix(self):
        matrix = {}
        for i_id, n_i in self.nodes.items():
            matrix[i_id] = {}
            for j_id, n_j in self.nodes.items():
                if i_id == j_id:
                    matrix[i_id][j_id] = 0.0
                else:
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
   
        
        
