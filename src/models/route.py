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

class Route:
    def __init__(self, vehicle_id: int, problem_data: ProblemData):
        self.vehicle_id = vehicle_id
        vehicle = problem_data.vehicles[vehicle_id]
        self.visits = [vehicle.start_node_id, vehicle.end_node_id]
        self.assigned_requests = set()
        
