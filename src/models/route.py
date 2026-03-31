import copy
from src.models.request import Node
from src.models.request import Request

class Vehicle:
  def __init__(self, vehicle_id, capacity, start_node_id, end_node_id):
    self.vehicle_id = vehicle_id
    self.capacity = capacity
    self.start_node_id = start_node_id
    self.end_node_id = end_node_id
