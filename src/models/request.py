import copy
class Node:
  def __init__(self, node_id, x, y, demand, TW_Early, TW_Latest, service_time):
    self.node_id = node_id
    self.x = x
    self.y = y
    self.demand = demand
    self.TW_Early = TW_Early
    self.TW_Latest = TW_Latest
    self.service_time = service_time

class Request:
  def __init__(self, request_id, pickup, delivery, feasible_fleet=None):
    self.request_id = request_id
    self.pickup = pickup
    self.delivery = delivery
    self.feasible_fleet = feasible_fleet
  def __deepcopy__(self,memo):
    new_request = Request(request_id = self.request_id, pickup = self.pickup, delivery = self.delivery,
                          feasible_fleet = copy.deepcopy(self.feasible_fleet,memo))
    memo[id(self)] = new_request
    return new_request
