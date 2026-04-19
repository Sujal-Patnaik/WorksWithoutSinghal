import random

from src.models.request import Node, Request
from src.models.route import ProblemData, Route, Vehicle
from src.models.solution import Solution
from src.operators.insertion import regret_k_insertion
from src.operators.removal import random_removal
from src.solver.alns import ALNSSolver
from src.utils.config import ALNSConfig


class _FixedPolicy:
    def begin_run(self):
        return

    def select(self, state_vector, num_removal_ops, num_insertion_ops, context):
        return 0, 0, 0

    def observe(self, state_vector, reward, accepted, is_new_best):
        return


def _build_single_request_problem():
    depot = Node(node_id=0, x=0.0, y=0.0, demand=0.0, TW_Early=0.0, TW_Latest=1000.0, service_time=0.0)
    pickup = Node(node_id=1, x=1.0, y=0.0, demand=1.0, TW_Early=0.0, TW_Latest=1000.0, service_time=0.0)
    delivery = Node(node_id=2, x=2.0, y=0.0, demand=-1.0, TW_Early=0.0, TW_Latest=1000.0, service_time=0.0)

    req = Request(request_id=1, pickup=pickup, delivery=delivery)
    vehicle = Vehicle(vehicle_id=0, speed=1.0, capacity=2.0, start_node_id=0, end_node_id=0)

    return ProblemData(nodes=[depot, pickup, delivery], requests=[req], vehicles=[vehicle])


def test_random_removal_uses_config_penalty():
    problem_data = _build_single_request_problem()
    route = Route(vehicle_id=0, problem_data=problem_data)
    route.insert_request(problem_data.requests[1], 1, 2)

    solution = Solution(routes=[route], unassigned_requests=[])
    cfg = ALNSConfig(unassigned_penalty=7777.0, weight_distance=1.0, weight_time=0.0)
    solution.evaluate(
        problem_data,
        penalty_per_unassigned=cfg.unassigned_penalty,
        weight_distance=cfg.weight_distance,
        weight_time=cfg.weight_time,
    )

    destroyed, removed = random_removal(solution, problem_data, q=1, config=cfg, rng=random.Random(0))

    assert removed == [1]
    assert len(destroyed.unassigned_requests) == 1
    assert destroyed.global_cost == 7777.0


def test_regret_k_insertion_uses_config_objective():
    problem_data = _build_single_request_problem()
    route = Route(vehicle_id=0, problem_data=problem_data)

    solution = Solution(routes=[route], unassigned_requests=[1])
    cfg = ALNSConfig(unassigned_penalty=5000.0, weight_distance=1.0, weight_time=0.0)

    repaired = regret_k_insertion(solution, problem_data, cfg, rng=random.Random(0))

    assert len(repaired.unassigned_requests) == 0
    assert repaired.total_distance == 4.0
    assert repaired.global_cost == 4.0


def test_alns_accumulates_operator_scores_on_acceptance():
    problem_data = _build_single_request_problem()

    initial_solution = Solution(routes=[], unassigned_requests=[])
    initial_solution.total_distance = 10.0
    initial_solution.total_time = 0.0
    initial_solution.global_cost = 50.0

    cfg = ALNSConfig(iterations=1, segment_length=10, sigma_1=33.0, sigma_2=9.0, sigma_3=13.0)

    def rem_op(solution, problem_data, q, config=None, rng=None):
        return solution.clone(), []

    def ins_op(solution, problem_data, config, k=2, num_to_insert=None, max_noise=0.0, rng=None):
        improved = solution.clone()
        improved.total_distance = max(0.0, solution.total_distance - 1.0)
        improved.total_time = solution.total_time
        improved.global_cost = solution.global_cost - 1.0
        return improved

    solver = ALNSSolver(
        problem_data=problem_data,
        initial_solution=initial_solution,
        removal_ops=[rem_op],
        insertion_ops=[ins_op],
        config=cfg,
        selection_policy=_FixedPolicy(),
        rng=random.Random(0),
    )

    solver.solve()

    assert solver.rem_scores[0] == cfg.sigma_1
    assert solver.ins_scores[0] == cfg.sigma_1
    assert solver.noise_scores[0] == cfg.sigma_1
